"""Mermaid output generator for design diagrams."""

from __future__ import annotations

from typing import TextIO
import io

from designit.model.base import DesignDocument
from designit.model.dfd import DFDModel
from designit.model.erd import ERDModel
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

        # External entities (rectangles)
        for name, ext in dfd.externals.items():
            if not self.include_placeholders and ext.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if ext.description:
                label += f"<br/><i>{self._escape(ext.description)}</i>"
            out.write(f'    {safe_id}["{label}"]\n')

        # Processes (rounded rectangles)
        for name, proc in dfd.processes.items():
            if not self.include_placeholders and proc.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if proc.description:
                label += f"<br/>{self._escape(proc.description)}"
            out.write(f'    {safe_id}("{label}")\n')

        # Data stores (cylinders)
        for name, ds in dfd.datastores.items():
            if not self.include_placeholders and ds.is_placeholder:
                continue
            safe_id = self._safe_id(name)
            label = self._escape(name)
            if ds.description:
                label += f"<br/>{self._escape(ds.description)}"
            out.write(f'    {safe_id}[("{label}")]\n')

        # Data flows (edges)
        out.write("\n")
        for name, flow in dfd.flows.items():
            source_id = self._safe_id(flow.source.name)
            target_id = self._safe_id(flow.target.name)
            label = self._escape(name)
            out.write(f'    {source_id} -->|"{label}"| {target_id}\n')

        # Style placeholders
        if self.include_placeholders:
            placeholder_ids = []
            for name, ext in dfd.externals.items():
                if ext.is_placeholder:
                    placeholder_ids.append(self._safe_id(name))
            for name, proc in dfd.processes.items():
                if proc.is_placeholder:
                    placeholder_ids.append(self._safe_id(name))
            for name, ds in dfd.datastores.items():
                if ds.is_placeholder:
                    placeholder_ids.append(self._safe_id(name))

            if placeholder_ids:
                out.write("\n")
                for pid in placeholder_ids:
                    out.write(f"    style {pid} stroke-dasharray: 5 5\n")

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
                out.write("        string _placeholder_ \"TBD\"\n")

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

            out.write(f'    {source_id} {left_card}--{right_card} {target_id} : "{self._escape(name)}"\n')

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

        # States with descriptions
        for name, state in std.states.items():
            if not self.include_placeholders and state.is_placeholder:
                continue

            safe_id = self._safe_id(name)

            if state.description or state.entry_action or state.exit_action or state.is_placeholder:
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

        # Transitions
        out.write("\n")
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

        # Modules (boxes)
        for name, module in structure.modules.items():
            if not self.include_placeholders and module.is_placeholder:
                continue

            safe_id = self._safe_id(name)
            label = self._escape(name)
            if module.description:
                label += f"<br/><i>{self._escape(module.description)}</i>"

            out.write(f'    {safe_id}["{label}"]\n')

        # Calls (edges)
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

        # Style placeholders
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
