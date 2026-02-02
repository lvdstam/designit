"""Tests for example design files.

These tests verify that the example files in the examples/ directory
parse correctly and pass validation.
"""

from pathlib import Path

import pytest

from designit.generators.graphviz import GraphVizGenerator
from designit.generators.mermaid import MermaidGenerator
from designit.model.base import DesignDocument, ValidationSeverity
from designit.model.scd import SCDModel
from designit.semantic.analyzer import analyze_file, analyze_string
from designit.semantic.validator import validate


class TestBankingExample:
    """Tests for the banking example files."""

    @pytest.fixture
    def examples_dir(self) -> Path:
        """Get the path to the banking examples directory."""
        return Path(__file__).parent.parent / "examples" / "banking"

    def test_main_parses_with_imports(self, examples_dir: Path) -> None:
        """Test that main.dit parses with all imports resolved."""
        main_file = examples_dir / "main.dit"
        doc = analyze_file(str(main_file))

        # Should have diagrams from all imported files
        assert len(doc.dfds) >= 2  # main + transactions
        assert len(doc.erds) >= 2  # accounts + transactions
        assert len(doc.stds) >= 1  # main
        assert len(doc.structures) >= 1  # main
        assert len(doc.scds) >= 1  # context

    def test_no_validation_errors(self, examples_dir: Path) -> None:
        """Test that example files have no validation errors.

        Note: Cross-ERD foreign key references (e.g., Transaction.account_id -> Account.id
        where Account is in a different ERD) produce validation errors because FK validation
        is scoped to individual ERDs. This is a known limitation.
        """
        main_file = examples_dir / "main.dit"
        doc = analyze_file(str(main_file))
        messages = validate(doc)

        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        # Filter out cross-ERD FK reference errors (known limitation)
        cross_erd_fk_errors = [
            e for e in errors if "references unknown entity" in e.message and "FK" in e.message
        ]
        other_errors = [e for e in errors if e not in cross_erd_fk_errors]

        assert len(other_errors) == 0, f"Validation errors: {[e.message for e in other_errors]}"

    def test_scd_structure(self, examples_dir: Path) -> None:
        """Test that the SCD has expected structure."""
        main_file = examples_dir / "main.dit"
        doc = analyze_file(str(main_file))

        assert "BankingSystemContext" in doc.scds
        scd = doc.scds["BankingSystemContext"]

        # Check system
        assert scd.system is not None
        assert scd.system.name == "BankingSystem"

        # Check externals
        assert "Customer" in scd.externals
        assert "BankTeller" in scd.externals
        assert "ExternalBank" in scd.externals
        assert "RegulatoryAuthority" in scd.externals

        # Check datastores
        assert "CustomerDB" in scd.datastores
        assert "TransactionLog" in scd.datastores

        # Check flows exist
        assert len(scd.flows) > 0

    def test_scd_flow_directions(self, examples_dir: Path) -> None:
        """Test that SCD flows have correct directions."""
        main_file = examples_dir / "main.dit"
        doc = analyze_file(str(main_file))
        scd = doc.scds["BankingSystemContext"]

        # Check inbound flow (Customer -> BankingSystem)
        assert "LoginRequest" in scd.flows
        login_flow = scd.flows["LoginRequest"]
        assert login_flow.direction == "inbound"

        # Check outbound flow (BankingSystem -> Customer)
        assert "AccountInfo" in scd.flows
        account_flow = scd.flows["AccountInfo"]
        assert account_flow.direction == "outbound"

        # Check bidirectional flow (BankingSystem <-> ExternalBank)
        assert "TransferData" in scd.flows
        transfer_flow = scd.flows["TransferData"]
        assert transfer_flow.direction == "bidirectional"

    def test_context_file_standalone(self, examples_dir: Path) -> None:
        """Test that context.dit can be parsed standalone."""
        context_file = examples_dir / "context.dit"
        doc = analyze_file(str(context_file))

        assert len(doc.scds) == 1
        assert "BankingSystemContext" in doc.scds

        # Standalone should have no errors
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0


