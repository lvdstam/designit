"""Language Server Protocol server for DesignIt."""

from __future__ import annotations

import logging
from typing import Any

from lsprotocol import types as lsp
from pygls.lsp.server import LanguageServer
from pygls.workspace import TextDocument

from designit.model.base import ValidationSeverity
from designit.parser.parser import ParseError
from designit.semantic.analyzer import analyze_string
from designit.semantic.validator import validate

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("designit-lsp")

# Create the language server
server = LanguageServer("designit-language-server", "v0.1.0")


# Document state cache
_document_cache: dict[str, Any] = {}


def _get_diagnostics(doc: TextDocument) -> list[lsp.Diagnostic]:
    """Get diagnostics for a document."""
    diagnostics: list[lsp.Diagnostic] = []

    try:
        # Parse the document
        design = analyze_string(doc.source, doc.uri)

        # Validate
        messages = validate(design)

        # Convert to LSP diagnostics
        for msg in messages:
            severity_map = {
                ValidationSeverity.ERROR: lsp.DiagnosticSeverity.Error,
                ValidationSeverity.WARNING: lsp.DiagnosticSeverity.Warning,
                ValidationSeverity.INFO: lsp.DiagnosticSeverity.Information,
            }

            line = (msg.line or 1) - 1  # LSP uses 0-based lines
            diagnostics.append(
                lsp.Diagnostic(
                    range=lsp.Range(
                        start=lsp.Position(line=line, character=0),
                        end=lsp.Position(line=line, character=100),
                    ),
                    message=msg.message,
                    severity=severity_map.get(msg.severity, lsp.DiagnosticSeverity.Information),
                    source="designit",
                )
            )

        # Cache the parsed document
        _document_cache[doc.uri] = design

    except ParseError as e:
        line = (e.line or 1) - 1
        column = (e.column or 1) - 1
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=line, character=column),
                    end=lsp.Position(line=line, character=column + 10),
                ),
                message=f"Parse error: {e.message}",
                severity=lsp.DiagnosticSeverity.Error,
                source="designit",
            )
        )

    except Exception as e:
        diagnostics.append(
            lsp.Diagnostic(
                range=lsp.Range(
                    start=lsp.Position(line=0, character=0),
                    end=lsp.Position(line=0, character=0),
                ),
                message=f"Internal error: {str(e)}",
                severity=lsp.DiagnosticSeverity.Error,
                source="designit",
            )
        )

    return diagnostics


@server.feature(lsp.TEXT_DOCUMENT_DID_OPEN)
def did_open(params: lsp.DidOpenTextDocumentParams) -> None:
    """Handle document open."""
    doc = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = _get_diagnostics(doc)
    server.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=doc.uri, diagnostics=diagnostics)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_CHANGE)
def did_change(params: lsp.DidChangeTextDocumentParams) -> None:
    """Handle document change."""
    doc = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = _get_diagnostics(doc)
    server.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=doc.uri, diagnostics=diagnostics)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_SAVE)
def did_save(params: lsp.DidSaveTextDocumentParams) -> None:
    """Handle document save."""
    doc = server.workspace.get_text_document(params.text_document.uri)
    diagnostics = _get_diagnostics(doc)
    server.text_document_publish_diagnostics(
        lsp.PublishDiagnosticsParams(uri=doc.uri, diagnostics=diagnostics)
    )


@server.feature(lsp.TEXT_DOCUMENT_DID_CLOSE)
def did_close(params: lsp.DidCloseTextDocumentParams) -> None:
    """Handle document close."""
    uri = params.text_document.uri
    if uri in _document_cache:
        del _document_cache[uri]
    server.text_document_publish_diagnostics(lsp.PublishDiagnosticsParams(uri=uri, diagnostics=[]))


# ============================================
# Completion
# ============================================

# Keywords and their descriptions
KEYWORDS = {
    # Top-level
    "import": "Import another .dit file",
    "dfd": "Define a Data Flow Diagram",
    "erd": "Define an Entity-Relationship Diagram",
    "std": "Define a State Transition Diagram",
    "scd": "Define a System Context Diagram",
    "structure": "Define a Structure Chart",
    "datadict": "Define a Data Dictionary",
    # DFD elements
    "external": "Define an external entity",
    "process": "Define a process",
    "datastore": "Define a data store",
    "flow": "Define a data flow",
    # SCD elements
    "system": "Define the system being modeled (SCD)",
    # ERD elements
    "entity": "Define an entity",
    "relationship": "Define a relationship",
    # STD elements
    "state": "Define a state",
    "transition": "Define a transition",
    "initial": "Set initial state",
    # Structure elements
    "module": "Define a module",
    "calls": "Specify called modules",
    "data_couple": "Specify data coupling",
    "control_couple": "Specify control coupling",
    # Common
    "description": "Add a description",
    "TBD": "Placeholder (to be defined)",
}

