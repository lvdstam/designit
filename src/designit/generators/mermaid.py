"""Mermaid output generator for design diagrams."""

from __future__ import annotations

import io
from typing import TextIO

from designit.model.base import DesignDocument
from designit.model.dfd import DFDModel
from designit.model.erd import ERDModel
from designit.model.scd import SCDModel
from designit.model.std import STDModel
from designit.model.structure import StructureModel


class MermaidGenerator:
    """Generates Mermaid diagram output for design diagrams."""

    def __init__(self, include_placeholders: bool = True):
        """Initialize the generator.

        Args:
            include_placeholders: If True, include placeholder elements with special styling.
        """
        self.include_placeholders = include_placeholders

    def _escape(self, text: str) -> str:
        """Escape text for Mermaid labels."""
        # Mermaid uses quotes for labels with special characters
        return text.replace('"', "'").replace("\n", "<br/>")

    def _safe_id(self, name: str) -> str:
        """Convert a name to a safe Mermaid ID."""
        # Replace spaces and special characters
        return name.replace(" ", "_").replace("-", "_").replace(".", "_")

    # ============================================
    # DFD Generation (using flowchart)
    # ============================================

    def generate_dfd(self, dfd: DFDModel) -> str:
        """Generate Mermaid output for a DFD.

        Args:
            dfd: The DFD model to generate.

        Returns:
            Mermaid format string.
        """
        output = io.StringIO()
        self._write_dfd(dfd, output)
        return output.getvalue()

    def _write_dfd(self, dfd: DFDModel, out: TextIO) -> None:
        """Write DFD to Mermaid format."""
        out.write(f"---\ntitle: {dfd.name}\n---\n")
        out.write("flowchart TB\n")

        # Write nodes
        self._write_dfd_externals(dfd, out)
        self._write_dfd_processes(dfd, out)
        self._write_dfd_datastores(dfd, out)

        # Detect bidirectional flows and write boundary nodes
        bidirectional = self._detect_dfd_bidirectional_flows(dfd)
        boundary_nodes = self._write_dfd_boundary_nodes(dfd, bidirectional, out)

        # Write flows
        out.write("\n")
        self._write_dfd_flows(dfd, bidirectional, out)

        # Write placeholder styles and boundary class
        self._write_dfd_styles(dfd, boundary_nodes, out)

    def _write_dfd_externals(self, dfd: DFDModel, out: TextIO) -> None:
        """Write external entity nodes to Mermaid output."""
        for name, ext in dfd.externals.items():
            if not self.include_placeholders and ext.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if ext.description:
                label += f"<br/><i>{self._escape(ext.description)}</i>"
            out.write(f'    {safe_id}["{label}"]\n')

    def _write_dfd_processes(self, dfd: DFDModel, out: TextIO) -> None:
        """Write process nodes to Mermaid output."""
        for name, proc in dfd.processes.items():
            if not self.include_placeholders and proc.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if proc.description:
                label += f"<br/>{self._escape(proc.description)}"
            out.write(f'    {safe_id}("{label}")\n')

    def _write_dfd_datastores(self, dfd: DFDModel, out: TextIO) -> None:
        """Write datastore nodes to Mermaid output."""
        for name, ds in dfd.datastores.items():
            if not self.include_placeholders and ds.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if ds.description:
                label += f"<br/>{self._escape(ds.description)}"
            out.write(f'    {safe_id}[("{label}")]\n')

    def _detect_dfd_bidirectional_flows(self, dfd: DFDModel) -> dict[str, str]:
        """Detect bidirectional boundary flows.

        Returns:
            Dict mapping flow_name to process_name for flows where the same
            process handles both inbound and outbound directions.
        """
        inbound_targets: dict[str, str] = {}
        outbound_sources: dict[str, str] = {}

        for (flow_name, flow_type), flow in dfd.flows.items():
            if flow_type == "inbound" and flow.target:
                inbound_targets[flow_name] = flow.target.name
            elif flow_type == "outbound" and flow.source:
                outbound_sources[flow_name] = flow.source.name

        # Find flows where same process handles both directions
        bidirectional: dict[str, str] = {}
        for flow_name, target in inbound_targets.items():
            if flow_name in outbound_sources and outbound_sources[flow_name] == target:
                bidirectional[flow_name] = target

        return bidirectional

    def _write_dfd_boundary_nodes(
        self, dfd: DFDModel, bidirectional: dict[str, str], out: TextIO
    ) -> set[str]:
        """Write boundary marker nodes for boundary flows.

        Returns:
            Set of boundary node IDs that were written.
        """
        boundary_nodes: set[str] = set()
        for (flow_name, flow_type), flow in dfd.flows.items():
            if flow_type not in ("inbound", "outbound"):
                continue
            # Skip outbound if it's part of a bidirectional pair (handled with inbound)
            if flow_name in bidirectional and flow_type == "outbound":
                continue
            boundary_id = f"_boundary_{self._safe_id(flow_name)}"
            if boundary_id not in boundary_nodes:
                boundary_nodes.add(boundary_id)
                out.write(f"    {boundary_id}(( )):::boundary\n")
        return boundary_nodes

    def _write_dfd_flows(self, dfd: DFDModel, bidirectional: dict[str, str], out: TextIO) -> None:
        """Write data flow edges to Mermaid output."""
        rendered_bidirectional: set[str] = set()
        for (flow_name, flow_type), flow in dfd.flows.items():
            label = self._escape(flow_name)

            if flow_name in bidirectional:
                if flow_name in rendered_bidirectional:
                    continue
                rendered_bidirectional.add(flow_name)
                boundary_id = f"_boundary_{self._safe_id(flow_name)}"
                process_id = self._safe_id(bidirectional[flow_name])
                out.write(f'    {boundary_id} <-->|"{label}"| {process_id}\n')
            elif flow_type == "inbound":
                assert flow.target is not None, "Inbound flow must have a target"
                source_id = f"_boundary_{self._safe_id(flow_name)}"
                target_id = self._safe_id(flow.target.name)
                out.write(f'    {source_id} -->|"{label}"| {target_id}\n')
            elif flow_type == "outbound":
                assert flow.source is not None, "Outbound flow must have a source"
                source_id = self._safe_id(flow.source.name)
                target_id = f"_boundary_{self._safe_id(flow_name)}"
                out.write(f'    {source_id} -->|"{label}"| {target_id}\n')
            else:  # internal
                assert flow.source is not None, "Internal flow must have a source"
                assert flow.target is not None, "Internal flow must have a target"
                source_id = self._safe_id(flow.source.name)
                target_id = self._safe_id(flow.target.name)
                out.write(f'    {source_id} -->|"{label}"| {target_id}\n')

    def _collect_dfd_placeholder_ids(self, dfd: DFDModel) -> list[str]:
        """Collect IDs of all placeholder elements in a DFD."""
        placeholder_ids: list[str] = []
        for name, ext in dfd.externals.items():
            if ext.is_placeholder:
                placeholder_ids.append(self._safe_id(name))
        for name, proc in dfd.processes.items():
            if proc.is_placeholder:
                placeholder_ids.append(self._safe_id(name))
        for name, ds in dfd.datastores.items():
            if ds.is_placeholder:
                placeholder_ids.append(self._safe_id(name))
        return placeholder_ids

    def _write_dfd_styles(self, dfd: DFDModel, boundary_nodes: set[str], out: TextIO) -> None:
        """Write placeholder styles and boundary class definition."""
        if self.include_placeholders:
            placeholder_ids = self._collect_dfd_placeholder_ids(dfd)
            if placeholder_ids:
                out.write("\n")
                for pid in placeholder_ids:
                    out.write(f"    style {pid} stroke-dasharray: 5 5\n")

        if boundary_nodes:
            out.write("\n    classDef boundary fill:none,stroke:#666,stroke-dasharray:3\n")

    # ============================================
    # ERD Generation
    # ============================================

    def generate_erd(self, erd: ERDModel) -> str:
        """Generate Mermaid output for an ERD.

        Args:
            erd: The ERD model to generate.

        Returns:
            Mermaid format string.
        """
        output = io.StringIO()
        self._write_erd(erd, output)
        return output.getvalue()

    def _write_erd(self, erd: ERDModel, out: TextIO) -> None:
        """Write ERD to Mermaid format."""
        out.write(f"---\ntitle: {erd.name}\n---\n")
        out.write("erDiagram\n")

        # Entities with attributes
        for name, entity in erd.entities.items():
            if not self.include_placeholders and entity.is_placeholder:
                continue

            out.write(f"    {self._safe_id(name)} {{\n")
            for attr_name, attr in entity.attributes.items():
                # Mermaid ERD format: type name constraints
                type_name = attr.type_name
                constraints = []
                if attr.is_primary_key:
                    constraints.append("PK")
                if attr.is_foreign_key:
                    constraints.append("FK")

                constraint_str = ",".join(constraints) if constraints else ""
                if constraint_str:
                    out.write(f"        {type_name} {attr_name} {constraint_str}\n")
                else:
                    out.write(f"        {type_name} {attr_name}\n")

            if entity.is_placeholder:
                out.write('        string _placeholder_ "TBD"\n')

            out.write("    }\n")

        # Relationships
        out.write("\n")
        for name, rel in erd.relationships.items():
            source_id = self._safe_id(rel.source_entity)
            target_id = self._safe_id(rel.target_entity)

            # Convert cardinality to Mermaid format
            # Mermaid uses: ||--o{ for 1:n, etc.
            left_card = self._cardinality_to_mermaid(rel.cardinality.source, "left")
            right_card = self._cardinality_to_mermaid(rel.cardinality.target, "right")

            out.write(
                f'    {source_id} {left_card}--{right_card} {target_id} : "{self._escape(name)}"\n'
            )

    def _cardinality_to_mermaid(self, card: str, side: str) -> str:
        """Convert cardinality spec to Mermaid ERD notation."""
        # Mermaid cardinality symbols:
        # |o = zero or one, || = exactly one
        # o{ = zero or more, |{ = one or more
        if card == "1":
            return "||" if side == "left" else "||"
        elif card == "n" or card == "m":
            return "}o" if side == "left" else "o{"
        elif card == "0..1":
            return "|o" if side == "left" else "o|"
        elif card == "0..n":
            return "}o" if side == "left" else "o{"
        elif card == "1..n":
            return "}|" if side == "left" else "|{"
        return "||"

    # ============================================
    # STD Generation (using stateDiagram-v2)
    # ============================================

    def generate_std(self, std: STDModel) -> str:
        """Generate Mermaid output for an STD.

        Args:
            std: The STD model to generate.

        Returns:
            Mermaid format string.
        """
        output = io.StringIO()
        self._write_std(std, output)
        return output.getvalue()

    def _write_std(self, std: STDModel, out: TextIO) -> None:
        """Write STD to Mermaid format."""
        out.write(f"---\ntitle: {std.name}\n---\n")
        out.write("stateDiagram-v2\n")

        # Initial state
        if std.initial_state:
            out.write(f"    [*] --> {self._safe_id(std.initial_state)}\n")

        # States
        self._write_std_states(std, out)

        # Transitions
        out.write("\n")
        self._write_std_transitions(std, out)

    def _write_std_states(self, std: STDModel, out: TextIO) -> None:
        """Write state nodes to Mermaid output."""
        for name, state in std.states.items():
            if not self.include_placeholders and state.is_placeholder:
                continue

            safe_id = self._safe_id(name)
            has_details = (
                state.description or state.entry_action or state.exit_action or state.is_placeholder
            )

            if has_details:
                out.write(f"    state {safe_id} {{\n")
                if state.description:
                    out.write(f"        {safe_id}: {self._escape(state.description)}\n")
                if state.entry_action:
                    out.write(f"        {safe_id}: entry/ {self._escape(state.entry_action)}\n")
                if state.exit_action:
                    out.write(f"        {safe_id}: exit/ {self._escape(state.exit_action)}\n")
                if state.is_placeholder:
                    out.write(f"        {safe_id}: [TBD]\n")
                out.write("    }\n")

            if state.is_final:
                out.write(f"    {safe_id} --> [*]\n")

    def _write_std_transitions(self, std: STDModel, out: TextIO) -> None:
        """Write transition edges to Mermaid output."""
        for name, trans in std.transitions.items():
            source_id = self._safe_id(trans.source_state)
            target_id = self._safe_id(trans.target_state)

            # Build label
            parts = []
            if trans.trigger:
                parts.append(trans.trigger)
            if trans.guard:
                parts.append(f"[{trans.guard}]")
            if trans.action:
                parts.append(f"/ {trans.action}")

            label = " ".join(parts) if parts else name
            out.write(f"    {source_id} --> {target_id}: {self._escape(label)}\n")

    # ============================================
    # Structure Chart Generation (using flowchart)
    # ============================================

    def generate_structure(self, structure: StructureModel) -> str:
        """Generate Mermaid output for a structure chart.

        Args:
            structure: The structure chart model to generate.

        Returns:
            Mermaid format string.
        """
        output = io.StringIO()
        self._write_structure(structure, output)
        return output.getvalue()

    def _write_structure(self, structure: StructureModel, out: TextIO) -> None:
        """Write structure chart to Mermaid format."""
        out.write(f"---\ntitle: {structure.name}\n---\n")
        out.write("flowchart TB\n")

        self._write_structure_modules(structure, out)
        self._write_structure_calls(structure, out)
        self._write_structure_styles(structure, out)

    def _write_structure_modules(self, structure: StructureModel, out: TextIO) -> None:
        """Write module nodes for structure chart."""
        for name, module in structure.modules.items():
            if not self.include_placeholders and module.is_placeholder:
                continue

            safe_id = self._safe_id(name)
            label = self._escape(name)
            if module.description:
                label += f"<br/><i>{self._escape(module.description)}</i>"

            out.write(f'    {safe_id}["{label}"]\n')

    def _write_structure_calls(self, structure: StructureModel, out: TextIO) -> None:
        """Write call edges for structure chart."""
        out.write("\n")
        for name, module in structure.modules.items():
            source_id = self._safe_id(name)
            for called in module.calls:
                target_id = self._safe_id(called)

                # Add data/control couples as edge labels
                couples = []
                if module.data_couples:
                    couples.extend([f"D:{c}" for c in module.data_couples])
                if module.control_couples:
                    couples.extend([f"C:{c}" for c in module.control_couples])

                if couples:
                    label = ", ".join(couples)
                    out.write(f'    {source_id} -->|"{label}"| {target_id}\n')
                else:
                    out.write(f"    {source_id} --> {target_id}\n")

    def _write_structure_styles(self, structure: StructureModel, out: TextIO) -> None:
        """Write placeholder styles for structure chart."""
        if self.include_placeholders:
            placeholder_ids = [
                self._safe_id(name)
                for name, module in structure.modules.items()
                if module.is_placeholder
            ]
            if placeholder_ids:
                out.write("\n")
                for pid in placeholder_ids:
                    out.write(f"    style {pid} stroke-dasharray: 5 5\n")

    # ============================================
    # SCD Generation (using flowchart)
    # ============================================

    def generate_scd(self, scd: SCDModel) -> str:
        """Generate Mermaid output for an SCD.

        Args:
            scd: The SCD model to generate.

        Returns:
            Mermaid format string.
        """
        output = io.StringIO()
        self._write_scd(scd, output)
        return output.getvalue()

    def _write_scd(self, scd: SCDModel, out: TextIO) -> None:
        """Write SCD to Mermaid format."""
        out.write(f"---\ntitle: {scd.name}\n---\n")
        out.write("flowchart LR\n")

        # Write nodes
        self._write_scd_system(scd, out)
        self._write_scd_externals(scd, out)
        self._write_scd_datastores(scd, out)

        # Write flows
        out.write("\n")
        self._write_scd_flows(scd, out)

        # Write styles
        self._write_scd_styles(scd, out)

    def _write_scd_system(self, scd: SCDModel, out: TextIO) -> None:
        """Write system node to Mermaid output."""
        if not scd.system:
            return
        sys = scd.system
        if not self.include_placeholders and sys.is_placeholder:
            return
        safe_id = self._safe_id(sys.name)
        label = self._escape(sys.name)
        # Note: description intentionally not included in diagram (REQ-GEN-062)
        out.write(f'    {safe_id}[["{label}"]]\n')

    def _write_scd_externals(self, scd: SCDModel, out: TextIO) -> None:
        """Write external entity nodes to Mermaid output."""
        for name, ext in scd.externals.items():
            if not self.include_placeholders and ext.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if ext.description:
                label += f"<br/><i>{self._escape(ext.description)}</i>"
            out.write(f'    {safe_id}["{label}"]\n')

    def _write_scd_datastores(self, scd: SCDModel, out: TextIO) -> None:
        """Write datastore nodes to Mermaid output."""
        for name, ds in scd.datastores.items():
            if not self.include_placeholders and ds.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if ds.description:
                label += f"<br/>{self._escape(ds.description)}"
            out.write(f'    {safe_id}[("{label}")]\n')

    def _write_scd_flows(self, scd: SCDModel, out: TextIO) -> None:
        """Write flow edges to Mermaid output."""
        for name, flow in scd.flows.items():
            source_id = self._safe_id(flow.source.name)
            target_id = self._safe_id(flow.target.name)
            label = self._escape(name)

            if flow.direction == "bidirectional":
                out.write(f'    {source_id} <-->|"{label}"| {target_id}\n')
            else:
                out.write(f'    {source_id} -->|"{label}"| {target_id}\n')

    def _collect_scd_placeholder_ids(self, scd: SCDModel) -> list[str]:
        """Collect IDs of all placeholder elements in an SCD."""
        placeholder_ids: list[str] = []
        if scd.system and scd.system.is_placeholder:
            placeholder_ids.append(self._safe_id(scd.system.name))
        for name, ext in scd.externals.items():
            if ext.is_placeholder:
                placeholder_ids.append(self._safe_id(name))
        for name, ds in scd.datastores.items():
            if ds.is_placeholder:
                placeholder_ids.append(self._safe_id(name))
        return placeholder_ids

    def _write_scd_styles(self, scd: SCDModel, out: TextIO) -> None:
        """Write placeholder and system styles to Mermaid output."""
        if self.include_placeholders:
            placeholder_ids = self._collect_scd_placeholder_ids(scd)
            if placeholder_ids:
                out.write("\n")
                for pid in placeholder_ids:
                    out.write(f"    style {pid} stroke-dasharray: 5 5\n")

        if scd.system:
            out.write(f"\n    style {self._safe_id(scd.system.name)} stroke-width:3px\n")

    # ============================================
    # Full Document Generation
    # ============================================

    def generate_all(self, doc: DesignDocument) -> dict[str, str]:
        """Generate Mermaid output for all diagrams in a document.

        Args:
            doc: The design document.

        Returns:
            A dictionary mapping diagram names to Mermaid strings.
        """
        result: dict[str, str] = {}

        for name, dfd in doc.dfds.items():
            result[f"dfd_{name}"] = self.generate_dfd(dfd)

        for name, erd in doc.erds.items():
            result[f"erd_{name}"] = self.generate_erd(erd)

        for name, std in doc.stds.items():
            result[f"std_{name}"] = self.generate_std(std)

        for name, structure in doc.structures.items():
            result[f"structure_{name}"] = self.generate_structure(structure)

        for name, scd in doc.scds.items():
            result[f"scd_{name}"] = self.generate_scd(scd)

        return result


def generate_mermaid(doc: DesignDocument, include_placeholders: bool = True) -> dict[str, str]:
    """Generate Mermaid output for all diagrams in a document.

    Args:
        doc: The design document.
        include_placeholders: If True, include placeholder elements.

    Returns:
        A dictionary mapping diagram names to Mermaid strings.
    """
    generator = MermaidGenerator(include_placeholders)
    return generator.generate_all(doc)