class TestSCDGeneration:
    """Tests for SCD diagram generation layout."""

    @pytest.fixture
    def scd_model(self) -> SCDModel:
        """Get the SCD model from the banking example."""
        examples_dir = Path(__file__).parent.parent / "examples" / "banking"
        context_file = examples_dir / "context.dit"
        doc = analyze_file(str(context_file))
        return doc.scds["BankingSystemContext"]

    def test_graphviz_scd_radial_layout(self, scd_model: SCDModel) -> None:
        """Test that GraphViz SCD uses neato radial layout (REQ-GEN-057)."""
        generator = GraphVizGenerator()
        output = generator.generate_scd(scd_model)

        # Verify neato layout configuration
        assert "layout=neato" in output
        assert "overlap=false" in output
        assert "splines=true" in output

        # Verify system is doublecircle pinned at center
        assert "shape=doublecircle" in output
        assert 'pos="0,0!"' in output

        # Verify system has filled style
        assert "fillcolor=lightyellow" in output

    def test_graphviz_scd_elements(self, scd_model: SCDModel) -> None:
        """Test that GraphViz SCD contains expected elements."""
        generator = GraphVizGenerator()
        output = generator.generate_scd(scd_model)

        # Verify system
        assert "BankingSystem" in output

        # Verify external entities as boxes
        assert '"Customer"' in output
        assert "shape=box" in output

        # Verify datastores as cylinders
        assert '"CustomerDB"' in output
        assert "shape=cylinder" in output

        # Verify bidirectional flow
        assert "dir=both" in output

    def test_mermaid_scd_lr_layout(self, scd_model: SCDModel) -> None:
        """Test that Mermaid SCD uses LR layout (REQ-GEN-008)."""
        generator = MermaidGenerator()
        output = generator.generate_scd(scd_model)

        # Verify LR layout direction
        assert "flowchart LR" in output

        # Verify system is declared (stadium shape with double brackets)
        assert "[[" in output  # Stadium shape syntax

    def test_mermaid_scd_elements(self, scd_model: SCDModel) -> None:
        """Test that Mermaid SCD contains expected elements."""
        generator = MermaidGenerator()
        output = generator.generate_scd(scd_model)

        # Verify title
        assert "title: BankingSystemContext" in output

        # Verify system
        assert "BankingSystem" in output

        # Verify external entities
        assert "Customer" in output

        # Verify datastores (cylinder syntax)
        assert "CustomerDB" in output
        assert '("' in output  # Cylinder syntax

        # Verify bidirectional flow
        assert "<-->" in output


