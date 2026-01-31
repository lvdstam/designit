"""Tests for the DesignIt parser."""

import pytest

from designit.parser.ast_nodes import (
    DocumentNode,
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
        """Parse a simple DFD."""
        source = """
        dfd TestSystem {
            external User {
                description: "System user"
            }
            process HandleRequest {
                description: "Handles user requests"
            }
            datastore Database {
                description: "Main database"
            }
            flow Request: User -> HandleRequest
            flow Data: HandleRequest -> Database
        }
        """
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        dfd = doc.dfds[0]
        assert dfd.name == "TestSystem"
        assert len(dfd.externals) == 1
        assert len(dfd.processes) == 1
        assert len(dfd.datastores) == 1
        assert len(dfd.flows) == 2

    def test_dfd_with_placeholder(self) -> None:
        """Parse DFD with placeholder elements."""
        source = """
        dfd System {
            process ToBeImplemented {
                ...
            }
            external User {
                TBD
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
        """ExternalNode should have source location."""
        source = """dfd Test {
    external MyExternal {}
    process P {}
    flow F: MyExternal -> P
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].externals) == 1
        ext = doc.dfds[0].externals[0]
        assert ext.location is not None, "External should have location set"
        assert ext.location.line == 2, f"Expected line 2, got {ext.location.line}"

    def test_process_node_has_location(self) -> None:
        """ProcessNode should have source location."""
        source = """dfd Test {
    external E {}
    process MyProcess {}
    flow F: E -> MyProcess
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].processes) == 1
        proc = doc.dfds[0].processes[0]
        assert proc.location is not None, "Process should have location set"
        assert proc.location.line == 3, f"Expected line 3, got {proc.location.line}"

    def test_datastore_node_has_location(self) -> None:
        """DatastoreNode should have source location."""
        source = """dfd Test {
    process P {}
    datastore MyDatastore {}
    flow F: P -> MyDatastore
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].datastores) == 1
        ds = doc.dfds[0].datastores[0]
        assert ds.location is not None, "Datastore should have location set"
        assert ds.location.line == 3, f"Expected line 3, got {ds.location.line}"

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
        source = """dfd Test {
    external A {}
    process B {}
    flow MyFlow: A -> B
}
"""
        doc = parse_string(source)
        assert len(doc.dfds) == 1
        assert len(doc.dfds[0].flows) == 1
        flow = doc.dfds[0].flows[0]
        # This test will FAIL until we fix the parser
        assert flow.location is not None, "Flow should have location set"
        assert flow.location.line == 4, f"Expected line 4, got {flow.location.line}"

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

        lines = [loc.line for loc in locations]
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
