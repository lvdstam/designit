"""Unit tests for diagram generator helper methods."""

from designit.generators.graphviz import GraphVizGenerator
from designit.generators.mermaid import MermaidGenerator
from designit.semantic.analyzer import analyze_string


class TestMermaidDFDBidirectionalDetection:
    """Tests for MermaidGenerator._detect_dfd_bidirectional_flows."""

    def test_detects_matching_pairs(self) -> None:
        """Bidirectional detection finds flows with same process for in/out."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Data: User -> Sys
            flow Data: Sys -> User
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Data: -> Handler
            flow Data: Handler ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = MermaidGenerator()
        bidirectional = generator._detect_dfd_bidirectional_flows(dfd)

        assert "Data" in bidirectional
        assert bidirectional["Data"] == "Handler"

    def test_empty_when_different_processes(self) -> None:
        """Bidirectional detection returns empty when in/out use different processes."""
        source = """
        datadict {
            Request = { value: string }
            Response = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Request: User -> Sys
            flow Response: Sys -> User
        }
        dfd Level0 {
            refines: Context.Sys
            process Receiver {}
            process Sender {}
            flow Request: -> Receiver
            flow Response: Sender ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = MermaidGenerator()
        bidirectional = generator._detect_dfd_bidirectional_flows(dfd)

        assert len(bidirectional) == 0

    def test_empty_when_no_boundary_flows(self) -> None:
        """Bidirectional detection returns empty when only internal flows exist."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Data: User -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process A {}
            process B {}
            flow Data: -> A
            flow Data: A -> B
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = MermaidGenerator()
        bidirectional = generator._detect_dfd_bidirectional_flows(dfd)

        assert len(bidirectional) == 0


class TestMermaidDFDPlaceholderCollection:
    """Tests for MermaidGenerator._collect_dfd_placeholder_ids."""

    def test_collects_all_placeholder_types(self) -> None:
        """Placeholder collection includes externals, processes, datastores."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Data: User -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            process PlaceholderProc { ... }
            datastore PlaceholderStore { ... }
            flow Data: -> Handler
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = MermaidGenerator()
        placeholder_ids = generator._collect_dfd_placeholder_ids(dfd)

        assert "PlaceholderProc" in placeholder_ids
        assert "PlaceholderStore" in placeholder_ids
        assert "Handler" not in placeholder_ids

    def test_empty_when_no_placeholders(self) -> None:
        """Placeholder collection returns empty list when none exist."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Data: User -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Data: -> Handler
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = MermaidGenerator()
        placeholder_ids = generator._collect_dfd_placeholder_ids(dfd)

        assert len(placeholder_ids) == 0


class TestGraphVizDFDBidirectionalDetection:
    """Tests for GraphVizGenerator._detect_dfd_bidirectional_flows."""

    def test_detects_matching_pairs(self) -> None:
        """Bidirectional detection finds flows with same process for in/out."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Data: User -> Sys
            flow Data: Sys -> User
        }
        dfd Level0 {
            refines: Context.Sys
            process Handler {}
            flow Data: -> Handler
            flow Data: Handler ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = GraphVizGenerator()
        bidirectional = generator._detect_dfd_bidirectional_flows(dfd)

        assert "Data" in bidirectional
        assert bidirectional["Data"] == "Handler"

    def test_empty_when_different_processes(self) -> None:
        """Bidirectional detection returns empty when in/out use different processes."""
        source = """
        datadict {
            Request = { value: string }
            Response = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Request: User -> Sys
            flow Response: Sys -> User
        }
        dfd Level0 {
            refines: Context.Sys
            process Receiver {}
            process Sender {}
            flow Request: -> Receiver
            flow Response: Sender ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = GraphVizGenerator()
        bidirectional = generator._detect_dfd_bidirectional_flows(dfd)

        assert len(bidirectional) == 0

    def test_empty_when_no_boundary_flows(self) -> None:
        """Bidirectional detection returns empty when only internal flows exist."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Data: User -> Sys
        }
        dfd Level0 {
            refines: Context.Sys
            process A {}
            process B {}
            flow Data: -> A
            flow Data: A -> B
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Level0"]

        generator = GraphVizGenerator()
        bidirectional = generator._detect_dfd_bidirectional_flows(dfd)

        assert len(bidirectional) == 0
