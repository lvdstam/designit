"""System Context Diagram model classes."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement, ElementReference


class System(BaseElement):
    """The system being modeled in an SCD."""

    pass


class SCDExternalEntity(BaseElement):
    """An external entity in an SCD (same structure as DFD external)."""

    pass


class SCDDatastore(BaseElement):
    """A data store in an SCD (same structure as DFD datastore)."""

    pass


class SCDFlow(BaseModel):
    """A data flow in an SCD with bidirectional support."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source: ElementReference
    target: ElementReference
    direction: Literal["inbound", "outbound", "bidirectional"]
    description: str | None = None
    source_file: str | None = None
    line: int | None = None


class SCDModel(BaseModel):
    """A System Context Diagram model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    system: System | None = None
    externals: dict[str, SCDExternalEntity] = Field(default_factory=dict)
    datastores: dict[str, SCDDatastore] = Field(default_factory=dict)
    flows: dict[str, SCDFlow] = Field(default_factory=dict)
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
