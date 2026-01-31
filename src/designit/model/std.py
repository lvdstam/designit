"""State Transition Diagram model classes."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from designit.model.base import BaseElement


class State(BaseElement):
    """A state in an STD."""

    is_initial: bool = False
    is_final: bool = False
    entry_action: str | None = None
    exit_action: str | None = None


class Transition(BaseModel):
    """A transition between states."""

    model_config = ConfigDict(extra="forbid")

    name: str
    source_state: str
    target_state: str
    trigger: str | None = None
    guard: str | None = None
    action: str | None = None
    description: str | None = None
    source_file: str | None = None
    line: int | None = None


class STDModel(BaseModel):
    """A State Transition Diagram model."""

    model_config = ConfigDict(extra="forbid")

    name: str
    description: str | None = None
    initial_state: str | None = None
    states: dict[str, State] = Field(default_factory=dict)
    transitions: dict[str, Transition] = Field(default_factory=dict)
    source_file: str | None = None

    def get_state(self, name: str) -> State | None:
        """Get a state by name."""
        return self.states.get(name)

    def get_transitions_from(self, state_name: str) -> list[Transition]:
        """Get all transitions originating from a state."""
        return [t for t in self.transitions.values() if t.source_state == state_name]

    def get_transitions_to(self, state_name: str) -> list[Transition]:
        """Get all transitions targeting a state."""
        return [t for t in self.transitions.values() if t.target_state == state_name]

    def get_reachable_states(self, from_state: str) -> set[str]:
        """Get all states reachable from a given state."""
        visited: set[str] = set()
        to_visit = [from_state]

        while to_visit:
            current = to_visit.pop()
            if current in visited:
                continue
            visited.add(current)
            for trans in self.get_transitions_from(current):
                if trans.target_state not in visited:
                    to_visit.append(trans.target_state)

        return visited
