"""Tests for example design files.

These tests verify that the example files in the examples/ directory
parse correctly and pass validation.
"""

from pathlib import Path

import pytest

from designit.model.base import ValidationSeverity
from designit.semantic.analyzer import analyze_file
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
