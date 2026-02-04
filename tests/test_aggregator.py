"""Tests for flow aggregation (REQ-GEN-070, REQ-GEN-071, REQ-GEN-072, REQ-GEN-073, REQ-CLI-027)."""

from __future__ import annotations

import pytest

from designit.model.base import DesignDocument, ElementReference
from designit.model.datadict import (
    DataDefinition,
    DataDictionaryModel,
    StructType,
    TypeRef,
    UnionType,
)
from designit.model.dfd import DataFlow, DFDModel, FlowTypeRef, Process
from designit.model.scd import SCDExternalEntity, SCDFlow, SCDFlowTypeRef, SCDModel, System
from designit.semantic.aggregator import aggregate_flows

# =============================================================================
# Test Fixtures
# =============================================================================


def make_scd_flow(
    name: str,
    source: str,
    target: str,
    direction: str = "inbound",
    namespace: str | None = None,
) -> SCDFlow:
    """Helper to create an SCDFlow.

    Args:
        name: The flow name (type name without namespace).
        source: Source element name.
        target: Target element name.
        direction: Flow direction.
        namespace: Optional namespace for the type_ref. If provided, creates
                   a type_ref with this namespace and the name.
    """
    type_ref = None
    if namespace is not None:
        type_ref = SCDFlowTypeRef(namespace=namespace, name=name)
    return SCDFlow(
        name=name,
        source=ElementReference(name=source),
        target=ElementReference(name=target),
        direction=direction,  # type: ignore[arg-type]
        type_ref=type_ref,
    )


def make_dfd_flow(
    name: str,
    source: str | None,
    target: str | None,
    flow_type: str = "internal",
    namespace: str | None = None,
) -> DataFlow:
    """Helper to create a DataFlow.

    Args:
        name: The flow name (type name without namespace).
        source: Source element name (None for inbound boundary flows).
        target: Target element name (None for outbound boundary flows).
        flow_type: Flow type (internal, inbound, outbound, bidirectional).
        namespace: Optional namespace for the type_ref. If provided, creates
                   a type_ref with this namespace and the name.
    """
    type_ref = None
    if namespace is not None:
        type_ref = FlowTypeRef(namespace=namespace, name=name)
    return DataFlow(
        name=name,
        source=ElementReference(name=source) if source else None,
        target=ElementReference(name=target) if target else None,
        flow_type=flow_type,  # type: ignore[arg-type]
        type_ref=type_ref,
    )


def make_union_type(alternatives: list[str]) -> UnionType:
    """Helper to create a UnionType."""
    return UnionType(alternatives=[TypeRef(name=a) for a in alternatives])


def make_data_dict(definitions: dict[str, DataDefinition]) -> DataDictionaryModel:
    """Helper to create a DataDictionaryModel."""
    return DataDictionaryModel(definitions=definitions)


def make_document(
    scds: dict[str, SCDModel] | None = None,
    dfds: dict[str, DFDModel] | None = None,
    data_dictionary: DataDictionaryModel | None = None,
) -> DesignDocument:
    """Helper to create a DesignDocument."""
    return DesignDocument(
        name="test",
        scds=scds or {},
        dfds=dfds or {},
        data_dictionary=data_dictionary,
    )


# =============================================================================
# Basic Functionality Tests
# =============================================================================


