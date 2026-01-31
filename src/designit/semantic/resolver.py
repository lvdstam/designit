"""Import resolver for multi-file support."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from designit.parser.parser import parse_file, ParseError
from designit.parser.ast_nodes import DocumentNode, ImportNode

if TYPE_CHECKING:
    pass


class ImportError(Exception):
    """Raised when an import cannot be resolved."""

    def __init__(
        self,
        message: str,
        import_path: str,
        source_file: str | None = None,
        line: int | None = None,
    ):
        self.message = message
        self.import_path = import_path
        self.source_file = source_file
        self.line = line
        super().__init__(f"{message}: {import_path}")


class CircularImportError(ImportError):
    """Raised when a circular import is detected."""

    def __init__(self, cycle: list[str]):
        self.cycle = cycle
        cycle_str = " -> ".join(cycle)
        super().__init__(f"Circular import detected: {cycle_str}", cycle[0])


class ResolvedDocument(DocumentNode):
    """A document with all imports resolved."""

    source_file: str | None = None
    imported_files: list[str] = []


class ImportResolver:
    """Resolves imports and merges multiple files into a single document."""

    def __init__(self, base_path: Path | str | None = None):
        """Initialize the resolver.

        Args:
            base_path: Base path for resolving relative imports.
                      If None, uses the current working directory.
        """
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self._parsed_files: dict[str, DocumentNode] = {}
        self._import_stack: list[str] = []

    def resolve(self, filepath: str | Path) -> tuple[DocumentNode, list[str]]:
        """Resolve all imports starting from a file.

        Args:
            filepath: Path to the entry file.

        Returns:
            A tuple of (merged document, list of all files).

        Raises:
            ImportError: If an import cannot be resolved.
            CircularImportError: If a circular import is detected.
            ParseError: If parsing fails.
        """
        self._parsed_files.clear()
        self._import_stack.clear()

        entry_path = self._resolve_path(filepath)
        self._resolve_file(entry_path)

        # Merge all documents
        merged = self._merge_documents(entry_path)
        all_files = list(self._parsed_files.keys())

        return merged, all_files

    def _resolve_path(self, filepath: str | Path, relative_to: Path | None = None) -> Path:
        """Resolve a file path.

        Args:
            filepath: The path to resolve.
            relative_to: If provided, resolve relative paths from this file's directory.

        Returns:
            The absolute path.
        """
        path = Path(filepath)

        if path.is_absolute():
            return path

        if relative_to:
            # Relative to the importing file
            return (relative_to.parent / path).resolve()

        return (self.base_path / path).resolve()

    def _resolve_file(self, filepath: Path) -> DocumentNode:
        """Parse and resolve a single file.

        Args:
            filepath: Absolute path to the file.

        Returns:
            The parsed document.

        Raises:
            ImportError: If the file cannot be found or read.
            CircularImportError: If a circular import is detected.
            ParseError: If parsing fails.
        """
        filepath_str = str(filepath)

        # Check for circular imports
        if filepath_str in self._import_stack:
            cycle = self._import_stack[self._import_stack.index(filepath_str) :] + [filepath_str]
            raise CircularImportError(cycle)

        # Return cached if already parsed
        if filepath_str in self._parsed_files:
            return self._parsed_files[filepath_str]

        # Check file exists
        if not filepath.exists():
            raise ImportError(
                "File not found",
                str(filepath),
                self._import_stack[-1] if self._import_stack else None,
            )

        # Push to import stack
        self._import_stack.append(filepath_str)

        try:
            # Parse the file
            doc = parse_file(filepath)
            self._parsed_files[filepath_str] = doc

            # Resolve imports
            for imp in doc.imports:
                import_path = self._resolve_path(imp.path, filepath)
                self._resolve_file(import_path)

            return doc

        finally:
            self._import_stack.pop()

    def _merge_documents(self, entry_path: Path) -> DocumentNode:
        """Merge all parsed documents into one.

        The entry file's definitions take precedence over imported ones.
        Later imports override earlier imports.

        Args:
            entry_path: Path to the entry file.

        Returns:
            A merged DocumentNode.
        """
        # Build import order (depth-first, post-order)
        import_order: list[str] = []
        visited: set[str] = set()

        def visit(filepath: str) -> None:
            if filepath in visited:
                return
            visited.add(filepath)

            doc = self._parsed_files.get(filepath)
            if doc:
                for imp in doc.imports:
                    imp_path = str(self._resolve_path(imp.path, Path(filepath)))
                    visit(imp_path)

            import_order.append(filepath)

        visit(str(entry_path))

        # Merge in import order (later files override earlier)
        merged = DocumentNode()

        for filepath in import_order:
            doc = self._parsed_files.get(filepath)
            if doc:
                # Merge each type of declaration
                merged.dfds.extend(doc.dfds)
                merged.erds.extend(doc.erds)
                merged.stds.extend(doc.stds)
                merged.structures.extend(doc.structures)
                merged.scds.extend(doc.scds)
                merged.datadicts.extend(doc.datadicts)
                # Don't merge imports - they're already resolved

        return merged


def resolve_imports(
    filepath: str | Path, base_path: Path | str | None = None
) -> tuple[DocumentNode, list[str]]:
    """Convenience function to resolve imports from a file.

    Args:
        filepath: Path to the entry file.
        base_path: Base path for resolving relative imports.

    Returns:
        A tuple of (merged document, list of all files).
    """
    resolver = ImportResolver(base_path)
    return resolver.resolve(filepath)
