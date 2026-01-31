"""Command-line interface for DesignIt."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Literal

import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich.panel import Panel

from designit.semantic.analyzer import analyze_file
from designit.semantic.validator import validate
from designit.generators.graphviz import generate_graphviz
from designit.generators.mermaid import generate_mermaid
from designit.model.base import ValidationSeverity


console = Console()
error_console = Console(stderr=True)


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

        # Show files included
        if len(doc.files) > 1:
            console.print("[bold]Files included:[/]")
            for f in doc.files:
                console.print(f"  - {f}")
            console.print()

        # Show summary
        table = Table(title="Document Summary")
        table.add_column("Type", style="cyan")
        table.add_column("Count", justify="right")
        table.add_column("Names")

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

        console.print(table)

        # Show placeholders
        placeholders = doc.placeholders
        if placeholders:
            console.print(f"\n[yellow]Placeholders ({len(placeholders)}):[/]")
            for elem_type, name, pfile in placeholders:
                loc = f" ({pfile})" if pfile else ""
                console.print(f"  - {elem_type}: [bold]{name}[/]{loc}")

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

        # Group messages by severity
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        infos = [m for m in messages if m.severity == ValidationSeverity.INFO]

        # Print messages
        for msg in errors:
            loc = f"{msg.file}:{msg.line}: " if msg.file and msg.line else ""
            console.print(f"[bold red]error:[/] {loc}{msg.message}")

        for msg in warnings:
            loc = f"{msg.file}:{msg.line}: " if msg.file and msg.line else ""
            console.print(f"[bold yellow]warning:[/] {loc}{msg.message}")

        for msg in infos:
            loc = f"{msg.file}:{msg.line}: " if msg.file and msg.line else ""
            console.print(f"[dim]info:[/] {loc}{msg.message}")

        # Summary
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

        # Exit with error if there are errors (or warnings in strict mode)
        if errors or (strict and warnings):
            sys.exit(1)

        console.print("[bold green]Validation passed![/]")

    except Exception as e:
        error_console.print(f"[bold red]Error:[/] {e}")
        sys.exit(1)


@main.command()
@click.argument("file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["graphviz", "dot", "mermaid"]),
    default="mermaid",
    help="Output format",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output directory (default: current directory)",
)
@click.option("--diagram", "-d", multiple=True, help="Only generate specific diagram(s)")
@click.option("--no-placeholders", is_flag=True, help="Exclude placeholder elements")
@click.option("--stdout", is_flag=True, help="Print to stdout instead of files")
def generate(
    file: Path,
    output_format: Literal["graphviz", "dot", "mermaid"],
    output: Path | None,
    diagram: tuple[str, ...],
    no_placeholders: bool,
    stdout: bool,
) -> None:
    """Generate diagrams from a DesignIt file.

    FILE: Path to the .dit file to process.
    """
    try:
        doc = analyze_file(file)

        # Normalize format
        if output_format == "dot":
            output_format = "graphviz"

        # Generate diagrams
        include_placeholders = not no_placeholders
        if output_format == "graphviz":
            diagrams = generate_graphviz(doc, include_placeholders)
            extension = ".dot"
        else:
            diagrams = generate_mermaid(doc, include_placeholders)
            extension = ".mmd"

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
            output_dir = output or Path.cwd()
            output_dir.mkdir(parents=True, exist_ok=True)

            for name, content in diagrams.items():
                out_file = output_dir / f"{name}{extension}"
                out_file.write_text(content)
                console.print(f"[green]Generated:[/] {out_file}")

        console.print(f"\n[bold green]Generated {len(diagrams)} diagram(s)[/]")

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
def lsp() -> None:
    """Start the Language Server Protocol server.

    This is typically called by editors, not directly by users.
    """
    from designit.lsp.server import start_server

    start_server()


if __name__ == "__main__":
    main()
