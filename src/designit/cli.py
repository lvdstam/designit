"""Command-line interface for DesignIt."""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from designit.generators.graphviz import generate_graphviz
from designit.generators.mermaid import generate_mermaid
from designit.model.base import DesignDocument, ValidationMessage, ValidationSeverity
from designit.semantic.analyzer import analyze_file
from designit.semantic.validator import validate

if TYPE_CHECKING:
    from designit.generators.markdown import GeneratedDocument
    from designit.parser.ast_nodes import DocumentNode

# Graphic formats supported by GraphViz rendering
GRAPHIC_FORMATS = ("svg", "png", "jpg", "tiff", "webp")
ALL_FORMATS = ("mermaid", "dot") + GRAPHIC_FORMATS

console = Console()
error_console = Console(stderr=True)


# ============================================
# Parse Command Helpers
# ============================================


def _print_files_included(doc: DesignDocument) -> None:
    """Print list of files included in the document."""
    if len(doc.files) > 1:
        console.print("[bold]Files included:[/]")
        for f in doc.files:
            console.print(f"  - {f}")
        console.print()


def _build_summary_table(doc: DesignDocument) -> Table:
    """Build a summary table of document contents."""
    table = Table(title="Document Summary")
    table.add_column("Type", style="cyan")
    table.add_column("Count", justify="right")
    table.add_column("Names")

    if doc.scds:
        table.add_row("SCDs", str(len(doc.scds)), ", ".join(doc.scds.keys()))
    if doc.dfds:
        table.add_row("DFDs", str(len(doc.dfds)), ", ".join(doc.dfds.keys()))
    if doc.erds:
        table.add_row("ERDs", str(len(doc.erds)), ", ".join(doc.erds.keys()))
    if doc.stds:
        table.add_row("STDs", str(len(doc.stds)), ", ".join(doc.stds.keys()))
    if doc.structures:
        table.add_row("Structures", str(len(doc.structures)), ", ".join(doc.structures.keys()))
    if doc.data_dictionary:
        table.add_row(
            "Data Definitions",
            str(len(doc.data_dictionary.definitions)),
            ", ".join(list(doc.data_dictionary.definitions.keys())[:5])
            + ("..." if len(doc.data_dictionary.definitions) > 5 else ""),
        )

    return table


def _print_placeholders(doc: DesignDocument) -> None:
    """Print placeholder elements in the document."""
    placeholders = doc.placeholders
    if placeholders:
        console.print(f"\n[yellow]Placeholders ({len(placeholders)}):[/]")
        for elem_type, name, pfile in placeholders:
            loc = f" ({pfile})" if pfile else ""
            console.print(f"  - {elem_type}: [bold]{name}[/]{loc}")


# ============================================
# Check Command Helpers
# ============================================


def _group_messages(
    messages: list[ValidationMessage],
) -> tuple[list[ValidationMessage], list[ValidationMessage], list[ValidationMessage]]:
    """Group validation messages by severity."""
    errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
    warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
    infos = [m for m in messages if m.severity == ValidationSeverity.INFO]
    return errors, warnings, infos


def _print_messages(
    errors: list[ValidationMessage],
    warnings: list[ValidationMessage],
    infos: list[ValidationMessage],
) -> None:
    """Print validation messages with appropriate formatting."""
    for msg in errors:
        loc = f"{msg.file}:{msg.line}: " if msg.file and msg.line else ""
        console.print(f"[bold red]error:[/] {loc}{msg.message}")

    for msg in warnings:
        loc = f"{msg.file}:{msg.line}: " if msg.file and msg.line else ""
        console.print(f"[bold yellow]warning:[/] {loc}{msg.message}")

    for msg in infos:
        loc = f"{msg.file}:{msg.line}: " if msg.file and msg.line else ""
        console.print(f"[dim]info:[/] {loc}{msg.message}")


def _print_summary(
    errors: list[ValidationMessage],
    warnings: list[ValidationMessage],
    infos: list[ValidationMessage],
) -> None:
    """Print summary counts of validation messages."""
    console.print()
    if errors:
        console.print(f"[bold red]{len(errors)} error(s)[/]", end="")
    if warnings:
        if errors:
            console.print(", ", end="")
        console.print(f"[bold yellow]{len(warnings)} warning(s)[/]", end="")
    if infos:
        if errors or warnings:
            console.print(", ", end="")
        console.print(f"[dim]{len(infos)} info(s)[/]", end="")
    console.print()


