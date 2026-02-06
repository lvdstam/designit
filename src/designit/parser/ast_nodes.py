"""AST node definitions for the DesignIt DSL.

These nodes represent the parsed structure of a DesignIt document
before it's transformed into the semantic model.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceLocation(BaseModel):
    """Location information for error reporting."""

    line: int
    column: int
    end_line: int | None = None
    end_column: int | None = None
    file: str | None = None


class ASTNode(BaseModel):
    """Base class for all AST nodes."""

    model_config = ConfigDict(extra="forbid")

    location: SourceLocation | None = None


# ============================================
# Placeholder
# ============================================


class PlaceholderNode(ASTNode):
    """Represents a TBD or ... placeholder."""

    kind: Literal["...", "TBD"] = "..."


# ============================================
# Common Elements
# ============================================


class FlowTypeRefNode(ASTNode):
    """A reference to a flow type, possibly qualified with namespace.

    Used within FlowDataTypeNode to represent each type in the data type clause.

    Examples:
    - Simple: "Money" -> namespace=None, name="Money"
    - Qualified: "PaymentGateway.Request" -> namespace="PaymentGateway", name="Request"
    """

    namespace: str | None = None
    name: str

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name


class FlowDataTypeNode(ASTNode):
    """Represents the data type clause of a flow.

    The data type clause is the content in parentheses after the flow name:
    - `flow Name(DataType)` -> types = [FlowTypeRefNode("DataType")]
    - `flow Name(Type1 | Type2)` -> types = [FlowTypeRefNode("Type1"), FlowTypeRefNode("Type2")]
    - `flow Name()` -> types = [] (control flow, no data)

    For DFD boundary flows, data_type may be None to indicate inheritance from parent.
    """

    types: list[FlowTypeRefNode] = Field(default_factory=list)

    @property
    def is_control_flow(self) -> bool:
        """Return True if this is a control flow (no data)."""
        return len(self.types) == 0

    @property
    def is_union(self) -> bool:
        """Return True if this carries multiple data types."""
        return len(self.types) > 1

    @property
    def primary_type(self) -> FlowTypeRefNode | None:
        """Return the primary (or only) type, or None for control flows."""
        return self.types[0] if self.types else None

    @property
    def display_name(self) -> str:
        """Return display string for the data type clause."""
        if not self.types:
            return "()"
        return "(" + " | ".join(t.qualified_name for t in self.types) + ")"


class PropertyNode(ASTNode):
    """A key-value property."""

    name: str
    value: str | int | float | bool | list[str | int | float | bool]


class BlockNode(ASTNode):
    """A block containing properties or a placeholder."""

    properties: list[PropertyNode] = Field(default_factory=list)
    is_placeholder: bool = False
    placeholder: PlaceholderNode | None = None


# ============================================
# Import
# ============================================


class ImportNode(ASTNode):
    """An import statement."""

    path: str


# ============================================
# Data Flow Diagram (DFD)
# ============================================


class FlowEndpointNode(ASTNode):
    """An endpoint in a data flow (entity.port or just entity)."""

    entity: str
    port: str | None = None


class RefinesNode(ASTNode):
    """A refinement declaration referencing Diagram.Element."""

    diagram_name: str
    element_name: str


class ExternalNode(ASTNode):
    """An external entity in a DFD."""

    name: str
    body: BlockNode | PlaceholderNode


class ProcessNode(ASTNode):
    """A process in a DFD."""

    name: str
    body: BlockNode | PlaceholderNode


class DatastoreNode(ASTNode):
    """A data store in a DFD."""

    name: str
    body: BlockNode | PlaceholderNode


class FlowNode(ASTNode):
    """A data flow in a DFD.

    For internal flows, both source and target are set.
    For boundary flows:
      - Inbound: source is None, target is set
      - Outbound: source is set, target is None

    Flow names can be simple or qualified:
      - Simple: "InternalFlow" -> namespace=None, name="InternalFlow"
      - Qualified: "Parent.BoundaryFlow" -> namespace="Parent", name="BoundaryFlow"

    Boundary flows (qualified names) may have data_type=None to inherit from parent.
    Internal flows must have data_type set.
    """

    name: str  # Simple name (just the flow name part)
    namespace: str | None = None  # Parent diagram name for boundary flows
    data_type: FlowDataTypeNode | None = None  # Data type clause; None means inherited
    source: FlowEndpointNode | None = None
    target: FlowEndpointNode | None = None
    properties: list[PropertyNode] = Field(default_factory=list)

    # Keep for backward compatibility during migration
    type_ref: FlowTypeRefNode | None = None

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified flow name."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name

    @property
    def is_boundary_flow(self) -> bool:
        """Return True if this is a boundary flow (qualified name)."""
        return self.namespace is not None

    @property
    def inherits_data_type(self) -> bool:
        """Return True if this boundary flow inherits its data type from parent."""
        return self.namespace is not None and self.data_type is None


class DFDNode(ASTNode):
    """A Data Flow Diagram declaration.

    DFDs must refine a system (from SCD) or a process (from parent DFD).
    DFDs contain NO external entities - externals exist only at the SCD level.
    """

    name: str
    refines: RefinesNode | None = None
    externals: list[ExternalNode] = Field(
        default_factory=list
    )  # Kept for backward compat but should be empty
    processes: list[ProcessNode] = Field(default_factory=list)
    datastores: list[DatastoreNode] = Field(default_factory=list)
    flows: list[FlowNode] = Field(default_factory=list)
    flow_unions: list[FlowUnionNode] = Field(default_factory=list)


# ============================================
# System Context Diagram (SCD)
# ============================================


class SystemNode(ASTNode):
    """The system in an SCD."""

    name: str
    body: BlockNode | PlaceholderNode


class SCDFlowNode(ASTNode):
    """A data flow in an SCD with direction.

    SCD flows always have explicit data types (parentheses required).
    Control flows use empty parentheses: `flow Name(): Source -> Target`

    The data_type contains the flow's data type information.
    """

    name: str  # Flow name (always simple, not qualified)
    data_type: FlowDataTypeNode  # Data type clause (required for SCD)
    source: str
    target: str
    direction: Literal["inbound", "outbound", "bidirectional"]
    properties: list[PropertyNode] = Field(default_factory=list)

    # Keep for backward compatibility during migration
    type_ref: FlowTypeRefNode | None = None


class FlowUnionNode(ASTNode):
    """A flow union definition combining multiple flows.

    Flow unions can be defined in SCD or DFD diagrams. They combine multiple
    flows into a single named bundle for visual simplification at higher
    abstraction levels.

    Example:
        flow LoginSession = LoginRequest | LoginResponse
    """

    name: str
    members: list[str] = Field(default_factory=list)  # Flow names


class SCDNode(ASTNode):
    """A System Context Diagram declaration."""

    name: str
    system: SystemNode | None = None
    externals: list[ExternalNode] = Field(default_factory=list)
    datastores: list[DatastoreNode] = Field(default_factory=list)
    flows: list[SCDFlowNode] = Field(default_factory=list)
    flow_unions: list[FlowUnionNode] = Field(default_factory=list)


# ============================================
# Entity-Relationship Diagram (ERD)
# ============================================


class ConstraintNode(ASTNode):
    """A constraint on an attribute."""

    kind: Literal["pk", "fk", "unique", "not_null", "pattern"]
    target_entity: str | None = None  # For FK
    target_attribute: str | None = None  # For FK
    pattern: str | None = None  # For pattern constraint


class AttributeNode(ASTNode):
    """An attribute in an entity."""

    name: str
    type_name: str
    constraints: list[ConstraintNode] = Field(default_factory=list)


class EntityNode(ASTNode):
    """An entity in an ERD."""

    name: str
    attributes: list[AttributeNode] = Field(default_factory=list)
    has_placeholder: bool = False


class CardinalityNode(ASTNode):
    """Cardinality specification for a relationship."""

    source: str  # "1", "n", "m", "0..1", "0..n", "1..n"
    target: str  # "1", "n", "m", "0..1", "0..n", "1..n"


class RelationshipNode(ASTNode):
    """A relationship between entities in an ERD."""

    name: str
    source_entity: str
    target_entity: str
    cardinality: CardinalityNode
    properties: list[PropertyNode] = Field(default_factory=list)


class ERDNode(ASTNode):
    """An Entity-Relationship Diagram declaration."""

    name: str
    entities: list[EntityNode] = Field(default_factory=list)
    relationships: list[RelationshipNode] = Field(default_factory=list)


# ============================================
# State Transition Diagram (STD)
# ============================================


class StateNode(ASTNode):
    """A state in an STD."""

    name: str
    body: BlockNode | PlaceholderNode


class TransitionNode(ASTNode):
    """A transition between states in an STD."""

    name: str
    source_state: str
    target_state: str
    properties: list[PropertyNode] = Field(default_factory=list)


class STDNode(ASTNode):
    """A State Transition Diagram declaration."""

    name: str
    initial_state: str | None = None
    states: list[StateNode] = Field(default_factory=list)
    transitions: list[TransitionNode] = Field(default_factory=list)


# ============================================
# Structure Chart
# ============================================


class ModuleNode(ASTNode):
    """A module in a structure chart."""

    name: str
    calls: list[str] = Field(default_factory=list)
    data_couples: list[str] = Field(default_factory=list)
    control_couples: list[str] = Field(default_factory=list)
    properties: list[PropertyNode] = Field(default_factory=list)
    has_placeholder: bool = False


class StructureNode(ASTNode):
    """A Structure Chart declaration."""

    name: str
    modules: list[ModuleNode] = Field(default_factory=list)


# ============================================
# Data Dictionary
# ============================================


class FieldConstraintNode(ASTNode):
    """A constraint on a data field."""

    kind: Literal["pattern", "optional", "min", "max"]
    value: str | int | float | None = None


class DataDictTypeRefNode(ASTNode):
    """A type reference in data dictionary, optionally qualified with namespace.

    Used in struct fields, union alternatives, and array element types.

    Examples:
    - Simple: "Address" -> namespace=None, name="Address"
    - Qualified: "ServiceA.Request" -> namespace="ServiceA", name="Request"
    """

    namespace: str | None = None
    name: str

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name


class StructFieldNode(ASTNode):
    """A field in a struct definition."""

    name: str
    type_ref: DataDictTypeRefNode
    constraints: list[FieldConstraintNode] = Field(default_factory=list)


class StructDefNode(ASTNode):
    """A struct type definition."""

    fields: list[StructFieldNode] = Field(default_factory=list)


class UnionDefNode(ASTNode):
    """A union type definition (alternatives).

    Alternatives can be string literals, base types, or type references.
    """

    alternatives: list[str | DataDictTypeRefNode] = Field(default_factory=list)


class ArrayDefNode(ASTNode):
    """An array type definition."""

    element_type: DataDictTypeRefNode
    min_length: int | None = None
    max_length: int | None = None


class SimpleTypeRefNode(ASTNode):
    """A simple reference to another type (base type or identifier).

    Used for top-level data definitions like: TypeName = OtherType
    """

    name: str


class DataDefNode(ASTNode):
    """A data definition in the data dictionary."""

    name: str
    definition: StructDefNode | UnionDefNode | ArrayDefNode | SimpleTypeRefNode | PlaceholderNode


class DataDictNode(ASTNode):
    """A Data Dictionary declaration.

    If namespace is None, this is an anonymous datadict and types are global.
    If namespace is set, types must be qualified as Namespace.TypeName in flows.
    """

    namespace: str | None = None
    definitions: list[DataDefNode] = Field(default_factory=list)


# ============================================
# Markdown Block
# ============================================


class MarkdownNode(ASTNode):
    """A markdown block containing raw markdown text with template expressions.

    The content is the raw text between the braces, with escape sequences preserved.
    Escape sequences (\\{ and \\}) are processed during rendering, not parsing.
    """

    content: str


# ============================================
# Document
# ============================================


class DocumentNode(ASTNode):
    """The root node representing an entire document."""

    imports: list[ImportNode] = Field(default_factory=list)
    scds: list[SCDNode] = Field(default_factory=list)
    dfds: list[DFDNode] = Field(default_factory=list)
    erds: list[ERDNode] = Field(default_factory=list)
    stds: list[STDNode] = Field(default_factory=list)
    structures: list[StructureNode] = Field(default_factory=list)
    datadicts: list[DataDictNode] = Field(default_factory=list)
    markdowns: list[MarkdownNode] = Field(default_factory=list)