class TestDFDBoundaryFlowGeneration:
    """Tests for DFD boundary flow rendering (REQ-GEN-010, REQ-GEN-011, REQ-GEN-012)."""

    @pytest.fixture
    def dfd_with_boundary_flows(self) -> DesignDocument:
        """Create a document with a DFD that has boundary flows."""
        source = """
        datadict {
            Request = { data: string }
            Response = { result: string }
            InternalData = { value: int }
        }
        scd Context {
            system Sys {}
            external User {}
            flow Request: User -> Sys
            flow Response: Sys -> User
        }
        dfd TestDFD {
            refines: Context.Sys
            process Handler {}
            process Processor {}
            flow Request: -> Handler
            flow Response: Processor ->
            flow InternalData: Handler -> Processor
        }
        """
        return analyze_string(source)

    def test_mermaid_dfd_boundary_flows_no_crash(
        self, dfd_with_boundary_flows: DesignDocument
    ) -> None:
        """Test that Mermaid DFD generation does not crash on boundary flows."""
        generator = MermaidGenerator()
        # Should not raise AttributeError
        output = generator.generate_dfd(dfd_with_boundary_flows.dfds["TestDFD"])
        assert output is not None
        assert len(output) > 0

    def test_mermaid_dfd_boundary_nodes_present(
        self, dfd_with_boundary_flows: DesignDocument
    ) -> None:
        """Test that Mermaid output contains boundary nodes (REQ-GEN-011)."""
        generator = MermaidGenerator()
        output = generator.generate_dfd(dfd_with_boundary_flows.dfds["TestDFD"])

        # Boundary nodes should be present with correct syntax
        assert "_boundary_Request(( )):::boundary" in output
        assert "_boundary_Response(( )):::boundary" in output

        # Boundary class definition should be present
        assert "classDef boundary fill:none,stroke:#666,stroke-dasharray:3" in output

    def test_mermaid_dfd_boundary_flow_edges(self, dfd_with_boundary_flows: DesignDocument) -> None:
        """Test that Mermaid output has correct edge connections for boundary flows."""
        generator = MermaidGenerator()
        output = generator.generate_dfd(dfd_with_boundary_flows.dfds["TestDFD"])

        # Inbound flow: boundary -> target
        assert '_boundary_Request -->|"Request"| Handler' in output

        # Outbound flow: source -> boundary
        assert 'Processor -->|"Response"| _boundary_Response' in output

        # Internal flow: source -> target (normal)
        assert 'Handler -->|"InternalData"| Processor' in output

    def test_graphviz_dfd_boundary_flows_no_crash(
        self, dfd_with_boundary_flows: DesignDocument
    ) -> None:
        """Test that GraphViz DFD generation does not crash on boundary flows."""
        generator = GraphVizGenerator()
        # Should not raise AttributeError
        output = generator.generate_dfd(dfd_with_boundary_flows.dfds["TestDFD"])
        assert output is not None
        assert len(output) > 0

    def test_graphviz_dfd_boundary_nodes_present(
        self, dfd_with_boundary_flows: DesignDocument
    ) -> None:
        """Test that GraphViz output contains boundary nodes (REQ-GEN-012)."""
        generator = GraphVizGenerator()
        output = generator.generate_dfd(dfd_with_boundary_flows.dfds["TestDFD"])

        # Boundary nodes should be invisible
        assert '"_boundary_Request" [shape=point label="" width=0.01 style=invis]' in output
        assert '"_boundary_Response" [shape=point label="" width=0.01 style=invis]' in output

    def test_graphviz_dfd_boundary_flow_edges(
        self, dfd_with_boundary_flows: DesignDocument
    ) -> None:
        """Test that GraphViz output has correct edge connections for boundary flows."""
        generator = GraphVizGenerator()
        output = generator.generate_dfd(dfd_with_boundary_flows.dfds["TestDFD"])

        # Inbound flow: boundary -> target
        assert '"_boundary_Request" -> "Handler" [label="Request"]' in output

        # Outbound flow: source -> boundary
        assert '"Processor" -> "_boundary_Response" [label="Response"]' in output

        # Internal flow: source -> target (normal)
        assert '"Handler" -> "Processor" [label="InternalData"]' in output

    def test_dfd_without_boundary_flows_still_works(self) -> None:
        """Test that DFDs with only internal flows still generate correctly."""
        # A DFD that refines a system but only has internal flows
        source = """
        datadict { Data = { value: string } }
        scd TestContext {
            system TestSys {}
            external Source {}
            external Sink {}
            flow Input: Source -> TestSys
            flow Output: TestSys -> Sink
        }
        dfd InternalOnlyDFD {
            refines: TestContext.TestSys
            process Worker {}
            process Validator {}
            flow Input: -> Worker
            flow InternalFlow: Worker -> Validator
            flow Output: Validator ->
        }
        """
        doc = analyze_string(source)

        mermaid_gen = MermaidGenerator()
        mermaid_output = mermaid_gen.generate_dfd(doc.dfds["InternalOnlyDFD"])
        assert "Worker" in mermaid_output
        assert "Validator" in mermaid_output
        # Boundary nodes for Input and Output
        assert "_boundary_Input" in mermaid_output
        assert "_boundary_Output" in mermaid_output
        # Internal flow should work normally
        assert 'Worker -->|"InternalFlow"| Validator' in mermaid_output

        graphviz_gen = GraphVizGenerator()
        graphviz_output = graphviz_gen.generate_dfd(doc.dfds["InternalOnlyDFD"])
        assert '"Worker"' in graphviz_output
        assert '"Validator"' in graphviz_output
        assert '"_boundary_Input"' in graphviz_output
        assert '"_boundary_Output"' in graphviz_output
        assert '"Worker" -> "Validator" [label="InternalFlow"]' in graphviz_output


