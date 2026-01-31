"""Structure Chart model classes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement


class Module(BaseElement):
    """A module in a structure chart."""

    calls: list[str] = Field(default_factory=list)
    data_couples: list[str] = Field(default_factory=list)
    control_couples: list[str] = Field(default_factory=list)


class StructureModel(BaseModel):
    """A Structure Chart model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    modules: dict[str, Module] = Field(default_factory=dict)
    source_file: str | None = None

    def get_module(self, name: str) -> Module | None:
        """Get a module by name."""
        return self.modules.get(name)

    def get_root_modules(self) -> list[Module]:
        """Get modules that are not called by any other module."""
        called_modules: set[str] = set()
        for module in self.modules.values():
            called_modules.update(module.calls)

        return [m for m in self.modules.values() if m.name not in called_modules]

    def get_call_hierarchy(self, module_name: str) -> dict[str, list[str]]:
        """Get the call hierarchy starting from a module."""
        result: dict[str, list[str]] = {}
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            module = self.modules.get(name)
            if module:
                result[name] = module.calls
                for called in module.calls:
                    visit(called)

        visit(module_name)
        return result

    def detect_cycles(self) -> list[list[str]]:
        """Detect cyclic calls in the structure chart."""
        cycles: list[list[str]] = []

        def dfs(node: str, path: list[str], visited: set[str]) -> None:
            if node in path:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            if node in visited:
                return
            visited.add(node)
            path.append(node)
            module = self.modules.get(node)
            if module:
                for called in module.calls:
                    dfs(called, path.copy(), visited)

        for module_name in self.modules:
            dfs(module_name, [], set())

        return cycles
