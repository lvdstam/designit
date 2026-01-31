"""Data Dictionary model classes."""

from __future__ import annotations

from enum import Enum
from typing import Union
from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement


class FieldConstraintType(str, Enum):
    """Types of field constraints."""

    PATTERN = "pattern"
    OPTIONAL = "optional"
    MIN = "min"
    MAX = "max"


class FieldConstraint(BaseModel):
    """A constraint on a data field."""

    model_config = ConfigDict(extra="forbid")

    type: FieldConstraintType
    value: str | int | float | None = None


class StructField(BaseModel):
    """A field in a struct definition."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type_name: str
    constraints: list[FieldConstraint] = Field(default_factory=list)
    description: str | None = None

    @property
    def is_optional(self) -> bool:
        """Check if this field is optional."""
        return any(c.type == FieldConstraintType.OPTIONAL for c in self.constraints)


class StructType(BaseModel):
    """A struct/record type definition."""

    model_config = ConfigDict(extra="forbid")

    fields: dict[str, StructField] = Field(default_factory=dict)


class UnionType(BaseModel):
    """A union/variant type definition."""

    model_config = ConfigDict(extra="forbid")

    alternatives: list[str] = Field(default_factory=list)


class ArrayType(BaseModel):
    """An array type definition."""

    model_config = ConfigDict(extra="forbid")

    element_type: str
    min_length: int | None = None
    max_length: int | None = None


class TypeReference(BaseModel):
    """A reference to another type."""

    model_config = ConfigDict(extra="forbid")

    name: str


# Union of all type definitions
TypeDefinition = Union[StructType, UnionType, ArrayType, TypeReference, None]


class DataDefinition(BaseElement):
    """A data definition in the data dictionary."""

    definition: TypeDefinition = None

    @property
    def is_struct(self) -> bool:
        """Check if this definition is a struct."""
        return isinstance(self.definition, StructType)

    @property
    def is_union(self) -> bool:
        """Check if this definition is a union."""
        return isinstance(self.definition, UnionType)

    @property
    def is_array(self) -> bool:
        """Check if this definition is an array."""
        return isinstance(self.definition, ArrayType)

    @property
    def is_reference(self) -> bool:
        """Check if this definition is a type reference."""
        return isinstance(self.definition, TypeReference)


class DataDictionaryModel(BaseModel):
    """A Data Dictionary model."""

    model_config = ConfigDict(extra="forbid")

    definitions: dict[str, DataDefinition] = Field(default_factory=dict)
    source_file: str | None = None

    def get_definition(self, name: str) -> DataDefinition | None:
        """Get a definition by name."""
        return self.definitions.get(name)

    def resolve_type(self, type_name: str) -> DataDefinition | None:
        """Resolve a type reference to its definition."""
        defn = self.definitions.get(type_name)
        if defn and defn.is_reference and isinstance(defn.definition, TypeReference):
            return self.resolve_type(defn.definition.name)
        return defn

    def get_all_referenced_types(self, type_name: str) -> set[str]:
        """Get all types referenced by a definition (recursively)."""
        result: set[str] = set()
        visited: set[str] = set()

        def collect(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            defn = self.definitions.get(name)
            if not defn or not defn.definition:
                return

            if isinstance(defn.definition, StructType):
                for field in defn.definition.fields.values():
                    result.add(field.type_name)
                    collect(field.type_name)
            elif isinstance(defn.definition, UnionType):
                for alt in defn.definition.alternatives:
                    result.add(alt)
                    collect(alt)
            elif isinstance(defn.definition, ArrayType):
                result.add(defn.definition.element_type)
                collect(defn.definition.element_type)
            elif isinstance(defn.definition, TypeReference):
                result.add(defn.definition.name)
                collect(defn.definition.name)

        collect(type_name)
        return result
