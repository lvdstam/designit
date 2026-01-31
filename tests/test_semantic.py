"""Tests for semantic analysis."""

import pytest
from designit.semantic.analyzer import analyze_string
from designit.semantic.validator import validate
from designit.model.base import ValidationSeverity


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