class TestAggregationBasics:
    """Test basic aggregation behavior."""

    def test_no_aggregation_without_data_dictionary(self) -> None:
        """Without a data dictionary, no aggregation occurs."""
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys"),
                "BankTransfer": make_scd_flow("BankTransfer", "Customer", "Sys"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=None)

        result = aggregate_flows(doc)

        # Document should be unchanged (same object)
        assert result is doc
        assert len(result.scds["Test"].flows) == 2

    def test_empty_document_unchanged(self) -> None:
        """Empty document remains unchanged."""
        doc = make_document()
        result = aggregate_flows(doc)
        assert result is doc

    def test_single_flow_unchanged(self) -> None:
        """Single flow is not aggregated."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={"CreditCard": make_scd_flow("CreditCard", "Customer", "Sys")},
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Single flow should remain unchanged
        assert len(result.scds["Test"].flows) == 1
        assert "CreditCard" in result.scds["Test"].flows


# =============================================================================
# Type Aggregation Tests (REQ-GEN-070)
# =============================================================================


class TestTypeAggregation:
    """Test union type coverage aggregation."""

    def test_scd_union_subtypes_aggregated_to_parent(self) -> None:
        """Flows covering all union subtypes aggregate to parent type (REQ-GEN-070)."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys"),
                "BankTransfer": make_scd_flow("BankTransfer", "Customer", "Sys"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        assert len(result.scds["Test"].flows) == 1
        assert "PaymentMethod" in result.scds["Test"].flows
        flow = result.scds["Test"].flows["PaymentMethod"]
        assert flow.source.name == "Customer"
        assert flow.target.name == "Sys"
        assert flow.direction == "inbound"

    def test_partial_coverage_no_aggregation(self) -> None:
        """Partial coverage does not aggregate (REQ-GEN-072)."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer", "Cash"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
                "Cash": DataDefinition(name="Cash", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys"),
                "BankTransfer": make_scd_flow("BankTransfer", "Customer", "Sys"),
                # Cash is missing
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should remain as individual flows
        assert len(result.scds["Test"].flows) == 2
        assert "CreditCard" in result.scds["Test"].flows
        assert "BankTransfer" in result.scds["Test"].flows

    def test_same_endpoints_required_for_aggregation(self) -> None:
        """Flows must have same endpoints to aggregate."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={
                "Customer": SCDExternalEntity(name="Customer"),
                "Merchant": SCDExternalEntity(name="Merchant"),
            },
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys"),
                "BankTransfer": make_scd_flow("BankTransfer", "Merchant", "Sys"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Different sources - should not aggregate
        assert len(result.scds["Test"].flows) == 2

    def test_same_direction_required_for_aggregation(self) -> None:
        """Flows must have same direction to aggregate."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys", "inbound"),
                "BankTransfer": make_scd_flow("BankTransfer", "Customer", "Sys", "outbound"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Different directions - should not aggregate
        assert len(result.scds["Test"].flows) == 2

    def test_enum_unions_not_aggregated(self) -> None:
        """Enum unions (quoted strings) are not aggregated."""
        data_dict = make_data_dict(
            {
                "Status": DataDefinition(
                    name="Status",
                    definition=UnionType(alternatives=['"active"', '"inactive"']),
                ),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                '"active"': make_scd_flow('"active"', "Customer", "Sys"),
                '"inactive"': make_scd_flow('"inactive"', "Customer", "Sys"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Enum unions should not aggregate
        assert len(result.scds["Test"].flows) == 2


# =============================================================================
# Highest-Level Aggregation Tests (REQ-GEN-071)
# =============================================================================


class TestHighestLevelAggregation:
    """Test aggregation to highest union level."""

    def test_nested_union_aggregates_to_highest_level(self) -> None:
        """Nested unions aggregate to highest level with complete coverage (REQ-GEN-071)."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CardPayment", "BankTransfer"]),
                ),
                "CardPayment": DataDefinition(
                    name="CardPayment",
                    definition=make_union_type(["CreditCard", "DebitCard"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "DebitCard": DataDefinition(name="DebitCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys"),
                "DebitCard": make_scd_flow("DebitCard", "Customer", "Sys"),
                "BankTransfer": make_scd_flow("BankTransfer", "Customer", "Sys"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to PaymentMethod (highest level)
        assert len(result.scds["Test"].flows) == 1
        assert "PaymentMethod" in result.scds["Test"].flows

    def test_nested_union_partial_aggregation(self) -> None:
        """Partial coverage aggregates to intermediate level."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CardPayment", "BankTransfer"]),
                ),
                "CardPayment": DataDefinition(
                    name="CardPayment",
                    definition=make_union_type(["CreditCard", "DebitCard"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "DebitCard": DataDefinition(name="DebitCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "CreditCard": make_scd_flow("CreditCard", "Customer", "Sys"),
                "DebitCard": make_scd_flow("DebitCard", "Customer", "Sys"),
                # BankTransfer is missing
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to CardPayment (intermediate level)
        assert len(result.scds["Test"].flows) == 1
        assert "CardPayment" in result.scds["Test"].flows


# =============================================================================
# Direction Aggregation Tests
# =============================================================================


class TestDirectionAggregation:
    """Test inbound/outbound -> bidirectional aggregation."""

    def test_scd_opposite_directions_become_bidirectional(self) -> None:
        """SCD flows with opposite directions and same label become bidirectional."""
        data_dict = make_data_dict(
            {
                "Data": DataDefinition(name="Data", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "Data_in": SCDFlow(
                    name="Data",
                    source=ElementReference(name="Customer"),
                    target=ElementReference(name="Sys"),
                    direction="inbound",
                ),
                "Data_out": SCDFlow(
                    name="Data",
                    source=ElementReference(name="Sys"),
                    target=ElementReference(name="Customer"),
                    direction="outbound",
                ),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should become one bidirectional flow
        assert len(result.scds["Test"].flows) == 1
        flow = list(result.scds["Test"].flows.values())[0]
        assert flow.name == "Data"
        assert flow.direction == "bidirectional"

    def test_different_labels_no_direction_aggregation(self) -> None:
        """Flows with different labels don't aggregate directions."""
        data_dict = make_data_dict(
            {
                "Request": DataDefinition(name="Request", definition=StructType()),
                "Response": DataDefinition(name="Response", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Customer": SCDExternalEntity(name="Customer")},
            flows={
                "Request": SCDFlow(
                    name="Request",
                    source=ElementReference(name="Customer"),
                    target=ElementReference(name="Sys"),
                    direction="inbound",
                ),
                "Response": SCDFlow(
                    name="Response",
                    source=ElementReference(name="Sys"),
                    target=ElementReference(name="Customer"),
                    direction="outbound",
                ),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Different names - should remain separate
        assert len(result.scds["Test"].flows) == 2


# =============================================================================
# Cross-Direction Type Aggregation Tests (REQ-GEN-073)
# =============================================================================


class TestCrossDirectionTypeAggregation:
    """Test aggregation of opposite-direction flows covering a union (REQ-GEN-073)."""

    def test_scd_cross_direction_subtypes_aggregate_to_bidirectional(self) -> None:
        """SCD flows with subtypes in opposite directions aggregate to bidirectional parent.

        This tests the case where:
        - SubtypeA flows from External -> System (inbound)
        - SubtypeB flows from System -> External (outbound)
        - SubtypeA and SubtypeB are subtypes of ParentType

        Expected result: Single bidirectional flow with ParentType.
        """
        data_dict = make_data_dict(
            {
                "PICiX.IPICiX": DataDefinition(
                    name="IPICiX",
                    namespace="PICiX",
                    definition=make_union_type(["PICiX_to_System", "System_to_PICiX"]),
                ),
                "PICiX.PICiX_to_System": DataDefinition(
                    name="PICiX_to_System",
                    namespace="PICiX",
                    definition=StructType(),
                ),
                "PICiX.System_to_PICiX": DataDefinition(
                    name="System_to_PICiX",
                    namespace="PICiX",
                    definition=StructType(),
                ),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"PICiX": SCDExternalEntity(name="PICiX")},
            flows={
                "PICiX_to_System": make_scd_flow(
                    "PICiX_to_System", "PICiX", "Sys", "inbound", namespace="PICiX"
                ),
                "System_to_PICiX": make_scd_flow(
                    "System_to_PICiX", "Sys", "PICiX", "outbound", namespace="PICiX"
                ),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to bidirectional PICiX.IPICiX
        assert len(result.scds["Test"].flows) == 1
        flow = list(result.scds["Test"].flows.values())[0]
        assert flow.name == "PICiX.IPICiX"
        assert flow.direction == "bidirectional"

    def test_scd_cross_direction_nested_union_aggregates_to_highest(self) -> None:
        """Cross-direction flows covering nested union aggregate to highest level.

        This tests multi-level type hierarchy:
        - A flows inbound, B flows outbound (A and B are subtypes of AB)
        - C flows inbound, D flows outbound (C and D are subtypes of CD)
        - AB and CD are subtypes of ParentType

        All 4 flows should aggregate to ParentType.
        """
        data_dict = make_data_dict(
            {
                "NS.Parent": DataDefinition(
                    name="Parent",
                    namespace="NS",
                    definition=make_union_type(["AB", "CD"]),
                ),
                "NS.AB": DataDefinition(
                    name="AB",
                    namespace="NS",
                    definition=make_union_type(["A", "B"]),
                ),
                "NS.CD": DataDefinition(
                    name="CD",
                    namespace="NS",
                    definition=make_union_type(["C", "D"]),
                ),
                "NS.A": DataDefinition(name="A", namespace="NS", definition=StructType()),
                "NS.B": DataDefinition(name="B", namespace="NS", definition=StructType()),
                "NS.C": DataDefinition(name="C", namespace="NS", definition=StructType()),
                "NS.D": DataDefinition(name="D", namespace="NS", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Ext": SCDExternalEntity(name="Ext")},
            flows={
                "A": make_scd_flow("A", "Ext", "Sys", "inbound", namespace="NS"),
                "B": make_scd_flow("B", "Sys", "Ext", "outbound", namespace="NS"),
                "C": make_scd_flow("C", "Ext", "Sys", "inbound", namespace="NS"),
                "D": make_scd_flow("D", "Sys", "Ext", "outbound", namespace="NS"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to NS.Parent
        assert len(result.scds["Test"].flows) == 1
        flow = list(result.scds["Test"].flows.values())[0]
        assert flow.name == "NS.Parent"
        assert flow.direction == "bidirectional"

    def test_scd_cross_direction_partial_coverage_no_aggregation(self) -> None:
        """Partial cross-direction coverage does not aggregate.

        If only some subtypes of a union flow in opposite directions,
        they should remain as separate flows.
        """
        data_dict = make_data_dict(
            {
                "NS.Parent": DataDefinition(
                    name="Parent",
                    namespace="NS",
                    definition=make_union_type(["A", "B", "C"]),
                ),
                "NS.A": DataDefinition(name="A", namespace="NS", definition=StructType()),
                "NS.B": DataDefinition(name="B", namespace="NS", definition=StructType()),
                "NS.C": DataDefinition(name="C", namespace="NS", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Ext": SCDExternalEntity(name="Ext")},
            flows={
                "A": make_scd_flow("A", "Ext", "Sys", "inbound", namespace="NS"),
                "B": make_scd_flow("B", "Sys", "Ext", "outbound", namespace="NS"),
                # C is missing
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should remain as separate flows (partial coverage)
        assert len(result.scds["Test"].flows) == 2

    def test_scd_cross_direction_preserves_existing_bidirectional(self) -> None:
        """Existing bidirectional flows are preserved during cross-direction aggregation."""
        data_dict = make_data_dict(
            {
                "NS.Parent": DataDefinition(
                    name="Parent",
                    namespace="NS",
                    definition=make_union_type(["A", "B"]),
                ),
                "NS.A": DataDefinition(name="A", namespace="NS", definition=StructType()),
                "NS.B": DataDefinition(name="B", namespace="NS", definition=StructType()),
                "Other": DataDefinition(name="Other", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Ext": SCDExternalEntity(name="Ext")},
            flows={
                "A": make_scd_flow("A", "Ext", "Sys", "inbound", namespace="NS"),
                "B": make_scd_flow("B", "Sys", "Ext", "outbound", namespace="NS"),
                "Other": make_scd_flow("Other", "Ext", "Sys", "bidirectional"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should have aggregated NS.Parent and preserved Other
        assert len(result.scds["Test"].flows) == 2
        flow_names = {f.name for f in result.scds["Test"].flows.values()}
        assert "NS.Parent" in flow_names
        assert "Other" in flow_names

    def test_dfd_boundary_cross_direction_aggregates(self) -> None:
        """DFD boundary flows with cross-direction subtypes aggregate to bidirectional."""
        data_dict = make_data_dict(
            {
                "NS.Parent": DataDefinition(
                    name="Parent",
                    namespace="NS",
                    definition=make_union_type(["Inbound", "Outbound"]),
                ),
                "NS.Inbound": DataDefinition(
                    name="Inbound", namespace="NS", definition=StructType()
                ),
                "NS.Outbound": DataDefinition(
                    name="Outbound", namespace="NS", definition=StructType()
                ),
            }
        )
        dfd = DFDModel(
            name="Test",
            processes={"Handler": Process(name="Handler")},
            flows={
                ("Inbound", "inbound"): make_dfd_flow(
                    "Inbound", None, "Handler", "inbound", namespace="NS"
                ),
                ("Outbound", "outbound"): make_dfd_flow(
                    "Outbound", "Handler", None, "outbound", namespace="NS"
                ),
            },
        )
        doc = make_document(dfds={"Test": dfd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to bidirectional NS.Parent
        flows = result.dfds["Test"].flows
        assert len(flows) == 1
        flow = list(flows.values())[0]
        assert flow.name == "NS.Parent"
        assert flow.flow_type == "bidirectional"

    def test_dfd_internal_cross_direction_aggregates(self) -> None:
        """DFD internal flows with cross-direction subtypes aggregate."""
        data_dict = make_data_dict(
            {
                "NS.Parent": DataDefinition(
                    name="Parent",
                    namespace="NS",
                    definition=make_union_type(["Forward", "Backward"]),
                ),
                "NS.Forward": DataDefinition(
                    name="Forward", namespace="NS", definition=StructType()
                ),
                "NS.Backward": DataDefinition(
                    name="Backward", namespace="NS", definition=StructType()
                ),
            }
        )
        dfd = DFDModel(
            name="Test",
            processes={
                "ProcessA": Process(name="ProcessA"),
                "ProcessB": Process(name="ProcessB"),
            },
            flows={
                ("Forward", "internal"): make_dfd_flow(
                    "Forward", "ProcessA", "ProcessB", "internal", namespace="NS"
                ),
                ("Backward", "internal"): make_dfd_flow(
                    "Backward", "ProcessB", "ProcessA", "internal", namespace="NS"
                ),
            },
        )
        doc = make_document(dfds={"Test": dfd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to single internal NS.Parent
        flows = result.dfds["Test"].flows
        assert len(flows) == 1
        flow = list(flows.values())[0]
        assert flow.name == "NS.Parent"
        assert flow.flow_type == "internal"

    def test_cross_direction_without_namespace_uses_flow_name(self) -> None:
        """Cross-direction aggregation works with non-namespaced types."""
        data_dict = make_data_dict(
            {
                "Parent": DataDefinition(
                    name="Parent",
                    definition=make_union_type(["Inbound", "Outbound"]),
                ),
                "Inbound": DataDefinition(name="Inbound", definition=StructType()),
                "Outbound": DataDefinition(name="Outbound", definition=StructType()),
            }
        )
        scd = SCDModel(
            name="Test",
            system=System(name="Sys"),
            externals={"Ext": SCDExternalEntity(name="Ext")},
            flows={
                "Inbound": make_scd_flow("Inbound", "Ext", "Sys", "inbound"),
                "Outbound": make_scd_flow("Outbound", "Sys", "Ext", "outbound"),
            },
        )
        doc = make_document(scds={"Test": scd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to Parent
        assert len(result.scds["Test"].flows) == 1
        flow = list(result.scds["Test"].flows.values())[0]
        assert flow.name == "Parent"
        assert flow.direction == "bidirectional"


# =============================================================================
# DFD Aggregation Tests
# =============================================================================


class TestDFDAggregation:
    """Test DFD-specific aggregation behavior."""

    def test_dfd_boundary_flows_aggregate(self) -> None:
        """DFD boundary flows with same process aggregate by type."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        dfd = DFDModel(
            name="Test",
            processes={"Handler": Process(name="Handler")},
            flows={
                ("CreditCard", "inbound"): make_dfd_flow("CreditCard", None, "Handler", "inbound"),
                ("BankTransfer", "inbound"): make_dfd_flow(
                    "BankTransfer", None, "Handler", "inbound"
                ),
            },
        )
        doc = make_document(dfds={"Test": dfd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to PaymentMethod
        flows = result.dfds["Test"].flows
        assert len(flows) == 1
        flow = list(flows.values())[0]
        assert flow.name == "PaymentMethod"

    def test_dfd_internal_flows_aggregate(self) -> None:
        """DFD internal flows with same endpoints aggregate by type."""
        data_dict = make_data_dict(
            {
                "PaymentMethod": DataDefinition(
                    name="PaymentMethod",
                    definition=make_union_type(["CreditCard", "BankTransfer"]),
                ),
                "CreditCard": DataDefinition(name="CreditCard", definition=StructType()),
                "BankTransfer": DataDefinition(name="BankTransfer", definition=StructType()),
            }
        )
        dfd = DFDModel(
            name="Test",
            processes={
                "Validate": Process(name="Validate"),
                "Process": Process(name="Process"),
            },
            flows={
                ("CreditCard", "internal"): make_dfd_flow(
                    "CreditCard", "Validate", "Process", "internal"
                ),
                ("BankTransfer", "internal"): make_dfd_flow(
                    "BankTransfer", "Validate", "Process", "internal"
                ),
            },
        )
        doc = make_document(dfds={"Test": dfd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should aggregate to PaymentMethod
        flows = result.dfds["Test"].flows
        assert len(flows) == 1
        flow = list(flows.values())[0]
        assert flow.name == "PaymentMethod"

    def test_dfd_boundary_direction_aggregation(self) -> None:
        """DFD inbound and outbound boundary flows with same label become bidirectional."""
        data_dict = make_data_dict(
            {
                "Data": DataDefinition(name="Data", definition=StructType()),
            }
        )
        dfd = DFDModel(
            name="Test",
            processes={"Handler": Process(name="Handler")},
            flows={
                ("Data", "inbound"): make_dfd_flow("Data", None, "Handler", "inbound"),
                ("Data", "outbound"): make_dfd_flow("Data", "Handler", None, "outbound"),
            },
        )
        doc = make_document(dfds={"Test": dfd}, data_dictionary=data_dict)

        result = aggregate_flows(doc)

        # Should become one bidirectional flow
        flows = result.dfds["Test"].flows
        assert len(flows) == 1
        # Verify it has the correct flow_type and key
        assert ("Data", "bidirectional") in flows
        flow = flows[("Data", "bidirectional")]
        assert flow.flow_type == "bidirectional"
        assert flow.target is not None
        assert flow.target.name == "Handler"
        assert flow.source is None  # Boundary flow


# =============================================================================
# CLI Integration Tests
# =============================================================================


class TestCLIIntegration:
    """Test CLI integration with aggregation."""

    def test_cli_generate_aggregates_by_default(self, tmp_path: pytest.TempPathFactory) -> None:
        """CLI generate command aggregates flows by default (REQ-CLI-027)."""
        from click.testing import CliRunner

        from designit.cli import main

        # Create a test file with aggregatable flows
        test_file = tmp_path / "test.dit"  # type: ignore[operator]
        test_file.write_text(
            """
datadict {
    PaymentMethod = CreditCard | BankTransfer
    CreditCard = { number: string }
    BankTransfer = { iban: string }
}
scd Context {
    system PaymentSystem {}
    external Customer {}
    flow CreditCard: Customer -> PaymentSystem
    flow BankTransfer: Customer -> PaymentSystem
}
"""
        )

        output_dir = tmp_path / "output"  # type: ignore[operator]
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["generate", str(test_file), "-f", "mermaid", "--output-diagram-dir", str(output_dir)],
        )

        assert result.exit_code == 0
        # Read the generated mermaid file to check for aggregation
        mmd_files = list(output_dir.glob("*.mmd"))
        assert len(mmd_files) > 0
        content = mmd_files[0].read_text()
        # Should show aggregated PaymentMethod, not individual flows
        assert "PaymentMethod" in content

    def test_cli_no_aggregate_flag_disables_aggregation(
        self, tmp_path: pytest.TempPathFactory
    ) -> None:
        """CLI --no-aggregate-flows flag disables aggregation (REQ-CLI-027)."""
        from click.testing import CliRunner

        from designit.cli import main

        test_file = tmp_path / "test.dit"  # type: ignore[operator]
        test_file.write_text(
            """
datadict {
    PaymentMethod = CreditCard | BankTransfer
    CreditCard = { number: string }
    BankTransfer = { iban: string }
}
scd Context {
    system PaymentSystem {}
    external Customer {}
    flow CreditCard: Customer -> PaymentSystem
    flow BankTransfer: Customer -> PaymentSystem
}
"""
        )

        output_dir = tmp_path / "output"  # type: ignore[operator]
        runner = CliRunner()
        result = runner.invoke(
            main,
            [
                "generate",
                str(test_file),
                "-f",
                "mermaid",
                "--output-diagram-dir",
                str(output_dir),
                "--no-aggregate-flows",
            ],
        )

        assert result.exit_code == 0
        # Read the generated mermaid file to check for individual flows
        mmd_files = list(output_dir.glob("*.mmd"))
        assert len(mmd_files) > 0
        content = mmd_files[0].read_text()
        # Should show individual flows
        assert "CreditCard" in content
        assert "BankTransfer" in content
