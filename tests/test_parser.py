"""Tests for the DesignIt parser."""

import pytest
from designit.parser.parser import parse_string, ParseError
from designit.parser.ast_nodes import (
    DocumentNode,
    DFDNode,
    ERDNode,
    STDNode,
    StructureNode,
    DataDictNode,
)


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
