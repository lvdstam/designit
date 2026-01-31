"""Validation rules for design documents."""

from __future__ import annotations

from designit.model.base import (
    DesignDocument,
    ValidationMessage,
    ValidationSeverity,
)


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
        self._validate_erds(doc)
        self._validate_stds(doc)
        self._validate_structures(doc)
        self._validate_scds(doc)
        self._validate_datadict(doc)
        self._validate_cross_references(doc)
        self._report_placeholders(doc)

        return self.messages

    def _validate_dfds(self, doc: DesignDocument) -> None:
        """Validate all DFDs."""
        for dfd_name, dfd in doc.dfds.items():
            # Check that flows reference valid elements
            all_elements = (
                set(dfd.externals.keys()) | set(dfd.processes.keys()) | set(dfd.datastores.keys())
            )

            for flow_name, flow in dfd.flows.items():
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

            # Check for orphan elements (no flows in or out)
            elements_with_flows: set[str] = set()
            for flow in dfd.flows.values():
                elements_with_flows.add(flow.source.name)
                elements_with_flows.add(flow.target.name)

            for element in dfd.all_elements():
                if element.name not in elements_with_flows and not element.is_placeholder:
                    self._warning(
                        f"Element '{element.name}' has no data flows",
                        element.name,
                        element.source_file,
                        element.line,
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
        """Validate the data dictionary."""
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

        for def_name, defn in dd.definitions.items():
            if defn.is_placeholder:
                continue

            # Check type references
            referenced = dd.get_all_referenced_types(def_name)
            for ref_type in referenced:
                if ref_type not in dd.definitions and ref_type not in builtin_types:
                    # Check if it's a string literal (for unions)
                    if not (ref_type.startswith('"') or ref_type.startswith("'")):
                        self._warning(
                            f"Type '{def_name}' references undefined type '{ref_type}'",
                            def_name,
                            defn.source_file,
                            defn.line,
                        )

    def _validate_cross_references(self, doc: DesignDocument) -> None:
        """Validate cross-references between different diagram types."""
        # Collect all data types from data dictionary
        data_types: set[str] = set()
        if doc.data_dictionary:
            data_types = set(doc.data_dictionary.definitions.keys())

        # Check DFD flow types against data dictionary (REQ-SEM-062)
        for dfd_name, dfd in doc.dfds.items():
            for flow in dfd.flows.values():
                if flow.name not in data_types:
                    self._error(
                        f"Flow '{flow.name}' in DFD '{dfd_name}' is not defined in data dictionary",
                        flow.name,
                        flow.source_file,
                        flow.line,
                    )

        # Check SCD flow types against data dictionary (REQ-SEM-061)
        for scd_name, scd in doc.scds.items():
            for flow in scd.flows.values():
                if flow.name not in data_types:
                    self._error(
                        f"Flow '{flow.name}' in SCD '{scd_name}' is not defined in data dictionary",
                        flow.name,
                        flow.source_file,
                        flow.line,
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
