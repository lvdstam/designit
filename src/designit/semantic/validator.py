"""Validation rules for design documents."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from designit.model.base import (
    DesignDocument,
    ValidationMessage,
    ValidationSeverity,
)

if TYPE_CHECKING:
    from designit.model.datadict import DataDefinition, TypeRef, UnionType
    from designit.model.dfd import DFDModel
    from designit.model.scd import SCDModel


class Validator:
    """Validates design documents for consistency and completeness."""

    def __init__(self) -> None:
        self.messages: list[ValidationMessage] = []

    def _add_message(
        self,
        severity: ValidationSeverity,
        message: str,
        element_name: str | None = None,
        file: str | None = None,
        line: int | None = None,
    ) -> None:
        """Add a validation message."""
        self.messages.append(
            ValidationMessage(
                severity=severity,
                message=message,
                file=file,
                line=line,
                element_name=element_name,
            )
        )

    def _error(
        self,
        message: str,
        element_name: str | None = None,
        file: str | None = None,
        line: int | None = None,
    ) -> None:
        self._add_message(ValidationSeverity.ERROR, message, element_name, file, line)

    def _warning(
        self,
        message: str,
        element_name: str | None = None,
        file: str | None = None,
        line: int | None = None,
    ) -> None:
        self._add_message(ValidationSeverity.WARNING, message, element_name, file, line)

    def _info(
        self,
        message: str,
        element_name: str | None = None,
        file: str | None = None,
        line: int | None = None,
    ) -> None:
        self._add_message(ValidationSeverity.INFO, message, element_name, file, line)

    def validate(self, doc: DesignDocument) -> list[ValidationMessage]:
        """Validate a design document.

        Args:
            doc: The document to validate.

        Returns:
            A list of validation messages.
        """
        self.messages.clear()

        self._validate_dfds(doc)
        self._validate_dfd_refinements(doc)
        self._validate_dfd_flow_coverage(doc)
        self._validate_unique_names(doc)
        self._validate_dfd_datastore_conflicts(doc)
        self._validate_datadict_name_conflicts(doc)
        self._validate_erds(doc)
        self._validate_stds(doc)
        self._validate_structures(doc)
        self._validate_scds(doc)
        self._validate_datadict(doc)
        self._validate_cross_references(doc)
        self._report_placeholders(doc)

        return self.messages

    def _validate_dfd_refinements(self, doc: DesignDocument) -> None:
        """Validate DFD refinement declarations.

        REQ-SEM-080: Every DFD shall declare what parent element it refines.
        REQ-SEM-081: The parent reference shall be resolved and validated.
        """
        for dfd_name, dfd in doc.dfds.items():
            if not dfd.refines:
                continue  # Grammar enforces this, but be safe

            diagram_name = dfd.refines.diagram_name
            element_name = dfd.refines.element_name
            line = dfd.refines.line

            # Check if diagram exists (could be SCD or DFD)
            parent_scd = doc.scds.get(diagram_name)
            parent_dfd = doc.dfds.get(diagram_name)

            if not parent_scd and not parent_dfd:
                self._error(
                    f"DFD '{dfd_name}' refines non-existent diagram '{diagram_name}'",
                    dfd_name,
                    dfd.source_file,
                    line,
                )
                continue

            # Check if element exists and is valid type
            if parent_scd:
                self._validate_scd_refinement(dfd_name, dfd, parent_scd, element_name, line)
            elif parent_dfd:
                self._validate_dfd_process_refinement(dfd_name, dfd, parent_dfd, element_name, line)

    def _validate_scd_refinement(
        self,
        dfd_name: str,
        dfd: DFDModel,
        parent_scd: SCDModel,
        element_name: str,
        line: int | None,
    ) -> None:
        """Validate that a DFD properly refines an SCD system."""
        diagram_name = parent_scd.name
        if parent_scd.system and parent_scd.system.name == element_name:
            pass  # Valid - refining a system
        elif element_name in parent_scd.externals:
            self._error(
                f"DFD '{dfd_name}' cannot refine external entity '{element_name}'",
                dfd_name,
                dfd.source_file,
                line,
            )
        elif element_name in parent_scd.datastores:
            self._error(
                f"DFD '{dfd_name}' cannot refine datastore '{element_name}'",
                dfd_name,
                dfd.source_file,
                line,
            )
        else:
            self._error(
                f"Element '{element_name}' not found in SCD '{diagram_name}'",
                dfd_name,
                dfd.source_file,
                line,
            )

    def _validate_dfd_process_refinement(
        self,
        dfd_name: str,
        dfd: DFDModel,
        parent_dfd: DFDModel,
        element_name: str,
        line: int | None,
    ) -> None:
        """Validate that a DFD properly refines a process in another DFD."""
        diagram_name = parent_dfd.name
        if element_name in parent_dfd.processes:
            pass  # Valid - refining a process
        elif element_name in parent_dfd.datastores:
            self._error(
                f"DFD '{dfd_name}' cannot refine datastore '{element_name}'",
                dfd_name,
                dfd.source_file,
                line,
            )
        else:
            self._error(
                f"Process '{element_name}' not found in DFD '{diagram_name}'",
                dfd_name,
                dfd.source_file,
                line,
            )

    def _validate_dfds(self, doc: DesignDocument) -> None:
        """Validate all DFDs."""
        for dfd_name, dfd in doc.dfds.items():
            # Check that flows reference valid elements
            all_elements = (
                set(dfd.externals.keys()) | set(dfd.processes.keys()) | set(dfd.datastores.keys())
            )

            for (flow_name, _flow_type), flow in dfd.flows.items():
                # For boundary flows, source or target may be None
                if flow.source is not None and flow.source.name not in all_elements:
                    self._error(
                        f"Flow '{flow_name}' references unknown source '{flow.source.name}'",
                        flow_name,
                        flow.source_file,
                        flow.line,
                    )
                if flow.target is not None and flow.target.name not in all_elements:
                    self._error(
                        f"Flow '{flow_name}' references unknown target '{flow.target.name}'",
                        flow_name,
                        flow.source_file,
                        flow.line,
                    )

            # Check for orphan elements (no flows in or out)
            elements_with_flows: set[str] = set()
            for flow in dfd.flows.values():
                if flow.source is not None:
                    elements_with_flows.add(flow.source.name)
                if flow.target is not None:
                    elements_with_flows.add(flow.target.name)

            for element in dfd.all_elements():
                if element.name not in elements_with_flows and not element.is_placeholder:
                    self._warning(
                        f"Element '{element.name}' has no data flows",
                        element.name,
                        element.source_file,
                        element.line,
                    )

    def _validate_dfd_flow_coverage(self, doc: DesignDocument) -> None:
        """Validate DFD flow coverage against parent diagram.

        REQ-SEM-082: Inbound flows must be handled by exactly one process.
        REQ-SEM-083: Outbound flows may be handled by zero or more processes.
        """
        for dfd_name, dfd in doc.dfds.items():
            if not dfd.refines:
                continue

            diagram_name = dfd.refines.diagram_name
            element_name = dfd.refines.element_name

            # Get parent diagram
            parent_scd = doc.scds.get(diagram_name)
            parent_dfd = doc.dfds.get(diagram_name)

            if not parent_scd and not parent_dfd:
                # Already handled by _validate_dfd_refinements
                continue

            # Get parent flows involving the refined element
            if parent_scd:
                parent_flows = self._get_parent_scd_flows(parent_scd, element_name)
            else:
                assert parent_dfd is not None  # Already checked above
                parent_flows = self._get_parent_dfd_flows(parent_dfd, element_name)

            # Validate flow directions and coverage
            self._validate_dfd_flow_directions(dfd, parent_flows)
            self._validate_dfd_inbound_handlers(dfd, dfd_name, parent_flows, doc)

    def _get_parent_scd_flows(
        self, parent_scd: SCDModel, system_name: str
    ) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        """Get inbound, outbound, and bidirectional flows for a system in an SCD.

        Returns:
            Tuple of (inbound_flows, outbound_flows, bidirectional_flows) dicts.
        """
        inbound: dict[str, str] = {}
        outbound: dict[str, str] = {}
        bidirectional: dict[str, str] = {}

        for flow_name, flow in parent_scd.flows.items():
            if flow.target.name == system_name:
                if flow.direction == "bidirectional":
                    bidirectional[flow_name] = "bidirectional"
                else:
                    inbound[flow_name] = "inbound"
            if flow.source.name == system_name:
                if flow.direction == "bidirectional":
                    bidirectional[flow_name] = "bidirectional"
                else:
                    outbound[flow_name] = "outbound"

        return inbound, outbound, bidirectional

    def _get_parent_dfd_flows(
        self, parent_dfd: DFDModel, process_name: str
    ) -> tuple[dict[str, str], dict[str, str], dict[str, str]]:
        """Get inbound and outbound flows for a process in a DFD.

        Returns:
            Tuple of (inbound_flows, outbound_flows, bidirectional_flows) dicts.
        """
        inbound: dict[str, str] = {}
        outbound: dict[str, str] = {}

        for (flow_name, _flow_type), flow in parent_dfd.flows.items():
            if flow.target and flow.target.name == process_name:
                inbound[flow_name] = "inbound"
            if flow.source and flow.source.name == process_name:
                outbound[flow_name] = "outbound"

        return inbound, outbound, {}

    def _validate_dfd_flow_directions(
        self,
        dfd: DFDModel,
        parent_flows: tuple[dict[str, str], dict[str, str], dict[str, str]],
    ) -> None:
        """Validate that DFD flow directions match parent diagram."""
        parent_inbound, parent_outbound, _ = parent_flows

        for (flow_name, _flow_type), flow in dfd.flows.items():
            if flow.flow_type == "inbound" and flow_name in parent_outbound:
                self._error(
                    f"Flow '{flow_name}' direction mismatch: "
                    "declared as inbound but parent has it as outbound",
                    flow_name,
                    flow.source_file,
                    flow.line,
                )
            elif flow.flow_type == "outbound" and flow_name in parent_inbound:
                self._error(
                    f"Flow '{flow_name}' direction mismatch: "
                    "declared as outbound but parent has it as inbound",
                    flow_name,
                    flow.source_file,
                    flow.line,
                )

    def _validate_dfd_inbound_handlers(
        self,
        dfd: DFDModel,
        dfd_name: str,
        parent_flows: tuple[dict[str, str], dict[str, str], dict[str, str]],
        doc: DesignDocument,
    ) -> None:
        """Validate that inbound flows are handled exactly once.

        Supports flow type decomposition (REQ-SEM-090, REQ-SEM-091, REQ-SEM-092):
        - Child can use parent type directly
        - Child can decompose union types into subtypes
        - Mixing parent type with subtypes is an error
        """
        parent_inbound, _, parent_bidirectional = parent_flows
        inbound_handler_counts: dict[str, list[str]] = getattr(dfd, "_inbound_flow_handlers", {})

        # Check inbound and bidirectional flows (both require exactly one handler)
        for flow_name in list(parent_inbound.keys()) + list(parent_bidirectional.keys()):
            self._validate_flow_coverage_with_decomposition(
                dfd, dfd_name, flow_name, inbound_handler_counts, doc
            )

    def _validate_flow_coverage_with_decomposition(
        self,
        dfd: DFDModel,
        dfd_name: str,
        parent_flow_name: str,
        inbound_handlers: dict[str, list[str]],
        doc: DesignDocument,
    ) -> None:
        """Validate coverage for a single parent flow, supporting type decomposition.

        REQ-SEM-090: Flow type decomposition in refinements
        REQ-SEM-091: Mixing prohibition
        REQ-SEM-092: Nested union decomposition
        """
        # Check if the parent flow type is handled directly
        direct_handlers = inbound_handlers.get(parent_flow_name, [])

        # Get all subtypes at all levels for this flow type
        all_subtypes = self._get_all_union_subtypes(parent_flow_name, doc)

        if not all_subtypes:
            # Not a union type - use simple validation
            if len(direct_handlers) == 0:
                self._error(
                    f"Inbound flow '{parent_flow_name}' from parent not handled "
                    f"in DFD '{dfd_name}'",
                    dfd_name,
                    dfd.source_file,
                    dfd.refines.line if dfd.refines else dfd.line,
                )
            elif len(direct_handlers) > 1:
                self._error(
                    f"Inbound flow '{parent_flow_name}' handled by multiple processes "
                    f"in DFD '{dfd_name}'",
                    dfd_name,
                    dfd.source_file,
                    dfd.line,
                )
            return

        # It's a union type - check for decomposition
        # Find which subtypes are used
        used_subtypes: set[str] = set()
        for subtype in all_subtypes:
            if subtype in inbound_handlers and inbound_handlers[subtype]:
                used_subtypes.add(subtype)

        # Check for mixing (REQ-SEM-091)
        if direct_handlers and used_subtypes:
            # Using both parent type and subtypes - ERROR
            self._error(
                f"Flow type '{parent_flow_name}' cannot be mixed with its subtype "
                f"'{next(iter(used_subtypes))}' in refinement of "
                f"'{dfd.refines.diagram_name}.{dfd.refines.element_name}'"
                if dfd.refines
                else f"'{dfd_name}'",
                dfd_name,
                dfd.source_file,
                dfd.refines.line if dfd.refines else dfd.line,
            )
            return

        if direct_handlers:
            # Using parent type directly - validate normally
            if len(direct_handlers) > 1:
                self._error(
                    f"Inbound flow '{parent_flow_name}' handled by multiple processes "
                    f"in DFD '{dfd_name}'",
                    dfd_name,
                    dfd.source_file,
                    dfd.line,
                )
            return

        if used_subtypes:
            # Using decomposition - validate that it's at one level (REQ-SEM-092)
            # and all subtypes at that level are covered
            self._validate_decomposition_coverage(
                dfd, dfd_name, parent_flow_name, used_subtypes, inbound_handlers, doc
            )
            return

        # Neither parent type nor any subtypes handled - ERROR
        self._error(
            f"Inbound flow '{parent_flow_name}' from parent not handled in DFD '{dfd_name}'",
            dfd_name,
            dfd.source_file,
            dfd.refines.line if dfd.refines else dfd.line,
        )

    def _validate_decomposition_coverage(
        self,
        dfd: DFDModel,
        dfd_name: str,
        parent_flow_name: str,
        used_subtypes: set[str],
        inbound_handlers: dict[str, list[str]],
        doc: DesignDocument,
    ) -> None:
        """Validate that decomposition covers all subtypes at one level.

        REQ-SEM-090: All subtypes must be covered
        REQ-SEM-091: No mixing of levels
        REQ-SEM-092: Decomposition may stop at any level
        """
        # Find the decomposition level by checking which union level the used subtypes belong to
        immediate_subtypes = self._get_immediate_union_subtypes(parent_flow_name, doc)

        if not immediate_subtypes:
            return  # Not a union, shouldn't happen here

        # Check for level mixing (REQ-SEM-091, REQ-SEM-092)
        # For each immediate subtype, check if it or any of its subtypes are used
        for imm_subtype in immediate_subtypes:
            imm_subtype_subtypes = self._get_all_union_subtypes(imm_subtype, doc)

            # Is the immediate subtype itself used?
            imm_used = imm_subtype in used_subtypes

            # Are any of its subtypes used?
            nested_used = imm_subtype_subtypes & used_subtypes

            if imm_used and nested_used:
                # Mixing immediate subtype with its own subtypes - ERROR
                self._error(
                    f"Flow type '{imm_subtype}' cannot be mixed with its subtype "
                    f"'{next(iter(nested_used))}' in refinement of "
                    f"'{dfd.refines.diagram_name}.{dfd.refines.element_name}'"
                    if dfd.refines
                    else f"'{dfd_name}'",
                    dfd_name,
                    dfd.source_file,
                    dfd.refines.line if dfd.refines else dfd.line,
                )
                return

        # Determine which level of decomposition is being used
        # and validate that ALL subtypes at that level are covered
        self._validate_complete_level_coverage(
            dfd, dfd_name, parent_flow_name, used_subtypes, inbound_handlers, doc
        )

    def _validate_complete_level_coverage(
        self,
        dfd: DFDModel,
        dfd_name: str,
        parent_flow_name: str,
        used_subtypes: set[str],
        inbound_handlers: dict[str, list[str]],
        doc: DesignDocument,
    ) -> None:
        """Validate that all subtypes at the decomposition level are covered."""
        # Get the required subtypes at the level being used
        required_subtypes = self._get_required_subtypes_for_coverage(
            parent_flow_name, used_subtypes, doc
        )

        # Check each required subtype is handled exactly once
        for subtype in required_subtypes:
            handlers = inbound_handlers.get(subtype, [])
            if len(handlers) == 0:
                self._error(
                    f"Inbound flow '{parent_flow_name}' (decomposed) is missing "
                    f"coverage for subtype '{subtype}'",
                    dfd_name,
                    dfd.source_file,
                    dfd.refines.line if dfd.refines else dfd.line,
                )
            elif len(handlers) > 1:
                self._error(
                    f"Inbound flow '{subtype}' handled by multiple processes in DFD '{dfd_name}'",
                    dfd_name,
                    dfd.source_file,
                    dfd.line,
                )

    def _get_required_subtypes_for_coverage(
        self,
        parent_type: str,
        used_subtypes: set[str],
        doc: DesignDocument,
    ) -> set[str]:
        """Determine which subtypes are required for complete coverage.

        This handles nested unions by finding the decomposition level.
        """
        immediate = self._get_immediate_union_subtypes(parent_type, doc)

        if not immediate:
            return {parent_type}

        required: set[str] = set()

        for imm in immediate:
            # Check if this immediate subtype is used
            if imm in used_subtypes:
                required.add(imm)
            else:
                # Check if any nested subtypes are used
                nested = self._get_all_union_subtypes(imm, doc)
                if nested & used_subtypes:
                    # Recurse into this branch
                    required.update(
                        self._get_required_subtypes_for_coverage(imm, used_subtypes, doc)
                    )
                else:
                    # This branch has no used subtypes - require the immediate subtype
                    required.add(imm)

        return required

    def _get_immediate_union_subtypes(self, type_name: str, doc: DesignDocument) -> set[str]:
        """Get immediate union alternatives for a type (not recursive)."""
        from designit.model.datadict import TypeRef, UnionType

        if not doc.data_dictionary:
            return set()

        dd = doc.data_dictionary
        defn = dd.definitions.get(type_name)

        if not defn or not defn.is_union or not isinstance(defn.definition, UnionType):
            return set()

        result: set[str] = set()
        for alt in defn.definition.alternatives:
            if isinstance(alt, TypeRef):
                result.add(alt.qualified_name)
            elif isinstance(alt, str) and not (alt.startswith('"') or alt.startswith("'")):
                # Unquoted string = type reference
                result.add(alt)
            # Quoted strings (enum literals) are not subtypes for decomposition

        return result

    def _get_all_union_subtypes(self, type_name: str, doc: DesignDocument) -> set[str]:
        """Get all union alternatives recursively (for nested unions)."""
        from designit.model.datadict import TypeRef, UnionType

        if not doc.data_dictionary:
            return set()

        dd = doc.data_dictionary
        result: set[str] = set()
        visited: set[str] = set()

        def collect(name: str) -> None:
            if name in visited:
                return
            visited.add(name)

            defn = dd.definitions.get(name)
            if not defn or not defn.is_union or not isinstance(defn.definition, UnionType):
                return

            for alt in defn.definition.alternatives:
                if isinstance(alt, TypeRef):
                    alt_name = alt.qualified_name
                elif isinstance(alt, str) and not (alt.startswith('"') or alt.startswith("'")):
                    alt_name = alt
                else:
                    continue  # Skip enum literals

                result.add(alt_name)
                collect(alt_name)  # Recurse into nested unions

        collect(type_name)
        return result

    def _validate_erds(self, doc: DesignDocument) -> None:
        """Validate all ERDs."""
        for erd_name, erd in doc.erds.items():
            self._validate_erd_relationships(erd_name, erd)
            self._validate_erd_foreign_keys(erd_name, erd)
            self._validate_erd_primary_keys(erd_name, erd)

    def _validate_erd_relationships(self, erd_name: str, erd: Any) -> None:
        """Validate that relationships reference valid entities."""
        for rel_name, rel in erd.relationships.items():
            if rel.source_entity not in erd.entities:
                self._error(
                    f"Relationship '{rel_name}' references unknown entity '{rel.source_entity}'",
                    rel_name,
                    rel.source_file,
                    rel.line,
                )
            if rel.target_entity not in erd.entities:
                self._error(
                    f"Relationship '{rel_name}' references unknown entity '{rel.target_entity}'",
                    rel_name,
                    rel.source_file,
                    rel.line,
                )

    def _validate_erd_foreign_keys(self, erd_name: str, erd: Any) -> None:
        """Validate foreign key references in entities."""
        for entity_name, entity in erd.entities.items():
            for attr_name, attr in entity.attributes.items():
                for constraint in attr.constraints:
                    if constraint.target_entity and constraint.target_entity not in erd.entities:
                        self._error(
                            f"FK in '{entity_name}.{attr_name}' references "
                            f"unknown entity '{constraint.target_entity}'",
                            f"{entity_name}.{attr_name}",
                            entity.source_file,
                            entity.line,
                        )

    def _validate_erd_primary_keys(self, erd_name: str, erd: Any) -> None:
        """Check for entities without primary key."""
        for entity_name, entity in erd.entities.items():
            if not entity.is_placeholder and not entity.primary_keys:
                self._warning(
                    f"Entity '{entity_name}' has no primary key defined",
                    entity_name,
                    entity.source_file,
                    entity.line,
                )

    def _validate_stds(self, doc: DesignDocument) -> None:
        """Validate all STDs."""
        for std_name, std in doc.stds.items():
            # Check that transitions reference valid states
            for trans_name, trans in std.transitions.items():
                if trans.source_state not in std.states:
                    self._error(
                        f"Transition '{trans_name}' references "
                        f"unknown state '{trans.source_state}'",
                        trans_name,
                        trans.source_file,
                        trans.line,
                    )
                if trans.target_state not in std.states:
                    self._error(
                        f"Transition '{trans_name}' references "
                        f"unknown state '{trans.target_state}'",
                        trans_name,
                        trans.source_file,
                        trans.line,
                    )

            # Check initial state exists
            if std.initial_state and std.initial_state not in std.states:
                self._error(
                    f"Initial state '{std.initial_state}' not defined",
                    std.initial_state,
                    std.source_file,
                )

            # Check for unreachable states (if initial state is defined)
            if std.initial_state:
                reachable = std.get_reachable_states(std.initial_state)
                for state_name, state in std.states.items():
                    if state_name not in reachable and not state.is_placeholder:
                        self._warning(
                            f"State '{state_name}' is unreachable from initial state",
                            state_name,
                            state.source_file,
                            state.line,
                        )

    def _validate_structures(self, doc: DesignDocument) -> None:
        """Validate all structure charts."""
        for struct_name, struct in doc.structures.items():
            # Check that calls reference valid modules
            for module_name, module in struct.modules.items():
                for called in module.calls:
                    if called not in struct.modules:
                        self._error(
                            f"Module '{module_name}' calls unknown module '{called}'",
                            module_name,
                            module.source_file,
                            module.line,
                        )

            # Check for cycles
            cycles = struct.detect_cycles()
            for cycle in cycles:
                cycle_str = " -> ".join(cycle)
                self._warning(
                    f"Cyclic call detected: {cycle_str}",
                    cycle[0],
                )

    def _validate_scds(self, doc: DesignDocument) -> None:
        """Validate all SCDs."""
        for scd_name, scd in doc.scds.items():
            self._validate_scd_system(scd_name, scd)
            all_elements = self._collect_scd_elements(scd)
            self._validate_scd_flows(scd_name, scd, all_elements)
            self._validate_scd_orphan_elements(scd_name, scd)

    def _validate_scd_system(self, scd_name: str, scd: Any) -> None:
        """Check that exactly one system is defined."""
        if not scd.system:
            self._error(
                f"SCD '{scd_name}' must have exactly one system declaration",
                scd_name,
                scd.source_file,
            )

    def _collect_scd_elements(self, scd: Any) -> set[str]:
        """Collect all valid element names in an SCD."""
        all_elements: set[str] = set()
        if scd.system:
            all_elements.add(scd.system.name)
        all_elements.update(scd.externals.keys())
        all_elements.update(scd.datastores.keys())
        return all_elements

    def _validate_scd_flows(self, scd_name: str, scd: Any, all_elements: set[str]) -> None:
        """Validate flows reference valid elements and involve the system."""
        for flow_name, flow in scd.flows.items():
            if flow.source.name not in all_elements:
                self._error(
                    f"Flow '{flow_name}' references unknown source '{flow.source.name}'",
                    flow_name,
                    flow.source_file,
                    flow.line,
                )
            if flow.target.name not in all_elements:
                self._error(
                    f"Flow '{flow_name}' references unknown target '{flow.target.name}'",
                    flow_name,
                    flow.source_file,
                    flow.line,
                )

            # Check that flows involve the system
            if scd.system:
                system_name = scd.system.name
                if flow.source.name != system_name and flow.target.name != system_name:
                    self._warning(
                        f"Flow '{flow_name}' does not involve the system '{system_name}'",
                        flow_name,
                        flow.source_file,
                        flow.line,
                    )

    def _validate_scd_orphan_elements(self, scd_name: str, scd: Any) -> None:
        """Check for elements with no flows."""
        elements_with_flows: set[str] = set()
        for flow in scd.flows.values():
            elements_with_flows.add(flow.source.name)
            elements_with_flows.add(flow.target.name)

        for element in scd.all_elements():
            if element.name not in elements_with_flows and not element.is_placeholder:
                self._warning(
                    f"Element '{element.name}' has no data flows",
                    element.name,
                    element.source_file,
                    element.line,
                )

    def _validate_datadict(self, doc: DesignDocument) -> None:
        """Validate the data dictionary.

        This validates:
        - REQ-SEM-068: Union type consistency (no mixing enum literals with type refs)
        - REQ-SEM-069: Union type reference validation
        - REQ-SEM-064: Cross-namespace reference restriction
        - REQ-SEM-066: Namespace shadowing warning
        """
        if not doc.data_dictionary:
            return

        dd = doc.data_dictionary
        builtin_types = {
            "string",
            "integer",
            "decimal",
            "boolean",
            "datetime",
            "date",
            "time",
            "binary",
        }

        # REQ-SEM-066: Check for namespace names that shadow global type names
        self._validate_namespace_shadowing(doc)

        for def_name, defn in dd.definitions.items():
            if defn.is_placeholder:
                continue

            # REQ-SEM-068: Check union type consistency
            self._validate_union_consistency(def_name, defn)

            # Check type references with namespace-first resolution
            referenced = dd.get_all_referenced_types(def_name)
            for type_ref in referenced:
                self._validate_type_reference(dd, def_name, defn, type_ref, builtin_types)

    def _validate_union_consistency(self, def_name: str, defn: DataDefinition) -> None:
        """REQ-SEM-068: Validate that union types don't mix enum literals with type refs."""
        from designit.model.datadict import UnionType

        if not defn.is_union or not isinstance(defn.definition, UnionType):
            return

        union_def: UnionType = defn.definition
        has_enum_literals = False
        has_type_refs = False

        for alt in union_def.alternatives:
            if isinstance(alt, str):
                if alt.startswith('"') or alt.startswith("'"):
                    has_enum_literals = True
                else:
                    # Unquoted string = type reference (identifier or base type)
                    has_type_refs = True
            else:
                # TypeRef object = qualified type reference
                has_type_refs = True

        if has_enum_literals and has_type_refs:
            self._error(
                f"Union type '{def_name}' mixes enum literals with type references",
                def_name,
                defn.source_file,
                defn.line,
            )

    def _validate_type_reference(
        self,
        dd: Any,
        def_name: str,
        defn: DataDefinition,
        type_ref: TypeRef,
        builtin_types: set[str],
    ) -> None:
        """Validate a single type reference in a definition."""
        from designit.model.datadict import UnionType

        # Resolve the type reference using namespace-first lookup
        resolved_name = self._resolve_type_ref(type_ref, defn.namespace, dd.definitions)

        if resolved_name is None and type_ref.name not in builtin_types:
            # Check if it's a string literal (for unions) - these are preserved as strings
            if not (type_ref.name.startswith('"') or type_ref.name.startswith("'")):
                # REQ-SEM-069: Union type references are ERRORs (needed for flow decomposition)
                # REQ-SEM-050: Other type references (struct fields, arrays) are WARNINGs
                if defn.is_union and isinstance(defn.definition, UnionType):
                    self._error(
                        f"Type '{def_name}' references undefined type '{type_ref.qualified_name}'",
                        def_name,
                        defn.source_file,
                        defn.line,
                    )
                else:
                    self._warning(
                        f"Type '{def_name}' references undefined type '{type_ref.qualified_name}'",
                        def_name,
                        defn.source_file,
                        defn.line,
                    )
            return

        # REQ-SEM-064: Cross-namespace reference restriction
        if defn.namespace and resolved_name:
            self._validate_cross_namespace_ref(dd, def_name, defn, type_ref, resolved_name)

    def _validate_cross_namespace_ref(
        self,
        dd: Any,
        def_name: str,
        defn: DataDefinition,
        type_ref: TypeRef,
        resolved_name: str,
    ) -> None:
        """Validate cross-namespace reference restrictions."""
        if type_ref.is_qualified:
            # Qualified reference like ServiceA.Type - check if it's a different namespace
            if type_ref.namespace != defn.namespace:
                self._error(
                    f"Type '{def_name}' in namespace '{defn.namespace}' "
                    f"cannot reference type '{type_ref.qualified_name}' from "
                    f"different namespace '{type_ref.namespace}'. Types can only "
                    f"reference same namespace or anonymous types.",
                    def_name,
                    defn.source_file,
                    defn.line,
                )
        else:
            # Simple reference - resolved via namespace-first lookup
            # Check if it resolved to a different namespace
            if resolved_name in dd.definitions:
                ref_defn = dd.definitions[resolved_name]
                if ref_defn.namespace is not None and ref_defn.namespace != defn.namespace:
                    self._error(
                        f"Type '{def_name}' in namespace '{defn.namespace}' "
                        f"cannot reference type '{resolved_name}' from different "
                        f"namespace '{ref_defn.namespace}'. Types can only "
                        f"reference same namespace or anonymous types.",
                        def_name,
                        defn.source_file,
                        defn.line,
                    )

    def _resolve_type_ref(
        self,
        type_ref: TypeRef,
        current_namespace: str | None,
        definitions: dict[str, DataDefinition],
    ) -> str | None:
        """Resolve a type reference to its qualified name, or None if not found.

        Resolution rules:
        1. If qualified (Namespace.Type): look for exact match
        2. If simple (Type) in a namespace: try same namespace first, then global
        3. If simple (Type) in anonymous: try global only

        Args:
            type_ref: The type reference to resolve.
            current_namespace: The namespace of the type containing this reference.
            definitions: All type definitions in the data dictionary.

        Returns:
            The qualified name of the resolved type, or None if not found.
        """
        if type_ref.is_qualified:
            # Qualified reference: look for exact match
            qualified = type_ref.qualified_name
            return qualified if qualified in definitions else None

        # Simple reference
        if current_namespace:
            # First: try same namespace
            namespaced = f"{current_namespace}.{type_ref.name}"
            if namespaced in definitions:
                return namespaced

        # Second: try global (anonymous namespace)
        if type_ref.name in definitions:
            defn = definitions[type_ref.name]
            if defn.namespace is None:  # Must be global (anonymous)
                return type_ref.name

        return None

    def _validate_namespace_shadowing(self, doc: DesignDocument) -> None:
        """Warn when namespace names shadow global type names (REQ-SEM-066).

        When a datadict namespace name matches a global (anonymous) type name,
        this can cause confusion. Emit a warning with both the namespace and
        the conflicting global type's qualified name.
        """
        if not doc.data_dictionary:
            return

        dd = doc.data_dictionary

        # Collect global (anonymous) type names
        global_types: dict[str, DataDefinition] = {}
        for name, defn in dd.definitions.items():
            if defn.namespace is None:
                global_types[name] = defn

        # Collect all namespace names and find one type per namespace for location info
        namespace_info: dict[str, DataDefinition] = {}  # namespace -> first definition in it
        for defn in dd.definitions.values():
            if defn.namespace and defn.namespace not in namespace_info:
                namespace_info[defn.namespace] = defn

        # Check for shadowing
        for namespace, ns_defn in namespace_info.items():
            if namespace in global_types:
                global_defn = global_types[namespace]
                self._warning(
                    f"Namespace '{namespace}' shadows global type '{namespace}' "
                    f"(defined at {global_defn.source_file or 'unknown'}:"
                    f"{global_defn.line or '?'}). "
                    f"Use qualified references to avoid ambiguity.",
                    namespace,
                    ns_defn.source_file,
                    ns_defn.line,
                )

    def _validate_cross_references(self, doc: DesignDocument) -> None:
        """Validate cross-references between different diagram types.

        This validates:
        - REQ-SEM-061: SCD flow types must be in data dictionary
        - REQ-SEM-062: DFD flow types must be in data dictionary
        - REQ-SEM-063: Namespaced types must be qualified in flows
        """
        data_types, namespaced_simple_names = self._build_datadict_type_maps(doc)
        self._validate_dfd_flow_types(doc, data_types, namespaced_simple_names)
        self._validate_scd_flow_types(doc, data_types, namespaced_simple_names)

    def _build_datadict_type_maps(
        self, doc: DesignDocument
    ) -> tuple[set[str], dict[str, list[str]]]:
        """Build maps of data types for cross-reference validation."""
        data_types: set[str] = set()
        namespaced_simple_names: dict[str, list[str]] = {}

        if doc.data_dictionary:
            data_types = set(doc.data_dictionary.definitions.keys())
            for qualified_name, defn in doc.data_dictionary.definitions.items():
                if defn.namespace:
                    if defn.name not in namespaced_simple_names:
                        namespaced_simple_names[defn.name] = []
                    namespaced_simple_names[defn.name].append(qualified_name)

        return data_types, namespaced_simple_names

    def _validate_dfd_flow_types(
        self,
        doc: DesignDocument,
        data_types: set[str],
        namespaced_simple_names: dict[str, list[str]],
    ) -> None:
        """Validate DFD flow types against data dictionary."""
        for dfd_name, dfd in doc.dfds.items():
            for flow in dfd.flows.values():
                type_name = flow.type_ref.qualified_name if flow.type_ref else flow.name
                self._check_flow_type(
                    flow, type_name, f"DFD '{dfd_name}'", data_types, namespaced_simple_names
                )

    def _validate_scd_flow_types(
        self,
        doc: DesignDocument,
        data_types: set[str],
        namespaced_simple_names: dict[str, list[str]],
    ) -> None:
        """Validate SCD flow types against data dictionary."""
        for scd_name, scd in doc.scds.items():
            for flow in scd.flows.values():
                type_name = flow.type_ref.qualified_name if flow.type_ref else flow.name
                self._check_flow_type(
                    flow, type_name, f"SCD '{scd_name}'", data_types, namespaced_simple_names
                )

    def _check_flow_type(
        self,
        flow: Any,
        type_name: str,
        diagram_desc: str,
        data_types: set[str],
        namespaced_simple_names: dict[str, list[str]],
    ) -> None:
        """Check if a flow type is defined in the data dictionary."""
        if type_name not in data_types:
            if type_name in namespaced_simple_names:
                opts = ", ".join(namespaced_simple_names[type_name])
                self._error(
                    f"Flow '{flow.name}' in {diagram_desc} uses unqualified "
                    f"type '{type_name}' which exists in namespace(s): {opts}. "
                    f"Use qualified name instead.",
                    flow.name,
                    flow.source_file,
                    flow.line,
                )
            else:
                self._error(
                    f"Flow '{flow.name}' in {diagram_desc} is not defined in data dictionary",
                    flow.name,
                    flow.source_file,
                    flow.line,
                )

    def _check_duplicate_name(
        self,
        seen_names: dict[str, tuple[str, str, str | None, int | None]],
        name: str,
        elem_type: str,
        diagram_name: str,
        source_file: str | None,
        line: int | None,
    ) -> None:
        """Check if a name is duplicate and report error if so.

        Args:
            seen_names: Dict tracking seen names -> (type, diagram, source_file, line).
            name: The element name to check.
            elem_type: The type of element (system, external, datastore, process).
            diagram_name: The name of the diagram containing the element.
            source_file: The source file of the element.
            line: The line number of the element.
        """
        if name in seen_names:
            prev_type, prev_diagram, _, _ = seen_names[name]
            self._error(
                f"Duplicate element name '{name}': {elem_type} in '{diagram_name}' "
                f"conflicts with {prev_type} in '{prev_diagram}'",
                name,
                source_file,
                line,
            )
        else:
            seen_names[name] = (elem_type, diagram_name, source_file, line)

    def _validate_unique_names(self, doc: DesignDocument) -> None:
        """Validate no duplicate element names across the document.

        REQ-SEM-087: No duplicate element names across the import tree.
        Applies to: systems, externals, datastores, processes.
        """
        # Track seen names with their location info: name -> (type, diagram, source_file, line)
        seen_names: dict[str, tuple[str, str, str | None, int | None]] = {}

        # Collect systems and their elements from all SCDs
        for scd_name, scd in doc.scds.items():
            if scd.system:
                self._check_duplicate_name(
                    seen_names,
                    scd.system.name,
                    "system",
                    f"SCD '{scd_name}'",
                    scd.system.source_file,
                    scd.system.line,
                )

            for ext_name, ext in scd.externals.items():
                self._check_duplicate_name(
                    seen_names,
                    ext_name,
                    "external",
                    f"SCD '{scd_name}'",
                    ext.source_file,
                    ext.line,
                )

            for ds_name, ds in scd.datastores.items():
                self._check_duplicate_name(
                    seen_names,
                    ds_name,
                    "datastore",
                    f"SCD '{scd_name}'",
                    ds.source_file,
                    ds.line,
                )

        # Collect processes from all DFDs
        for dfd_name, dfd in doc.dfds.items():
            for proc_name, proc in dfd.processes.items():
                self._check_duplicate_name(
                    seen_names,
                    proc_name,
                    "process",
                    f"DFD '{dfd_name}'",
                    proc.source_file,
                    proc.line,
                )

    def _validate_dfd_datastore_conflicts(self, doc: DesignDocument) -> None:
        """Validate DFD local datastores don't conflict with SCD elements.

        REQ-SEM-085: DFDs may declare local datastores.
        REQ-SEM-086: Child DFDs can reference datastores from the parent tree.
        """
        # Collect all SCD element names (externals and datastores)
        scd_element_names: dict[str, tuple[str, str]] = {}  # name -> (type, scd_name)

        for scd_name, scd in doc.scds.items():
            for ext_name in scd.externals:
                scd_element_names[ext_name] = ("external", scd_name)
            for ds_name in scd.datastores:
                scd_element_names[ds_name] = ("datastore", scd_name)

        # Check DFD datastores for conflicts
        for dfd_name, dfd in doc.dfds.items():
            for ds_name, ds in dfd.datastores.items():
                if ds_name in scd_element_names:
                    elem_type, scd_name = scd_element_names[ds_name]
                    self._error(
                        f"Duplicate element name '{ds_name}': datastore in DFD '{dfd_name}' "
                        f"conflicts with {elem_type} in SCD '{scd_name}'",
                        ds_name,
                        ds.source_file,
                        ds.line,
                    )

    def _collect_all_element_names(self, doc: DesignDocument) -> dict[str, tuple[str, str]]:
        """Collect all element names from SCDs and DFDs.

        Returns: dict mapping name -> (element_type, location_description)
        """
        all_element_names: dict[str, tuple[str, str]] = {}

        # From SCDs: systems, externals, datastores
        for scd_name, scd in doc.scds.items():
            if scd.system:
                all_element_names[scd.system.name] = ("system", f"SCD '{scd_name}'")
            for ext_name in scd.externals:
                all_element_names[ext_name] = ("external", f"SCD '{scd_name}'")
            for ds_name in scd.datastores:
                all_element_names[ds_name] = ("datastore", f"SCD '{scd_name}'")

        # From DFDs: processes, local datastores
        for dfd_name, dfd in doc.dfds.items():
            for proc_name in dfd.processes:
                all_element_names[proc_name] = ("process", f"DFD '{dfd_name}'")
            for ds_name in dfd.datastores:
                all_element_names[ds_name] = ("datastore", f"DFD '{dfd_name}'")

        return all_element_names

    def _check_namespaced_type_conflict(self, defn: DataDefinition, doc: DesignDocument) -> None:
        """Check if a namespaced datadict type conflicts with elements in same-named SCD/DFD."""
        type_name = defn.name
        namespace = defn.namespace
        assert namespace is not None

        # Check SCD with same name as namespace
        if namespace in doc.scds:
            scd = doc.scds[namespace]
            conflict = self._find_scd_element_conflict(scd, type_name)
            if conflict:
                self._error(
                    f"Duplicate name '{type_name}': datadict type in '{namespace}' "
                    f"conflicts with {conflict} in SCD '{namespace}'",
                    type_name,
                    defn.source_file,
                    defn.line,
                )

        # Check DFD with same name as namespace
        if namespace in doc.dfds:
            dfd = doc.dfds[namespace]
            conflict = self._find_dfd_element_conflict(dfd, type_name)
            if conflict:
                self._error(
                    f"Duplicate name '{type_name}': datadict type in '{namespace}' "
                    f"conflicts with {conflict} in DFD '{namespace}'",
                    type_name,
                    defn.source_file,
                    defn.line,
                )

    def _find_scd_element_conflict(self, scd: SCDModel, name: str) -> str | None:
        """Find if name conflicts with any SCD element. Returns element type or None."""
        if scd.system and scd.system.name == name:
            return "system"
        if name in scd.externals:
            return "external"
        if name in scd.datastores:
            return "datastore"
        return None

    def _find_dfd_element_conflict(self, dfd: DFDModel, name: str) -> str | None:
        """Find if name conflicts with any DFD element. Returns element type or None."""
        if name in dfd.processes:
            return "process"
        if name in dfd.datastores:
            return "datastore"
        return None

    def _validate_datadict_name_conflicts(self, doc: DesignDocument) -> None:
        """Validate datadict type names don't conflict with diagram element names.

        REQ-SEM-088: Datadict type names must not conflict with element names.

        Rules:
        - Anonymous types must not match any element name (external, datastore, system, process)
        - Namespaced types must not match elements in same-named SCD or DFD
        """
        if not doc.data_dictionary:
            return

        all_element_names = self._collect_all_element_names(doc)

        # Check each datadict type
        for defn in doc.data_dictionary.definitions.values():
            type_name = defn.name
            namespace = defn.namespace

            if namespace is None:
                # Anonymous type: check against ALL element names
                if type_name in all_element_names:
                    elem_type, elem_loc = all_element_names[type_name]
                    self._error(
                        f"Duplicate name '{type_name}': datadict type conflicts with "
                        f"{elem_type} in {elem_loc}",
                        type_name,
                        defn.source_file,
                        defn.line,
                    )
            else:
                # Namespaced type: check against same-named SCD or DFD only
                self._check_namespaced_type_conflict(defn, doc)

    def _report_placeholders(self, doc: DesignDocument) -> None:
        """Report all placeholder elements."""
        placeholders = doc.placeholders
        if placeholders:
            self._info(f"Document contains {len(placeholders)} placeholder(s) to be defined")
            for elem_type, name, file in placeholders:
                self._info(f"Placeholder: {elem_type} '{name}'", name, file)


def validate(doc: DesignDocument) -> list[ValidationMessage]:
    """Validate a design document.

    Args:
        doc: The document to validate.

    Returns:
        A list of validation messages.
    """
    validator = Validator()
    messages = validator.validate(doc)
    doc.validation_messages.extend(messages)
    return messages
