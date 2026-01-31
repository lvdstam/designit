# DesignIt Project

A Domain-Specific Language (DSL) for creating Yourdon-style design documents. See [Structured Analysis](https://en.wikipedia.org/wiki/Structured_analysis) for more details. DesignIt allows you to define system designs using a clean, text-based syntax that can be version-controlled, validated, and transformed into visual diagrams.

## External Documentation

For detailed feature requirements and acceptance criteria, see: @docs/requirements.md

## Technology Stack

| Component | Technology | Version |
|-----------|------------|---------|
| Language | Python | 3.13+ |
| Parser | Lark | >= 1.2.2 |
| Models | Pydantic | >= 2.10 |
| LSP Server | pygls | >= 2.0 |
| CLI | Click + Rich | >= 8.1, >= 13.9 |
| Diagrams | Mermaid, GraphViz | - |
| Build | uv + uv_build | - |

## Project Structure

```
designit/
├── src/designit/           # Main source code
│   ├── cli.py              # CLI entry point (Click)
│   ├── grammar/            # Lark grammar definition
│   │   └── designit.lark   # DSL grammar
│   ├── parser/             # Parser and AST
│   │   ├── parser.py       # Lark parser with transformer
│   │   └── ast_nodes.py    # AST node definitions (Pydantic)
│   ├── semantic/           # Semantic analysis
│   │   ├── analyzer.py     # AST to semantic model
│   │   ├── validator.py    # Validation rules
│   │   └── resolver.py     # Multi-file import resolution
│   ├── model/              # Semantic model classes (Pydantic)
│   │   ├── base.py         # Base classes, DesignDocument
│   │   ├── dfd.py          # Data Flow Diagram model
│   │   ├── erd.py          # Entity-Relationship model
│   │   ├── std.py          # State Transition model
│   │   ├── structure.py    # Structure Chart model
│   │   └── datadict.py     # Data Dictionary model
│   ├── generators/         # Output generators
│   │   ├── mermaid.py      # Mermaid diagram generator
│   │   └── graphviz.py     # GraphViz/DOT generator
│   └── lsp/                # Language Server Protocol
│       └── server.py       # LSP server (pygls 2.0)
├── tests/                  # Test suite
│   ├── test_parser.py      # Parser tests
│   └── test_semantic.py    # Semantic analysis tests
├── examples/               # Example .dit files
│   └── banking/            # Multi-file banking system example
├── vscode-extension/       # VS Code extension
│   ├── src/extension.ts    # LSP client
│   ├── syntaxes/           # TextMate grammar
│   └── package.json        # Extension manifest
├── docs/                   # Documentation
│   └── requirements.md     # Detailed requirements
├── pyproject.toml          # Project configuration
└── README.md               # User documentation
```

## Code Conventions

### Python Style

- **Line length:** 100 characters (configured in ruff)
- **Target version:** Python 3.13
- **Type hints:** Required everywhere (mypy strict mode)
- **Linting:** Ruff with rules: E, F, I, N, W, UP

### Model Classes

- All AST nodes inherit from `ASTNode` (Pydantic BaseModel)
- All semantic models inherit from `BaseModel` (Pydantic)
- Use `SourceLocation` for tracking line/column positions
- Include `model_config = ConfigDict(frozen=True)` for immutable models where appropriate

### Parser Implementation

- Grammar defined in Lark LALR format with basic lexer (`lexer="basic"`)
- Basic lexer ensures tokens are not split (e.g., `dfda` stays as one token, not `dfd` + `a`)
- Terminal priorities (`.2`, `.3`) control lexer precedence for overlapping patterns
- `DesignItTransformer` class transforms parse tree to AST
- Each grammar rule has a corresponding transformer method
- Preserve source locations during transformation

### LSP Server (pygls 2.0)

- Import from `pygls.lsp.server` (not `pygls.server`)
- Use `server.text_document_publish_diagnostics()` with `PublishDiagnosticsParams`
- Feature handlers use `@server.feature()` decorator

### Error Handling

- Parse errors: Raise `ParseError` with location info
- Validation errors: Return `ValidationMessage` with severity
- Import errors: Raise `CircularImportError` for cycles

## Testing Requirements

### Running Tests

```bash
# Run all tests
uv run pytest tests/ -v

# Run with coverage
uv run pytest tests/ --cov=src/designit

# Run specific test file
uv run pytest tests/test_parser.py -v
```

### Test Organization

- `test_parser.py` - Parser and AST tests
- `test_semantic.py` - Semantic analysis and validation tests

### When Tests Are Required

Tests **must** be added or updated when:
- Fixing a bug (add a test that would have caught the bug)
- Adding new features or behavior
- Changing existing behavior
- Modifying error messages or error handling

This ensures regressions are caught and behavior is documented through tests.

### Writing Tests

- Use pytest fixtures for common test data
- Test both success cases and error cases
- Include edge cases (empty documents, placeholders)
- Verify error messages include location information
- Reference requirement IDs in docstrings when testing specific requirements (e.g., `REQ-CLI-030`)

## Development Workflow

### Setup

```bash
git clone <repository>
cd designit
uv sync --dev
```

### Common Tasks

```bash
# Run linting
uv run ruff check src/ tests/

# Run type checking
uv run mypy src/

# Test CLI
uv run designit check examples/banking/main.dit

# Test LSP imports
uv run python -c "from designit.lsp.server import server; print('OK')"

# Build VS Code extension
cd vscode-extension && npm install && npm run package
```

### Before Committing

1. Run tests: `uv run pytest tests/ -v`
2. Run linting: `uv run ruff check src/ tests/`
3. Run type checking: `uv run mypy src/`
4. Test CLI commands work correctly

## Diagram Types

The DSL supports five diagram types:

1. **DFD** (Data Flow Diagram) - External entities, processes, datastores, flows
2. **ERD** (Entity-Relationship Diagram) - Entities with attributes, relationships with cardinality
3. **STD** (State Transition Diagram) - States, transitions with triggers/guards/actions
4. **Structure Chart** - Modules with calls, data/control couples
5. **Data Dictionary** - Type definitions (struct, union, array, references)

## Key Implementation Notes

### Import Resolution

- Imports are resolved depth-first, post-order
- Circular imports are detected and reported as errors
- Relative paths resolved from the importing file's directory

### Validation Severity Levels

- **ERROR** - Invalid references, missing required elements
- **WARNING** - Best practice violations (orphan elements, missing PK)
- **INFO** - Suggestions (placeholders, undocumented data types)

### Code Generation

- Mermaid: `.mmd` files with frontmatter titles
- GraphViz: `.dot` files with Helvetica font styling
- Placeholders rendered with dashed/gray styling

### pygls 2.0 API Changes

The LSP server uses pygls 2.0 which has breaking changes from 1.x:

```python
# Import from new location
from pygls.lsp.server import LanguageServer

# Publish diagnostics with params object
server.text_document_publish_diagnostics(
    lsp.PublishDiagnosticsParams(
        uri=uri,
        diagnostics=diagnostics
    )
)
```
