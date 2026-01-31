"""GraphViz/DOT output generator for design diagrams."""

from __future__ import annotations

from typing import TextIO
import io

from designit.model.base import DesignDocument
from designit.model.dfd import DFDModel
from designit.model.erd import ERDModel
from designit.model.std import STDModel
from designit.model.structure import StructureModel


class GraphVizGenerator:
    """Generates GraphViz DOT output for design diagrams."""

    def __init__(self, include_placeholders: bool = True):
        """Initialize the generator.

        Args:
            include_placeholders: If True, include placeholder elements with dashed borders.
        """
        self.include_placeholders = include_placeholders

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
        out.write('  rankdir=TB;\n')
        out.write('  node [fontname="Helvetica"];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # External entities (rectangles)
        out.write('  // External Entities\n')
        for name, ext in dfd.externals.items():
            if not self.include_placeholders and ext.is_placeholder:
                continue
            style = self._placeholder_style() if ext.is_placeholder else ""
            label = self._escape(name)
            if ext.description:
                label += f"\\n({self._escape(ext.description)})"
            out.write(f'  "{name}" [shape=box label="{label}" {style}];\n')

        # Processes (circles/ellipses)
        out.write('\n  // Processes\n')
        for name, proc in dfd.processes.items():
            if not self.include_placeholders and proc.is_placeholder:
                continue
            style = self._placeholder_style() if proc.is_placeholder else ""
            label = self._escape(name)
            if proc.description:
                label += f"\\n{self._escape(proc.description)}"
            out.write(f'  "{name}" [shape=ellipse label="{label}" {style}];\n')

        # Data stores (open-ended rectangles, approximated with cylinder)
        out.write('\n  // Data Stores\n')
        for name, ds in dfd.datastores.items():
            if not self.include_placeholders and ds.is_placeholder:
                continue
            style = self._placeholder_style() if ds.is_placeholder else ""
            label = self._escape(name)
            if ds.description:
                label += f"\\n{self._escape(ds.description)}"
            out.write(f'  "{name}" [shape=cylinder label="{label}" {style}];\n')

        # Data flows (edges)
        out.write('\n  // Data Flows\n')
        for name, flow in dfd.flows.items():
            label = self._escape(name)
            out.write(f'  "{flow.source.name}" -> "{flow.target.name}" [label="{label}"];\n')

        out.write('}\n')

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
        out.write('  rankdir=LR;\n')
        out.write('  node [fontname="Helvetica" shape=record];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Entities (as records with attributes)
        out.write('  // Entities\n')
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
        out.write('\n  // Relationships\n')
        for name, rel in erd.relationships.items():
            label = f"{self._escape(name)}\\n{rel.cardinality}"
            out.write(
                f'  "{rel.source_entity}" -> "{rel.target_entity}" '
                f'[label="{label}" arrowhead=none arrowtail=none];\n'
            )

        out.write('}\n')

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
        out.write('  rankdir=LR;\n')
        out.write('  node [fontname="Helvetica"];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Initial state marker
        if std.initial_state:
            out.write('  // Initial state\n')
            out.write('  __start__ [shape=point width=0.2];\n')
            out.write(f'  __start__ -> "{std.initial_state}";\n\n')

        # States (rounded rectangles)
        out.write('  // States\n')
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

        # Transitions (edges)
        out.write('\n  // Transitions\n')
        for name, trans in std.transitions.items():
            # Build transition label: trigger[guard]/action
            parts = []
            if trans.trigger:
                parts.append(self._escape(trans.trigger))
            if trans.guard:
                parts.append(f"[{self._escape(trans.guard)}]")
            if trans.action:
                parts.append(f"/ {self._escape(trans.action)}")
            label = "".join(parts) if parts else self._escape(name)

            out.write(f'  "{trans.source_state}" -> "{trans.target_state}" [label="{label}"];\n')

        out.write('}\n')

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
        out.write('  rankdir=TB;\n')
        out.write('  node [fontname="Helvetica" shape=box];\n')
        out.write('  edge [fontname="Helvetica"];\n\n')

        # Modules (boxes)
        out.write('  // Modules\n')
        for name, module in structure.modules.items():
            if not self.include_placeholders and module.is_placeholder:
                continue

            style = self._placeholder_style() if module.is_placeholder else ""
            label = self._escape(name)
            if module.description:
                label += f"\\n{self._escape(module.description)}"

            out.write(f'  "{name}" [label="{label}" {style}];\n')

        # Calls (edges)
        out.write('\n  // Module Calls\n')
        for name, module in structure.modules.items():
            for called in module.calls:
                # Add data/control couples as edge labels
                couples = []
                if module.data_couples:
                    couples.extend([f"D:{c}" for c in module.data_couples])
                if module.control_couples:
                    couples.extend([f"C:{c}" for c in module.control_couples])

                label = ", ".join(couples) if couples else ""
                out.write(f'  "{name}" -> "{called}" [label="{label}"];\n')

        out.write('}\n')

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

        return result


def generate_graphviz(doc: DesignDocument, include_placeholders: bool = True) -> dict[str, str]:
    """Generate GraphViz DOT output for all diagrams in a document.

    Args:
        doc: The design document.
        include_placeholders: If True, include placeholder elements.

    Returns:
        A dictionary mapping diagram names to DOT strings.
    """
    generator = GraphVizGenerator(include_placeholders)
    return generator.generate_all(doc)
