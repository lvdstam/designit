"""Tests for semantic analysis."""

from designit.model.base import ValidationSeverity
from designit.semantic.analyzer import analyze_string
from designit.semantic.validator import validate


class TestSemanticAnalysis:
    """Tests for semantic analyzer."""

    def test_analyze_dfd(self) -> None:
        """Test DFD analysis with refines declaration."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system TestSystem {}
            external User { description: "Test user" }
            flow Request: User -> TestSystem
        }
        dfd TestDFD {
            refines: Context.TestSystem
            process Handle { description: "Handler" }
            flow Request: -> Handle
        }
        """
        doc = analyze_string(source)
        assert "TestDFD" in doc.dfds
        dfd = doc.dfds["TestDFD"]
        assert dfd.refines is not None
        assert dfd.refines.diagram_name == "Context"
        assert dfd.refines.element_name == "TestSystem"
        assert "Handle" in dfd.processes
        # Verify flow exists using compound key
        assert ("Request", "inbound") in dfd.flows
        # Verify flow type
        assert dfd.flows[("Request", "inbound")].flow_type == "inbound"

    def test_analyze_erd(self) -> None:
        """Test ERD analysis."""
        source = """
        erd TestERD {
            entity User {
                id: integer [pk]
                name: string
            }
        }
        """
        doc = analyze_string(source)
        assert "TestERD" in doc.erds
        erd = doc.erds["TestERD"]
        assert "User" in erd.entities
        entity = erd.entities["User"]
        assert "id" in entity.attributes
        assert entity.attributes["id"].is_primary_key

    def test_placeholder_detection(self) -> None:
        """Test that placeholders are properly detected."""
        source = """
        scd Ctx {
            system Sys {}
        }
        dfd System {
            refines: Ctx.Sys
            process Todo { ... }
        }
        """
        doc = analyze_string(source)
        placeholders = doc.placeholders
        assert len(placeholders) == 1