@click.group()
@click.version_option(package_name="designit")
def main() -> None:
    """DesignIt - A DSL for Yourdon-style design documents.

    Use this tool to parse, validate, and generate diagrams from .dit files.
    """
    pass


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--no-imports", is_flag=True, help="Don't resolve imports")
def parse(file: Path, no_imports: bool) -> None:
    """Parse a DesignIt file and show its structure.

    FILE: Path to the .dit file to parse.
    """
    try:
        doc = analyze_file(file, resolve_all_imports=not no_imports)

        console.print(f"\n[bold green]Successfully parsed:[/] {file}\n")

        _print_files_included(doc)
        console.print(_build_summary_table(doc))
        _print_placeholders(doc)

    except Exception as e:
        error_console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option("--no-imports", is_flag=True, help="Don't resolve imports")
@click.option("--strict", is_flag=True, help="Treat warnings as errors")
def check(file: Path, no_imports: bool, strict: bool) -> None:
    """Validate a DesignIt file.

    FILE: Path to the .dit file to validate.
    """
    try:
        doc = analyze_file(file, resolve_all_imports=not no_imports)
        messages = validate(doc)

        errors, warnings, infos = _group_messages(messages)
        _print_messages(errors, warnings, infos)
        _print_summary(errors, warnings, infos)

        # Exit with error if there are errors (or warnings in strict mode)
        if errors or (strict and warnings):
            sys.exit(1)

        console.print("[bold green]Validation passed![/]")

    except Exception as e:
        error_console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


def _check_graphviz_installed() -> None:
    """Check if GraphViz is installed and raise a helpful error if not."""
    missing = []
    if shutil.which("dot") is None:
        missing.append("dot")
    if shutil.which("neato") is None:
        missing.append("neato")

    if missing:
        raise click.ClickException(
            f"GraphViz commands not found: {', '.join(missing)}. Install GraphViz with:\n"
            "  - Ubuntu/Debian: sudo apt install graphviz\n"
            "  - macOS: brew install graphviz\n"
            "  - Windows: choco install graphviz"
        )


def _get_graphviz_engine(dot_content: str) -> str:
    """Determine the appropriate GraphViz layout engine based on DOT content.

    Returns:
        'neato' if the DOT content specifies layout=neato, otherwise 'dot'
    """
    return "neato" if "layout=neato" in dot_content else "dot"


