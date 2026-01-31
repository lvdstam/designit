"""Base model classes for design documents."""

from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    pass


class DiagramType(str, Enum):
    """Types of diagrams supported."""

    SCD = "scd"
    DFD = "dfd"
    ERD = "erd"
    STD = "std"
    STRUCTURE = "structure"
    DATADICT = "datadict"


class ValidationSeverity(str, Enum):
    """Severity levels for validation messages."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class ValidationMessage(BaseModel):
    """A validation message."""

    severity: ValidationSeverity
    message: str
    line: int | None = None
    column: int | None = None
    file: str | None = None
    element_name: str | None = None


class ElementReference(BaseModel):
    """A reference to an element, possibly in another file."""

    name: str
    file: str | None = None
    resolved: bool = False


class BaseElement(BaseModel):
    """Base class for all design elements."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    is_placeholder: bool = False
    source_file: str | None = None
    line: int | None = None


class DesignDocument(BaseModel):
    """Represents a complete design document (possibly spanning multiple files)."""

    name: str
    files: list[str] = Field(default_factory=list)
    scds: dict[str, SCDModel] = Field(default_factory=dict)
    dfds: dict[str, DFDModel] = Field(default_factory=dict)
    erds: dict[str, ERDModel] = Field(default_factory=dict)
    stds: dict[str, STDModel] = Field(default_factory=dict)
    structures: dict[str, StructureModel] = Field(default_factory=dict)
    data_dictionary: DataDictionaryModel | None = None
    validation_messages: list[ValidationMessage] = Field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """Check if the document has no errors."""
        return not any(msg.severity == ValidationSeverity.ERROR for msg in self.validation_messages)

    @property
    def placeholders(self) -> list[tuple[str, str, str | None]]:
        """Get all placeholder elements as (type, name, file) tuples."""
        result: list[tuple[str, str, str | None]] = []

        for scd in self.scds.values():
            if scd.system and scd.system.is_placeholder:
                result.append(("system", scd.system.name, scd.system.source_file))
            for ext in scd.externals.values():
                if ext.is_placeholder:
                    result.append(("external", ext.name, ext.source_file))
            for ds in scd.datastores.values():
                if ds.is_placeholder:
                    result.append(("datastore", ds.name, ds.source_file))

        for dfd in self.dfds.values():
            for ext in dfd.externals.values():
                if ext.is_placeholder:
                    result.append(("external", ext.name, ext.source_file))
            for proc in dfd.processes.values():
                if proc.is_placeholder:
                    result.append(("process", proc.name, proc.source_file))
            for ds in dfd.datastores.values():
                if ds.is_placeholder:
                    result.append(("datastore", ds.name, ds.source_file))

        for erd in self.erds.values():
            for entity in erd.entities.values():
                if entity.is_placeholder:
                    result.append(("entity", entity.name, entity.source_file))

        for std in self.stds.values():
            for state in std.states.values():
                if state.is_placeholder:
                    result.append(("state", state.name, state.source_file))

        for structure in self.structures.values():
            for module in structure.modules.values():
                if module.is_placeholder:
                    result.append(("module", module.name, module.source_file))

        if self.data_dictionary:
            for defn in self.data_dictionary.definitions.values():
                if defn.is_placeholder:
                    result.append(("datadef", defn.name, defn.source_file))

        return result


# Forward references for type hints
from designit.model.datadict import DataDictionaryModel  # noqa: E402
from designit.model.dfd import DFDModel  # noqa: E402
from designit.model.erd import ERDModel  # noqa: E402
from designit.model.scd import SCDModel  # noqa: E402
from designit.model.std import STDModel  # noqa: E402
from designit.model.structure import StructureModel  # noqa: E402

# Update forward references
DesignDocument.model_rebuild()