TYPES = ["string", "integer", "decimal", "boolean", "datetime", "date", "time", "binary"]

CONSTRAINTS = ["pk", "fk", "unique", "not null", "pattern", "optional", "min", "max"]


@server.feature(lsp.TEXT_DOCUMENT_COMPLETION)
def completion(params: lsp.CompletionParams) -> lsp.CompletionList:
    """Provide completion suggestions."""
    doc = server.workspace.get_text_document(params.text_document.uri)
    position = params.position

    # Get the current line
    lines = doc.source.split("\n")
    if position.line >= len(lines):
        return lsp.CompletionList(is_incomplete=False, items=[])

    line = lines[position.line]
    line_prefix = line[: position.character].strip()

    items: list[lsp.CompletionItem] = []

    # Context-aware completions
    if line_prefix.endswith(":"):
        # After colon - likely expecting a type or value
        for type_name in TYPES:
            items.append(
                lsp.CompletionItem(
                    label=type_name,
                    kind=lsp.CompletionItemKind.TypeParameter,
                    detail="Built-in type",
                )
            )
    elif "[" in line_prefix and "]" not in line_prefix:
        # Inside constraints
        for constraint in CONSTRAINTS:
            items.append(
                lsp.CompletionItem(
                    label=constraint,
                    kind=lsp.CompletionItemKind.Keyword,
                    detail="Constraint",
                )
            )
    else:
        # General keyword completions
        for keyword, description in KEYWORDS.items():
            items.append(
                lsp.CompletionItem(
                    label=keyword,
                    kind=lsp.CompletionItemKind.Keyword,
                    detail=description,
                    documentation=lsp.MarkupContent(
                        kind=lsp.MarkupKind.Markdown,
                        value=f"**{keyword}**\n\n{description}",
                    ),
                )
            )

    return lsp.CompletionList(is_incomplete=False, items=items)


# ============================================
# Hover
# ============================================

HOVER_DOCS = {
    "scd": """# System Context Diagram (SCD)

An SCD shows the system boundary and its interactions with external entities.

```designit
scd OrderSystem {
    system OrderService { description: "Main order processing system" }
    external Customer { description: "End user placing orders" }
    external PaymentGateway { description: "External payment processor" }
    datastore InventoryDB { description: "Product inventory database" }
    flow PlaceOrder: Customer -> OrderService
    flow ProcessPayment: OrderService <-> PaymentGateway
    flow CheckStock: OrderService -> InventoryDB
}
```
""",
    "dfd": """# Data Flow Diagram (DFD)

A DFD shows the flow of data through a system.

```designit
dfd SystemName {
    external User { description: "System user" }
    process ProcessData { description: "Processes input" }
    datastore Database { description: "Stores data" }
    flow InputData: User -> ProcessData
}
```
""",
    "erd": """# Entity-Relationship Diagram (ERD)

An ERD shows entities and their relationships.

```designit
erd DataModel {
    entity User {
        id: integer [pk]
        name: string
    }
    entity Order {
        id: integer [pk]
        user_id: integer [fk -> User.id]
    }
    relationship places: User -1:n-> Order
}
```
""",
    "std": """# State Transition Diagram (STD)

An STD shows states and transitions between them.

```designit
std OrderLifecycle {
    initial: Pending
    state Pending { description: "Order placed" }
    state Confirmed { description: "Order confirmed" }
    transition confirm: Pending -> Confirmed {
        trigger: "payment_received"
    }
}
```
""",
    "structure": """# Structure Chart

A structure chart shows module hierarchy and calls.

```designit
structure MainProgram {
    module Main {
        calls: [ValidateInput, ProcessData]
    }
    module ValidateInput {
        data_couple: InputData
    }
    module ProcessData { ... }
}
```
""",
    "datadict": """# Data Dictionary

Defines data types and structures.

```designit
datadict {
    UserData = {
        name: string
        email: string [pattern: ".*@.*"]
        age: integer [optional]
    }
    Status = "active" | "inactive" | "pending"
    UserList = UserData[] [min: 0, max: 100]
}
```
""",
}


