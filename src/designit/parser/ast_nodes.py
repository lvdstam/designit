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
    """A data flow in a DFD."""

    name: str
    source: FlowEndpointNode
    target: FlowEndpointNode
    properties: list[PropertyNode] = Field(default_factory=list)


class DFDNode(ASTNode):
    """A Data Flow Diagram declaration."""

    name: str
    externals: list[ExternalNode] = Field(default_factory=list)
    processes: list[ProcessNode] = Field(default_factory=list)
    datastores: list[DatastoreNode] = Field(default_factory=list)
    flows: list[FlowNode] = Field(default_factory=list)


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


class StructFieldNode(ASTNode):
    """A field in a struct definition."""

    name: str
    type_name: str
    constraints: list[FieldConstraintNode] = Field(default_factory=list)


class StructDefNode(ASTNode):
    """A struct type definition."""

    fields: list[StructFieldNode] = Field(default_factory=list)


class UnionDefNode(ASTNode):
    """A union type definition (alternatives)."""

    alternatives: list[str] = Field(default_factory=list)


class ArrayDefNode(ASTNode):
    """An array type definition."""

    element_type: str
    min_length: int | None = None
    max_length: int | None = None


class TypeRefNode(ASTNode):
    """A reference to another type."""

    name: str


class DataDefNode(ASTNode):
    """A data definition in the data dictionary."""

    name: str
    definition: StructDefNode | UnionDefNode | ArrayDefNode | TypeRefNode | PlaceholderNode


class DataDictNode(ASTNode):
    """A Data Dictionary declaration."""

    definitions: list[DataDefNode] = Field(default_factory=list)


# ============================================
# Document
# ============================================


class DocumentNode(ASTNode):
    """The root node representing an entire document."""

    imports: list[ImportNode] = Field(default_factory=list)
    dfds: list[DFDNode] = Field(default_factory=list)
    erds: list[ERDNode] = Field(default_factory=list)
    stds: list[STDNode] = Field(default_factory=list)
    structures: list[StructureNode] = Field(default_factory=list)
    datadicts: list[DataDictNode] = Field(default_factory=list)
