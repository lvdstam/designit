"""Markdown document generator with template expression support.

This module provides:
1. Template expression parsing for markdown blocks
2. Template validation against the semantic model
3. Document generation with diagram embedding
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from designit.model.base import DesignDocument


class TemplateExprType(Enum):
    """Types of template expressions."""

    DIAGRAM = "diagram"  # {{diagram:DiagramName}}
    PROPERTY = "property"  # {{Diagram.Element.property}}
    EACH_START = "each_start"  # {{#each Diagram.collection}}
    EACH_END = "each_end"  # {{/each}}
    TEXT = "text"  # Plain text between expressions


@dataclass
class TemplateExpr:
    """A parsed template expression."""

    expr_type: TemplateExprType
    raw: str  # The raw text including delimiters
    content: str  # The content inside delimiters (without {{ }})

    # For DIAGRAM: diagram_name
    diagram_name: str | None = None

    # For PROPERTY: parts like ["Diagram", "Element", "property"]
    property_path: list[str] | None = None

    # For EACH_START: diagram_name and collection_name
    each_diagram: str | None = None
    each_collection: str | None = None

    # Source location for error reporting
    line: int | None = None
    column: int | None = None


@dataclass
class TemplateError:
    """An error found during template parsing or validation."""

    message: str
    line: int | None = None
    column: int | None = None
    source_file: str | None = None


class TemplateParser:
    """Parses template expressions from markdown content.

    Supported expressions:
    - {{diagram:DiagramName}} - Insert a diagram
    - {{Diagram.Element.property}} - Access element property
    - {{property}} - Access property in current iteration context
    - {{#each Diagram.collection}} - Start iteration
    - {{/each}} - End iteration
    """

    # Regex patterns for template expressions
    # Matches {{ ... }} but not escaped \{{ or \}}
    EXPR_PATTERN = re.compile(r"(?<!\\)\{\{(.+?)(?<!\\)\}\}")

    # Pattern for diagram insertion: diagram:Name
    DIAGRAM_PATTERN = re.compile(r"^diagram:(\w+)$")

    # Pattern for each start: #each Diagram.collection
    EACH_START_PATTERN = re.compile(r"^#each\s+(\w+)\.(\w+)$")

    # Pattern for each end: /each
    EACH_END_PATTERN = re.compile(r"^/each$")

    # Pattern for property access: Diagram.Element.property or just property
    PROPERTY_PATTERN = re.compile(r"^(\w+(?:\.\w+)*)$")

    def __init__(self, source_file: str | None = None, start_line: int = 1) -> None:
        """Initialize the parser.

        Args:
            source_file: Source file path for error reporting.
            start_line: Starting line number of the markdown content.
        """
        self.source_file = source_file
        self.start_line = start_line
        self.errors: list[TemplateError] = []

    def parse(self, content: str) -> list[TemplateExpr]:
        """Parse markdown content into template expressions.

        Args:
            content: The markdown content to parse.

        Returns:
            List of TemplateExpr objects (text and expressions interleaved).
        """
        self.errors = []
        expressions: list[TemplateExpr] = []
        last_end = 0
        current_line = self.start_line

        for match in self.EXPR_PATTERN.finditer(content):
            # Add text before this expression
            text_before = content[last_end : match.start()]
            if text_before:
                expressions.append(
                    TemplateExpr(
                        expr_type=TemplateExprType.TEXT,
                        raw=text_before,
                        content=text_before,
                    )
                )
                # Update line count
                current_line += text_before.count("\n")

            # Parse the expression
            expr_content = match.group(1).strip()
            expr_line = current_line
            expr_column = match.start() - content.rfind("\n", 0, match.start())

            expr = self._parse_expression(
                raw=match.group(0),
                content=expr_content,
                line=expr_line,
                column=expr_column,
            )
            expressions.append(expr)

            last_end = match.end()

        # Add remaining text
        if last_end < len(content):
            text_after = content[last_end:]
            expressions.append(
                TemplateExpr(
                    expr_type=TemplateExprType.TEXT,
                    raw=text_after,
                    content=text_after,
                )
            )

        return expressions

    def _parse_expression(
        self,
        raw: str,
        content: str,
        line: int,
        column: int,
    ) -> TemplateExpr:
        """Parse a single template expression.

        Args:
            raw: The raw expression text including {{ }}.
            content: The content inside the delimiters.
            line: Line number for error reporting.
            column: Column number for error reporting.

        Returns:
            A TemplateExpr object.
        """
        # Try diagram pattern
        match = self.DIAGRAM_PATTERN.match(content)
        if match:
            return TemplateExpr(
                expr_type=TemplateExprType.DIAGRAM,
                raw=raw,
                content=content,
                diagram_name=match.group(1),
                line=line,
                column=column,
            )

        # Try each start pattern
        match = self.EACH_START_PATTERN.match(content)
        if match:
            return TemplateExpr(
                expr_type=TemplateExprType.EACH_START,
                raw=raw,
                content=content,
                each_diagram=match.group(1),
                each_collection=match.group(2),
                line=line,
                column=column,
            )

        # Try each end pattern
        match = self.EACH_END_PATTERN.match(content)
        if match:
            return TemplateExpr(
                expr_type=TemplateExprType.EACH_END,
                raw=raw,
                content=content,
                line=line,
                column=column,
            )

        # Try property pattern
        match = self.PROPERTY_PATTERN.match(content)
        if match:
            path = match.group(1).split(".")
            return TemplateExpr(
                expr_type=TemplateExprType.PROPERTY,
                raw=raw,
                content=content,
                property_path=path,
                line=line,
                column=column,
            )

        # Unknown expression format
        self.errors.append(
            TemplateError(
                message=f"Invalid template expression: {{{{{content}}}}}",
                line=line,
                column=column,
                source_file=self.source_file,
            )
        )

        # Return as text to preserve the original
        return TemplateExpr(
            expr_type=TemplateExprType.TEXT,
            raw=raw,
            content=content,
            line=line,
            column=column,
        )


def unescape_braces(content: str) -> str:
    """Process escape sequences in markdown content.

    Converts \\{ to { and \\} to }.

    Args:
        content: The content with escape sequences.

    Returns:
        The content with escape sequences resolved.
    """
    return content.replace("\\{", "{").replace("\\}", "}")


# Valid collections for each diagram type (per REQ-DOC-012)
VALID_COLLECTIONS: dict[str, set[str]] = {
    "scd": {"externals", "datastores", "flows"},
    "dfd": {"processes", "datastores", "flows"},
    "erd": {"entities", "relationships"},
    "std": {"states", "transitions"},
    "structure": {"modules"},
    "datadict": {"definitions"},
}

# Valid properties for elements in each collection
ELEMENT_PROPERTIES: dict[str, set[str]] = {
    # Common properties for all BaseElement subclasses
    "base": {"name", "description", "is_placeholder", "source_file", "line"},
    # SCD-specific
    "system": {"name", "description", "is_placeholder", "source_file", "line"},
    "scd_external": {"name", "description", "is_placeholder", "source_file", "line"},
    "scd_datastore": {"name", "description", "is_placeholder", "source_file", "line"},
    "scd_flow": {"name", "direction", "description", "source_file", "line"},
    # DFD-specific
    "process": {
        "name",
        "description",
        "is_placeholder",
        "source_file",
        "line",
        "inputs",
        "outputs",
    },
    "datastore": {"name", "description", "is_placeholder", "source_file", "line"},
    "dfd_flow": {"name", "flow_type", "description", "source_file", "line"},
    # ERD-specific
    "entity": {"name", "description", "is_placeholder", "source_file", "line"},
    "relationship": {
        "name",
        "source_entity",
        "target_entity",
        "description",
        "source_file",
        "line",
    },
    # STD-specific
    "state": {
        "name",
        "description",
        "is_placeholder",
        "source_file",
        "line",
        "is_initial",
        "is_final",
        "entry_action",
        "exit_action",
    },
    "transition": {
        "name",
        "source_state",
        "target_state",
        "trigger",
        "guard",
        "action",
        "description",
        "source_file",
        "line",
    },
    # Structure-specific
    "module": {
        "name",
        "description",
        "is_placeholder",
        "source_file",
        "line",
        "calls",
        "data_couples",
        "control_couples",
    },
    # DataDict-specific
    "definition": {"name", "description", "is_placeholder", "namespace", "source_file", "line"},
}


@dataclass
class ValidationResult:
    """Result of template validation."""

    errors: list[TemplateError] = field(default_factory=list)
    warnings: list[TemplateError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if validation passed (no errors)."""
        return len(self.errors) == 0


class TemplateValidator:
    """Validates template expressions against the semantic model.

    Validates:
    - {{diagram:X}} - diagram X exists
    - {{X.Y.property}} - diagram X, element Y, and property exist
    - {{#each X.collection}} - diagram X and collection are valid
    """

    MAX_ERRORS = 10  # Stop after this many errors (per REQ-DOC-020)

    def __init__(self, document: DesignDocument, source_file: str | None = None) -> None:
        """Initialize the validator.

        Args:
            document: The semantic model to validate against.
            source_file: Source file path for error reporting.
        """
        self.document = document
        self.source_file = source_file
        self.errors: list[TemplateError] = []
        self.warnings: list[TemplateError] = []

    def validate(self, expressions: list[TemplateExpr]) -> ValidationResult:
        """Validate a list of template expressions.

        Args:
            expressions: Parsed template expressions to validate.

        Returns:
            ValidationResult with errors and warnings.
        """
        self.errors = []
        self.warnings = []
        each_stack: list[tuple[str, str]] = []  # Stack of (diagram, collection) for context

        for expr in expressions:
            if len(self.errors) >= self.MAX_ERRORS:
                break

            if expr.expr_type == TemplateExprType.DIAGRAM:
                self._validate_diagram(expr)
            elif expr.expr_type == TemplateExprType.PROPERTY:
                self._validate_property(expr, each_stack)
            elif expr.expr_type == TemplateExprType.EACH_START:
                self._validate_each_start(expr)
                if expr.each_diagram and expr.each_collection:
                    each_stack.append((expr.each_diagram, expr.each_collection))
            elif expr.expr_type == TemplateExprType.EACH_END:
                if each_stack:
                    each_stack.pop()

        return ValidationResult(errors=self.errors, warnings=self.warnings)

    def _add_error(self, message: str, expr: TemplateExpr) -> None:
        """Add an error with location information."""
        if len(self.errors) < self.MAX_ERRORS:
            self.errors.append(
                TemplateError(
                    message=message,
                    line=expr.line,
                    column=expr.column,
                    source_file=self.source_file,
                )
            )

    def _get_diagram(self, name: str) -> tuple[Any, str] | None:
        """Get a diagram by name and return (diagram, type).

        Returns:
            Tuple of (diagram_model, diagram_type) or None if not found.
        """
        if name in self.document.scds:
            return (self.document.scds[name], "scd")
        if name in self.document.dfds:
            return (self.document.dfds[name], "dfd")
        if name in self.document.erds:
            return (self.document.erds[name], "erd")
        if name in self.document.stds:
            return (self.document.stds[name], "std")
        if name in self.document.structures:
            return (self.document.structures[name], "structure")
        return None

    def _validate_diagram(self, expr: TemplateExpr) -> None:
        """Validate a diagram reference expression."""
        if not expr.diagram_name:
            return

        result = self._get_diagram(expr.diagram_name)
        if result is None:
            self._add_error(
                f"Unknown diagram: '{expr.diagram_name}'",
                expr,
            )

    def _validate_each_start(self, expr: TemplateExpr) -> None:
        """Validate an each iteration start expression."""
        if not expr.each_diagram or not expr.each_collection:
            return

        result = self._get_diagram(expr.each_diagram)
        if result is None:
            self._add_error(
                f"Unknown diagram: '{expr.each_diagram}'",
                expr,
            )
            return

        _, diagram_type = result
        valid_collections = VALID_COLLECTIONS.get(diagram_type, set())

        if expr.each_collection not in valid_collections:
            self._add_error(
                f"Invalid collection '{expr.each_collection}' for {diagram_type.upper()} diagram. "
                f"Valid collections: {', '.join(sorted(valid_collections))}",
                expr,
            )

    def _validate_property(self, expr: TemplateExpr, each_stack: list[tuple[str, str]]) -> None:
        """Validate a property access expression.

        Args:
            expr: The property expression to validate.
            each_stack: Current stack of (diagram, collection) contexts from #each blocks.
        """
        if not expr.property_path:
            return

        path = expr.property_path
        path_len = len(path)

        if path_len == 1:
            self._validate_single_part_path(path, each_stack, expr)
        elif path_len == 2:
            self._validate_two_part_path(path, expr)
        elif path_len == 3:
            self._validate_three_part_path(path, expr)
        else:
            self._add_error(
                f"Invalid property path: '{'.'.join(path)}'. Use Diagram.Element.property format",
                expr,
            )

    def _validate_single_part_path(
        self, path: list[str], each_stack: list[tuple[str, str]], expr: TemplateExpr
    ) -> None:
        """Validate a single-part property path (must be inside #each block)."""
        if not each_stack:
            self._add_error(
                f"Property '{path[0]}' requires context from an {{{{#each}}}} block",
                expr,
            )
            return
        diagram_name, collection = each_stack[-1]
        self._validate_collection_element_property(diagram_name, collection, path[0], expr)

    def _validate_two_part_path(self, path: list[str], expr: TemplateExpr) -> None:
        """Validate a two-part path: Diagram.Element or Diagram.property."""
        diagram_name, second = path
        result = self._get_diagram(diagram_name)
        if result is None:
            self._add_error(f"Unknown diagram: '{diagram_name}'", expr)
            return

        diagram, diagram_type = result

        if second in VALID_COLLECTIONS.get(diagram_type, set()):
            self._add_error(
                f"Use '{{{{#each {diagram_name}.{second}}}}}' to iterate over collections",
                expr,
            )
            return

        if second in {"name", "description", "source_file"}:
            return  # Valid diagram property

        element = self._get_element_from_diagram(diagram, diagram_type, second)
        if element is None:
            self._add_error(f"Element '{second}' not found in diagram '{diagram_name}'", expr)

    def _validate_three_part_path(self, path: list[str], expr: TemplateExpr) -> None:
        """Validate a three-part path: Diagram.Element.property."""
        diagram_name, element_name, prop = path
        result = self._get_diagram(diagram_name)
        if result is None:
            self._add_error(f"Unknown diagram: '{diagram_name}'", expr)
            return

        diagram, diagram_type = result
        element = self._get_element_from_diagram(diagram, diagram_type, element_name)
        if element is None:
            self._add_error(f"Element '{element_name}' not found in diagram '{diagram_name}'", expr)
            return

        element_type = self._get_element_type(diagram_type, element_name, diagram)
        valid_props = ELEMENT_PROPERTIES.get(element_type, ELEMENT_PROPERTIES["base"])
        if prop not in valid_props:
            self._add_error(
                f"Unknown property '{prop}' for element '{element_name}'. "
                f"Valid properties: {', '.join(sorted(valid_props))}",
                expr,
            )

    def _get_element_from_diagram(self, diagram: Any, diagram_type: str, element_name: str) -> Any:
        """Get an element from a diagram by name."""
        handlers = {
            "scd": self._get_scd_element,
            "dfd": self._get_dfd_element,
            "erd": self._get_erd_element,
            "std": self._get_std_element,
            "structure": self._get_structure_element,
        }
        handler = handlers.get(diagram_type)
        if handler:
            return handler(diagram, element_name)
        return None

    def _get_scd_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from an SCD diagram."""
        if diagram.system and diagram.system.name == element_name:
            return diagram.system
        if element_name in diagram.externals:
            return diagram.externals[element_name]
        if element_name in diagram.datastores:
            return diagram.datastores[element_name]
        if element_name in diagram.flows:
            return diagram.flows[element_name]
        return None

    def _get_dfd_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from a DFD diagram."""
        if element_name in diagram.processes:
            return diagram.processes[element_name]
        if element_name in diagram.datastores:
            return diagram.datastores[element_name]
        for (name, _), flow in diagram.flows.items():
            if name == element_name:
                return flow
        return None

    def _get_erd_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from an ERD diagram."""
        if element_name in diagram.entities:
            return diagram.entities[element_name]
        if element_name in diagram.relationships:
            return diagram.relationships[element_name]
        return None

    def _get_std_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from an STD diagram."""
        if element_name in diagram.states:
            return diagram.states[element_name]
        if element_name in diagram.transitions:
            return diagram.transitions[element_name]
        return None

    def _get_structure_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from a Structure Chart diagram."""
        if element_name in diagram.modules:
            return diagram.modules[element_name]
        return None

    def _get_element_type(self, diagram_type: str, element_name: str, diagram: Any) -> str:
        """Determine the element type for property validation."""
        handlers: dict[str, Callable[[str, Any], str]] = {
            "scd": self._get_scd_element_type,
            "dfd": self._get_dfd_element_type,
            "erd": self._get_erd_element_type,
            "std": self._get_std_element_type,
            "structure": self._get_structure_element_type,
        }
        handler = handlers.get(diagram_type)
        if handler:
            return handler(element_name, diagram)
        return "base"

    def _get_scd_element_type(self, element_name: str, diagram: Any) -> str:
        """Get the element type for an SCD element."""
        if diagram.system and diagram.system.name == element_name:
            return "system"
        if element_name in diagram.externals:
            return "scd_external"
        if element_name in diagram.datastores:
            return "scd_datastore"
        if element_name in diagram.flows:
            return "scd_flow"
        return "base"

    def _get_dfd_element_type(self, element_name: str, diagram: Any) -> str:
        """Get the element type for a DFD element."""
        if element_name in diagram.processes:
            return "process"
        if element_name in diagram.datastores:
            return "datastore"
        return "dfd_flow"

    def _get_erd_element_type(self, element_name: str, diagram: Any) -> str:
        """Get the element type for an ERD element."""
        if element_name in diagram.entities:
            return "entity"
        return "relationship"

    def _get_std_element_type(self, element_name: str, diagram: Any) -> str:
        """Get the element type for an STD element."""
        if element_name in diagram.states:
            return "state"
        return "transition"

    def _get_structure_element_type(self, element_name: str, diagram: Any) -> str:
        """Get the element type for a Structure Chart element."""
        # All structure elements are modules
        del element_name, diagram  # unused but needed for consistent interface
        return "module"

    def _validate_collection_element_property(
        self, diagram_name: str, collection: str, prop: str, expr: TemplateExpr
    ) -> None:
        """Validate a property access within an #each context."""
        result = self._get_diagram(diagram_name)
        if result is None:
            return  # Already validated in _validate_each_start

        _, diagram_type = result

        # Map collection to element type
        element_type = self._collection_to_element_type(diagram_type, collection)
        valid_props = ELEMENT_PROPERTIES.get(element_type, ELEMENT_PROPERTIES["base"])

        if prop not in valid_props:
            self._add_error(
                f"Unknown property '{prop}' for {collection} elements. "
                f"Valid properties: {', '.join(sorted(valid_props))}",
                expr,
            )

    def _collection_to_element_type(self, diagram_type: str, collection: str) -> str:
        """Map a collection name to its element type for property validation."""
        mapping: dict[str, dict[str, str]] = {
            "scd": {
                "externals": "scd_external",
                "datastores": "scd_datastore",
                "flows": "scd_flow",
            },
            "dfd": {
                "processes": "process",
                "datastores": "datastore",
                "flows": "dfd_flow",
            },
            "erd": {
                "entities": "entity",
                "relationships": "relationship",
            },
            "std": {
                "states": "state",
                "transitions": "transition",
            },
            "structure": {
                "modules": "module",
            },
            "datadict": {
                "definitions": "definition",
            },
        }
        return mapping.get(diagram_type, {}).get(collection, "base")


@dataclass
class DiagramReference:
    """A reference to a diagram that needs to be generated."""

    name: str
    diagram_type: str  # "scd", "dfd", "erd", "std", "structure"


@dataclass
class GeneratedDocument:
    """Result of markdown generation."""

    content: str
    diagram_refs: list[DiagramReference]
    errors: list[TemplateError]


class MarkdownGenerator:
    """Generates markdown documents from template expressions.

    Renders template expressions against the semantic model:
    - {{diagram:X}} -> diagram reference placeholder for embedding
    - {{X.Y.property}} -> property value from model
    - {{#each X.collection}}...{{/each}} -> repeated content for each element
    """

    def __init__(
        self,
        document: DesignDocument,
        diagram_format: str = "svg",
        diagram_dir: str = "diagrams",
    ) -> None:
        """Initialize the generator.

        Args:
            document: The semantic model to render against.
            diagram_format: Format for diagrams ("svg", "png", "mmd").
            diagram_dir: Directory where diagram files will be stored (relative path).
        """
        self.document = document
        self.diagram_format = diagram_format
        self.diagram_dir = diagram_dir
        self.diagram_refs: list[DiagramReference] = []
        self.errors: list[TemplateError] = []

    def generate(self, expressions: list[TemplateExpr]) -> GeneratedDocument:
        """Generate markdown from template expressions.

        Args:
            expressions: Parsed and validated template expressions.

        Returns:
            GeneratedDocument with rendered content and diagram references.
        """
        self.diagram_refs = []
        self.errors = []

        output_parts: list[str] = []
        self._render_expressions(expressions, output_parts, context=None)

        # Unescape braces in final output
        content = unescape_braces("".join(output_parts))

        return GeneratedDocument(
            content=content,
            diagram_refs=self.diagram_refs,
            errors=self.errors,
        )

    def _render_expressions(
        self,
        expressions: list[TemplateExpr],
        output: list[str],
        context: Any | None,
    ) -> int:
        """Render expressions to output, returning index after last processed.

        Args:
            expressions: List of expressions to render.
            output: List to append output strings to.
            context: Current iteration context (element being iterated).

        Returns:
            Index after the last processed expression.
        """
        i = 0
        while i < len(expressions):
            expr = expressions[i]

            if expr.expr_type == TemplateExprType.TEXT:
                output.append(expr.content)
                i += 1

            elif expr.expr_type == TemplateExprType.DIAGRAM:
                output.append(self._render_diagram(expr))
                i += 1

            elif expr.expr_type == TemplateExprType.PROPERTY:
                output.append(self._render_property(expr, context))
                i += 1

            elif expr.expr_type == TemplateExprType.EACH_START:
                # Find matching {{/each}} and process the block
                end_idx = self._find_matching_each_end(expressions, i)
                if end_idx == -1:
                    self.errors.append(
                        TemplateError(
                            message="Unmatched {{#each}} block",
                            line=expr.line,
                            column=expr.column,
                        )
                    )
                    i += 1
                else:
                    # Get the block content (between #each and /each)
                    block = expressions[i + 1 : end_idx]
                    self._render_each_block(expr, block, output)
                    i = end_idx + 1

            elif expr.expr_type == TemplateExprType.EACH_END:
                # Should not encounter this here if blocks are balanced
                i += 1

            else:
                i += 1

        return i

    def _render_diagram(self, expr: TemplateExpr) -> str:
        """Render a diagram reference as markdown image link."""
        if not expr.diagram_name:
            return ""

        # Get diagram type
        diagram_type = self._get_diagram_type(expr.diagram_name)
        if diagram_type:
            self.diagram_refs.append(
                DiagramReference(name=expr.diagram_name, diagram_type=diagram_type)
            )

        # Generate markdown image reference
        ext = self.diagram_format
        filename = f"{expr.diagram_name}.{ext}"
        rel_path = f"{self.diagram_dir}/{filename}"

        return f"![{expr.diagram_name}]({rel_path})"

    def _get_diagram_type(self, name: str) -> str | None:
        """Get the type of a diagram by name."""
        if name in self.document.scds:
            return "scd"
        if name in self.document.dfds:
            return "dfd"
        if name in self.document.erds:
            return "erd"
        if name in self.document.stds:
            return "std"
        if name in self.document.structures:
            return "structure"
        return None

    def _render_property(self, expr: TemplateExpr, context: Any | None) -> str:
        """Render a property access expression."""
        if not expr.property_path:
            return ""

        path = expr.property_path
        path_len = len(path)

        if path_len == 1:
            return self._render_single_part_property(path[0], context)
        if path_len == 2:
            return self._render_two_part_property(path)
        if path_len == 3:
            return self._render_three_part_property(path)
        return f"{{{{INVALID PATH: {'.'.join(path)}}}}}"

    def _render_single_part_property(self, prop: str, context: Any | None) -> str:
        """Render a single-part property path (from context)."""
        if context is None:
            return f"{{{{MISSING CONTEXT: {prop}}}}}"
        return self._get_property_value(context, prop)

    def _render_two_part_property(self, path: list[str]) -> str:
        """Render a two-part property path: Diagram.property or Diagram.Element."""
        diagram_name, second = path
        diagram = self._get_diagram_by_name(diagram_name)
        if diagram is None:
            return f"{{{{UNKNOWN: {diagram_name}}}}}"

        if second in {"name", "description", "source_file"}:
            return self._get_property_value(diagram, second)

        return second  # Element name

    def _render_three_part_property(self, path: list[str]) -> str:
        """Render a three-part property path: Diagram.Element.property."""
        diagram_name, element_name, prop = path
        diagram = self._get_diagram_by_name(diagram_name)
        if diagram is None:
            return f"{{{{UNKNOWN: {diagram_name}}}}}"

        diagram_type = self._get_diagram_type(diagram_name)
        if diagram_type is None:
            return f"{{{{UNKNOWN: {diagram_name}}}}}"

        element = self._get_element_from_diagram(diagram, diagram_type, element_name)
        if element is None:
            return f"{{{{UNKNOWN: {element_name}}}}}"

        return self._get_property_value(element, prop)

    def _get_diagram_by_name(self, name: str) -> Any:
        """Get a diagram model by name."""
        if name in self.document.scds:
            return self.document.scds[name]
        if name in self.document.dfds:
            return self.document.dfds[name]
        if name in self.document.erds:
            return self.document.erds[name]
        if name in self.document.stds:
            return self.document.stds[name]
        if name in self.document.structures:
            return self.document.structures[name]
        return None

    def _get_element_from_diagram(self, diagram: Any, diagram_type: str, element_name: str) -> Any:
        """Get an element from a diagram by name."""
        handlers = {
            "scd": self._get_scd_element,
            "dfd": self._get_dfd_element,
            "erd": self._get_erd_element,
            "std": self._get_std_element,
            "structure": self._get_structure_element,
        }
        handler = handlers.get(diagram_type)
        if handler:
            return handler(diagram, element_name)
        return None

    def _get_scd_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from an SCD diagram."""
        if diagram.system and diagram.system.name == element_name:
            return diagram.system
        if element_name in diagram.externals:
            return diagram.externals[element_name]
        if element_name in diagram.datastores:
            return diagram.datastores[element_name]
        return None

    def _get_dfd_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from a DFD diagram."""
        if element_name in diagram.processes:
            return diagram.processes[element_name]
        if element_name in diagram.datastores:
            return diagram.datastores[element_name]
        return None

    def _get_erd_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from an ERD diagram."""
        if element_name in diagram.entities:
            return diagram.entities[element_name]
        return None

    def _get_std_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from an STD diagram."""
        if element_name in diagram.states:
            return diagram.states[element_name]
        return None

    def _get_structure_element(self, diagram: Any, element_name: str) -> Any:
        """Get an element from a Structure Chart diagram."""
        if element_name in diagram.modules:
            return diagram.modules[element_name]
        return None

    def _get_property_value(self, obj: Any, prop: str) -> str:
        """Get a property value from an object, converting to string."""
        if hasattr(obj, prop):
            value = getattr(obj, prop)
            if value is None:
                return ""
            if isinstance(value, bool):
                return "yes" if value else "no"
            if isinstance(value, list):
                return ", ".join(str(v) for v in value)
            return str(value)
        return ""

    def _render_each_block(
        self,
        each_expr: TemplateExpr,
        block: list[TemplateExpr],
        output: list[str],
    ) -> None:
        """Render an #each block by iterating over a collection."""
        if not each_expr.each_diagram or not each_expr.each_collection:
            return

        diagram = self._get_diagram_by_name(each_expr.each_diagram)
        if diagram is None:
            return

        collection = self._get_collection(diagram, each_expr.each_collection)
        if collection is None:
            return

        # Iterate over collection items
        for item in collection:
            # Render the block with this item as context
            self._render_expressions(block, output, context=item)

    def _get_collection(self, diagram: Any, collection_name: str) -> list[Any] | None:
        """Get a collection from a diagram."""
        if hasattr(diagram, collection_name):
            coll = getattr(diagram, collection_name)
            if isinstance(coll, dict):
                return list(coll.values())
            if isinstance(coll, list):
                return coll
        return None

    def _find_matching_each_end(self, expressions: list[TemplateExpr], start: int) -> int:
        """Find the index of the matching {{/each}} for an {{#each}}.

        Args:
            expressions: List of all expressions.
            start: Index of the {{#each}} expression.

        Returns:
            Index of matching {{/each}}, or -1 if not found.
        """
        depth = 1
        for i in range(start + 1, len(expressions)):
            if expressions[i].expr_type == TemplateExprType.EACH_START:
                depth += 1
            elif expressions[i].expr_type == TemplateExprType.EACH_END:
                depth -= 1
                if depth == 0:
                    return i
        return -1


def generate_document(
    document: DesignDocument,
    markdown_contents: list[tuple[str, str | None, int | None]],
    diagram_format: str = "svg",
    diagram_dir: str = "diagrams",
) -> GeneratedDocument:
    """Generate a complete markdown document from markdown blocks.

    This is the main entry point for document generation (REQ-DOC-021).

    Args:
        document: The validated semantic model.
        markdown_contents: List of (content, source_file, start_line) tuples.
        diagram_format: Format for diagrams ("svg", "png", "mmd").
        diagram_dir: Directory for diagram files (relative path).

    Returns:
        GeneratedDocument with rendered content and diagram references.
    """
    all_errors: list[TemplateError] = []
    all_expressions: list[TemplateExpr] = []

    # Parse all markdown blocks
    for content, source_file, start_line in markdown_contents:
        parser = TemplateParser(source_file=source_file, start_line=start_line or 1)
        expressions = parser.parse(content)
        all_errors.extend(parser.errors)
        all_expressions.extend(expressions)

    # Validate all expressions
    validator = TemplateValidator(document)
    validation_result = validator.validate(all_expressions)
    all_errors.extend(validation_result.errors)

    # If there are errors, return early
    if all_errors:
        return GeneratedDocument(
            content="",
            diagram_refs=[],
            errors=all_errors,
        )

    # Generate the document
    generator = MarkdownGenerator(
        document=document,
        diagram_format=diagram_format,
        diagram_dir=diagram_dir,
    )
    result = generator.generate(all_expressions)
    result.errors.extend(all_errors)

    return result