@server.feature(lsp.TEXT_DOCUMENT_HOVER)
def hover(params: lsp.HoverParams) -> lsp.Hover | None:
    """Provide hover information."""
    doc = server.workspace.get_text_document(params.text_document.uri)
    position = params.position

    # Get the word at the position
    lines = doc.source.split("\n")
    if position.line >= len(lines):
        return None

    line = lines[position.line]

    # Simple word extraction
    start = position.character
    end = position.character

    while start > 0 and line[start - 1].isalnum():
        start -= 1
    while end < len(line) and line[end].isalnum():
        end += 1

    word = line[start:end]

    # Check for documentation
    if word in HOVER_DOCS:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.Markdown,
                value=HOVER_DOCS[word],
            ),
            range=lsp.Range(
                start=lsp.Position(line=position.line, character=start),
                end=lsp.Position(line=position.line, character=end),
            ),
        )

    if word in KEYWORDS:
        return lsp.Hover(
            contents=lsp.MarkupContent(
                kind=lsp.MarkupKind.Markdown,
                value=f"**{word}**\n\n{KEYWORDS[word]}",
            ),
            range=lsp.Range(
                start=lsp.Position(line=position.line, character=start),
                end=lsp.Position(line=position.line, character=end),
            ),
        )

    return None


# ============================================
# Document Symbols
# ============================================


def _make_symbol(name: str, kind: lsp.SymbolKind) -> lsp.DocumentSymbol:
    """Create a DocumentSymbol with default range."""
    return lsp.DocumentSymbol(
        name=name,
        kind=kind,
        range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)),
        selection_range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)),
    )


def _make_symbol_with_children(
    name: str, kind: lsp.SymbolKind, children: list[lsp.DocumentSymbol]
) -> lsp.DocumentSymbol:
    """Create a DocumentSymbol with children and default range."""
    return lsp.DocumentSymbol(
        name=name,
        kind=kind,
        range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)),
        selection_range=lsp.Range(lsp.Position(0, 0), lsp.Position(0, 0)),
        children=children,
    )


def _collect_dfd_symbols(design: Any) -> list[lsp.DocumentSymbol]:
    """Collect document symbols for all DFDs."""
    symbols: list[lsp.DocumentSymbol] = []
    for name, dfd in design.dfds.items():
        children: list[lsp.DocumentSymbol] = []
        for ext_name in dfd.externals:
            children.append(_make_symbol(ext_name, lsp.SymbolKind.Interface))
        for proc_name in dfd.processes:
            children.append(_make_symbol(proc_name, lsp.SymbolKind.Function))
        symbols.append(_make_symbol_with_children(f"DFD: {name}", lsp.SymbolKind.Module, children))
    return symbols


def _collect_erd_symbols(design: Any) -> list[lsp.DocumentSymbol]:
    """Collect document symbols for all ERDs."""
    symbols: list[lsp.DocumentSymbol] = []
    for name, erd in design.erds.items():
        children = [_make_symbol(entity_name, lsp.SymbolKind.Class) for entity_name in erd.entities]
        symbols.append(_make_symbol_with_children(f"ERD: {name}", lsp.SymbolKind.Module, children))
    return symbols


def _collect_std_symbols(design: Any) -> list[lsp.DocumentSymbol]:
    """Collect document symbols for all STDs."""
    symbols: list[lsp.DocumentSymbol] = []
    for name, std in design.stds.items():
        children = [_make_symbol(state_name, lsp.SymbolKind.Enum) for state_name in std.states]
        symbols.append(_make_symbol_with_children(f"STD: {name}", lsp.SymbolKind.Module, children))
    return symbols


def _collect_scd_symbols(design: Any) -> list[lsp.DocumentSymbol]:
    """Collect document symbols for all SCDs."""
    symbols: list[lsp.DocumentSymbol] = []
    for name, scd in design.scds.items():
        children: list[lsp.DocumentSymbol] = []
        if scd.system:
            children.append(_make_symbol(scd.system.name, lsp.SymbolKind.Class))
        for ext_name in scd.externals:
            children.append(_make_symbol(ext_name, lsp.SymbolKind.Interface))
        for ds_name in scd.datastores:
            children.append(_make_symbol(ds_name, lsp.SymbolKind.Variable))
        symbols.append(_make_symbol_with_children(f"SCD: {name}", lsp.SymbolKind.Module, children))
    return symbols


@server.feature(lsp.TEXT_DOCUMENT_DOCUMENT_SYMBOL)
def document_symbol(params: lsp.DocumentSymbolParams) -> list[lsp.DocumentSymbol]:
    """Provide document symbols for outline view."""
    uri = params.text_document.uri
    design = _document_cache.get(uri)

    if not design:
        return []

    symbols: list[lsp.DocumentSymbol] = []
    symbols.extend(_collect_dfd_symbols(design))
    symbols.extend(_collect_erd_symbols(design))
    symbols.extend(_collect_std_symbols(design))
    symbols.extend(_collect_scd_symbols(design))

    return symbols


def start_server() -> None:
    """Start the language server."""
    logger.info("Starting DesignIt Language Server")
    server.start_io()


if __name__ == "__main__":
    start_server()
