"""Tests for semantic analysis."""

from designit.model.base import ValidationSeverity
from designit.semantic.analyzer import analyze_string
from designit.semantic.validator import validate


class TestSemanticAnalysis:
    """Tests for semantic analyzer."""

    def test_analyze_dfd(self) -> None:
        """Test DFD analysis."""
        source = """
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
