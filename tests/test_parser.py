"""Tests for the DesignIt parser."""

import pytest

from designit.parser.ast_nodes import (
    ArrayDefNode,
    DataDictTypeRefNode,
    DocumentNode,
    StructDefNode,
    UnionDefNode,
)
from designit.parser.parser import ParseError, parse_string


class TestParserBasics:
    """Basic parser tests."""

    def test_empty_document(self) -> None:
        """Parse an empty document."""
        doc = parse_string("")
        assert isinstance(doc, DocumentNode)
        assert len(doc.dfds) == 0
        assert len(doc.erds) == 0

    def test_comment_only(self) -> None:
        """Parse a document with only comments."""
        doc = parse_string("// This is a comment\n/* Block comment */")
        assert isinstance(doc, DocumentNode)

    def test_import_statement(self) -> None:
        """Parse import statements."""
        doc = parse_string('import "./other.dit"')
        assert len(doc.imports) == 1
        assert doc.imports[0].path == "./other.dit"


class TestDFDParsing:
    """Tests for DFD parsing."""

    def test_simple_dfd(self) -> None:
        """Parse a simple DFD with refines declaration."""
        source = """
        scd Context {
            system TestSystem {}
            external User {}
            datastore Database {}
            flow Request: User -> TestSystem
            flow Data: TestSystem -> Database
        }
        dfd TestDFD {
            refines: Context.TestSystem
            process HandleRequest {
                description: "Handles user requests"
            }
            datastore LocalCache {}
            flow Request: -> HandleRequest
            flow Data: HandleRequest ->
            flow CacheWrite: HandleRequest -> LocalCache
        }
        """
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        dfd = doc.dfds[0]
        assert dfd.name == "TestDFD"
        assert dfd.refines is not None
        assert dfd.refines.diagram_name == "Context"
        assert dfd.refines.element_name == "TestSystem"
        assert len(dfd.processes) == 1
        assert len(dfd.datastores) == 1
        assert len(dfd.flows) == 3

    def test_dfd_with_placeholder(self) -> None:
        """Parse DFD with placeholder elements."""
        source = """
        scd Ctx {
            system Sys {}
        }
        dfd System {
            refines: Ctx.Sys
            process ToBeImplemented {
                ...
            }
        }
        """
        doc = parse_string(source)
        assert len(doc.dfds) == 1


class TestERDParsing:
    """Tests for ERD parsing."""

    def test_simple_erd(self) -> None:
        """Parse a simple ERD."""
        source = """
        erd DataModel {
            entity User {
                id: integer [pk]
                name: string
                email: string [unique]
            }
            entity Order {
                id: integer [pk]
                user_id: integer [fk -> User.id]
                total: decimal
            }
            relationship places: User -1:n-> Order
        }
        """
        doc = parse_string(source)
        assert len(doc.erds) == 1
        erd = doc.erds[0]
        assert erd.name == "DataModel"
        assert len(erd.entities) == 2
        assert len(erd.relationships) == 1

    def test_entity_with_constraints(self) -> None:
        """Parse entity with various constraints."""
        source = """
        erd Model {
            entity Item {
                id: integer [pk]
                code: string [unique, not null]
                pattern_field: string [pattern: "[A-Z]+"]
            }
        }
        """
        doc = parse_string(source)
        entity = doc.erds[0].entities[0]
        assert entity.name == "Item"
        assert len(entity.attributes) == 3


class TestSTDParsing:
    """Tests for STD parsing."""

    def test_simple_std(self) -> None:
        """Parse a simple STD."""
        source = """
        std OrderLifecycle {
            initial: Pending
            state Pending {
                description: "Order pending"
            }
            state Confirmed {
                description: "Order confirmed"
            }
            transition confirm: Pending -> Confirmed {
                trigger: "payment_received"
            }
        }
        """
        doc = parse_string(source)
        assert len(doc.stds) == 1
        std = doc.stds[0]
        assert std.name == "OrderLifecycle"
        assert std.initial_state == "Pending"
        assert len(std.states) == 2
        assert len(std.transitions) == 1


class TestStructureParsing:
    """Tests for structure chart parsing."""

    def test_simple_structure(self) -> None:
        """Parse a simple structure chart."""
        source = """
        structure MainProgram {
            module Main {
                calls: [Init, Process, Cleanup]
            }
            module Init {
                data_couple: Config
            }
            module Process {
                data_couple: Data
                control_couple: Status
            }
            module Cleanup {
                ...
            }
        }
        """
        doc = parse_string(source)
        assert len(doc.structures) == 1
        structure = doc.structures[0]
        assert structure.name == "MainProgram"
        assert len(structure.modules) == 4


