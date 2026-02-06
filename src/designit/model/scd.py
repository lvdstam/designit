"""System Context Diagram model classes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement, ElementReference

# Type alias for SCD flow directions
SCDDirection = Literal["inbound", "outbound", "bidirectional"]


class System(BaseElement):
    """The system being modeled in an SCD."""

    flows: list[SCDFlow] = Field(default_factory=list)


class SCDExternalEntity(BaseElement):
    """An external entity in an SCD (same structure as DFD external)."""

    flows: list[SCDFlow] = Field(default_factory=list)


class SCDDatastore(BaseElement):
    """A data store in an SCD (same structure as DFD datastore)."""

    flows: list[SCDFlow] = Field(default_factory=list)


class SCDFlowTypeRef(BaseModel):
    """A reference to a type in the data dictionary for SCD flows.

    If namespace is None, refers to an anonymous datadict type.
    If namespace is set, refers to a namespaced type (Namespace.TypeName).
    """

    model_config = ConfigDict(extra="forbid")

    namespace: str | None = None
    name: str

    @property
    def qualified_name(self) -> str:
        """Return the fully qualified type name."""
        if self.namespace:
            return f"{self.namespace}.{self.name}"
        return self.name


class SCDFlow(BaseModel):
    """A data flow in an SCD with bidirectional support.

    The type_ref field optionally specifies the data type being transferred,
    which may be a qualified reference to a namespaced datadict type.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    source: ElementReference
    target: ElementReference
    direction: SCDDirection
    type_ref: SCDFlowTypeRef | None = None
    description: str | None = None
    source_file: str | None = None
    line: int | None = None


class SCDFlowUnion(BaseModel):
    """A flow union combining multiple flows into a single named bundle.

    Flow unions allow visual simplification at higher abstraction levels.
    Member flows are stored directly in the union (not as names requiring lookup).
    The direction is inferred from member flows:
    - All inbound -> inbound
    - All outbound -> outbound
    - Mixed or bidirectional -> bidirectional

    The `requested_member_names` field stores the original member names from the DSL,
    which may include references that couldn't be resolved. This is used for validation
    to report errors about missing members.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    members: list[SCDFlow] = Field(default_factory=list)  # Actual flow objects
    requested_member_names: list[str] = Field(default_factory=list)  # Original names from DSL
    source_file: str | None = None
    line: int | None = None

    @property
    def direction(self) -> SCDDirection | None:
        """Infer direction from member flows."""
        if not self.members:
            return None
        directions = {flow.direction for flow in self.members}
        if len(directions) == 1:
            # All members have the same direction
            return next(iter(directions))
        return "bidirectional"

    @property
    def source(self) -> ElementReference | None:
        """Get the common source endpoint (for rendering)."""
        if not self.members:
            return None
        # For unions, we need a representative source for rendering
        # Use the first member's source
        return self.members[0].source

    @property
    def target(self) -> ElementReference | None:
        """Get the common target endpoint (for rendering)."""
        if not self.members:
            return None
        # For unions, we need a representative target for rendering
        # Use the first member's target
        return self.members[0].target

    @property
    def member_names(self) -> list[str]:
        """Get list of member flow names (for backward compatibility)."""
        return [flow.name for flow in self.members]


class SCDModel(BaseModel):
    """A System Context Diagram model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    system: System | None = None
    externals: dict[str, SCDExternalEntity] = Field(default_factory=dict)
    datastores: dict[str, SCDDatastore] = Field(default_factory=dict)
    flows: dict[str, SCDFlow] = Field(default_factory=dict)
    flow_unions: dict[str, SCDFlowUnion] = Field(default_factory=dict)
    source_file: str | None = None

    def get_element(self, name: str) -> System | SCDExternalEntity | SCDDatastore | None:
        """Get an element by name from any category."""
        if self.system and self.system.name == name:
            return self.system
        if name in self.externals:
            return self.externals[name]
        if name in self.datastores:
            return self.datastores[name]
        return None

    def all_elements(self) -> list[BaseElement]:
        """Get all elements in the SCD."""
        elements: list[BaseElement] = []
        if self.system:
            elements.append(self.system)
        elements.extend(self.externals.values())
        elements.extend(self.datastores.values())
        return elements

    def get_system_name(self) -> str | None:
        """Get the system name, if defined."""
        return self.system.name if self.system else None
