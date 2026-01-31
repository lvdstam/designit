"""Entity-Relationship Diagram model classes."""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement


class ConstraintType(str, Enum):
    """Types of attribute constraints."""

    PRIMARY_KEY = "pk"
    FOREIGN_KEY = "fk"
    UNIQUE = "unique"
    NOT_NULL = "not_null"
    PATTERN = "pattern"


class AttributeConstraint(BaseModel):
    """A constraint on an entity attribute."""

    model_config = ConfigDict(extra="forbid")

    type: ConstraintType
    target_entity: str | None = None  # For FK
    target_attribute: str | None = None  # For FK
    pattern: str | None = None  # For pattern constraint


class Attribute(BaseModel):
    """An attribute of an entity."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type_name: str
    constraints: list[AttributeConstraint] = Field(default_factory=list)
    description: str | None = None

    @property
    def is_primary_key(self) -> bool:
        """Check if this attribute is a primary key."""
        return any(c.type == ConstraintType.PRIMARY_KEY for c in self.constraints)

    @property
    def is_foreign_key(self) -> bool:
        """Check if this attribute is a foreign key."""
        return any(c.type == ConstraintType.FOREIGN_KEY for c in self.constraints)


class Entity(BaseElement):
    """An entity in an ERD."""

    attributes: dict[str, Attribute] = Field(default_factory=dict)

    @property
    def primary_keys(self) -> list[Attribute]:
        """Get all primary key attributes."""
        return [attr for attr in self.attributes.values() if attr.is_primary_key]

    @property
    def foreign_keys(self) -> list[Attribute]:
        """Get all foreign key attributes."""
        return [attr for attr in self.attributes.values() if attr.is_foreign_key]


class Cardinality(BaseModel):
    """Cardinality specification for a relationship."""

    model_config = ConfigDict(extra="forbid")

    source: str  # "1", "n", "m", "0..1", "0..n", "1..n"
    target: str

    def __str__(self) -> str:
        return f"{self.source}:{self.target}"


class Relationship(BaseModel):
    """A relationship between entities."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source_entity: str
    target_entity: str
    cardinality: Cardinality
    description: str | None = None
    source_file: str | None = None
    line: int | None = None


class ERDModel(BaseModel):
    """An Entity-Relationship Diagram model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    entities: dict[str, Entity] = Field(default_factory=dict)
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    source_file: str | None = None

    def get_entity(self, name: str) -> Entity | None:
        """Get an entity by name."""
        return self.entities.get(name)

    def get_relationships_for_entity(self, entity_name: str) -> list[Relationship]:
        """Get all relationships involving an entity."""
        return [
            rel
            for rel in self.relationships.values()
            if rel.source_entity == entity_name or rel.target_entity == entity_name
        ]
