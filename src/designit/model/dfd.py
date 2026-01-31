"""Data Flow Diagram model classes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement, ElementReference


class ExternalEntity(BaseElement):
    """An external entity in a DFD."""

    pass


class Process(BaseElement):
    """A process in a DFD."""

    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)


class Datastore(BaseElement):
    """A data store in a DFD."""

    pass


class DataFlow(BaseModel):
    """A data flow between DFD elements."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source: ElementReference
    target: ElementReference
    description: str | None = None
    source_file: str | None = None
    line: int | None = None


class DFDModel(BaseModel):
    """A Data Flow Diagram model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    externals: dict[str, ExternalEntity] = Field(default_factory=dict)
    processes: dict[str, Process] = Field(default_factory=dict)
    datastores: dict[str, Datastore] = Field(default_factory=dict)
    flows: dict[str, DataFlow] = Field(default_factory=dict)
    source_file: str | None = None

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
