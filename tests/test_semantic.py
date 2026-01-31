"""Tests for semantic analysis."""

from designit.model.base import ValidationSeverity
from designit.semantic.analyzer import analyze_string
from designit.semantic.validator import validate


class TestSemanticAnalysis:
    """Tests for semantic analyzer."""

    def test_analyze_dfd(self) -> None:
        """Test DFD analysis."""
        source = """
        datadict {
            Request = { data: string }
        }
        dfd TestDFD {
            external User { description: "Test user" }
            process Handle { description: "Handler" }
            flow Request: User -> Handle
        }
        """
        doc = analyze_string(source)
        assert "TestDFD" in doc.dfds
        dfd = doc.dfds["TestDFD"]
        assert "User" in dfd.externals
        assert "Handle" in dfd.processes
        assert "Request" in dfd.flows

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
        dfd System {
            process Todo { ... }
            external Future { TBD }
        }
        """
        doc = analyze_string(source)
        placeholders = doc.placeholders
        assert len(placeholders) == 2


class TestValidation:
    """Tests for validation."""

    def test_valid_document(self) -> None:
        """Test validation of a valid document."""
        source = """
        datadict {
            Request = { data: string }
        }
        dfd Valid {
            external User { description: "User" }
            process Handle { description: "Handler" }
            flow Request: User -> Handle
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 0

    def test_missing_flow_endpoint(self) -> None:
        """Test validation catches missing flow endpoints."""
        source = """
        datadict {
            Request = { data: string }
        }
        dfd Invalid {
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
        """Test validation warns about orphan elements."""
        source = """
        datadict {
            Request = { data: string }
        }
        dfd Orphan {
            external User { description: "User" }
            process Unused { description: "Not connected" }
            flow Request: User -> User
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
        dfd TestDFD {
            external User {}
            process Handle {}
            flow UndefinedFlow: User -> Handle
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 1
        assert "UndefinedFlow" in errors[0].message
        assert "DFD" in errors[0].message
        assert "data dictionary" in errors[0].message.lower()

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
        dfd TestDFD {
            external User {}
            process Handle {}
            flow DefinedFlow: User -> Handle
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
        dfd TestDFD {
            external User {}
            process Handle {}
            flow DFDOnlyFlow: User -> Handle
        }
        scd TestSCD {
            system Core {}
            external Client {}
            flow SCDOnlyFlow: Client -> Core
        }
        """
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]
        assert len(errors) == 2
        error_messages = [e.message for e in errors]
        assert any("DFDOnlyFlow" in msg and "DFD" in msg for msg in error_messages)
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
        # Expected format: "Flow '<flow_name>' in SCD '<diagram_name>' is not defined in data dictionary"
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
        source = """dfd TestDFD {
    external User {}
    process Handle {}
    flow UndefinedFlow: User -> Handle
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        errors = [m for m in messages if m.severity == ValidationSeverity.ERROR]

        assert len(errors) == 1
        # This test will FAIL until we fix the parser
        assert errors[0].line is not None, "Validation error should have line number"
        assert errors[0].line == 4, f"Expected line 4, got {errors[0].line}"

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
        lines = sorted([e.line for e in errors])
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
dfd TestDFD {
    external User {}
    external Orphan {}
    process Handle {}
    flow Request: User -> Handle
}
"""
        doc = analyze_string(source)
        messages = validate(doc)
        warnings = [m for m in messages if m.severity == ValidationSeverity.WARNING]

        orphan_warning = next((w for w in warnings if "Orphan" in w.message), None)
        assert orphan_warning is not None, "Should have warning about Orphan element"
        assert orphan_warning.line is not None, "Orphan warning should have line number"
        assert orphan_warning.line == 6, f"Expected line 6, got {orphan_warning.line}"

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
