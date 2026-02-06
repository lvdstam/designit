"""Data Flow Diagram model classes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement, ElementReference

# Type aliases for flow keys
FlowType = Literal["internal", "inbound", "outbound", "bidirectional"]
FlowKey = tuple[str, FlowType]


class ExternalEntity(BaseElement):
    """An external entity in a DFD."""

    flows: list[DataFlow] = Field(default_factory=list)


class Process(BaseElement):
    """A process in a DFD."""

    flows: list[DataFlow] = Field(default_factory=list)


class Datastore(BaseElement):
    """A data store in a DFD."""

    flows: list[DataFlow] = Field(default_factory=list)


class RefinesRef(BaseModel):
    """Reference to the element this DFD refines."""

    model_config = ConfigDict(extra="forbid")

    diagram_name: str
    element_name: str
    line: int | None = None


class FlowTypeRef(BaseModel):
    """A reference to a type in the data dictionary.

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


class DataFlow(BaseModel):
    """A data flow between DFD elements.

    For internal flows, both source and target are set.
    For boundary flows:
      - Inbound: source is None, target is set
      - Outbound: source is set, target is None

    The type_ref field optionally specifies the data type being transferred,
    which may be a qualified reference to a namespaced datadict type.

    The parent_ref field is set for boundary flows that reference a parent flow
    (e.g., "flow Context.PayFlow: -> Handler" has parent_ref="Context").
    When parent_ref is set and type_ref is None, the flow inherits its data type
    from the referenced parent flow.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    source: ElementReference | None = None
    target: ElementReference | None = None
    flow_type: FlowType = "internal"
    type_ref: FlowTypeRef | None = None
    parent_ref: str | None = None  # Parent diagram name for inherited boundary flows
    description: str | None = None
    source_file: str | None = None
    line: int | None = None


class DFDFlowUnion(BaseModel):
    """A flow union combining multiple flows into a single named bundle.

    Flow unions allow visual simplification at higher abstraction levels.
    Member flows are stored directly in the union (not as names requiring lookup).
    The direction is inferred from member flows:
    - All inbound -> inbound
    - All outbound -> outbound
    - Mixed or all internal -> bidirectional (or internal)

    The `requested_member_names` field stores the original member names from the DSL,
    which may include references that couldn't be resolved. This is used for validation
    to report errors about missing members.
    """

    model_config = ConfigDict(extra="forbid")

    name: str
    members: list[DataFlow] = Field(default_factory=list)  # Actual flow objects
    requested_member_names: list[str] = Field(default_factory=list)  # Original names from DSL
    source_file: str | None = None
    line: int | None = None

    @property
    def direction(self) -> FlowType | None:
        """Infer direction from member flows."""
        if not self.members:
            return None
        directions = {flow.flow_type for flow in self.members}
        if len(directions) == 1:
            return next(iter(directions))
        # Mixed directions
        if "internal" in directions:
            return "internal"
        return "bidirectional"

    @property
    def member_names(self) -> list[str]:
        """Get list of member flow names (for backward compatibility)."""
        return [flow.name for flow in self.members]


class DFDModel(BaseModel):
    """A Data Flow Diagram model.

    DFDs must refine a system (from SCD) or a process (from parent DFD).
    DFDs contain NO external entities - externals exist only at the SCD level.

    Flows are stored with compound keys (name, flow_type) to allow multiple
    flows with the same name but different directions (e.g., bidirectional
    parent flow decomposed into inbound + outbound).
    """

    model_config = ConfigDict(extra="allow")  # Allow extra attributes like _inbound_flow_handlers

    name: str
    description: str | None = None
    refines: RefinesRef | None = None
    externals: dict[str, ExternalEntity] = Field(default_factory=dict)  # Kept for backward compat
    processes: dict[str, Process] = Field(default_factory=dict)
    datastores: dict[str, Datastore] = Field(default_factory=dict)
    flows: dict[FlowKey, DataFlow] = Field(default_factory=dict)
    flow_unions: dict[str, DFDFlowUnion] = Field(default_factory=dict)
    source_file: str | None = None
    line: int | None = None

    def get_flow(self, name: str, flow_type: FlowType) -> DataFlow | None:
        """Get a specific flow by name and type.

        Args:
            name: The flow name.
            flow_type: The flow type ('internal', 'inbound', or 'outbound').

        Returns:
            The DataFlow if found, None otherwise.
        """
        return self.flows.get((name, flow_type))

    def get_flows_by_name(self, name: str) -> list[DataFlow]:
        """Get all flows with a given name.

        This is useful when a bidirectional parent flow is decomposed into
        separate inbound and outbound flows with the same name.

        Args:
            name: The flow name to search for.

        Returns:
            List of DataFlow objects with that name (may be empty).
        """
        return [flow for (n, _), flow in self.flows.items() if n == name]

    def get_element(self, name: str) -> ExternalEntity | Process | Datastore | None:
        """Get an element by name from any category."""
        if name in self.externals:
            return self.externals[name]
        if name in self.processes:
            return self.processes[name]
        if name in self.datastores:
            return self.datastores[name]
        return None

    def all_elements(self) -> list[BaseElement]:
        """Get all elements in the DFD."""
        elements: list[BaseElement] = []
        elements.extend(self.externals.values())
        elements.extend(self.processes.values())
        elements.extend(self.datastores.values())
        return elements