def _render_graphviz(
    dot_content: str,
    output_path: Path,
    output_format: str,
) -> None:
    """Render DOT content to a graphic file using the appropriate GraphViz engine.

    Args:
        dot_content: The DOT source content
        output_path: Path to write the output file
        output_format: Output format (svg, png, jpg, tiff, webp)
    """
    engine = _get_graphviz_engine(dot_content)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".dot", delete=False) as dot_file:
        dot_file.write(dot_content)
        dot_file_path = Path(dot_file.name)

    try:
        result = subprocess.run(
            [engine, f"-T{output_format}", str(dot_file_path), "-o", str(output_path)],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip() or "Unknown error"
            raise click.ClickException(f"GraphViz rendering failed: {error_msg}")
    finally:
        dot_file_path.unlink(missing_ok=True)


def _generate_diagrams(
    doc: DesignDocument,
    output_format: str,
    include_placeholders: bool,
) -> tuple[dict[str, str], str]:
    """Generate diagram content based on format.

    Returns:
        Tuple of (diagrams dict, file extension)
    """
    if output_format == "mermaid":
        diagrams = generate_mermaid(doc, include_placeholders)
        extension = ".mmd"
    else:
        # All other formats use GraphViz DOT
        diagrams = generate_graphviz(doc, include_placeholders)
        extension = ".dot" if output_format == "dot" else f".{output_format}"
    return diagrams, extension


def _output_diagrams_to_files(
    diagrams: dict[str, str],
    output_dir: Path,
    extension: str,
    output_format: str,
    is_graphic_format: bool,
) -> None:
    """Write diagrams to files in the output directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, content in diagrams.items():
        out_file = output_dir / f"{name}{extension}"

        if is_graphic_format:
            _render_graphviz(content, out_file, output_format)
        else:
            out_file.write_text(content)

        console.print(f"[green]Generated:[/] {out_file}")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(list(ALL_FORMATS)),
    default="svg",
    help="Output format (default: svg)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: ./generated)",
)
@click.option("--diagram", "-d", multiple=True, help="Only generate specific diagram(s)")
@click.option("--no-placeholders", is_flag=True, help="Exclude placeholder elements")
@click.option("--stdout", is_flag=True, help="Print to stdout instead of files (text formats only)")
def generate(
    file: Path,
    output_format: str,
    output: Path | None,
    diagram: tuple[str, ...],
    no_placeholders: bool,
    stdout: bool,
) -> None:
    """Generate diagrams from a DesignIt file.

    FILE: Path to the .dit file to process.

    Supported formats:
      - mermaid: Mermaid diagram text (.mmd)
      - dot: GraphViz DOT text (.dot)
      - svg, png, jpg, tiff, webp: Rendered graphics via GraphViz
    """
    try:
        is_graphic_format = output_format in GRAPHIC_FORMATS
        if is_graphic_format:
            _check_graphviz_installed()

        if stdout and is_graphic_format:
            raise click.ClickException(
                f"Cannot use --stdout with graphic format '{output_format}'. "
                "Use 'dot' or 'mermaid' for text output."
            )

        doc = analyze_file(file)
        diagrams, extension = _generate_diagrams(doc, output_format, not no_placeholders)

        # Filter diagrams if specified
        if diagram:
            diagrams = {k: v for k, v in diagrams.items() if any(d in k for d in diagram)}

        if not diagrams:
            console.print("[yellow]No diagrams to generate[/]")
            return

        # Output
        if stdout:
            for name, content in diagrams.items():
                console.print(Panel(Syntax(content, "text"), title=name))
        else:
            output_dir = output or (Path.cwd() / "generated")
            _output_diagrams_to_files(
                diagrams, output_dir, extension, output_format, is_graphic_format
            )

        console.print(f"\n[bold green]Generated {len(diagrams)} diagram(s)[/]")

    except click.ClickException:
        raise
    except Exception as e:
        error_console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
def placeholders(file: Path) -> None:
    """List all placeholders in a DesignIt file.

    FILE: Path to the .dit file to analyze.
    """
    try:
        doc = analyze_file(file)
        phs = doc.placeholders

        if not phs:
            console.print("[green]No placeholders found - document is complete![/]")
            return

        table = Table(title=f"Placeholders ({len(phs)})")
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="bold")
        table.add_column("File")

        for elem_type, name, pfile in phs:
            table.add_row(elem_type, name, pfile or "-")

        console.print(table)

    except Exception as e:
        error_console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@main.command()
@click.option(
    "--stdio", is_flag=True, default=True, hidden=True, help="Use stdio transport (default)"
)
def lsp(stdio: bool) -> None:
    """Start the Language Server Protocol server.

    This is typically called by editors, not directly by users.
    """
    from designit.lsp.server import start_server

    start_server()


# ============================================
# Doc Command Helpers
# ============================================

# Supported diagram formats for doc command
DOC_DIAGRAM_FORMATS = ("svg", "png", "mmd")


def _get_system_name(doc: DesignDocument) -> str | None:
    """Get the system name from the first SCD that has a system defined."""
    for scd in doc.scds.values():
        if scd.system:
            return scd.system.name
    return None


def _validate_doc_prerequisites(design_doc: DesignDocument, doc_node: DocumentNode) -> str:
    """Validate prerequisites for document generation.

    Returns the system name if valid, raises ClickException otherwise.
    """
    system_name = _get_system_name(design_doc)
    if not design_doc.scds or system_name is None:
        raise click.ClickException("Document generation requires an SCD with a system definition")

    if not doc_node.markdowns:
        raise click.ClickException("No markdown blocks found in document")

    messages = validate(design_doc)
    errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
    if errors:
        _print_messages(errors, [], [])
        raise click.ClickException(f"Validation failed with {len(errors)} error(s)")

    return system_name


def _prepare_markdown_contents(
    doc_node: DocumentNode,
) -> list[tuple[str, str | None, int | None]]:
    """Prepare markdown content tuples from document node."""
    markdown_contents: list[tuple[str, str | None, int | None]] = []
    for md in doc_node.markdowns:
        source_file = md.location.file if md.location else None
        start_line = md.location.line if md.location else None
        markdown_contents.append((md.content, source_file, start_line))
    return markdown_contents


def _generate_doc_diagrams(
    doc: DesignDocument,
    diagram_refs: list[tuple[str, str]],  # (name, type)
    output_dir: Path,
    diagram_format: str,
) -> None:
    """Generate diagram files referenced in the document.

    Args:
        doc: The design document.
        diagram_refs: List of (diagram_name, diagram_type) tuples.
        output_dir: Directory to write diagram files.
        diagram_format: Format for diagrams ("svg", "png", "mmd").
    """
    from designit.generators.graphviz import generate_graphviz
    from designit.generators.mermaid import generate_mermaid

    output_dir.mkdir(parents=True, exist_ok=True)

    # Get all diagrams in the requested format
    if diagram_format == "mmd":
        all_diagrams = generate_mermaid(doc, include_placeholders=True)
        extension = "mmd"
    else:
        all_diagrams = generate_graphviz(doc, include_placeholders=True)
        extension = diagram_format

    # Generate only referenced diagrams
    for name, _ in diagram_refs:
        if name not in all_diagrams:
            continue

        content = all_diagrams[name]
        out_file = output_dir / f"{name}.{extension}"

        if diagram_format in ("svg", "png"):
            _render_graphviz(content, out_file, diagram_format)
        else:
            out_file.write_text(content)

        console.print(f"[dim]Generated diagram:[/] {out_file}")


def _handle_doc_result(
    result: GeneratedDocument,
    design_doc: DesignDocument,
    output_dir: Path,
    diagram_dir: Path,
    diagram_format: str,
    name: str | None,
    system_name: str,
) -> None:
    """Handle the generated document result: output errors or write files."""
    if result.errors:
        for err in result.errors:
            loc = f"{err.source_file}:{err.line}: " if err.source_file and err.line else ""
            console.print(f"[bold red]error:[/] {loc}{err.message}")
        raise click.ClickException(f"Template validation failed with {len(result.errors)} error(s)")

    if result.diagram_refs:
        diagram_tuples = [(ref.name, ref.diagram_type) for ref in result.diagram_refs]
        _generate_doc_diagrams(design_doc, diagram_tuples, diagram_dir, diagram_format)

    output_dir.mkdir(parents=True, exist_ok=True)
    output_filename = name or f"{system_name}.md"
    output_file = output_dir / output_filename
    output_file.write_text(result.content)

    console.print(f"[bold green]Generated:[/] {output_file}")
    if result.diagram_refs:
        console.print(f"[dim]Generated {len(result.diagram_refs)} diagram(s) in {diagram_dir}[/]")


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: ./generated)",
)
@click.option(
    "--name",
    type=str,
    help="Override output filename (default: <system_name>.md)",
)
@click.option(
    "--format",
    "-f",
    "diagram_format",
    type=click.Choice(list(DOC_DIAGRAM_FORMATS)),
    default="svg",
    help="Diagram format (default: svg)",
)
@click.option(
    "--output-diagrams",
    type=click.Path(path_type=Path),
    help="Directory for diagram files (default: <output>/diagrams)",
)
def doc(
    file: Path,
    output: Path | None,
    name: str | None,
    diagram_format: str,
    output_diagrams: Path | None,
) -> None:
    """Generate markdown documentation from a DesignIt file.

    FILE: Path to the .dit file to process.

    This command processes markdown blocks in the .dit file and generates
    a combined markdown document with embedded diagrams.

    Example:
        designit doc design.dit -o docs --format svg
    """
    from designit.generators.markdown import generate_document
    from designit.semantic.resolver import resolve_imports

    try:
        if diagram_format in ("svg", "png"):
            _check_graphviz_installed()

        doc_node, _ = resolve_imports(file)
        design_doc = analyze_file(file)
        system_name = _validate_doc_prerequisites(design_doc, doc_node)
        markdown_contents = _prepare_markdown_contents(doc_node)

        output_dir = output or (Path.cwd() / "generated")
        diagram_dir = output_diagrams or (output_dir / "diagrams")
        rel_diagram_dir = (
            diagram_dir.relative_to(output_dir) if output_diagrams else Path("diagrams")
        )

        result = generate_document(
            document=design_doc,
            markdown_contents=markdown_contents,
            diagram_format=diagram_format,
            diagram_dir=str(rel_diagram_dir),
        )

        _handle_doc_result(
            result, design_doc, output_dir, diagram_dir, diagram_format, name, system_name
        )

    except click.ClickException:
        raise
    except Exception as e:
        error_console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
