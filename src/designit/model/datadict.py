"""Data Dictionary model classes."""

from __future__ import annotations

from enum import Enum

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


class TypeRef(BaseModel):
    """A type reference, optionally qualified with namespace.

    Used in struct fields, union alternatives, and array element types.

    Examples:
    - Simple: TypeRef(namespace=None, name="Address")
    - Qualified: TypeRef(namespace="ServiceA", name="Request")
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    namespace: str | None = None
    name: str

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name

    @property
    def is_qualified(self) -> bool:
        """Check if this is a qualified (namespaced) reference."""
        return self.namespace is not None


class StructField(BaseModel):
    """A field in a struct definition."""

    model_config = ConfigDict(extra="forbid")

    name: str
    type_ref: TypeRef
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
    """A union/variant type definition.

    Alternatives can be string literals (as str) or type references (as TypeRef).
    """

    model_config = ConfigDict(extra="forbid")

    alternatives: list[str | TypeRef] = Field(default_factory=list)


class ArrayType(BaseModel):
    """An array type definition."""

    model_config = ConfigDict(extra="forbid")

    element_type: TypeRef
    min_length: int | None = None
    max_length: int | None = None


class TypeReference(BaseModel):
    """A reference to another type."""

    model_config = ConfigDict(extra="forbid")

    name: str


# Union of all type definitions
TypeDefinition = StructType | UnionType | ArrayType | TypeReference | None


class DataDefinition(BaseElement):
    """A data definition in the data dictionary.

    If namespace is None, this is an anonymous type accessible without qualification.
    If namespace is set, the type must be qualified as Namespace.TypeName in flows.
    """

    namespace: str | None = None
    definition: TypeDefinition = None

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified name."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name

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
    """A Data Dictionary model.

    The definitions dict uses qualified names as keys:
    - Anonymous types: "TypeName"
    - Namespaced types: "Namespace.TypeName"
    """

    model_config = ConfigDict(extra="forbid")

    definitions: dict[str, DataDefinition] = Field(default_factory=dict)
    source_file: str | None = None

    def get_definition(self, name: str) -> DataDefinition | None:
        """Get a definition by name (qualified or unqualified)."""
        return self.definitions.get(name)

    def get_anonymous_types(self) -> dict[str, DataDefinition]:
        """Get all types from anonymous datadicts (no namespace)."""
        return {name: defn for name, defn in self.definitions.items() if defn.namespace is None}

    def get_namespaced_types(self) -> dict[str, DataDefinition]:
        """Get all types from named datadicts (with namespace)."""
        return {name: defn for name, defn in self.definitions.items() if defn.namespace is not None}

    def get_types_by_namespace(self, namespace: str) -> dict[str, DataDefinition]:
        """Get all types from a specific namespace."""
        return {
            name: defn for name, defn in self.definitions.items() if defn.namespace == namespace
        }

    def get_namespaces(self) -> set[str]:
        """Get all namespace names (excluding anonymous)."""
        return {defn.namespace for defn in self.definitions.values() if defn.namespace is not None}

    def find_by_simple_name(self, simple_name: str) -> list[DataDefinition]:
        """Find all types with a given simple name (may be in multiple namespaces)."""
        return [defn for defn in self.definitions.values() if defn.name == simple_name]

    def resolve_type(self, type_name: str) -> DataDefinition | None:
        """Resolve a type reference to its definition."""
        defn = self.definitions.get(type_name)
        if defn and defn.is_reference and isinstance(defn.definition, TypeReference):
            return self.resolve_type(defn.definition.name)
        return defn

    def get_all_referenced_types(self, type_name: str) -> set[TypeRef]:
        """Get all types referenced by a definition (recursively).

        Returns TypeRef objects to preserve namespace information.
        """
        result: set[TypeRef] = set()
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
                    result.add(field.type_ref)
                    collect(field.type_ref.qualified_name)
            elif isinstance(defn.definition, UnionType):
                for alt in defn.definition.alternatives:
                    if isinstance(alt, TypeRef):
                        result.add(alt)
                        collect(alt.qualified_name)
                    # String literals are not type references, skip them
            elif isinstance(defn.definition, ArrayType):
                result.add(defn.definition.element_type)
                collect(defn.definition.element_type.qualified_name)
            elif isinstance(defn.definition, TypeReference):
                # Simple type reference (top-level TypeName = OtherType)
                ref = TypeRef(namespace=None, name=defn.definition.name)
                result.add(ref)
                collect(defn.definition.name)

        collect(type_name)
        return result