class TestDataDictParsing:
    """Tests for data dictionary parsing."""

    def test_simple_datadict(self) -> None:
        """Parse a simple data dictionary."""
        source = """
        datadict {
            UserName = string
            Status = "active" | "inactive"
            UserData = {
                name: string
                email: string [optional]
                age: integer [min: 0, max: 150]
            }
            UserList = UserData[] [min: 0, max: 100]
            FutureDef = TBD
        }
        """
        doc = parse_string(source)
        assert len(doc.datadicts) == 1
        datadict = doc.datadicts[0]
        assert len(datadict.definitions) == 5


class TestSCDParsing:
    """Tests for System Context Diagram parsing."""

    def test_simple_scd(self) -> None:
        """Parse a simple SCD."""
        source = """
        scd OrderProcessing {
            system OrderSystem {
                description: "Processes customer orders"
            }
            external Customer {
                description: "Places orders"
            }
            external PaymentGateway {
                description: "Handles payments"
            }
            flow OrderRequest: Customer -> OrderSystem
            flow Confirmation: OrderSystem -> Customer
        }
        """
        doc = parse_string(source)
        assert len(doc.scds) == 1
        scd = doc.scds[0]
        assert scd.name == "OrderProcessing"
        assert scd.system is not None
        assert scd.system.name == "OrderSystem"
        assert len(scd.externals) == 2
        assert len(scd.flows) == 2

    def test_scd_with_datastore(self) -> None:
        """Parse SCD with data stores."""
        source = """
        scd DataSystem {
            system MainSystem {}
            datastore Database {
                description: "Primary database"
            }
            flow Query: MainSystem -> Database
            flow Results: Database -> MainSystem
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        assert len(scd.datastores) == 1
        assert "Database" in [ds.name for ds in scd.datastores]

    def test_scd_bidirectional_flow(self) -> None:
        """Parse SCD with bidirectional flows."""
        source = """
        scd BidiSystem {
            system Core {}
            external Partner {}
            flow DataExchange: Core <-> Partner
        }
        """
        doc = parse_string(source)
        scd = doc.scds[0]
        assert len(scd.flows) == 1
        flow = scd.flows[0]
        assert flow.direction == "bidirectional"
        assert flow.source == "Core"
        assert flow.target == "Partner"

    def test_scd_with_placeholder(self) -> None:
        """Parse SCD with placeholder elements."""
        source = """
        scd IncompleteSystem {
            system Core {
                ...
            }
            external ToBeDefinedEntity {
                TBD
            }
        }
        """
        doc = parse_string(source)
        assert len(doc.scds) == 1
        scd = doc.scds[0]
        assert scd.system is not None


class TestParseErrors:
    """Tests for parse error handling."""

    def test_invalid_syntax(self) -> None:
        """Test that invalid syntax raises ParseError."""
        with pytest.raises(ParseError):
            parse_string("dfd {}")  # Missing name

    def test_unclosed_block(self) -> None:
        """Test that unclosed blocks raise ParseError."""
        with pytest.raises(ParseError):
            parse_string("dfd Test { process P {")

    def test_misspelled_keyword_error_message(self) -> None:
        """Test that misspelled keywords show the full word in error message.

        REQ-CLI-030: When a keyword like 'dfd' is misspelled as 'dfda',
        the error message should show 'dfda' as the unexpected token,
        not split it into 'dfd' + 'a'.
        """
        source = """
        dfda TestSystem {
            process Test {}
        }
        """
        with pytest.raises(ParseError) as exc_info:
            parse_string(source)

        error_msg = str(exc_info.value)
        # The error should mention 'dfda' as the unexpected token
        assert "dfda" in error_msg
        # The error should NOT mention 'a' as a separate token artifact
        assert "Token('IDENTIFIER', 'a')" not in error_msg

    def test_misspelled_keyword_suggests_valid_keywords(self) -> None:
        """Test that parse errors list valid top-level keywords."""
        with pytest.raises(ParseError) as exc_info:
            parse_string("xyz Invalid {}")

        error_msg = str(exc_info.value)
        # Should mention at least some valid keywords
        assert "DFD" in error_msg or "dfd" in error_msg.lower()


class TestNodeLocation:
    """Tests for source location tracking on all AST node types.

    REQ-SEM-002: All validation messages shall include accurate source location.
    This requires all AST nodes to capture location during parsing.
    """

    # ============================================
    # DFD Elements
    # ============================================

    def test_external_node_has_location(self) -> None:
        """ExternalNode in SCD should have source location (DFDs no longer have externals)."""
        source = """scd Test {
    system S {}
    external MyExternal {}
    flow F: MyExternal -> S
}
"""
        doc = parse_string(source)
        assert len(doc.scds) == 1
        assert len(doc.scds[0].externals) == 1
        ext = doc.scds[0].externals[0]
        assert ext.location is not None, "External should have location set"
        assert ext.location.line == 3, f"Expected line 3, got {ext.location.line}"

    def test_process_node_has_location(self) -> None:
        """ProcessNode should have source location."""
        source = """scd Ctx {
    system S {}
}
dfd Test {
    refines: Ctx.S
    process MyProcess {}
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].processes) == 1
        proc = doc.dfds[0].processes[0]
        assert proc.location is not None, "Process should have location set"
        assert proc.location.line == 6, f"Expected line 6, got {proc.location.line}"

    def test_datastore_node_has_location(self) -> None:
        """DatastoreNode should have source location."""
        source = """scd Ctx {
    system S {}
}
dfd Test {
    refines: Ctx.S
    datastore MyDatastore {}
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].datastores) == 1
        ds = doc.dfds[0].datastores[0]
        assert ds.location is not None, "Datastore should have location set"
        assert ds.location.line == 6, f"Expected line 6, got {ds.location.line}"

    # ============================================
    # SCD Elements
    # ============================================

    def test_system_node_has_location(self) -> None:
        """SystemNode should have source location."""
        source = """scd Test {
    system MySystem {}
    external E {}
    flow F: E -> MySystem
}
"""
        doc = parse_string(source)
        assert len(doc.scds) == 1
        assert doc.scds[0].system is not None
        sys = doc.scds[0].system
        assert sys.location is not None, "System should have location set"
        assert sys.location.line == 2, f"Expected line 2, got {sys.location.line}"

    def test_scd_external_node_has_location(self) -> None:
        """ExternalNode in SCD should have source location."""
        source = """scd Test {
    system S {}
    external MyExternal {}
    flow F: MyExternal -> S
}
"""
        doc = parse_string(source)
        assert len(doc.scds) == 1
        assert len(doc.scds[0].externals) == 1
        ext = doc.scds[0].externals[0]
        assert ext.location is not None, "SCD External should have location set"
        assert ext.location.line == 3, f"Expected line 3, got {ext.location.line}"

    def test_scd_datastore_node_has_location(self) -> None:
        """DatastoreNode in SCD should have source location."""
        source = """scd Test {
    system S {}
    datastore MyDatastore {}
    flow F: S -> MyDatastore
}
"""
        doc = parse_string(source)
        assert len(doc.scds) == 1
        assert len(doc.scds[0].datastores) == 1
        ds = doc.scds[0].datastores[0]
        assert ds.location is not None, "SCD Datastore should have location set"
        assert ds.location.line == 3, f"Expected line 3, got {ds.location.line}"

    # ============================================
    # ERD Elements
    # ============================================

    def test_entity_node_has_location(self) -> None:
        """EntityNode should have source location."""
        source = """erd Test {
    entity MyEntity {
        id: integer [pk]
    }
}
"""
        doc = parse_string(source)
        assert len(doc.erds) == 1
        assert len(doc.erds[0].entities) == 1
        entity = doc.erds[0].entities[0]
        assert entity.location is not None, "Entity should have location set"
        assert entity.location.line == 2, f"Expected line 2, got {entity.location.line}"

    def test_relationship_node_has_location(self) -> None:
        """RelationshipNode should have source location."""
        source = """erd Test {
    entity A { id: integer [pk] }
    entity B { id: integer [pk] }
    relationship MyRel: A -1:n-> B
}
"""
        doc = parse_string(source)
        assert len(doc.erds) == 1
        assert len(doc.erds[0].relationships) == 1
        rel = doc.erds[0].relationships[0]
        assert rel.location is not None, "Relationship should have location set"
        assert rel.location.line == 4, f"Expected line 4, got {rel.location.line}"

    # ============================================
    # STD Elements
    # ============================================

    def test_state_node_has_location(self) -> None:
        """StateNode should have source location."""
        source = """std Test {
    initial: Idle
    state Idle {}
    state MyState {}
}
"""
        doc = parse_string(source)
        assert len(doc.stds) == 1
        # MyState is the second state (after Idle)
        states = doc.stds[0].states
        assert len(states) == 2
        my_state = next((s for s in states if s.name == "MyState"), None)
        assert my_state is not None
        assert my_state.location is not None, "State should have location set"
        assert my_state.location.line == 4, f"Expected line 4, got {my_state.location.line}"

    def test_transition_node_has_location(self) -> None:
        """TransitionNode should have source location."""
        source = """std Test {
    initial: A
    state A {}
    state B {}
    transition MyTrans: A -> B
}
"""
        doc = parse_string(source)
        assert len(doc.stds) == 1
        assert len(doc.stds[0].transitions) == 1
        trans = doc.stds[0].transitions[0]
        assert trans.location is not None, "Transition should have location set"
        assert trans.location.line == 5, f"Expected line 5, got {trans.location.line}"

    # ============================================
    # Structure Chart Elements
    # ============================================

    def test_module_node_has_location(self) -> None:
        """ModuleNode should have source location."""
        source = """structure Test {
    module MyModule {
        calls: [SubModule]
    }
    module SubModule {}
}
"""
        doc = parse_string(source)
        assert len(doc.structures) == 1
        modules = doc.structures[0].modules
        assert len(modules) == 2
        # First module is MyModule on line 2
        mod = modules[0]
        assert mod.location is not None, "Module should have location set"
        assert mod.location.line == 2, f"Expected line 2, got {mod.location.line}"

    # ============================================
    # Data Dictionary Elements
    # ============================================

    def test_datadef_node_has_location(self) -> None:
        """DataDefNode should have source location."""
        source = """datadict {
    MyType = string
}
"""
        doc = parse_string(source)
        assert len(doc.datadicts) == 1
        assert len(doc.datadicts[0].definitions) == 1
        defn = doc.datadicts[0].definitions[0]
        assert defn.location is not None, "DataDef should have location set"
        assert defn.location.line == 2, f"Expected line 2, got {defn.location.line}"


class TestFlowLocation:
    """Tests for source location tracking on flow nodes."""

    def test_dfd_flow_has_location(self) -> None:
        """DFD flow nodes should have source location."""
        source = """scd Ctx {
    system S {}
    external A {}
    flow F: A -> S
}
dfd Test {
    refines: Ctx.S
    process B {}
    flow InboundF: -> B
    flow MyFlow: B ->
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].flows) == 2
        flow = doc.dfds[0].flows[1]  # MyFlow
        assert flow.location is not None, "Flow should have location set"
        assert flow.location.line == 10, f"Expected line 10, got {flow.location.line}"

    def test_scd_flow_has_location(self) -> None:
        """SCD flow nodes should have source location."""
        source = """scd Test {
    system Core {}
    external User {}
    flow MyFlow: User -> Core
}
"""
        doc = parse_string(source)
        assert len(doc.scds) == 1
        assert len(doc.scds[0].flows) == 1
        flow = doc.scds[0].flows[0]
        # This test will FAIL until we fix the parser
        assert flow.location is not None, "SCD flow should have location set"
        assert flow.location.line == 4, f"Expected line 4, got {flow.location.line}"

    def test_multiple_flows_have_distinct_locations(self) -> None:
        """Multiple flows should have distinct line numbers."""
        source = """scd Test {
    system Core {}
    external A {}
    external B {}
    flow Flow1: A -> Core
    flow Flow2: Core -> B
    flow Flow3: A <-> B
}
"""
        doc = parse_string(source)
        flows = doc.scds[0].flows
        assert len(flows) == 3

        # This test will FAIL until we fix the parser
        locations = [f.location for f in flows]
        assert all(loc is not None for loc in locations), "All flows should have locations"

        for loc in locations:
            assert loc is not None
        # Type narrowing: after the loop, mypy still sees Optional, so we filter explicitly
        non_null_locations = [loc for loc in locations if loc is not None]
        lines = [loc.line for loc in non_null_locations]
        assert lines == [5, 6, 7], f"Expected lines [5, 6, 7], got {lines}"

    def test_flow_location_has_column(self) -> None:
        """Flow location should include column information."""
        source = """scd Test {
    system Core {}
    external User {}
    flow MyFlow: User -> Core
}
"""
        doc = parse_string(source)
        flow = doc.scds[0].flows[0]
        # This test will FAIL until we fix the parser
        assert flow.location is not None
        assert flow.location.column is not None
        assert flow.location.column > 0


