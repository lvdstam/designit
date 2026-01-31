"""Tests for Language Server Protocol functionality."""

from lsprotocol import types as lsp
from pygls.workspace import TextDocument

from designit.lsp.server import _get_diagnostics


class TestLSPDiagnostics:
    """Tests for LSP diagnostic generation."""

    def test_scd_flow_not_in_datadict_produces_diagnostic(self) -> None:
        """SCD flow not in data dictionary should produce error diagnostic."""
        source = """
scd TestSCD {
    system Core {}
    external User {}
    flow UndefinedFlow: User -> Core
}
"""
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) == 1
        assert "UndefinedFlow" in errors[0].message
        assert "data dictionary" in errors[0].message.lower()

    def test_dfd_flow_not_in_datadict_produces_diagnostic(self) -> None:
        """DFD flow not in data dictionary should produce error diagnostic."""
        source = """
scd Context {
    system Sys {}
    external User {}
    flow UndefinedFlow: User -> Sys
}
dfd TestDFD {
    refines: Context.Sys
    process Handle {}
    flow UndefinedFlow: -> Handle
}
"""
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) >= 1
        assert any("UndefinedFlow" in e.message for e in errors)
        assert any("data dictionary" in e.message.lower() for e in errors)

    def test_flow_diagnostic_has_correct_line_number(self) -> None:
        """Flow validation diagnostic should point to the flow's line."""
        # Using non-indented source so line numbers are predictable
        source = """scd TestSCD {
    system Core {}
    external User {}
    flow UndefinedFlow: User -> Core
}
"""
        # Line 1: "scd TestSCD {"
        # Line 2: "    system Core {}"
        # Line 3: "    external User {}"
        # Line 4: "    flow UndefinedFlow: User -> Core"
        # Line 5: "}"
        # The flow is on line 4 (1-based), so LSP line should be 3 (0-based)
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) == 1
        # This test will FAIL until we fix the parser to capture line numbers
        assert errors[0].range.start.line == 3, (
            f"Expected line 3 (0-based), got {errors[0].range.start.line}"
        )

    def test_multiple_flows_have_distinct_line_numbers(self) -> None:
        """Multiple undefined flows should have distinct line numbers."""
        source = """scd TestSCD {
    system Core {}
    external A {}
    external B {}
    flow FlowA: A -> Core
    flow FlowB: Core -> B
}
"""
        # FlowA on line 5 (1-based) -> line 4 (0-based)
        # FlowB on line 6 (1-based) -> line 5 (0-based)
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) == 2

        lines = sorted([e.range.start.line for e in errors])
        # This test will FAIL until we fix the parser
        assert lines == [4, 5], f"Expected lines [4, 5] (0-based), got {lines}"

    def test_dfd_flow_diagnostic_has_correct_line_number(self) -> None:
        """DFD flow validation diagnostic should point to the flow's line."""
        source = """scd Context {
    system Sys {}
    external User {}
    flow UndefinedFlow: User -> Sys
}
dfd TestDFD {
    refines: Context.Sys
    process Handle {}
    flow UndefinedFlow: -> Handle
}
"""
        # The DFD flow is on line 9 (1-based), so LSP line should be 8 (0-based)
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        dfd_errors = [e for e in errors if "DFD" in e.message]
        assert len(dfd_errors) >= 1
        assert dfd_errors[0].range.start.line == 8, (
            f"Expected line 8 (0-based), got {dfd_errors[0].range.start.line}"
        )

    def test_valid_document_no_error_diagnostics(self) -> None:
        """Document with flows defined in datadict should have no error diagnostics."""
        source = """
datadict {
    ValidFlow = { data: string }
}
scd TestSCD {
    system Core {}
    external User {}
    flow ValidFlow: User -> Core
}
"""
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) == 0

    def test_diagnostic_severity_is_error(self) -> None:
        """Flow not in datadict should produce Error severity, not Warning."""
        source = """
scd TestSCD {
    system Core {}
    external User {}
    flow UndefinedFlow: User -> Core
}
"""
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        flow_diagnostics = [d for d in diagnostics if "UndefinedFlow" in d.message]
        assert len(flow_diagnostics) == 1
        assert flow_diagnostics[0].severity == lsp.DiagnosticSeverity.Error

    def test_diagnostic_source_is_designit(self) -> None:
        """Diagnostics should have source set to 'designit'."""
        source = """
scd TestSCD {
    system Core {}
    external User {}
    flow UndefinedFlow: User -> Core
}
"""
        doc = TextDocument(uri="file:///test.dit", source=source)
        diagnostics = _get_diagnostics(doc)

        errors = [d for d in diagnostics if d.severity == lsp.DiagnosticSeverity.Error]
        assert len(errors) == 1
        assert errors[0].source == "designit"