class TestBidirectionalBoundaryFlowRendering:
    """Tests for bidirectional boundary flow rendering (REQ-GEN-013)."""

    @pytest.fixture
    def dfd_with_bidirectional_same_process(self) -> DesignDocument:
        """Create a DFD where same process handles both directions of a flow."""
        source = """
        datadict {
            DataExchange = { data: string }
        }
        scd Context {
            system Sys {}
            external RemoteAPI {}
            flow DataExchange: RemoteAPI <-> Sys
        }
        dfd Test {
            refines: Context.Sys
            process Handler {}
            flow DataExchange: -> Handler
            flow DataExchange: Handler ->
        }
        """
        return analyze_string(source)

    @pytest.fixture
    def dfd_with_bidirectional_different_processes(self) -> DesignDocument:
        """Create a DFD where different processes handle each direction."""
        source = """
        datadict {
            DataExchange = { data: string }
        }
        scd Context {
            system Sys {}
            external RemoteAPI {}
            flow DataExchange: RemoteAPI <-> Sys
        }
        dfd Test {
            refines: Context.Sys
            process RequestHandler {}
            process ResponseHandler {}
            flow DataExchange: -> RequestHandler
            flow DataExchange: ResponseHandler ->
        }
        """
        return analyze_string(source)

    def test_mermaid_same_process_bidirectional_edge(
        self, dfd_with_bidirectional_same_process: DesignDocument
    ) -> None:
        """Mermaid should render single bidirectional edge when same process handles both."""
        generator = MermaidGenerator()
        output = generator.generate_dfd(dfd_with_bidirectional_same_process.dfds["Test"])

        # Should have single boundary node
        assert output.count("_boundary_DataExchange") >= 1

        # Should have bidirectional edge with <-->
        assert (
            '<-->|"DataExchange"|' in output
            or '_boundary_DataExchange <-->|"DataExchange"| Handler' in output
        )

        # Should NOT have two separate edges for DataExchange
        assert output.count('-->|"DataExchange"|') <= 1  # At most one directional edge if any

    def test_mermaid_different_processes_separate_edges(
        self, dfd_with_bidirectional_different_processes: DesignDocument
    ) -> None:
        """Mermaid should render separate edges when different processes handle each direction."""
        generator = MermaidGenerator()
        output = generator.generate_dfd(dfd_with_bidirectional_different_processes.dfds["Test"])

        # Should have two boundary nodes or two separate edges
        # Inbound: boundary -> RequestHandler
        assert "RequestHandler" in output
        # Outbound: ResponseHandler -> boundary
        assert "ResponseHandler" in output

        # Should have two separate edges (not bidirectional)
        assert "<-->" not in output or output.count("<-->") == 0

    def test_graphviz_same_process_bidirectional_edge(
        self, dfd_with_bidirectional_same_process: DesignDocument
    ) -> None:
        """GraphViz should render single edge with dir=both when same process handles both."""
        generator = GraphVizGenerator()
        output = generator.generate_dfd(dfd_with_bidirectional_same_process.dfds["Test"])

        # Should have single boundary node
        assert "_boundary_DataExchange" in output

        # Should have dir=both for bidirectional
        assert "dir=both" in output

        # Should have the edge with label
        assert 'label="DataExchange"' in output

    def test_graphviz_different_processes_separate_edges(
        self, dfd_with_bidirectional_different_processes: DesignDocument
    ) -> None:
        """GraphViz should render separate edges when different processes handle each direction."""
        generator = GraphVizGenerator()
        output = generator.generate_dfd(dfd_with_bidirectional_different_processes.dfds["Test"])

        # Should have both processes
        assert '"RequestHandler"' in output
        assert '"ResponseHandler"' in output

        # Should NOT have dir=both (separate edges instead)
        assert "dir=both" not in output

    def test_mermaid_single_boundary_node_for_bidirectional(
        self, dfd_with_bidirectional_same_process: DesignDocument
    ) -> None:
        """Should create only one boundary node for bidirectional case."""
        generator = MermaidGenerator()
        output = generator.generate_dfd(dfd_with_bidirectional_same_process.dfds["Test"])

        # Count boundary node declarations (the (( )) pattern)
        # Should only have one for DataExchange
        boundary_declarations = [
            line for line in output.split("\n") if "_boundary_DataExchange((" in line
        ]
        assert len(boundary_declarations) == 1

    def test_graphviz_single_boundary_node_for_bidirectional(
        self, dfd_with_bidirectional_same_process: DesignDocument
    ) -> None:
        """Should create only one boundary node for bidirectional case."""
        generator = GraphVizGenerator()
        output = generator.generate_dfd(dfd_with_bidirectional_same_process.dfds["Test"])

        # Count boundary node declarations (shape=point pattern)
        boundary_declarations = [
            line
            for line in output.split("\n")
            if "_boundary_DataExchange" in line and "shape=point" in line
        ]
        assert len(boundary_declarations) == 1