class TestRefinesParsing:
    """Tests for DFD refines declaration parsing.

    REQ-SEM-080: Every DFD shall declare what parent element it refines.
    REQ-SEM-084: DFDs shall support boundary flows with a single endpoint.
    REQ-SEM-088: DFDs shall not declare external entities.
    """

    def test_dfd_with_refines_scd_parses(self) -> None:
        """DFD refining an SCD system should parse correctly."""
        source = """
        scd OrderContext {
            system OrderSystem {}
            external Customer {}
            flow OrderRequest: Customer -> OrderSystem
        }

        dfd Level0 {
            refines: OrderContext.OrderSystem

            process ValidateOrder {}

            flow OrderRequest: -> ValidateOrder
        }
        """
        doc = parse_string(source)
        assert len(doc.scds) == 1
        assert len(doc.dfds) == 1
        dfd = doc.dfds[0]
        assert dfd.name == "Level0"
        assert dfd.refines is not None
        assert dfd.refines.diagram_name == "OrderContext"
        assert dfd.refines.element_name == "OrderSystem"

    def test_dfd_with_refines_dfd_parses(self) -> None:
        """DFD refining a DFD process should parse correctly."""
        source = """
        scd Context {
            system Sys {}
            external Ext {}
            flow F: Ext -> Sys
        }

        dfd Level0 {
            refines: Context.Sys

            process SubProcess {}

            flow F: -> SubProcess
        }

        dfd Level1 {
            refines: Level0.SubProcess

            process DetailA {}
            process DetailB {}

            flow F: -> DetailA
            flow Internal: DetailA -> DetailB
        }
        """
        doc = parse_string(source)
        assert len(doc.dfds) == 2
        level1 = doc.dfds[1]
        assert level1.name == "Level1"
        assert level1.refines is not None
        assert level1.refines.diagram_name == "Level0"
        assert level1.refines.element_name == "SubProcess"

    def test_dfd_without_refines_parse_error(self) -> None:
        """DFD without refines declaration should produce parse error.

        REQ-SEM-080: Every DFD must have a refines declaration.
        """
        source = """
        dfd InvalidDFD {
            process SomeProcess {}
        }
        """
        with pytest.raises(ParseError):
            parse_string(source)

    def test_refines_node_has_location(self) -> None:
        """RefinesNode should have source location."""
        source = """scd Ctx {
    system Sys {}
    external E {}
    flow F: E -> Sys
}

dfd Test {
    refines: Ctx.Sys

    process P {}

    flow F: -> P
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        dfd = doc.dfds[0]
        assert dfd.refines is not None
        assert dfd.refines.location is not None, "Refines should have location set"
        assert dfd.refines.location.line == 8, f"Expected line 8, got {dfd.refines.location.line}"

    def test_refines_with_qualified_reference(self) -> None:
        """Refines should correctly extract diagram and element names."""
        source = """
        scd MyDiagram {
            system TheSystem {}
            external E {}
            flow F: E -> TheSystem
        }

        dfd Child {
            refines: MyDiagram.TheSystem

            process P {}

            flow F: -> P
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert dfd.refines is not None
        assert dfd.refines.diagram_name == "MyDiagram"
        assert dfd.refines.element_name == "TheSystem"


class TestBoundaryFlowParsing:
    """Tests for DFD boundary flow syntax parsing.

    REQ-SEM-084: DFDs shall support boundary flows with a single endpoint.
    """

    def test_inbound_boundary_flow_parses(self) -> None:
        """Inbound boundary flow syntax should parse: flow Name: -> Process"""
        source = """
        scd Ctx {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Test {
            refines: Ctx.Sys

            process Handler {}

            flow Request: -> Handler
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.flows) == 1
        flow = dfd.flows[0]
        assert flow.name == "Request"
        # Inbound boundary flow has no source, only target
        assert flow.source is None
        assert flow.target is not None
        assert flow.target.entity == "Handler"

    def test_outbound_boundary_flow_parses(self) -> None:
        """Outbound boundary flow syntax should parse: flow Name: Process ->"""
        source = """
        scd Ctx {
            system Sys {}
            external E {}
            flow Response: Sys -> E
        }

        dfd Test {
            refines: Ctx.Sys

            process Handler {}

            flow Response: Handler ->
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.flows) == 1
        flow = dfd.flows[0]
        assert flow.name == "Response"
        # Outbound boundary flow has source, no target
        assert flow.source is not None
        assert flow.source.entity == "Handler"
        assert flow.target is None

    def test_internal_flow_still_parses(self) -> None:
        """Internal flows with both endpoints should still parse."""
        source = """
        scd Ctx {
            system Sys {}
            external E {}
            flow F: E -> Sys
        }

        dfd Test {
            refines: Ctx.Sys

            process A {}
            process B {}

            flow F: -> A
            flow Internal: A -> B
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.flows) == 2

        internal = next((f for f in dfd.flows if f.name == "Internal"), None)
        assert internal is not None
        assert internal.source is not None
        assert internal.target is not None
        assert internal.source.entity == "A"
        assert internal.target.entity == "B"

    def test_boundary_flow_has_location(self) -> None:
        """Boundary flows should have source location."""
        source = """scd Ctx {
    system Sys {}
    external E {}
    flow F: E -> Sys
}

dfd Test {
    refines: Ctx.Sys

    process P {}

    flow F: -> P
}
"""
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.flows) == 1
        flow = dfd.flows[0]
        assert flow.location is not None, "Boundary flow should have location set"
        assert flow.location.line == 12, f"Expected line 12, got {flow.location.line}"

    def test_multiple_boundary_flows_parse(self) -> None:
        """Multiple boundary flows in different directions should parse."""
        source = """
        scd Ctx {
            system Sys {}
            external A {}
            external B {}
            flow In1: A -> Sys
            flow In2: B -> Sys
            flow Out1: Sys -> A
            flow Out2: Sys -> B
        }

        dfd Test {
            refines: Ctx.Sys

            process P1 {}
            process P2 {}

            flow In1: -> P1
            flow In2: -> P2
            flow Out1: P1 ->
            flow Out2: P2 ->
            flow Internal: P1 -> P2
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.flows) == 5

        # Count boundary flows
        inbound = [f for f in dfd.flows if f.source is None]
        outbound = [f for f in dfd.flows if f.target is None]
        internal = [f for f in dfd.flows if f.source is not None and f.target is not None]

        assert len(inbound) == 2
        assert len(outbound) == 2
        assert len(internal) == 1


class TestDFDNoExternals:
    """Tests for DFD external entity restriction.

    REQ-SEM-088: DFDs shall not declare external entities.
    """

    def test_dfd_with_external_parse_error(self) -> None:
        """DFD with external declaration should produce parse error."""
        source = """
        scd Ctx {
            system Sys {}
            external E {}
            flow F: E -> Sys
        }

        dfd Test {
            refines: Ctx.Sys

            external NotAllowed {}
            process P {}

            flow F: -> P
        }
        """
        with pytest.raises(ParseError):
            parse_string(source)


class TestDFDLocalDatastore:
    """Tests for DFD local datastore parsing.

    REQ-SEM-085: DFDs may declare local datastores.
    """

    def test_dfd_with_local_datastore_parses(self) -> None:
        """DFD with local datastore should parse."""
        source = """
        scd Ctx {
            system Sys {}
            external E {}
            flow F: E -> Sys
        }

        dfd Test {
            refines: Ctx.Sys

            process P {}
            datastore LocalCache {}

            flow F: -> P
            flow CacheWrite: P -> LocalCache
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.datastores) == 1
        assert dfd.datastores[0].name == "LocalCache"

    def test_dfd_datastore_flow_is_internal(self) -> None:
        """Flow to local datastore should be internal (both endpoints)."""
        source = """
        scd Ctx {
            system Sys {}
            external E {}
            flow F: E -> Sys
        }

        dfd Test {
            refines: Ctx.Sys

            process P {}
            datastore LocalDB {}

            flow F: -> P
            flow Write: P -> LocalDB
            flow Read: LocalDB -> P
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]

        write_flow = next((f for f in dfd.flows if f.name == "Write"), None)
        read_flow = next((f for f in dfd.flows if f.name == "Read"), None)

        assert write_flow is not None
        assert write_flow.source is not None
        assert write_flow.target is not None

        assert read_flow is not None
        assert read_flow.source is not None
        assert read_flow.target is not None


class TestNamedDataDictParsing:
    """Tests for named/namespaced datadict parsing.

    REQ-GRAM-051: Data dictionaries support optional namespace identifier.
    REQ-GRAM-052: Flow type references support namespace qualification.
    """

    def test_anonymous_datadict_parses(self) -> None:
        """Anonymous datadict (no namespace) should parse."""
        source = """
        datadict {
            Money = {
                amount: decimal
                currency: string
            }
            Status = "pending" | "complete"
        }
        """
        doc = parse_string(source)
        assert len(doc.datadicts) == 1
        dd = doc.datadicts[0]
        assert dd.namespace is None
        assert len(dd.definitions) == 2

    def test_named_datadict_parses(self) -> None:
        """Named datadict with namespace identifier should parse."""
        source = """
        datadict PaymentGateway {
            GetStatusRequest = {
                transaction_id: string
            }
            GetStatusResponse = {
                status: string
                amount: decimal
            }
        }
        """
        doc = parse_string(source)
        assert len(doc.datadicts) == 1
        dd = doc.datadicts[0]
        assert dd.namespace == "PaymentGateway"
        assert len(dd.definitions) == 2

    def test_multiple_datadicts_with_different_namespaces(self) -> None:
        """Multiple datadicts with different namespaces should parse."""
        source = """
        datadict {
            SharedType = { id: string }
        }

        datadict PaymentGateway {
            Request = { amount: decimal }
        }

        datadict ShippingService {
            Request = { address: string }
        }
        """
        doc = parse_string(source)
        assert len(doc.datadicts) == 3

        anon = doc.datadicts[0]
        assert anon.namespace is None

        pg = doc.datadicts[1]
        assert pg.namespace == "PaymentGateway"

        ss = doc.datadicts[2]
        assert ss.namespace == "ShippingService"

    def test_qualified_flow_type_ref_in_scd(self) -> None:
        """SCD flows should support qualified type references."""
        source = """
        datadict PaymentGateway {
            PaymentRequest = { amount: decimal }
        }

        scd TestContext {
            system BankingSystem {}
            external PaymentGw {}
            flow PaymentGateway.PaymentRequest: BankingSystem -> PaymentGw
        }
        """
        doc = parse_string(source)
        assert len(doc.scds) == 1
        scd = doc.scds[0]
        assert len(scd.flows) == 1

        flow = scd.flows[0]
        # name is the simple name (last part) for display purposes
        assert flow.name == "PaymentRequest"
        # type_ref contains the full qualified reference
        assert flow.type_ref is not None
        assert flow.type_ref.namespace == "PaymentGateway"
        assert flow.type_ref.name == "PaymentRequest"
        assert flow.type_ref.qualified_name == "PaymentGateway.PaymentRequest"

    def test_unqualified_flow_type_ref_in_scd(self) -> None:
        """SCD flows with unqualified type ref should have no namespace."""
        source = """
        datadict {
            SimpleRequest = { id: string }
        }

        scd TestContext {
            system S {}
            external E {}
            flow SimpleRequest: E -> S
        }
        """
        doc = parse_string(source)
        flow = doc.scds[0].flows[0]
        assert flow.name == "SimpleRequest"
        assert flow.type_ref is not None
        assert flow.type_ref.namespace is None
        assert flow.type_ref.name == "SimpleRequest"
        assert flow.type_ref.qualified_name == "SimpleRequest"

    def test_qualified_flow_type_ref_in_dfd_inbound(self) -> None:
        """DFD inbound boundary flows should support qualified type references."""
        source = """
        datadict PaymentGateway {
            PaymentRequest = { amount: decimal }
        }

        scd Ctx {
            system S {}
            external E {}
            flow PaymentGateway.PaymentRequest: E -> S
        }

        dfd Test {
            refines: Ctx.S
            process Handler {}
            flow PaymentGateway.PaymentRequest: -> Handler
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        assert len(dfd.flows) == 1

        flow = dfd.flows[0]
        # name is the simple name
        assert flow.name == "PaymentRequest"
        # type_ref has the full reference
        assert flow.type_ref is not None
        assert flow.type_ref.namespace == "PaymentGateway"
        assert flow.type_ref.name == "PaymentRequest"

    def test_qualified_flow_type_ref_in_dfd_outbound(self) -> None:
        """DFD outbound boundary flows should support qualified type references."""
        source = """
        datadict PaymentGateway {
            PaymentResponse = { status: string }
        }

        scd Ctx {
            system S {}
            external E {}
            flow PaymentGateway.PaymentResponse: S -> E
        }

        dfd Test {
            refines: Ctx.S
            process Handler {}
            flow PaymentGateway.PaymentResponse: Handler ->
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        flow = dfd.flows[0]

        assert flow.type_ref is not None
        assert flow.type_ref.namespace == "PaymentGateway"
        assert flow.type_ref.name == "PaymentResponse"

    def test_qualified_flow_type_ref_in_dfd_internal(self) -> None:
        """DFD internal flows should support qualified type references."""
        source = """
        datadict Internal {
            ProcessedData = { result: string }
        }

        scd Ctx {
            system S {}
        }

        dfd Test {
            refines: Ctx.S
            process A {}
            process B {}
            flow Internal.ProcessedData: A -> B
        }
        """
        doc = parse_string(source)
        dfd = doc.dfds[0]
        flow = dfd.flows[0]

        assert flow.type_ref is not None
        assert flow.type_ref.namespace == "Internal"
        assert flow.type_ref.name == "ProcessedData"

    def test_bidirectional_scd_flow_with_qualified_type(self) -> None:
        """SCD bidirectional flows should support qualified type references."""
        source = """
        datadict PaymentGateway {
            PaymentExchange = { data: string }
        }

        scd TestContext {
            system S {}
            external E {}
            flow PaymentGateway.PaymentExchange: S <-> E
        }
        """
        doc = parse_string(source)
        flow = doc.scds[0].flows[0]

        assert flow.direction == "bidirectional"
        assert flow.type_ref is not None
        assert flow.type_ref.namespace == "PaymentGateway"
        assert flow.type_ref.name == "PaymentExchange"

    def test_named_datadict_node_has_namespace(self) -> None:
        """DataDictNode should store the namespace."""
        source = """
        datadict MyNamespace {
            Type1 = { field: string }
        }
        """
        doc = parse_string(source)
        dd = doc.datadicts[0]
        assert dd.namespace == "MyNamespace"

    def test_same_namespace_multiple_blocks(self) -> None:
        """Multiple datadict blocks with same namespace should parse."""
        source = """
        datadict PaymentGateway {
            Request1 = { data: string }
        }

        datadict PaymentGateway {
            Request2 = { data: string }
        }
        """
        doc = parse_string(source)
        assert len(doc.datadicts) == 2
        assert doc.datadicts[0].namespace == "PaymentGateway"
        assert doc.datadicts[1].namespace == "PaymentGateway"


class TestQualifiedTypeRefParsing:
    """Tests for qualified type references in struct fields, unions, and arrays.

    REQ-GRAM-051: Qualified type references (Namespace.TypeName) in data dictionary.
    """

    def test_qualified_type_ref_in_struct_field(self) -> None:
        """Struct fields should support qualified type references."""
        source = """
        datadict ServiceA {
            Response = { data: string }
        }

        datadict ServiceB {
            Request = {
                serviceA_response: ServiceA.Response
                simple_field: string
            }
        }
        """
        doc = parse_string(source)
        assert len(doc.datadicts) == 2

        service_b = doc.datadicts[1]
        assert service_b.namespace == "ServiceB"

        request_def = service_b.definitions[0]
        assert request_def.name == "Request"

        struct = request_def.definition
        assert isinstance(struct, StructDefNode)
        assert len(struct.fields) == 2

        # Qualified type reference field
        qualified_field = struct.fields[0]
        assert qualified_field.name == "serviceA_response"
        assert qualified_field.type_ref.namespace == "ServiceA"
        assert qualified_field.type_ref.name == "Response"
        assert qualified_field.type_ref.qualified_name == "ServiceA.Response"

        # Simple type reference field
        simple_field = struct.fields[1]
        assert simple_field.name == "simple_field"
        assert simple_field.type_ref.namespace is None
        assert simple_field.type_ref.name == "string"

    def test_simple_type_ref_in_struct_field(self) -> None:
        """Struct fields should still support simple type references."""
        source = """
        datadict {
            Address = { street: string }
            Person = {
                name: string
                home: Address
            }
        }
        """
        doc = parse_string(source)
        person = doc.datadicts[0].definitions[1]
        struct = person.definition
        assert isinstance(struct, StructDefNode)

        name_field = struct.fields[0]
        assert name_field.type_ref.namespace is None
        assert name_field.type_ref.name == "string"

        home_field = struct.fields[1]
        assert home_field.type_ref.namespace is None
        assert home_field.type_ref.name == "Address"

    def test_qualified_type_ref_in_union(self) -> None:
        """Union alternatives should support qualified type references."""
        source = """
        datadict ServiceA {
            TypeA = { a: string }
        }

        datadict ServiceB {
            TypeB = { b: string }
        }

        datadict {
            Combined = ServiceA.TypeA | ServiceB.TypeB | "literal"
        }
        """
        doc = parse_string(source)
        combined = doc.datadicts[2].definitions[0]
        union = combined.definition
        assert isinstance(union, UnionDefNode)

        assert len(union.alternatives) == 3

        # First alternative: qualified
        alt1 = union.alternatives[0]
        assert isinstance(alt1, DataDictTypeRefNode)
        assert alt1.namespace == "ServiceA"
        assert alt1.name == "TypeA"

        # Second alternative: qualified
        alt2 = union.alternatives[1]
        assert isinstance(alt2, DataDictTypeRefNode)
        assert alt2.namespace == "ServiceB"
        assert alt2.name == "TypeB"

        # Third alternative: string literal
        alt3 = union.alternatives[2]
        assert isinstance(alt3, str)

    def test_qualified_type_ref_in_array(self) -> None:
        """Array element types should support qualified type references."""
        source = """
        datadict ServiceA {
            Item = { id: string }
        }

        datadict {
            ItemList = ServiceA.Item[]
            StringList = string[]
        }
        """
        doc = parse_string(source)

        item_list = doc.datadicts[1].definitions[0]
        array1 = item_list.definition
        assert isinstance(array1, ArrayDefNode)
        assert array1.element_type.namespace == "ServiceA"
        assert array1.element_type.name == "Item"
        assert array1.element_type.qualified_name == "ServiceA.Item"

        string_list = doc.datadicts[1].definitions[1]
        array2 = string_list.definition
        assert isinstance(array2, ArrayDefNode)
        assert array2.element_type.namespace is None
        assert array2.element_type.name == "string"

    def test_type_ref_node_properties(self) -> None:
        """DataDictTypeRefNode should have correct namespace, name, and qualified_name."""
        source = """
        datadict NS {
            TypeA = {
                qualified: Other.Type
                simple: LocalType
            }
        }
        """
        doc = parse_string(source)
        struct = doc.datadicts[0].definitions[0].definition
        assert isinstance(struct, StructDefNode)

        qualified = struct.fields[0].type_ref
        assert qualified.namespace == "Other"
        assert qualified.name == "Type"
        assert qualified.qualified_name == "Other.Type"

        simple = struct.fields[1].type_ref
        assert simple.namespace is None
        assert simple.name == "LocalType"
        assert simple.qualified_name == "LocalType"

    def test_struct_field_with_constraints_and_qualified_type(self) -> None:
        """Struct fields with qualified types and constraints should parse."""
        source = """
        datadict ServiceA {
            Config = { setting: string }
        }

        datadict {
            MyStruct = {
                config: ServiceA.Config [optional]
                name: string [pattern: "^[a-z]+$"]
            }
        }
        """
        doc = parse_string(source)
        struct = doc.datadicts[1].definitions[0].definition
        assert isinstance(struct, StructDefNode)

        config_field = struct.fields[0]
        assert config_field.type_ref.namespace == "ServiceA"
        assert config_field.type_ref.name == "Config"
        assert len(config_field.constraints) == 1
        assert config_field.constraints[0].kind == "optional"

        name_field = struct.fields[1]
        assert name_field.type_ref.namespace is None
        assert name_field.type_ref.name == "string"
        assert len(name_field.constraints) == 1
        assert name_field.constraints[0].kind == "pattern"
