"""GraphViz/DOT output generator for design diagrams."""

from __future__ import annotations

import io
from typing import TextIO

from designit.model.base import DesignDocument
from designit.model.dfd import DataFlow, DFDModel
from designit.model.erd import ERDModel
from designit.model.scd import SCDFlow, SCDFlowUnion, SCDModel
from designit.model.std import STDModel
from designit.model.structure import StructureModel


class GraphVizGenerator:
    """Generates GraphViz DOT output for design diagrams."""

    def __init__(self, include_placeholders: bool = True, expand_unions: bool = False):
        """Initialize the generator.

        Args:
            include_placeholders: If True, include placeholder elements with dashed borders.
            expand_unions: If True, expand flow unions into individual member flows.
                          If False (default), render unions as bundled single flows.
        """
        self.include_placeholders = include_placeholders
        self.expand_unions = expand_unions

    def _escape(self, text: str) -> str:
        """Escape text for DOT labels."""
        return text.replace('"', '\\"').replace("\n", "\\n")

    def _placeholder_style(self) -> str:
        """Return style attributes for placeholder elements."""
        return 'style="dashed" color="gray"'

    # ============================================
    # DFD Generation
    # ============================================

    def generate_dfd(self, dfd: DFDModel) -> str:
        """Generate DOT output for a DFD.

        Args:
            dfd: The DFD model to generate.

        Returns:
            DOT format string.
        """
        output = io.StringIO()
        self._write_dfd(dfd, output)
        return output.getvalue()

    def _write_dfd(self, dfd: DFDModel, out: TextIO) -> None:
        """Write DFD to DOT format."""
        out.write(f'digraph "{self._escape(dfd.name)}" {{\n')
        out.write("  layout=neato;\n")
        out.write("  overlap=false;\n")
        out.write("  splines=true;\n")
        out.write('  node [fontname="Helvetica"];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Write nodes
        self._write_dfd_externals(dfd, out)
        self._write_dfd_processes(dfd, out)
        self._write_dfd_datastores(dfd, out)

        # Detect bidirectional flows and write boundary nodes
        bidirectional = self._detect_dfd_bidirectional_flows(dfd)
        self._write_dfd_boundary_nodes(dfd, bidirectional, out)

        # Write flows
        self._write_dfd_flows(dfd, bidirectional, out)

        out.write("}\n")

    def _write_dfd_externals(self, dfd: DFDModel, out: TextIO) -> None:
        """Write external entity nodes to DOT output."""
        out.write("  // External Entities\n")
        for name, ext in dfd.externals.items():
            if not self.include_placeholders and ext.is_placeholder:
                continue
            style = self._placeholder_style() if ext.is_placeholder else ""
            label = self._escape(name)
            if ext.description:
                label += f"\\n({self._escape(ext.description)})"
            out.write(f'  "{name}" [shape=box label="{label}" {style}];\n')

    def _write_dfd_processes(self, dfd: DFDModel, out: TextIO) -> None:
        """Write process nodes to DOT output."""
        out.write("\n  // Processes\n")
        for name, proc in dfd.processes.items():
            if not self.include_placeholders and proc.is_placeholder:
                continue
            style = self._placeholder_style() if proc.is_placeholder else ""
            label = self._escape(name)
            # Note: description intentionally not included in diagram (REQ-GEN-063)
            out.write(f'  "{name}" [shape=circle label="{label}" {style}];\n')

    def _write_dfd_datastores(self, dfd: DFDModel, out: TextIO) -> None:
        """Write datastore nodes to DOT output."""
        out.write("\n  // Data Stores\n")
        for name, ds in dfd.datastores.items():
            if not self.include_placeholders and ds.is_placeholder:
                continue
            style = self._placeholder_style() if ds.is_placeholder else ""
            label = self._escape(name)
            if ds.description:
                label += f"\\n{self._escape(ds.description)}"
            out.write(f'  "{name}" [shape=cylinder label="{label}" {style}];\n')

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
    ) -> None:
        """Write boundary marker nodes for boundary flows."""
        boundary_nodes: set[str] = set()
        for (flow_name, flow_type), flow in dfd.flows.items():
            if flow_type not in ("inbound", "outbound", "bidirectional"):
                continue
            # Skip outbound if it's part of a bidirectional pair (handled with inbound)
            if flow_name in bidirectional and flow_type == "outbound":
                continue
            boundary_id = f"_boundary_{flow_name}"
            if boundary_id not in boundary_nodes:
                boundary_nodes.add(boundary_id)
                out.write(f'  "{boundary_id}" [shape=point label="" width=0.01 style=invis];\n')

    def _write_dfd_flows(self, dfd: DFDModel, bidirectional: dict[str, str], out: TextIO) -> None:
        """Write data flow edges to DOT output."""
        out.write("\n  // Data Flows\n")
        rendered_bidirectional: set[str] = set()
        for (flow_name, flow_type), flow in dfd.flows.items():
            label = self._escape(flow_name)

            if flow_name in bidirectional:
                if flow_name not in rendered_bidirectional:
                    rendered_bidirectional.add(flow_name)
                    self._write_dfd_detected_bidirectional(flow_name, bidirectional, label, out)
            elif flow_type == "bidirectional":
                self._write_dfd_bidirectional_flow(flow_name, flow, label, out)
            elif flow_type == "inbound":
                self._write_dfd_inbound_flow(flow_name, flow, label, out)
            elif flow_type == "outbound":
                self._write_dfd_outbound_flow(flow_name, flow, label, out)
            else:  # internal
                self._write_dfd_internal_flow(flow, label, out)

    def _write_dfd_detected_bidirectional(
        self, flow_name: str, bidirectional: dict[str, str], label: str, out: TextIO
    ) -> None:
        """Write a detected bidirectional flow (from inbound/outbound pair)."""
        boundary_id = f"_boundary_{flow_name}"
        process_name = bidirectional[flow_name]
        out.write(f'  "{boundary_id}" -> "{process_name}" [label=" {label} " dir=both];\n')

    def _write_dfd_bidirectional_flow(
        self, flow_name: str, flow: DataFlow, label: str, out: TextIO
    ) -> None:
        """Write an explicit bidirectional boundary flow."""
        if flow.target is None:
            raise ValueError(self._flow_error("Bidirectional flow", flow, "must have a target"))
        boundary_id = f"_boundary_{flow_name}"
        process_name = flow.target.name
        out.write(f'  "{boundary_id}" -> "{process_name}" [label=" {label} " dir=both];\n')

    def _write_dfd_inbound_flow(
        self, flow_name: str, flow: DataFlow, label: str, out: TextIO
    ) -> None:
        """Write an inbound boundary flow."""
        if flow.target is None:
            raise ValueError(self._flow_error("Inbound flow", flow, "must have a target"))
        source_id = f"_boundary_{flow_name}"
        target_id = flow.target.name
        out.write(f'  "{source_id}" -> "{target_id}" [label=" {label} "];\n')

    def _write_dfd_outbound_flow(
        self, flow_name: str, flow: DataFlow, label: str, out: TextIO
    ) -> None:
        """Write an outbound boundary flow."""
        if flow.source is None:
            raise ValueError(self._flow_error("Outbound flow", flow, "must have a source"))
        source_id = flow.source.name
        target_id = f"_boundary_{flow_name}"
        out.write(f'  "{source_id}" -> "{target_id}" [label=" {label} "];\n')

    def _write_dfd_internal_flow(self, flow: DataFlow, label: str, out: TextIO) -> None:
        """Write an internal flow between two elements in the DFD."""
        if flow.source is None:
            raise ValueError(self._flow_error("Internal flow", flow, "must have a source"))
        if flow.target is None:
            raise ValueError(self._flow_error("Internal flow", flow, "must have a target"))
        source_id = flow.source.name
        target_id = flow.target.name
        out.write(f'  "{source_id}" -> "{target_id}" [label=" {label} "];\n')

    def _flow_error(self, flow_type_desc: str, flow: DataFlow, message: str) -> str:
        """Format a flow error message with location info if available."""
        loc = ""
        if flow.source_file and flow.line:
            loc = f" at {flow.source_file}:{flow.line}"
        elif flow.source_file:
            loc = f" in {flow.source_file}"
        elif flow.line:
            loc = f" at line {flow.line}"
        return f"{flow_type_desc} '{flow.name}' {message}{loc}"

    # ============================================
    # ERD Generation
    # ============================================

    def generate_erd(self, erd: ERDModel) -> str:
        """Generate DOT output for an ERD.

        Args:
            erd: The ERD model to generate.

        Returns:
            DOT format string.
        """
        output = io.StringIO()
        self._write_erd(erd, output)
        return output.getvalue()

    def _write_erd(self, erd: ERDModel, out: TextIO) -> None:
        """Write ERD to DOT format."""
        out.write(f'digraph "{self._escape(erd.name)}" {{\n')
        out.write("  rankdir=LR;\n")
        out.write('  node [fontname="Helvetica" shape=record];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Entities (as records with attributes)
        out.write("  // Entities\n")
        for name, entity in erd.entities.items():
            if not self.include_placeholders and entity.is_placeholder:
                continue

            style = self._placeholder_style() if entity.is_placeholder else ""

            # Build record label with attributes
            label_parts = [f"<name> {self._escape(name)}"]

            for attr_name, attr in entity.attributes.items():
                attr_label = f"{self._escape(attr_name)}: {self._escape(attr.type_name)}"
                # Add constraint markers
                markers = []
                if attr.is_primary_key:
                    markers.append("PK")
                if attr.is_foreign_key:
                    markers.append("FK")
                if markers:
                    attr_label += f" [{', '.join(markers)}]"
                label_parts.append(attr_label)

            if entity.is_placeholder:
                label_parts.append("...")

            label = "|".join(label_parts)
            out.write(f'  "{name}" [label="{{{label}}}" {style}];\n')

        # Relationships (edges with cardinality labels)
        out.write("\n  // Relationships\n")
        for name, rel in erd.relationships.items():
            label = f" {self._escape(name)}\\n{rel.cardinality} "
            out.write(
                f'  "{rel.source_entity}" -> "{rel.target_entity}" '
                f'[label="{label}" arrowhead=none arrowtail=none];\n'
            )

        out.write("}\n")

    # ============================================
    # STD Generation
    # ============================================

    def generate_std(self, std: STDModel) -> str:
        """Generate DOT output for an STD.

        Args:
            std: The STD model to generate.

        Returns:
            DOT format string.
        """
        output = io.StringIO()
        self._write_std(std, output)
        return output.getvalue()

    def _write_std(self, std: STDModel, out: TextIO) -> None:
        """Write STD to DOT format."""
        out.write(f'digraph "{self._escape(std.name)}" {{\n')
        out.write("  rankdir=LR;\n")
        out.write('  node [fontname="Helvetica"];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Initial state marker
        if std.initial_state:
            out.write("  // Initial state\n")
            out.write("  __start__ [shape=point width=0.2];\n")
            out.write(f'  __start__ -> "{std.initial_state}";\n\n')

        # States and transitions
        self._write_std_states(std, out)
        self._write_std_transitions(std, out)

        out.write("}\n")

    def _write_std_states(self, std: STDModel, out: TextIO) -> None:
        """Write state nodes to DOT output."""
        out.write("  // States\n")
        for name, state in std.states.items():
            if not self.include_placeholders and state.is_placeholder:
                continue

            style = self._placeholder_style() if state.is_placeholder else ""
            label = self._escape(name)
            if state.description:
                label += f"\\n{self._escape(state.description)}"
            if state.entry_action:
                label += f"\\nentry/ {self._escape(state.entry_action)}"
            if state.exit_action:
                label += f"\\nexit/ {self._escape(state.exit_action)}"

            shape = "doublecircle" if state.is_final else "ellipse"
            out.write(f'  "{name}" [shape={shape} label="{label}" {style}];\n')

    def _write_std_transitions(self, std: STDModel, out: TextIO) -> None:
        """Write transition edges to DOT output."""
        out.write("\n  // Transitions\n")
        for name, trans in std.transitions.items():
            parts = []
            if trans.trigger:
                parts.append(self._escape(trans.trigger))
            if trans.guard:
                parts.append(f"[{self._escape(trans.guard)}]")
            if trans.action:
                parts.append(f"/ {self._escape(trans.action)}")
            label = "".join(parts) if parts else self._escape(name)

            out.write(f'  "{trans.source_state}" -> "{trans.target_state}" [label=" {label} "];\n')

    # ============================================
    # Structure Chart Generation
    # ============================================

    def generate_structure(self, structure: StructureModel) -> str:
        """Generate DOT output for a structure chart.

        Args:
            structure: The structure chart model to generate.

        Returns:
            DOT format string.
        """
        output = io.StringIO()
        self._write_structure(structure, output)
        return output.getvalue()

    def _write_structure(self, structure: StructureModel, out: TextIO) -> None:
        """Write structure chart to DOT format."""
        out.write(f'digraph "{self._escape(structure.name)}" {{\n')
        out.write("  rankdir=TB;\n")
        out.write('  node [fontname="Helvetica" shape=box];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Modules (boxes)
        out.write("  // Modules\n")
        for name, module in structure.modules.items():
            if not self.include_placeholders and module.is_placeholder:
                continue

            style = self._placeholder_style() if module.is_placeholder else ""
            label = self._escape(name)
            if module.description:
                label += f"\\n{self._escape(module.description)}"

            out.write(f'  "{name}" [label="{label}" {style}];\n')

        # Calls (edges)
        out.write("\n  // Module Calls\n")
        for name, module in structure.modules.items():
            for called in module.calls:
                # Add data/control couples as edge labels
                couples = []
                if module.data_couples:
                    couples.extend([f"D:{c}" for c in module.data_couples])
                if module.control_couples:
                    couples.extend([f"C:{c}" for c in module.control_couples])

                label = ", ".join(couples) if couples else ""
                if label:
                    out.write(f'  "{name}" -> "{called}" [label=" {label} "];\n')
                else:
                    out.write(f'  "{name}" -> "{called}";\n')

        out.write("}\n")

    # ============================================
    # SCD Generation
    # ============================================

    def generate_scd(self, scd: SCDModel) -> str:
        """Generate DOT output for an SCD.

        Args:
            scd: The SCD model to generate.

        Returns:
            DOT format string.
        """
        output = io.StringIO()
        self._write_scd(scd, output)
        return output.getvalue()

    def _write_scd(self, scd: SCDModel, out: TextIO) -> None:
        """Write SCD to DOT format with radial layout."""
        out.write(f'digraph "{self._escape(scd.name)}" {{\n')
        out.write("  layout=neato;\n")
        out.write("  overlap=false;\n")
        out.write("  splines=true;\n")
        out.write('  node [fontname="Helvetica"];\n')
        out.write('  edge [fontname="Helvetica", fontsize=10];\n\n')

        # Write nodes
        self._write_scd_system(scd, out)
        self._write_scd_externals(scd, out)
        self._write_scd_datastores(scd, out)

        # Write flows
        self._write_scd_flows(scd, out)

        out.write("}\n")

    def _write_scd_system(self, scd: SCDModel, out: TextIO) -> None:
        """Write system node to DOT output."""
        if not scd.system:
            return
        out.write("  // System (centered)\n")
        sys = scd.system
        if not self.include_placeholders and sys.is_placeholder:
            return
        label = self._escape(sys.name)
        # Note: description intentionally not included in diagram (REQ-GEN-062)
        if sys.is_placeholder:
            style = 'pos="0,0!" style="dashed,filled" fillcolor=lightgray'
        else:
            style = 'pos="0,0!" style=filled fillcolor=lightyellow'
        out.write(f'  "{sys.name}" [shape=doublecircle label="{label}" {style}];\n')

    def _write_scd_externals(self, scd: SCDModel, out: TextIO) -> None:
        """Write external entity nodes to DOT output."""
        out.write("\n  // External Entities\n")
        for name, ext in scd.externals.items():
            if not self.include_placeholders and ext.is_placeholder:
                continue
            style = self._placeholder_style() if ext.is_placeholder else ""
            label = self._escape(name)
            out.write(f'  "{name}" [shape=box label="{label}" {style}];\n')

    def _write_scd_datastores(self, scd: SCDModel, out: TextIO) -> None:
        """Write datastore nodes to DOT output."""
        out.write("\n  // Data Stores\n")
        for name, ds in scd.datastores.items():
            if not self.include_placeholders and ds.is_placeholder:
                continue
            style = self._placeholder_style() if ds.is_placeholder else ""
            label = self._escape(name)
            out.write(f'  "{name}" [shape=cylinder label="{label}" {style}];\n')

    def _write_scd_flows(self, scd: SCDModel, out: TextIO) -> None:
        """Write flow edges to DOT output.

        Handles both standalone flows and flow unions based on expand_unions setting:
        - expand_unions=False (default): Render unions as single flows, skip members
        - expand_unions=True: Render member flows from unions, skip the union itself
        """
        out.write("\n  // Data Flows\n")

        # Write standalone flows (not in any union)
        for name, flow in scd.flows.items():
            self._write_scd_single_flow(name, flow, out)

        # Write flow unions
        for union_name, union in scd.flow_unions.items():
            if self.expand_unions:
                # Expanded mode: render each member flow individually
                for flow in union.members:
                    # Add union annotation to label
                    self._write_scd_single_flow(flow.name, flow, out, union_annotation=union_name)
            else:
                # Bundled mode: render union as a single flow
                self._write_scd_union_flow(union_name, union, out)

    def _write_scd_single_flow(
        self,
        name: str,
        flow: SCDFlow,
        out: TextIO,
        union_annotation: str | None = None,
    ) -> None:
        """Write a single SCD flow edge."""
        if union_annotation:
            label = self._escape(f"{name} [{union_annotation}]")
        else:
            label = self._escape(name)

        src = flow.source.name
        tgt = flow.target.name
        if flow.direction == "bidirectional":
            out.write(f'  "{src}" -> "{tgt}" [label=" {label} " dir=both];\n')
        else:
            out.write(f'  "{src}" -> "{tgt}" [label=" {label} "];\n')

    def _write_scd_union_flow(self, union_name: str, union: SCDFlowUnion, out: TextIO) -> None:
        """Write a flow union as a single bundled flow."""
        if not union.members:
            return

        # Use the first member's endpoints for the union line
        source = union.source
        target = union.target
        if not source or not target:
            return

        # Label shows union name with member count
        member_count = len(union.members)
        label = self._escape(f"{union_name} ({member_count} flows)")

        if union.direction == "bidirectional":
            out.write(f'  "{source.name}" -> "{target.name}" [label=" {label} " dir=both];\n')
        else:
            out.write(f'  "{source.name}" -> "{target.name}" [label=" {label} "];\n')

    # ============================================
    # Full Document Generation
    # ============================================
    # Full Document Generation
    # ============================================

    def generate_all(self, doc: DesignDocument) -> dict[str, str]:
        """Generate DOT output for all diagrams in a document.

        Args:
            doc: The design document.

        Returns:
            A dictionary mapping diagram names to DOT strings.
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


def generate_graphviz(
    doc: DesignDocument, include_placeholders: bool = True, expand_unions: bool = False
) -> dict[str, str]:
    """Generate GraphViz DOT output for all diagrams in a document.

    Args:
        doc: The design document.
        include_placeholders: If True, include placeholder elements.
        expand_unions: If True, expand flow unions into individual member flows.

    Returns:
        A dictionary mapping diagram names to DOT strings.
    """
    generator = GraphVizGenerator(include_placeholders, expand_unions)
    return generator.generate_all(doc)