class TestValidation:
    """Tests for validation."""

    def test_valid_document(self) -> None:
        """Test validation of a valid document."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Valid {}
            external User { description: "User" }
            flow Request: User -> Valid
        }
        dfd ValidDFD {
            refines: Context.Valid
            process Handle { description: "Handler" }
            flow Request: -> Handle
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_missing_flow_endpoint(self) -> None:
        """Test validation catches missing flow endpoints in SCD."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Invalid {
            system Sys {}
            external User { description: "User" }
            flow Request: User -> NonExistent
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("NonExistent" in m.message for m in errors)

    def test_missing_state_in_transition(self) -> None:
        """Test validation catches missing states in transitions."""
        source = """
        std Invalid {
            state Start { description: "Start" }
            transition go: Start -> Missing
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("Missing" in m.message for m in errors)

    def test_missing_entity_in_relationship(self) -> None:
        """Test validation catches missing entities in relationships."""
        source = """
        erd Invalid {
            entity User {
                id: integer [pk]
            }
            relationship owns: User -1:n-> Order
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("Order" in m.message for m in errors)

    def test_orphan_element_warning(self) -> None:
        """Test validation warns about orphan elements in DFD."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Orphan {}
            external User { description: "User" }
            flow Request: User -> Orphan
        }
        dfd OrphanDFD {
            refines: Context.Orphan
            process Used {}
            process Unused { description: "Not connected" }
            flow Request: -> Used
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        assert any("Unused" in m.message for m in warnings)

    def test_missing_primary_key_warning(self) -> None:
        """Test validation warns about entities without primary key."""
        source = """
        erd NoPK {
            entity User {
                name: string
                email: string
            }
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        assert any("primary key" in m.message.lower() for m in warnings)


class TestSCDAnalysis:
    """Tests for SCD semantic analysis."""

    def test_analyze_scd(self) -> None:
        """Test SCD analysis creates proper model."""
        source = """
        datadict {
            Request = { data: string }
            Data = { content: string }
        }
        scd TestSCD {
            system MainSystem { description: "Main system" }
            external User { description: "User" }
            datastore DB { description: "Database" }
            flow Request: User -> MainSystem
            flow Data: MainSystem -> DB
        }
        """
        doc = analyze_string(source)
        assert "TestSCD" in doc.scds
        scd = doc.scds["TestSCD"]
        assert scd.system is not None
        assert scd.system.name == "MainSystem"
        assert "User" in scd.externals
        assert "DB" in scd.datastores
        assert "Request" in scd.flows
        assert "Data" in scd.flows

    def test_scd_flow_direction_inbound(self) -> None:
        """Test that flows to system are marked as inbound."""
        source = """
        datadict {
            Input = { data: string }
        }
        scd FlowTest {
            system Core {}
            external Client {}
            flow Input: Client -> Core
        }
        """
        doc = analyze_string(source)
        scd = doc.scds["FlowTest"]
        flow = scd.flows["Input"]
        assert flow.direction == "inbound"

    def test_scd_flow_direction_outbound(self) -> None:
        """Test that flows from system are marked as outbound."""
        source = """
        datadict {
            Output = { data: string }
        }
        scd FlowTest {
            system Core {}
            external Client {}
            flow Output: Core -> Client
        }
        """
        doc = analyze_string(source)
        scd = doc.scds["FlowTest"]
        flow = scd.flows["Output"]
        assert flow.direction == "outbound"

    def test_scd_flow_direction_bidirectional(self) -> None:
        """Test that bidirectional flows are marked correctly."""
        source = """
        datadict {
            Exchange = { data: string }
        }
        scd FlowTest {
            system Core {}
            external Partner {}
            flow Exchange: Core <-> Partner
        }
        """
        doc = analyze_string(source)
        scd = doc.scds["FlowTest"]
        flow = scd.flows["Exchange"]
        assert flow.direction == "bidirectional"


class TestSCDValidation:
    """Tests for SCD validation."""

    def test_valid_scd(self) -> None:
        """Test validation of a valid SCD."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Valid {
            system MainSystem {}
            external User {}
            flow Request: User -> MainSystem
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_missing_system_error(self) -> None:
        """Test validation catches missing system declaration."""
        source = """
        scd NoSystem {
            external User {}
            external Other {}
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("system" in m.message.lower() for m in errors)

    def test_missing_flow_endpoint_error(self) -> None:
        """Test validation catches unknown flow endpoints."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Invalid {
            system MainSystem {}
            external User {}
            flow Request: User -> NonExistent
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) > 0
        assert any("NonExistent" in m.message for m in errors)

    def test_orphan_element_warning(self) -> None:
        """Test validation warns about elements without flows."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Orphan {
            system MainSystem {}
            external User {}
            external Unused {}
            flow Request: User -> MainSystem
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        assert any("Unused" in m.message for m in warnings)

    def test_flow_not_involving_system_warning(self) -> None:
        """Test validation warns about flows not involving the system."""
        source = """
        datadict {
            Direct = { data: string }
        }
        scd BadFlow {
            system Core {}
            external A {}
            external B {}
            flow Direct: A -> B
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        assert any("not involve" in m.message.lower() or "Core" in m.message for m in warnings)


class TestFlowDataDictValidation:
    """Tests for flow data dictionary validation (REQ-SEM-061, REQ-SEM-062)."""

    def test_dfd_flow_not_in_datadict_error(self) -> None:
        """Test DFD flow not in data dictionary produces error."""
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
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        # Should have error for the DFD flow
        assert any("UndefinedFlow" in e.message and "DFD" in e.message for e in errors)

    def test_scd_flow_not_in_datadict_error(self) -> None:
        """Test SCD flow not in data dictionary produces error."""
        source = """
        scd TestSCD {
            system Core {}
            external User {}
            flow UndefinedFlow: User -> Core
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 1
        assert "UndefinedFlow" in errors[0].message
        assert "SCD" in errors[0].message
        assert "data dictionary" in errors[0].message.lower()

    def test_dfd_flow_in_datadict_no_error(self) -> None:
        """Test DFD flow defined in data dictionary produces no error."""
        source = """
        datadict {
            DefinedFlow = { data: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow DefinedFlow: User -> Sys
        }
        dfd TestDFD {
            refines: Context.Sys
            process Handle {}
            flow DefinedFlow: -> Handle
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_scd_flow_in_datadict_no_error(self) -> None:
        """Test SCD flow defined in data dictionary produces no error."""
        source = """
        datadict {
            DefinedFlow = { data: string }
        }
        scd TestSCD {
            system Core {}
            external User {}
            flow DefinedFlow: User -> Core
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_multiple_undefined_flows_multiple_errors(self) -> None:
        """Test multiple undefined flows produce multiple errors."""
        source = """
        scd TestSCD {
            system Core {}
            external UserA {}
            external UserB {}
            flow FlowA: UserA -> Core
            flow FlowB: Core -> UserB
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 2
        flow_names = [e.message for e in errors]
        assert any("FlowA" in msg for msg in flow_names)
        assert any("FlowB" in msg for msg in flow_names)

    def test_mixed_defined_undefined_flows(self) -> None:
        """Test only undefined flows produce errors."""
        source = """
        datadict {
            DefinedFlow = { data: string }
        }
        scd TestSCD {
            system Core {}
            external UserA {}
            external UserB {}
            flow DefinedFlow: UserA -> Core
            flow UndefinedFlow: Core -> UserB
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 1
        assert "UndefinedFlow" in errors[0].message
        assert "DefinedFlow" not in errors[0].message

    def test_dfd_and_scd_both_validated(self) -> None:
        """Test both DFD and SCD flows are validated against datadict."""
        source = """
        datadict {
            SharedFlow = { data: string }
        }
        scd Context {
            system Sys {}
            external User {}
            flow SCDOnlyFlow: User -> Sys
        }
        scd TestSCD {
            system Core {}
            external Client {}
            flow SCDOnlyFlow2: Client -> Core
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 2
        error_messages = [e.message for e in errors]
        assert any("SCDOnlyFlow" in msg and "SCD" in msg for msg in error_messages)

    def test_error_message_format(self) -> None:
        """Test error message has correct format per requirements."""
        source = """
        scd ContextDiagram {
            system MySystem {}
            external External {}
            flow TestFlow: External -> MySystem
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 1
        # Expected format:
        # "Flow '<flow_name>' in SCD '<diagram_name>' is not defined in data dictionary"
        assert "Flow 'TestFlow'" in errors[0].message
        assert "SCD 'ContextDiagram'" in errors[0].message
        assert "not defined in data dictionary" in errors[0].message


class TestValidationMessageLineNumbers:
    """Tests for line number tracking in validation messages."""

    def test_scd_flow_validation_error_has_line_number(self) -> None:
        """SCD flow validation errors should include line numbers."""
        source = """scd TestSCD {
    system Core {}
    external User {}
    flow UndefinedFlow: User -> Core
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) == 1
        # This test will FAIL until we fix the parser to capture line numbers
        assert errors[0].line is not None, "Validation error should have line number"
        assert errors[0].line == 4, f"Expected line 4, got {errors[0].line}"

    def test_dfd_flow_validation_error_has_line_number(self) -> None:
        """DFD flow validation errors should include line numbers."""
        source = """scd Ctx {
    system Sys {}
    external User {}
    flow UndefinedFlow: User -> Sys
}
dfd TestDFD {
    refines: Ctx.Sys
    process Handle {}
    flow UndefinedFlow: -> Handle
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        # Look for DFD-specific errors
        dfd_errors = [
            m for m in messages if m.severity == ValidationSeverity.ERROR and "DFD" in m.message
        ]

        assert len(dfd_errors) >= 1
        assert dfd_errors[0].line is not None, "Validation error should have line number"

    def test_multiple_flow_errors_have_distinct_line_numbers(self) -> None:
        """Multiple flow validation errors should have distinct line numbers."""
        source = """scd TestSCD {
    system Core {}
    external A {}
    external B {}
    flow FlowA: A -> Core
    flow FlowB: Core -> B
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) == 2
        # This test will FAIL until we fix the parser
        assert all(e.line is not None for e in errors), "All errors should have line numbers"
        lines = sorted([e.line for e in errors if e.line is not None])
        assert lines == [5, 6], f"Expected lines [5, 6], got {lines}"

    def test_flow_validation_error_has_source_file(self) -> None:
        """Flow validation errors should include source file when available."""
        source = """scd TestSCD {
    system Core {}
    external User {}
    flow UndefinedFlow: User -> Core
}
"""
        doc = analyze_string(source, filename="test.dit")
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) == 1
        assert errors[0].file == "test.dit"


class TestAllValidationMessageLineNumbers:
    """Tests for line number tracking in validation messages for ALL element types.

    REQ-SEM-002: All validation messages shall include accurate source location.
    """

    def test_erd_relationship_error_has_line_number(self) -> None:
        """ERD relationship validation errors should include line numbers."""
        source = """erd TestERD {
    entity Person {
        id: integer [pk]
    }
    relationship Owns: Person -1:n-> NonExistent
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) >= 1
        rel_error = next((e for e in errors if "NonExistent" in e.message), None)
        assert rel_error is not None, "Should have error about NonExistent entity"
        assert rel_error.line is not None, "Relationship error should have line number"
        assert rel_error.line == 5, f"Expected line 5, got {rel_error.line}"

    def test_std_transition_error_has_line_number(self) -> None:
        """STD transition validation errors should include line numbers."""
        source = """std TestSTD {
    initial: Idle
    state Idle {}
    transition BadTrans: Idle -> NonExistent
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) >= 1
        trans_error = next((e for e in errors if "NonExistent" in e.message), None)
        assert trans_error is not None, "Should have error about NonExistent state"
        assert trans_error.line is not None, "Transition error should have line number"
        assert trans_error.line == 4, f"Expected line 4, got {trans_error.line}"

    def test_structure_module_error_has_line_number(self) -> None:
        """Structure module validation errors should include line numbers."""
        source = """structure TestStructure {
    module Main {
        calls: [NonExistent]
    }
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) >= 1
        mod_error = next((e for e in errors if "NonExistent" in e.message), None)
        assert mod_error is not None, "Should have error about NonExistent module"
        assert mod_error.line is not None, "Module error should have line number"
        assert mod_error.line == 2, f"Expected line 2, got {mod_error.line}"

    def test_erd_entity_pk_warning_has_line_number(self) -> None:
        """ERD entity PK warning should include line numbers."""
        source = """erd TestERD {
    entity NoPK {
        name: string
    }
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]

        pk_warning = next((w for w in warnings if "primary key" in w.message.lower()), None)
        assert pk_warning is not None, "Should have warning about missing primary key"
        assert pk_warning.line is not None, "PK warning should have line number"
        assert pk_warning.line == 2, f"Expected line 2, got {pk_warning.line}"

    def test_dfd_orphan_warning_has_line_number(self) -> None:
        """DFD orphan element warning should include line numbers."""
        source = """datadict {
    Request = { data: string }
}
scd Ctx {
    system Sys {}
    external User {}
    flow Request: User -> Sys
}
dfd TestDFD {
    refines: Ctx.Sys
    process Handle {}
    process Orphan {}
    flow Request: -> Handle
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]

        orphan_warning = next((w for w in warnings if "Orphan" in w.message), None)
        assert orphan_warning is not None, "Should have warning about Orphan element"
        assert orphan_warning.line is not None, "Orphan warning should have line number"
        # Orphan is on line 12 in this source
        # (lines are counted from 1, with string starting with newline)
        assert orphan_warning.line == 12, f"Expected line 12, got {orphan_warning.line}"

    def test_scd_orphan_warning_has_line_number(self) -> None:
        """SCD orphan element warning should include line numbers."""
        source = """datadict {
    Request = { data: string }
}
scd TestSCD {
    system Core {}
    external User {}
    external Orphan {}
    flow Request: User -> Core
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]

        orphan_warning = next((w for w in warnings if "Orphan" in w.message), None)
        assert orphan_warning is not None, "Should have warning about Orphan element"
        assert orphan_warning.line is not None, "Orphan warning should have line number"
        assert orphan_warning.line == 7, f"Expected line 7, got {orphan_warning.line}"

    def test_std_unreachable_state_warning_has_line_number(self) -> None:
        """STD unreachable state warning should include line numbers."""
        source = """std TestSTD {
    initial: Start
    state Start {}
    state Unreachable {}
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]

        unreachable_warning = next(
            (
                w
                for w in warnings
                if "Unreachable" in w.message or "unreachable" in w.message.lower()
            ),
            None,
        )
        assert unreachable_warning is not None, "Should have warning about unreachable state"
        assert unreachable_warning.line is not None, "Unreachable warning should have line number"
        assert unreachable_warning.line == 4, f"Expected line 4, got {unreachable_warning.line}"


class TestDFDRefinementResolution:
    """Tests for DFD refinement parent resolution.

    REQ-SEM-080: Every DFD shall declare what parent element it refines.
    REQ-SEM-081: The parent reference shall be resolved and validated.
    """

    def test_refines_scd_system_valid(self) -> None:
        """DFD refining an SCD system should be valid."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd OrderContext {
            system OrderSystem {}
            external Customer {}
            flow Request: Customer -> OrderSystem
        }

        dfd Level0 {
            refines: OrderContext.OrderSystem

            process ValidateOrder {}

            flow Request: -> ValidateOrder
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_refines_dfd_process_valid(self) -> None:
        """DFD refining a DFD process should be valid."""
        source = """
        datadict {
            Request = { data: string }
            Internal = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Level0 {
            refines: Context.Sys

            process SubProcess {}

            flow Request: -> SubProcess
        }

        dfd Level1 {
            refines: Level0.SubProcess

            process DetailA {}
            process DetailB {}

            flow Request: -> DetailA
            flow Internal: DetailA -> DetailB
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_refines_nonexistent_diagram_error(self) -> None:
        """Refining a non-existent diagram should produce an error."""
        source = """
        datadict {
            F = { data: string }
        }
        dfd Test {
            refines: NonExistent.System

            process P {}

            flow F: -> P
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("NonExistent" in e.message for e in errors)

    def test_refines_nonexistent_element_error(self) -> None:
        """Refining a non-existent element should produce an error."""
        source = """
        datadict {
            F = { data: string }
        }
        scd Context {
            system RealSystem {}
            external E {}
            flow F: E -> RealSystem
        }

        dfd Test {
            refines: Context.NonExistentSystem

            process P {}

            flow F: -> P
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("NonExistentSystem" in e.message for e in errors)

    def test_refines_external_error(self) -> None:
        """Refining an external entity should produce an error."""
        source = """
        datadict {
            F = { data: string }
        }
        scd Context {
            system Sys {}
            external Customer {}
            flow F: Customer -> Sys
        }

        dfd Test {
            refines: Context.Customer

            process P {}

            flow F: -> P
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("external" in e.message.lower() or "Customer" in e.message for e in errors)

    def test_refines_datastore_error(self) -> None:
        """Refining a datastore should produce an error."""
        source = """
        datadict {
            F = { data: string }
        }
        scd Context {
            system Sys {}
            datastore DB {}
            flow F: Sys -> DB
        }

        dfd Test {
            refines: Context.DB

            process P {}

            flow F: P ->
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("datastore" in e.message.lower() or "DB" in e.message for e in errors)


class TestDFDFlowCoverage:
    """Tests for DFD flow coverage validation.

    REQ-SEM-082: Inbound flows must be handled by exactly one process.
    REQ-SEM-083: Outbound flows may be handled by zero or more processes.
    """

    def test_inbound_flow_handled_once_valid(self) -> None:
        """Inbound flow handled by exactly one process should be valid."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            flow Request: -> Handler
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_inbound_flow_not_handled_error(self) -> None:
        """Inbound flow not handled by any process should produce an error."""
        source = """
        datadict {
            Request = { data: string }
            Response = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
            flow Response: Sys -> E
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            // Missing: flow Request: -> Handler
            flow Response: Handler ->
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("Request" in e.message for e in errors)

    def test_inbound_flow_handled_twice_error(self) -> None:
        """Inbound flow handled by multiple processes should produce an error."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler1 {}
            process Handler2 {}

            flow Request: -> Handler1
            flow Request: -> Handler2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("Request" in e.message and "multiple" in e.message.lower() for e in errors)

    def test_outbound_flow_handled_once_valid(self) -> None:
        """Outbound flow handled by one process should be valid."""
        source = """
        datadict {
            Response = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Response: Sys -> E
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            flow Response: Handler ->
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_outbound_flow_handled_multiple_valid(self) -> None:
        """Outbound flow from multiple processes should be valid."""
        source = """
        datadict {
            Request = { data: string }
            Response = { data: string }
            Internal = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
            flow Response: Sys -> E
        }

        dfd Test {
            refines: Context.Sys

            process Handler1 {}
            process Handler2 {}

            flow Request: -> Handler1
            flow Response: Handler1 ->
            flow Response: Handler2 ->
            flow Internal: Handler1 -> Handler2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_outbound_flow_not_handled_valid(self) -> None:
        """Outbound flow not handled by any process should be valid (zero is allowed)."""
        source = """
        datadict {
            Request = { data: string }
            Response = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
            flow Response: Sys -> E
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            flow Request: -> Handler
            // Response not used - should be OK
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_flow_direction_mismatch_error(self) -> None:
        """Declaring inbound parent flow as outbound should produce an error."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            // Request is inbound in parent, but declared as outbound here
            flow Request: Handler ->
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("Request" in e.message and "direction" in e.message.lower() for e in errors)

    def test_internal_flow_no_parent_match_valid(self) -> None:
        """Internal flows don't need to match parent flows."""
        source = """
        datadict {
            Request = { data: string }
            InternalData = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Test {
            refines: Context.Sys

            process A {}
            process B {}

            flow Request: -> A
            flow InternalData: A -> B
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_bidirectional_parent_flow_decomposition(self) -> None:
        """Bidirectional parent flow can be decomposed into separate in/out flows."""
        source = """
        datadict {
            Exchange = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Exchange: E <-> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            // Bidirectional flow decomposed into separate inbound and outbound
            flow Exchange: -> Handler
            flow Exchange: Handler ->
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_bidirectional_inbound_only_valid(self) -> None:
        """Handling only inbound part of bidirectional flow should be valid."""
        source = """
        datadict {
            Exchange = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Exchange: E <-> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            // Only handle the inbound part
            flow Exchange: -> Handler
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"


class TestDFDDatastores:
    """Tests for DFD datastore handling.

    REQ-SEM-085: DFDs may declare local datastores.
    REQ-SEM-086: Child DFDs can reference datastores from the parent tree.
    REQ-SEM-087: No duplicate element names across the import tree.
    """

    def test_local_datastore_valid(self) -> None:
        """DFD with local datastore should be valid."""
        source = """
        datadict {
            Request = { data: string }
            CacheData = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}
            datastore LocalCache {}

            flow Request: -> Handler
            flow CacheData: Handler -> LocalCache
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_local_datastore_name_conflict_with_scd_datastore_error(self) -> None:
        """Local datastore with same name as SCD datastore should produce an error."""
        source = """
        datadict {
            Request = { data: string }
            Data = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            datastore SharedDB {}
            flow Request: E -> Sys
            flow Data: Sys -> SharedDB
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}
            datastore SharedDB {}

            flow Request: -> Handler
            flow Data: Handler -> SharedDB
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("SharedDB" in e.message and "duplicate" in e.message.lower() for e in errors)

    def test_local_datastore_name_conflict_with_external_error(self) -> None:
        """Local datastore with same name as SCD external should produce an error."""
        source = """
        datadict {
            Request = { data: string }
            Data = { data: string }
        }
        scd Context {
            system Sys {}
            external Customer {}
            flow Request: Customer -> Sys
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}
            datastore Customer {}

            flow Request: -> Handler
            flow Data: Handler -> Customer
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("Customer" in e.message and "duplicate" in e.message.lower() for e in errors)

    def test_boundary_datastore_flow_valid(self) -> None:
        """Boundary flow to SCD datastore should be valid."""
        source = """
        datadict {
            Request = { data: string }
            SaveData = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            datastore MainDB {}
            flow Request: E -> Sys
            flow SaveData: Sys -> MainDB
        }

        dfd Test {
            refines: Context.Sys

            process Handler {}

            flow Request: -> Handler
            flow SaveData: Handler ->
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_ancestor_local_datastore_accessible(self) -> None:
        """Child DFD should be able to access ancestor's local datastore."""
        source = """
        datadict {
            Request = { data: string }
            CacheData = { data: string }
            Internal = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }

        dfd Level0 {
            refines: Context.Sys

            process Handler {}
            datastore ParentCache {}

            flow Request: -> Handler
            flow CacheData: Handler -> ParentCache
        }

        dfd Level1 {
            refines: Level0.Handler

            process SubA {}
            process SubB {}

            flow Request: -> SubA
            flow CacheData: SubB ->
            flow Internal: SubA -> SubB
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"


class TestNoDuplicateNames:
    """Tests for duplicate name validation.

    REQ-SEM-087: No duplicate element names across the import tree.
    """

    def test_duplicate_system_names_error(self) -> None:
        """Duplicate system names should produce an error (REQ-SEM-087)."""
        source = """
        scd Context1 {
            system CoreSystem {}
            external Client1 {}
            flow F1: Client1 -> CoreSystem
        }

        scd Context2 {
            system CoreSystem {}
            external Client2 {}
            flow F2: Client2 -> CoreSystem
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should have error about duplicate "CoreSystem" system name
        assert len(errors) >= 1
        assert any("CoreSystem" in e.message for e in errors)

    def test_duplicate_external_names_error(self) -> None:
        """Duplicate external names should produce an error."""
        source = """
        scd Context1 {
            system Sys1 {}
            external Customer {}
            flow F1: Customer -> Sys1
        }

        scd Context2 {
            system Sys2 {}
            external Customer {}
            flow F2: Customer -> Sys2
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should have error about duplicate "Customer" name
        assert len(errors) >= 1
        assert any("Customer" in e.message for e in errors)

    def test_duplicate_process_names_across_dfds_error(self) -> None:
        """Duplicate process names across DFDs should produce an error (REQ-SEM-087)."""
        source = """
        datadict {
            Request = { data: string }
            Response = { data: string }
        }
        scd Context1 {
            system Sys1 {}
            external Client1 {}
            flow Request: Client1 -> Sys1
        }
        scd Context2 {
            system Sys2 {}
            external Client2 {}
            flow Response: Client2 -> Sys2
        }

        dfd DFD1 {
            refines: Context1.Sys1
            process Handler {}
            flow Request: -> Handler
        }

        dfd DFD2 {
            refines: Context2.Sys2
            process Handler {}
            flow Response: -> Handler
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should have error about duplicate "Handler" process name
        assert len(errors) >= 1
        assert any("Handler" in e.message for e in errors)

    def test_duplicate_datastore_names_error(self) -> None:
        """Duplicate datastore names should produce an error."""
        source = """
        scd Context1 {
            system Sys1 {}
            datastore SharedDB {}
            flow F1: Sys1 -> SharedDB
        }

        scd Context2 {
            system Sys2 {}
            datastore SharedDB {}
            flow F2: Sys2 -> SharedDB
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should have error about duplicate "SharedDB" name
        assert len(errors) >= 1
        assert any("SharedDB" in e.message for e in errors)


class TestDFDRefinementLineNumbers:
    """Tests for line number tracking in DFD refinement validation messages."""

    def test_refinement_resolution_error_has_line_number(self) -> None:
        """Refinement resolution errors should include line numbers."""
        source = """datadict {
    F = { data: string }
}
dfd Test {
    refines: NonExistent.System

    process P {}

    flow F: -> P
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) >= 1
        refines_error = next((e for e in errors if "NonExistent" in e.message), None)
        assert refines_error is not None, "Should have error about NonExistent diagram"
        assert refines_error.line is not None, "Refinement error should have line number"
        assert refines_error.line == 5, f"Expected line 5, got {refines_error.line}"

    def test_flow_coverage_error_has_line_number(self) -> None:
        """Flow coverage errors should include line numbers."""
        source = """datadict {
    Request = { data: string }
}
scd Context {
    system Sys {}
    external E {}
    flow Request: E -> Sys
}

dfd Test {
    refines: Context.Sys

    process Handler {}

    // Missing Request flow - error should point to the DFD or refines line
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) >= 1
        coverage_error = next((e for e in errors if "Request" in e.message), None)
        assert coverage_error is not None, "Should have error about missing Request flow"
        assert coverage_error.line is not None, "Coverage error should have line number"


class TestDFDFlowCompoundKeys:
    """Tests for DFD flow compound key storage (REQ-MODEL-010)."""

    def test_same_name_different_types_coexist(self) -> None:
        """Two flows with same name but different types should coexist."""
        source = """
        datadict {
            I_PicIX = { data: string }
        }
        scd Context {
            system Sys {}
            external PicIX {}
            flow I_PicIX: PicIX <-> Sys
        }
        dfd Test {
            refines: Context.Sys
            process Handler {}
            flow I_PicIX: -> Handler
            flow I_PicIX: Handler ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Test"]

        # Both flows should exist with compound keys
        assert ("I_PicIX", "inbound") in dfd.flows
        assert ("I_PicIX", "outbound") in dfd.flows

        # They should be different flow objects
        inbound = dfd.flows[("I_PicIX", "inbound")]
        outbound = dfd.flows[("I_PicIX", "outbound")]
        assert inbound.flow_type == "inbound"
        assert outbound.flow_type == "outbound"
        assert inbound.target is not None
        assert inbound.target.name == "Handler"
        assert outbound.source is not None
        assert outbound.source.name == "Handler"

    def test_internal_flow_uses_compound_key(self) -> None:
        """Internal flows should also use compound keys."""
        source = """
        datadict {
            Data = { value: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Data: E -> Sys
        }
        dfd Test {
            refines: Context.Sys
            process A {}
            process B {}
            flow Data: -> A
            flow InternalFlow: A -> B
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Test"]

        # Internal flow should use compound key
        assert ("InternalFlow", "internal") in dfd.flows
        internal = dfd.flows[("InternalFlow", "internal")]
        assert internal.flow_type == "internal"
        assert internal.source is not None
        assert internal.source.name == "A"
        assert internal.target is not None
        assert internal.target.name == "B"

    def test_duplicate_flow_same_name_and_type_warning(self) -> None:
        """Duplicate flow with same name AND type should produce validation error."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }
        dfd Test {
            refines: Context.Sys
            process A {}
            process B {}
            flow Request: -> A
            flow Request: -> B
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)

        # Should have an error about inbound flow handled by multiple processes
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        duplicate_error = next(
            (e for e in errors if "multiple processes" in e.message and "Request" in e.message),
            None,
        )
        assert duplicate_error is not None, "Should error about flow handled by multiple processes"


class TestDFDFlowHelperMethods:
    """Tests for DFD flow helper methods (REQ-MODEL-011)."""

    def test_get_flow_returns_correct_flow(self) -> None:
        """get_flow should return the correct flow by name and type."""
        source = """
        datadict {
            I_PicIX = { data: string }
        }
        scd Context {
            system Sys {}
            external PicIX {}
            flow I_PicIX: PicIX <-> Sys
        }
        dfd Test {
            refines: Context.Sys
            process Handler {}
            flow I_PicIX: -> Handler
            flow I_PicIX: Handler ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Test"]

        inbound = dfd.get_flow("I_PicIX", "inbound")
        assert inbound is not None
        assert inbound.flow_type == "inbound"

        outbound = dfd.get_flow("I_PicIX", "outbound")
        assert outbound is not None
        assert outbound.flow_type == "outbound"

    def test_get_flow_returns_none_for_nonexistent(self) -> None:
        """get_flow should return None for nonexistent flow."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }
        dfd Test {
            refines: Context.Sys
            process Handler {}
            flow Request: -> Handler
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Test"]

        # Nonexistent flow name
        assert dfd.get_flow("NonExistent", "inbound") is None

        # Existing name but wrong type
        assert dfd.get_flow("Request", "outbound") is None

    def test_get_flows_by_name_returns_all_matching(self) -> None:
        """get_flows_by_name should return all flows with that name."""
        source = """
        datadict {
            I_PicIX = { data: string }
        }
        scd Context {
            system Sys {}
            external PicIX {}
            flow I_PicIX: PicIX <-> Sys
        }
        dfd Test {
            refines: Context.Sys
            process Handler {}
            flow I_PicIX: -> Handler
            flow I_PicIX: Handler ->
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Test"]

        flows = dfd.get_flows_by_name("I_PicIX")
        assert len(flows) == 2
        flow_types = {f.flow_type for f in flows}
        assert flow_types == {"inbound", "outbound"}

    def test_get_flows_by_name_returns_empty_for_nonexistent(self) -> None:
        """get_flows_by_name should return empty list for nonexistent name."""
        source = """
        datadict {
            Request = { data: string }
        }
        scd Context {
            system Sys {}
            external E {}
            flow Request: E -> Sys
        }
        dfd Test {
            refines: Context.Sys
            process Handler {}
            flow Request: -> Handler
        }
        """
        doc = analyze_string(source)
        dfd = doc.dfds["Test"]

        flows = dfd.get_flows_by_name("NonExistent")
        assert flows == []


class TestNamespacedDataDict:
    """Tests for namespaced data dictionary validation.

    REQ-GRAM-051: Named data dictionary with namespace identifier.
    REQ-SEM-063: Namespaced types must be qualified in flows.
    REQ-SEM-064: Cross-namespace reference restriction.
    REQ-SEM-065: Datadict namespace merging.
    """

    def test_qualified_namespaced_type_valid(self) -> None:
        """Using qualified namespaced type in flow should be valid."""
        source = """
        datadict PaymentGateway {
            PaymentRequest = { amount: decimal }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow PaymentGateway.PaymentRequest: Sys -> PayGw
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_unqualified_namespaced_type_error(self) -> None:
        """Using unqualified namespaced type in flow should produce an error (REQ-SEM-063)."""
        source = """
        datadict PaymentGateway {
            PaymentRequest = { amount: decimal }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow PaymentRequest: Sys -> PayGw
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        # Should mention that the type exists in a namespace
        assert any(
            "PaymentRequest" in e.message
            and ("namespace" in e.message.lower() or "qualified" in e.message.lower())
            for e in errors
        )

    def test_anonymous_type_no_qualification_needed(self) -> None:
        """Anonymous datadict types should work without qualification."""
        source = """
        datadict {
            SimpleRequest = { data: string }
        }

        scd Context {
            system Sys {}
            external E {}
            flow SimpleRequest: E -> Sys
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_namespace_merging_same_namespace(self) -> None:
        """Multiple datadict blocks with same namespace should merge (REQ-SEM-065)."""
        source = """
        datadict PaymentGateway {
            Request1 = { data: string }
        }

        datadict PaymentGateway {
            Request2 = { data: string }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow PaymentGateway.Request1: Sys -> PayGw
            flow PaymentGateway.Request2: PayGw -> Sys
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

        # Verify both types exist in datadict
        dd = doc.data_dictionary
        assert dd is not None
        assert "PaymentGateway.Request1" in dd.definitions
        assert "PaymentGateway.Request2" in dd.definitions

    def test_namespace_merging_duplicate_type_error(self) -> None:
        """Duplicate type name within same namespace should produce an error (REQ-SEM-065).

        When multiple datadict blocks with the same namespace define a type with
        the same name, this should be reported as an error.
        """
        source = """
        datadict PaymentGateway {
            Request = { id: string }
        }

        datadict PaymentGateway {
            Request = { other: string }
        }

        scd Context {
            system Sys {}
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        # Combine messages from both analyzer and validator
        all_messages = list(doc.validation_messages) + messages
        errors = [m for m in all_messages if m.severity == ValidationSeverity.ERROR]

        # Should have an error about duplicate type definition
        assert len(errors) >= 1, "Expected error for duplicate type in namespace"
        assert any(
            "duplicate" in e.message.lower() and "request" in e.message.lower() for e in errors
        ), f"Expected duplicate type error, got: {[e.message for e in errors]}"

    def test_cross_namespace_reference_error(self) -> None:
        """Type in named datadict referencing another namespace should error (REQ-SEM-064).

        A type in ServiceB cannot reference ServiceA.TypeA.
        Only same-namespace or anonymous types can be referenced.
        """
        source = """
        datadict ServiceA {
            TypeA = { data: string }
        }

        datadict ServiceB {
            TypeB = { ref: ServiceA.TypeA }
        }

        scd Context {
            system Sys {}
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any(
            "namespace" in e.message.lower() and "reference" in e.message.lower() for e in errors
        )

    def test_namespaced_type_can_reference_anonymous_type(self) -> None:
        """Type in named datadict can reference anonymous datadict types."""
        source = """
        datadict {
            CommonType = { id: string }
        }

        datadict ServiceA {
            TypeA = { common: CommonType }
        }

        scd Context {
            system Sys {}
            external Svc {}
            flow ServiceA.TypeA: Sys -> Svc
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should not have cross-namespace error for referencing anonymous types
        cross_ns_errors = [
            e
            for e in errors
            if "namespace" in e.message.lower() and "reference" in e.message.lower()
        ]
        assert len(cross_ns_errors) == 0, f"Got cross-namespace errors: {cross_ns_errors}"

    def test_namespaced_type_can_reference_same_namespace(self) -> None:
        """Type in named datadict can reference types in same namespace."""
        source = """
        datadict PaymentGateway {
            Amount = { value: decimal }
            PaymentRequest = { amount: Amount }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow PaymentGateway.PaymentRequest: Sys -> PayGw
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_dfd_qualified_flow_type_valid(self) -> None:
        """DFD flows with qualified namespaced types should be valid."""
        source = """
        datadict PaymentGateway {
            PaymentRequest = { amount: decimal }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow PaymentGateway.PaymentRequest: PayGw -> Sys
        }

        dfd Level0 {
            refines: Context.Sys

            process Handler {}

            flow PaymentGateway.PaymentRequest: -> Handler
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0, f"Expected no errors, got: {[e.message for e in errors]}"

    def test_dfd_unqualified_namespaced_type_error(self) -> None:
        """DFD flows with unqualified namespaced types should error."""
        source = """
        datadict PaymentGateway {
            PaymentRequest = { amount: decimal }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow PaymentGateway.PaymentRequest: PayGw -> Sys
        }

        dfd Level0 {
            refines: Context.Sys

            process Handler {}

            flow PaymentRequest: -> Handler
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        assert any("PaymentRequest" in e.message for e in errors)

    def test_datadict_model_qualified_name_property(self) -> None:
        """DataDefinition.qualified_name should return correct value."""
        source = """
        datadict MyNamespace {
            MyType = { data: string }
        }

        datadict {
            AnonymousType = { data: string }
        }
        """
        doc = analyze_string(source)
        dd = doc.data_dictionary
        assert dd is not None

        # Namespaced type
        ns_type = dd.definitions.get("MyNamespace.MyType")
        assert ns_type is not None
        assert ns_type.qualified_name == "MyNamespace.MyType"
        assert ns_type.namespace == "MyNamespace"
        assert ns_type.name == "MyType"

        # Anonymous type
        anon_type = dd.definitions.get("AnonymousType")
        assert anon_type is not None
        assert anon_type.qualified_name == "AnonymousType"
        assert anon_type.namespace is None
        assert anon_type.name == "AnonymousType"

    def test_datadict_model_helper_methods(self) -> None:
        """DataDictionaryModel helper methods should work correctly."""
        source = """
        datadict {
            AnonType1 = { data: string }
            AnonType2 = { data: string }
        }

        datadict ServiceA {
            TypeA = { data: string }
        }

        datadict ServiceB {
            TypeB = { data: string }
        }
        """
        doc = analyze_string(source)
        dd = doc.data_dictionary
        assert dd is not None

        # Test get_anonymous_types
        anon = dd.get_anonymous_types()
        assert "AnonType1" in anon
        assert "AnonType2" in anon
        assert "ServiceA.TypeA" not in anon

        # Test get_namespaced_types
        namespaced = dd.get_namespaced_types()
        assert "ServiceA.TypeA" in namespaced
        assert "ServiceB.TypeB" in namespaced
        assert "AnonType1" not in namespaced

        # Test get_namespaces
        namespaces = dd.get_namespaces()
        assert "ServiceA" in namespaces
        assert "ServiceB" in namespaces

        # Test get_types_by_namespace
        service_a_types = dd.get_types_by_namespace("ServiceA")
        assert "ServiceA.TypeA" in service_a_types
        assert "ServiceB.TypeB" not in service_a_types

    def test_namespace_shadowing_warning(self) -> None:
        """Namespace name matching global type name should emit warning (REQ-SEM-066)."""
        source = """
        datadict {
            Request = { id: string }
        }

        datadict Request {
            Payload = { data: string }
        }

        scd Context {
            system Sys {}
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        assert len(warnings) >= 1
        # Should warn that namespace "Request" shadows global type "Request"
        assert any("shadow" in w.message.lower() for w in warnings)
        assert any("Request" in w.message for w in warnings)

    def test_namespace_shadowing_warning_includes_both_names(self) -> None:
        """Namespace shadowing warning should mention both namespace and type."""
        source = """
        datadict {
            Common = { id: string }
        }

        datadict Common {
            Payload = { data: string }
        }

        scd Context {
            system Sys {}
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]
        shadowing_warnings = [w for w in warnings if "shadow" in w.message.lower()]
        assert len(shadowing_warnings) >= 1
        # Warning should mention "Common" (both as namespace and type)
        assert any("Common" in w.message for w in shadowing_warnings)

    def test_type_resolution_same_namespace_first(self) -> None:
        """Type resolution should prefer same namespace over global (REQ-SEM-067)."""
        source = """
        datadict {
            Amount = { value: string }
        }

        datadict Payment {
            Amount = { value: decimal }
            Request = { amount: Amount }
        }

        scd Context {
            system Sys {}
            external PayGw {}
            flow Payment.Request: Sys -> PayGw
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # Should resolve Amount to Payment.Amount (same namespace), not global Amount
        # No undefined type errors expected
        undefined_errors = [e for e in errors if "undefined" in e.message.lower()]
        assert len(undefined_errors) == 0, f"Got undefined errors: {undefined_errors}"

    def test_type_resolution_fallback_to_global(self) -> None:
        """Type resolution should fall back to global when not in same namespace."""
        source = """
        datadict {
            CommonId = { value: string }
        }

        datadict ServiceA {
            Request = { id: CommonId }
        }

        scd Context {
            system Sys {}
            external Svc {}
            flow ServiceA.Request: Sys -> Svc
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # CommonId should resolve to global CommonId (no ServiceA.CommonId exists)
        undefined_errors = [e for e in errors if "undefined" in e.message.lower()]
        assert len(undefined_errors) == 0, f"Got undefined errors: {undefined_errors}"

    def test_qualified_ref_to_different_namespace_error(self) -> None:
        """Qualified reference to different namespace should error (REQ-SEM-064)."""
        source = """
        datadict ServiceA {
            TypeA = { data: string }
        }

        datadict ServiceB {
            TypeB = { ref: ServiceA.TypeA }
        }

        scd Context {
            system Sys {}
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) >= 1
        # Should error about cross-namespace reference
        cross_ns_errors = [
            e for e in errors if "namespace" in e.message.lower() or "cross" in e.message.lower()
        ]
        assert len(cross_ns_errors) >= 1, f"Expected cross-namespace error, got: {errors}"

    def test_qualified_ref_exact_resolution(self) -> None:
        """Qualified type reference should resolve to exact qualified name."""
        source = """
        datadict {
            TypeA = { data: string }
        }

        datadict ServiceA {
            TypeA = { data: decimal }
            TypeB = { ref: ServiceA.TypeA }
        }

        scd Context {
            system Sys {}
            external Svc {}
            flow ServiceA.TypeB: Sys -> Svc
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        # ServiceA.TypeA should resolve exactly to ServiceA.TypeA (not global TypeA)
        # This is allowed because it's the same namespace
        cross_ns_errors = [
            e
            for e in errors
            if "namespace" in e.message.lower() and "reference" in e.message.lower()
        ]
        assert len(cross_ns_errors) == 0, f"Got unexpected errors: {cross_ns_errors}"
