"""Validation rules for design documents."""

from __future__ import annotations

from typing import TYPE_CHECKING

from designit.model.base import (
    DesignDocument,
    ValidationMessage,
    ValidationSeverity,
)

if TYPE_CHECKING:
    from designit.model.datadict import DataDefinition, TypeRef


class Validator:
    """Validates design documents for consistency and completeness."""

    def __init__(self):
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
                # Can only refine system
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
            elif parent_dfd:
                # Can only refine process
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
            parent_inbound_flows: dict[str, str] = {}  # flow_name -> direction
            parent_outbound_flows: dict[str, str] = {}
            parent_bidirectional_flows: dict[str, str] = {}

            if parent_scd:
                system_name = element_name
                for flow_name, flow in parent_scd.flows.items():
                    if flow.target.name == system_name:
                        # Flow into the system (inbound)
                        if flow.direction == "bidirectional":
                            parent_bidirectional_flows[flow_name] = "bidirectional"
                        else:
                            parent_inbound_flows[flow_name] = "inbound"
                    if flow.source.name == system_name:
                        # Flow out of the system (outbound)
                        if flow.direction == "bidirectional":
                            parent_bidirectional_flows[flow_name] = "bidirectional"
                        else:
                            parent_outbound_flows[flow_name] = "outbound"
            elif parent_dfd:
                process_name = element_name
                for (flow_name, _flow_type), flow in parent_dfd.flows.items():
                    if flow.target and flow.target.name == process_name:
                        parent_inbound_flows[flow_name] = "inbound"
                    if flow.source and flow.source.name == process_name:
                        parent_outbound_flows[flow_name] = "outbound"

            # Get inbound handler counts from the analyzer (tracks duplicate declarations)
            inbound_handler_counts: dict[str, list[str]] = getattr(
                dfd, "_inbound_flow_handlers", {}
            )

            # Check for direction mismatches in declared flows
            for (flow_name, _flow_type), flow in dfd.flows.items():
                if flow.flow_type == "inbound":
                    # Check for direction mismatch with parent
                    if flow_name in parent_outbound_flows:
                        self._error(
                            f"Flow '{flow_name}' direction mismatch: declared as inbound but parent has it as outbound",
                            flow_name,
                            flow.source_file,
                            flow.line,
                        )
                elif flow.flow_type == "outbound":
                    # Check for direction mismatch with parent
                    if flow_name in parent_inbound_flows:
                        self._error(
                            f"Flow '{flow_name}' direction mismatch: declared as outbound but parent has it as inbound",
                            flow_name,
                            flow.source_file,
                            flow.line,
                        )
                    # Outbound flows can be handled 0+ times, no error needed

            # Check inbound flows: must be handled exactly once
            for flow_name in parent_inbound_flows:
                handlers = inbound_handler_counts.get(flow_name, [])
                if len(handlers) == 0:
                    self._error(
                        f"Inbound flow '{flow_name}' from parent not handled in DFD '{dfd_name}'",
                        dfd_name,
                        dfd.source_file,
                        dfd.refines.line if dfd.refines else dfd.line,
                    )
                elif len(handlers) > 1:
                    self._error(
                        f"Inbound flow '{flow_name}' handled by multiple processes in DFD '{dfd_name}'",
                        dfd_name,
                        dfd.source_file,
                        dfd.line,
                    )

            # Check bidirectional flows: inbound part must be handled exactly once
            for flow_name in parent_bidirectional_flows:
                handlers = inbound_handler_counts.get(flow_name, [])
                if len(handlers) == 0:
                    self._error(
                        f"Inbound flow '{flow_name}' from parent not handled in DFD '{dfd_name}'",
                        dfd_name,
                        dfd.source_file,
                        dfd.refines.line if dfd.refines else dfd.line,
                    )
                elif len(handlers) > 1:
                    self._error(
                        f"Inbound flow '{flow_name}' handled by multiple processes in DFD '{dfd_name}'",
                        dfd_name,
                        dfd.source_file,
                        dfd.line,
                    )

    def _validate_erds(self, doc: DesignDocument) -> None:
        """Validate all ERDs."""
        for erd_name, erd in doc.erds.items():
            # Check that relationships reference valid entities
            for rel_name, rel in erd.relationships.items():
                if rel.source_entity not in erd.entities:
                    self._error(
                        f"Relationship '{rel_name}' references "
                        f"unknown entity '{rel.source_entity}'",
                        rel_name,
                        rel.source_file,
                        rel.line,
                    )
                if rel.target_entity not in erd.entities:
                    self._error(
                        f"Relationship '{rel_name}' references "
                        f"unknown entity '{rel.target_entity}'",
                        rel_name,
                        rel.source_file,
                        rel.line,
                    )

            # Check FK references
            for entity_name, entity in erd.entities.items():
                for attr_name, attr in entity.attributes.items():
                    for constraint in attr.constraints:
                        if (
                            constraint.target_entity
                            and constraint.target_entity not in erd.entities
                        ):
                            self._error(
                                f"FK in '{entity_name}.{attr_name}' references "
                                f"unknown entity '{constraint.target_entity}'",
                                f"{entity_name}.{attr_name}",
                                entity.source_file,
                                entity.line,
                            )

            # Check for entities without primary key
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
            # Check that exactly one system is defined
            if not scd.system:
                self._error(
                    f"SCD '{scd_name}' must have exactly one system declaration",
                    scd_name,
                    scd.source_file,
                )

            # Collect all valid element names
            all_elements: set[str] = set()
            if scd.system:
                all_elements.add(scd.system.name)
            all_elements.update(scd.externals.keys())
            all_elements.update(scd.datastores.keys())

            # Check that flows reference valid elements
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

            # Check for orphan elements (no flows in or out)
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
        - Type references exist
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

        # Build a map of simple names to their namespaces for cross-reference checking
        type_namespaces: dict[str, str | None] = {}  # simple_name -> namespace (None = anonymous)
        for qualified_name, defn in dd.definitions.items():
            type_namespaces[qualified_name] = defn.namespace

        for def_name, defn in dd.definitions.items():
            if defn.is_placeholder:
                continue

            # Check type references with namespace-first resolution
            referenced = dd.get_all_referenced_types(def_name)
            for type_ref in referenced:
                # Resolve the type reference using namespace-first lookup
                resolved_name = self._resolve_type_ref(type_ref, defn.namespace, dd.definitions)

                if resolved_name is None and type_ref.name not in builtin_types:
                    # Check if it's a string literal (for unions) - these are preserved as strings
                    if not (type_ref.name.startswith('"') or type_ref.name.startswith("'")):
                        self._warning(
                            f"Type '{def_name}' references undefined type "
                            f"'{type_ref.qualified_name}'",
                            def_name,
                            defn.source_file,
                            defn.line,
                        )
                    continue

                # REQ-SEM-064: Cross-namespace reference restriction
                # Types in named datadict can only reference same namespace or anonymous types
                if defn.namespace and resolved_name:
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
                            if (
                                ref_defn.namespace is not None
                                and ref_defn.namespace != defn.namespace
                            ):
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
        type_ref: "TypeRef",
        current_namespace: str | None,
        definitions: dict[str, "DataDefinition"],
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
        from designit.model.datadict import TypeRef  # Import here to avoid circular import

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
        global_types: dict[str, "DataDefinition"] = {}
        for name, defn in dd.definitions.items():
            if defn.namespace is None:
                global_types[name] = defn

        # Collect all namespace names and find one type per namespace for location info
        namespace_info: dict[str, "DataDefinition"] = {}  # namespace -> first definition in it
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
        # Collect all data types from data dictionary
        data_types: set[str] = set()
        namespaced_simple_names: dict[str, list[str]] = {}  # simple_name -> [qualified_names]

        if doc.data_dictionary:
            data_types = set(doc.data_dictionary.definitions.keys())
            # Build a map of simple names to their namespaced qualified names
            for qualified_name, defn in doc.data_dictionary.definitions.items():
                if defn.namespace:  # Only track namespaced types
                    if defn.name not in namespaced_simple_names:
                        namespaced_simple_names[defn.name] = []
                    namespaced_simple_names[defn.name].append(qualified_name)

        # Check DFD flow types against data dictionary (REQ-SEM-062, REQ-SEM-063)
        for dfd_name, dfd in doc.dfds.items():
            for flow in dfd.flows.values():
                # Determine the type name to check
                if flow.type_ref:
                    # Flow has explicit type reference
                    type_name = flow.type_ref.qualified_name
                else:
                    # Use flow name as type name (backward compatibility)
                    type_name = flow.name

                if type_name not in data_types:
                    # Check if it's an unqualified reference to a namespaced type
                    if type_name in namespaced_simple_names:
                        qualified_options = namespaced_simple_names[type_name]
                        opts = ", ".join(qualified_options)
                        self._error(
                            f"Flow '{flow.name}' in DFD '{dfd_name}' uses unqualified "
                            f"type '{type_name}' which exists in namespace(s): {opts}. "
                            f"Use qualified name instead.",
                            flow.name,
                            flow.source_file,
                            flow.line,
                        )
                    else:
                        self._error(
                            f"Flow '{flow.name}' in DFD '{dfd_name}' is not defined "
                            f"in data dictionary",
                            flow.name,
                            flow.source_file,
                            flow.line,
                        )

        # Check SCD flow types against data dictionary (REQ-SEM-061, REQ-SEM-063)
        for scd_name, scd in doc.scds.items():
            for flow in scd.flows.values():
                # Determine the type name to check
                if flow.type_ref:
                    # Flow has explicit type reference
                    type_name = flow.type_ref.qualified_name
                else:
                    # Use flow name as type name (backward compatibility)
                    type_name = flow.name

                if type_name not in data_types:
                    # Check if it's an unqualified reference to a namespaced type
                    if type_name in namespaced_simple_names:
                        qualified_options = namespaced_simple_names[type_name]
                        opts = ", ".join(qualified_options)
                        self._error(
                            f"Flow '{flow.name}' in SCD '{scd_name}' uses unqualified "
                            f"type '{type_name}' which exists in namespace(s): {opts}. "
                            f"Use qualified name instead.",
                            flow.name,
                            flow.source_file,
                            flow.line,
                        )
                    else:
                        self._error(
                            f"Flow '{flow.name}' in SCD '{scd_name}' is not defined "
                            f"in data dictionary",
                            flow.name,
                            flow.source_file,
                            flow.line,
                        )

    def _validate_unique_names(self, doc: DesignDocument) -> None:
        """Validate no duplicate element names across the document.

        REQ-SEM-087: No duplicate element names across the import tree.
        """
        # Track seen names with their location info: name -> (type, diagram, source_file, line)
        seen_names: dict[str, tuple[str, str, str | None, int | None]] = {}

        # Collect externals from all SCDs
        for scd_name, scd in doc.scds.items():
            for ext_name, ext in scd.externals.items():
                if ext_name in seen_names:
                    prev_type, prev_diagram, _, _ = seen_names[ext_name]
                    self._error(
                        f"Duplicate element name '{ext_name}': external in SCD '{scd_name}' "
                        f"conflicts with {prev_type} in '{prev_diagram}'",
                        ext_name,
                        ext.source_file,
                        ext.line,
                    )
                else:
                    seen_names[ext_name] = ("external", scd_name, ext.source_file, ext.line)

            # Collect datastores from SCDs
            for ds_name, ds in scd.datastores.items():
                if ds_name in seen_names:
                    prev_type, prev_diagram, _, _ = seen_names[ds_name]
                    self._error(
                        f"Duplicate element name '{ds_name}': datastore in SCD '{scd_name}' "
                        f"conflicts with {prev_type} in '{prev_diagram}'",
                        ds_name,
                        ds.source_file,
                        ds.line,
                    )
                else:
                    seen_names[ds_name] = ("datastore", scd_name, ds.source_file, ds.line)

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
