"""Flow aggregation for design documents.

This module provides a model transformation that aggregates flows
based on union type coverage (REQ-GEN-070, REQ-GEN-071, REQ-GEN-072, REQ-GEN-073).

Aggregation is applied as a post-processing step after parsing and validation,
returning a new DesignDocument with aggregated flows. The original document
is not modified.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from designit.model.base import DesignDocument
from designit.model.dfd import DataFlow, DFDModel, FlowKey
from designit.model.scd import SCDFlow, SCDModel

if TYPE_CHECKING:
    from designit.model.datadict import DataDictionaryModel


def aggregate_flows(document: DesignDocument) -> DesignDocument:
    """Return a new DesignDocument with flows aggregated based on union type coverage.

    Aggregation rules:
    1. Type aggregation: flows covering all subtypes of a union -> single flow with parent type
    2. Cross-direction type aggregation: opposite-direction flows covering a union -> bidirectional
    3. Same-label direction aggregation: inbound + outbound with same label -> bidirectional
    4. Highest level: aggregate to the highest union level with complete coverage
    5. Enum unions (quoted strings) are not aggregated

    Args:
        document: The validated DesignDocument to aggregate.

    Returns:
        A new DesignDocument with aggregated flows. If no data dictionary exists
        or no aggregation is possible, the original document may be returned.
    """
    if not document.data_dictionary:
        return document

    aggregator = _FlowAggregator(document.data_dictionary)

    # Aggregate all SCDs
    new_scds = {name: aggregator.aggregate_scd(scd) for name, scd in document.scds.items()}

    # Aggregate all DFDs
    new_dfds = {name: aggregator.aggregate_dfd(dfd) for name, dfd in document.dfds.items()}

    # Check if anything changed
    scds_changed = any(new_scds[k] is not document.scds[k] for k in new_scds)
    dfds_changed = any(new_dfds[k] is not document.dfds[k] for k in new_dfds)

    if not scds_changed and not dfds_changed:
        return document

    return document.model_copy(update={"scds": new_scds, "dfds": new_dfds})


class _FlowAggregator:
    """Internal helper class for flow aggregation logic."""

    def __init__(self, data_dictionary: DataDictionaryModel) -> None:
        """Initialize the aggregator.

        Args:
            data_dictionary: The data dictionary for looking up union types.
        """
        self.data_dictionary = data_dictionary
        # Cache for union subtypes
        self._subtype_cache: dict[str, set[str]] = {}
        # Cache for parent type lookups (maps frozenset of subtypes to parent type)
        self._parent_cache: dict[frozenset[str], str | None] = {}

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def _get_qualified_type_name(self, flow: SCDFlow | DataFlow) -> str:
        """Get the qualified type name for union matching from a flow.

        Uses type_ref.qualified_name if available, otherwise falls back to flow.name.
        The qualified name is needed to match against data dictionary definitions.
        """
        if flow.type_ref:
            return flow.type_ref.qualified_name
        return flow.name

    # =========================================================================
    # SCD Aggregation
    # =========================================================================

    def aggregate_scd(self, scd: SCDModel) -> SCDModel:
        """Return new SCDModel with aggregated flows."""
        if not scd.flows:
            return scd

        # Step 1: Group flows by (source, target, direction) and apply type aggregation
        groups = self._group_scd_flows(scd.flows)
        aggregated_flows: list[SCDFlow] = []
        for (source, target, direction), group_flows in groups.items():
            aggregated = self._aggregate_scd_flow_group(group_flows, source, target, direction)
            aggregated_flows.extend(aggregated)

        # Step 2: Cross-direction type aggregation (REQ-GEN-073)
        aggregated_flows = self._aggregate_scd_cross_direction_types(aggregated_flows)

        # Step 3: Same-label direction aggregation (inbound + outbound -> bidirectional)
        final_flows = self._aggregate_scd_directions(aggregated_flows)

        # Build new flows dict with unique keys
        new_flows: dict[str, SCDFlow] = {}
        for flow in final_flows:
            key = flow.name
            # Handle duplicate names by appending direction suffix
            if key in new_flows:
                key = f"{flow.name}_{flow.direction}"
            new_flows[key] = flow

        if new_flows == scd.flows:
            return scd

        return scd.model_copy(update={"flows": new_flows})

    def _group_scd_flows(
        self, flows: dict[str, SCDFlow]
    ) -> dict[tuple[str, str, str], list[SCDFlow]]:
        """Group SCD flows by (source_name, target_name, direction)."""
        groups: dict[tuple[str, str, str], list[SCDFlow]] = {}
        for flow in flows.values():
            key = (flow.source.name, flow.target.name, flow.direction)
            if key not in groups:
                groups[key] = []
            groups[key].append(flow)
        return groups

    def _aggregate_scd_flow_group(
        self,
        flows: list[SCDFlow],
        source: str,
        target: str,
        direction: str,
    ) -> list[SCDFlow]:
        """Apply type aggregation to a group of SCD flows with same endpoints/direction."""
        if len(flows) <= 1:
            return flows

        # Use qualified type names for union matching
        qualified_names = {self._get_qualified_type_name(f) for f in flows}
        # Map qualified names to flows for lookup
        name_to_flow = {self._get_qualified_type_name(f): f for f in flows}
        remaining = set(qualified_names)
        result: list[SCDFlow] = []

        # Try to find covering parent types
        while remaining:
            parent_type = self._find_covering_parent_type(remaining)

            if parent_type:
                covered = self._get_all_leaf_subtypes(parent_type) & remaining
                if not covered:
                    covered = self._get_immediate_union_subtypes(parent_type) & remaining

                if covered:
                    # Find a representative flow for metadata
                    representative = name_to_flow[next(iter(covered))]
                    result.append(
                        SCDFlow(
                            name=parent_type,
                            source=representative.source,
                            target=representative.target,
                            direction=direction,  # type: ignore[arg-type]
                            type_ref=representative.type_ref,
                            description=representative.description,
                            source_file=representative.source_file,
                            line=representative.line,
                        )
                    )
                    remaining -= covered
                    continue

            # No parent type found - output remaining individually
            for name in sorted(remaining):
                result.append(name_to_flow[name])
            break

        return result

    def _aggregate_scd_directions(self, flows: list[SCDFlow]) -> list[SCDFlow]:
        """Aggregate opposite-direction SCD flows into bidirectional."""
        result: list[SCDFlow] = []
        processed: set[int] = set()  # Track by index

        for i, flow in enumerate(flows):
            if i in processed:
                continue

            if flow.direction == "bidirectional":
                result.append(flow)
                processed.add(i)
                continue

            # Look for opposite direction with same label
            opposite_dir = "outbound" if flow.direction == "inbound" else "inbound"
            opposite_idx: int | None = None

            for j, other_flow in enumerate(flows):
                if j in processed or j == i:
                    continue
                if other_flow.name != flow.name:
                    continue
                if other_flow.direction != opposite_dir:
                    continue
                # Check if endpoints are swapped
                if (
                    other_flow.source.name == flow.target.name
                    and other_flow.target.name == flow.source.name
                ):
                    opposite_idx = j
                    break

            if opposite_idx is not None:
                # Merge into bidirectional
                result.append(
                    SCDFlow(
                        name=flow.name,
                        source=flow.source,
                        target=flow.target,
                        direction="bidirectional",
                        type_ref=flow.type_ref,
                        description=flow.description,
                        source_file=flow.source_file,
                        line=flow.line,
                    )
                )
                processed.add(i)
                processed.add(opposite_idx)
            else:
                result.append(flow)
                processed.add(i)

        return result

    def _aggregate_scd_cross_direction_types(self, flows: list[SCDFlow]) -> list[SCDFlow]:
        """Aggregate flows between same elements with opposite directions if they cover a union.

        This handles the case where subtypes of a union flow in opposite directions
        between the same two elements (REQ-GEN-073), e.g.:
        - PICiX.PICiX_to_VVSS: PICiX -> System (inbound)
        - PICiX.VVSS_to_PICiX: System -> PICiX (outbound)

        If these cover all subtypes of a union (e.g., PICiX.IPICiX), they merge into:
        - PICiX.IPICiX: PICiX <-> System (bidirectional)
        """
        # Group flows by unordered element pair
        pairs: dict[frozenset[str], list[SCDFlow]] = {}
        for flow in flows:
            pair_key = frozenset([flow.source.name, flow.target.name])
            pairs.setdefault(pair_key, []).append(flow)

        result: list[SCDFlow] = []

        for pair_key, pair_flows in pairs.items():
            if len(pair_key) == 1:
                # Self-loop (same source and target) - no cross-direction possible
                result.extend(pair_flows)
                continue

            # Separate by direction relative to canonical ordering
            elements = sorted(pair_key)
            e1, e2 = elements[0], elements[1]

            forward = [
                f for f in pair_flows if f.source.name == e1 and f.direction != "bidirectional"
            ]
            backward = [
                f for f in pair_flows if f.source.name == e2 and f.direction != "bidirectional"
            ]
            bidirectional = [f for f in pair_flows if f.direction == "bidirectional"]

            # If no flows in both directions, no cross-direction aggregation
            if not forward or not backward:
                result.extend(pair_flows)
                continue

            # Use qualified type names for union matching
            forward_names = {self._get_qualified_type_name(f) for f in forward}
            backward_names = {self._get_qualified_type_name(f) for f in backward}
            all_names = forward_names | backward_names

            # Names must be disjoint (each subtype in exactly one direction)
            if not forward_names.isdisjoint(backward_names):
                result.extend(pair_flows)
                continue

            parent_type = self._find_covering_parent_type(all_names)

            if parent_type:
                # Create bidirectional flow with parent type
                representative = forward[0]
                result.append(
                    SCDFlow(
                        name=parent_type,
                        source=representative.source,
                        target=representative.target,
                        direction="bidirectional",
                        type_ref=representative.type_ref,
                        description=representative.description,
                        source_file=representative.source_file,
                        line=representative.line,
                    )
                )
                result.extend(bidirectional)
            else:
                # No covering union - keep flows as-is
                result.extend(pair_flows)

        return result

    # =========================================================================
    # DFD Aggregation
    # =========================================================================

    def aggregate_dfd(self, dfd: DFDModel) -> DFDModel:
        """Return new DFDModel with aggregated flows."""
        if not dfd.flows:
            return dfd

        # Step 1: Group flows by (source, target, flow_type) and apply type aggregation
        groups = self._group_dfd_flows(dfd.flows)
        new_flows: dict[FlowKey, DataFlow] = {}
        for (source, target, flow_type), group_flows in groups.items():
            aggregated = self._aggregate_dfd_flow_group(group_flows, source, target, flow_type)
            for flow in aggregated:
                new_flows[(flow.name, flow.flow_type)] = flow

        # Step 2: Cross-direction type aggregation (REQ-GEN-073)
        new_flows = self._aggregate_dfd_cross_direction_types(new_flows)

        # Step 3: Same-label direction aggregation for boundary flows
        new_flows = self._aggregate_dfd_directions(new_flows)

        if new_flows == dfd.flows:
            return dfd

        return dfd.model_copy(update={"flows": new_flows})

    def _group_dfd_flows(
        self, flows: dict[FlowKey, DataFlow]
    ) -> dict[tuple[str | None, str | None, str], list[DataFlow]]:
        """Group DFD flows by (source_name, target_name, flow_type)."""
        groups: dict[tuple[str | None, str | None, str], list[DataFlow]] = {}
        for flow in flows.values():
            source_name = flow.source.name if flow.source else None
            target_name = flow.target.name if flow.target else None
            key = (source_name, target_name, flow.flow_type)
            if key not in groups:
                groups[key] = []
            groups[key].append(flow)
        return groups

    def _aggregate_dfd_flow_group(
        self,
        flows: list[DataFlow],
        source: str | None,
        target: str | None,
        flow_type: str,
    ) -> list[DataFlow]:
        """Apply type aggregation to a group of DFD flows with same endpoints/type."""
        if len(flows) <= 1:
            return flows

        # Use qualified type names for union matching
        qualified_names = {self._get_qualified_type_name(f) for f in flows}
        # Map qualified names to flows for lookup
        name_to_flow = {self._get_qualified_type_name(f): f for f in flows}
        remaining = set(qualified_names)
        result: list[DataFlow] = []

        while remaining:
            parent_type = self._find_covering_parent_type(remaining)

            if parent_type:
                covered = self._get_all_leaf_subtypes(parent_type) & remaining
                if not covered:
                    covered = self._get_immediate_union_subtypes(parent_type) & remaining

                if covered:
                    representative = name_to_flow[next(iter(covered))]
                    result.append(
                        DataFlow(
                            name=parent_type,
                            source=representative.source,
                            target=representative.target,
                            flow_type=flow_type,  # type: ignore[arg-type]
                            type_ref=representative.type_ref,
                            description=representative.description,
                            source_file=representative.source_file,
                            line=representative.line,
                        )
                    )
                    remaining -= covered
                    continue

            for name in sorted(remaining):
                result.append(name_to_flow[name])
            break

        return result

    def _aggregate_dfd_directions(self, flows: dict[FlowKey, DataFlow]) -> dict[FlowKey, DataFlow]:
        """Aggregate opposite-direction DFD boundary flows into bidirectional."""
        result: dict[FlowKey, DataFlow] = {}
        processed: set[FlowKey] = set()

        # Build lookups for matching boundary flows
        inbound_by_target, outbound_by_source = self._build_dfd_boundary_lookups(flows)

        # Process flows
        for key, flow in flows.items():
            if key in processed:
                continue

            if flow.flow_type == "internal":
                result[key] = flow
                processed.add(key)
                continue

            # Try to find matching opposite direction
            match_key = self._find_dfd_opposite_direction(
                flow, inbound_by_target, outbound_by_source
            )

            if match_key and match_key not in processed:
                # Create bidirectional flow from the inbound flow
                base_flow = flow if flow.flow_type == "inbound" else flows[match_key]
                bidirectional = self._create_bidirectional_dfd_flow(base_flow)
                result[(base_flow.name, "bidirectional")] = bidirectional
                processed.add(key)
                processed.add(match_key)
            else:
                result[key] = flow
                processed.add(key)

        return result

    def _build_dfd_boundary_lookups(
        self, flows: dict[FlowKey, DataFlow]
    ) -> tuple[dict[tuple[str, str], FlowKey], dict[tuple[str, str], FlowKey]]:
        """Build lookup dicts for matching inbound/outbound boundary flows."""
        inbound_by_target: dict[tuple[str, str], FlowKey] = {}
        outbound_by_source: dict[tuple[str, str], FlowKey] = {}

        for key, flow in flows.items():
            if flow.flow_type == "inbound" and flow.target:
                inbound_by_target[(flow.target.name, flow.name)] = key
            elif flow.flow_type == "outbound" and flow.source:
                outbound_by_source[(flow.source.name, flow.name)] = key

        return inbound_by_target, outbound_by_source

    def _find_dfd_opposite_direction(
        self,
        flow: DataFlow,
        inbound_by_target: dict[tuple[str, str], FlowKey],
        outbound_by_source: dict[tuple[str, str], FlowKey],
    ) -> FlowKey | None:
        """Find the opposite-direction flow that matches this one."""
        if flow.flow_type == "inbound" and flow.target:
            lookup = (flow.target.name, flow.name)
            return outbound_by_source.get(lookup)
        elif flow.flow_type == "outbound" and flow.source:
            lookup = (flow.source.name, flow.name)
            return inbound_by_target.get(lookup)
        return None

    def _create_bidirectional_dfd_flow(self, base_flow: DataFlow) -> DataFlow:
        """Create a bidirectional DFD boundary flow from an inbound base flow."""
        return DataFlow(
            name=base_flow.name,
            source=None,
            target=base_flow.target,
            flow_type="bidirectional",
            type_ref=base_flow.type_ref,
            description=base_flow.description,
            source_file=base_flow.source_file,
            line=base_flow.line,
        )

    def _aggregate_dfd_cross_direction_types(
        self, flows: dict[FlowKey, DataFlow]
    ) -> dict[FlowKey, DataFlow]:
        """Aggregate DFD flows with opposite directions if they cover a union (REQ-GEN-073).

        For boundary flows, groups by process endpoint.
        For internal flows, groups by unordered process pair.
        """
        # Separate boundary and internal flows
        boundary_flows = {k: f for k, f in flows.items() if f.flow_type in ("inbound", "outbound")}
        internal_flows = {k: f for k, f in flows.items() if f.flow_type == "internal"}
        other_flows = {
            k: f for k, f in flows.items() if f.flow_type not in ("inbound", "outbound", "internal")
        }

        # Process boundary flows - group by process
        boundary_result = self._aggregate_dfd_boundary_cross_direction(boundary_flows)

        # Process internal flows - group by process pair
        internal_result = self._aggregate_dfd_internal_cross_direction(internal_flows)

        # Combine results
        result: dict[FlowKey, DataFlow] = {}
        result.update(boundary_result)
        result.update(internal_result)
        result.update(other_flows)

        return result

    def _try_cross_direction_merge(
        self,
        forward_flows: list[tuple[FlowKey, DataFlow]],
        backward_flows: list[tuple[FlowKey, DataFlow]],
    ) -> str | None:
        """Try to find a covering union for flows in opposite directions.

        Returns the parent union type name if found, or None if no merge is possible.
        """
        if not forward_flows or not backward_flows:
            return None

        forward_names = {self._get_qualified_type_name(f) for _, f in forward_flows}
        backward_names = {self._get_qualified_type_name(f) for _, f in backward_flows}

        # Names must be disjoint (each subtype in exactly one direction)
        if not forward_names.isdisjoint(backward_names):
            return None

        all_names = forward_names | backward_names
        return self._find_covering_parent_type(all_names)

    def _aggregate_dfd_boundary_cross_direction(
        self, flows: dict[FlowKey, DataFlow]
    ) -> dict[FlowKey, DataFlow]:
        """Aggregate boundary flows by process if they cover a union across directions."""
        # Group by process (target for inbound, source for outbound)
        by_process: dict[str, list[tuple[FlowKey, DataFlow]]] = {}
        for key, flow in flows.items():
            if flow.flow_type == "inbound" and flow.target:
                process = flow.target.name
            elif flow.flow_type == "outbound" and flow.source:
                process = flow.source.name
            else:
                continue
            by_process.setdefault(process, []).append((key, flow))

        result: dict[FlowKey, DataFlow] = {}

        for process_flows in by_process.values():
            inbound = [(k, f) for k, f in process_flows if f.flow_type == "inbound"]
            outbound = [(k, f) for k, f in process_flows if f.flow_type == "outbound"]

            parent_type = self._try_cross_direction_merge(inbound, outbound)

            if parent_type:
                representative = inbound[0][1]
                bidirectional = DataFlow(
                    name=parent_type,
                    source=None,
                    target=representative.target,
                    flow_type="bidirectional",
                    type_ref=representative.type_ref,
                    description=representative.description,
                    source_file=representative.source_file,
                    line=representative.line,
                )
                result[(parent_type, "bidirectional")] = bidirectional
            else:
                for key, flow in process_flows:
                    result[key] = flow

        return result

    def _aggregate_dfd_internal_cross_direction(
        self, flows: dict[FlowKey, DataFlow]
    ) -> dict[FlowKey, DataFlow]:
        """Aggregate internal flows by process pair if they cover a union across directions."""
        # Group by unordered process pair
        by_pair: dict[frozenset[str], list[tuple[FlowKey, DataFlow]]] = {}
        for key, flow in flows.items():
            if flow.source and flow.target:
                pair = frozenset([flow.source.name, flow.target.name])
                by_pair.setdefault(pair, []).append((key, flow))

        result: dict[FlowKey, DataFlow] = {}

        for pair, pair_flows in by_pair.items():
            if len(pair) == 1:
                # Self-loop - no cross-direction aggregation possible
                for key, flow in pair_flows:
                    result[key] = flow
                continue

            elements = sorted(pair)
            e1, e2 = elements[0], elements[1]

            forward = [(k, f) for k, f in pair_flows if f.source and f.source.name == e1]
            backward = [(k, f) for k, f in pair_flows if f.source and f.source.name == e2]

            parent_type = self._try_cross_direction_merge(forward, backward)

            if parent_type:
                representative = forward[0][1]
                # For internal flows, keep as internal but with aggregated name
                aggregated = DataFlow(
                    name=parent_type,
                    source=representative.source,
                    target=representative.target,
                    flow_type="internal",
                    type_ref=representative.type_ref,
                    description=representative.description,
                    source_file=representative.source_file,
                    line=representative.line,
                )
                result[(parent_type, "internal")] = aggregated
            else:
                for key, flow in pair_flows:
                    result[key] = flow

        return result

    # =========================================================================
    # Union Type Helpers
    # =========================================================================

    def _resolve_type_ref(self, type_ref_name: str, current_namespace: str | None) -> str | None:
        """Resolve a type reference name to its qualified name in the data dictionary.

        Resolution rules:
        1. If already qualified (Namespace.Type): look for exact match
        2. If simple (Type) in a namespace: try same namespace first, then global
        3. If simple (Type) in anonymous: try global only

        Args:
            type_ref_name: The type name to resolve (may be simple or qualified).
            current_namespace: The namespace context for resolution.

        Returns:
            The qualified name of the resolved type, or None if not found.
        """
        # Check if already qualified
        if "." in type_ref_name:
            return type_ref_name if type_ref_name in self.data_dictionary.definitions else None

        # Simple reference - try same namespace first
        if current_namespace:
            namespaced = f"{current_namespace}.{type_ref_name}"
            if namespaced in self.data_dictionary.definitions:
                return namespaced

        # Try global (anonymous namespace)
        if type_ref_name in self.data_dictionary.definitions:
            defn = self.data_dictionary.definitions[type_ref_name]
            if defn.namespace is None:
                return type_ref_name

        return None

    def _find_covering_parent_type(self, flow_names: set[str]) -> str | None:
        """Find the highest-level union type that covers a subset of flow names."""
        if not flow_names:
            return None

        cache_key = frozenset(flow_names)
        if cache_key in self._parent_cache:
            return self._parent_cache[cache_key]

        best_match, _ = self._find_best_union_match(flow_names)
        self._parent_cache[cache_key] = best_match
        return best_match

    def _find_best_union_match(self, flow_names: set[str]) -> tuple[str | None, int]:
        """Find the best matching union type for the given flow names."""
        best_match: str | None = None
        best_match_level = -1

        for type_name, defn in self.data_dictionary.definitions.items():
            if not defn.is_union or self._is_enum_union(type_name):
                continue

            match_level = self._check_union_coverage(type_name, flow_names)
            if match_level > best_match_level:
                best_match = type_name
                best_match_level = match_level

        return best_match, best_match_level

    def _check_union_coverage(self, type_name: str, flow_names: set[str]) -> int:
        """Check if a union type covers the flow names and return its depth level."""
        # Check leaf subtypes coverage
        leaf_subtypes = self._get_all_leaf_subtypes(type_name)
        if leaf_subtypes and leaf_subtypes <= flow_names:
            if leaf_subtypes == (flow_names & leaf_subtypes):
                return self._get_union_depth(type_name)

        # Check immediate subtypes exact match
        immediate = self._get_immediate_union_subtypes(type_name)
        if immediate and immediate == flow_names:
            return self._get_union_depth(type_name)

        return -1

    def _get_immediate_union_subtypes(self, type_name: str) -> set[str]:
        """Get immediate union alternatives for a type (fully qualified names).

        Resolves type references in the context of the parent type's namespace,
        so unqualified references within a namespace are properly qualified.
        """
        from designit.model.datadict import TypeRef, UnionType

        defn = self.data_dictionary.definitions.get(type_name)
        if not defn or not defn.is_union or not isinstance(defn.definition, UnionType):
            return set()

        result: set[str] = set()
        for alt in defn.definition.alternatives:
            if isinstance(alt, TypeRef):
                # Resolve in parent type's namespace context
                resolved = self._resolve_type_ref(alt.qualified_name, defn.namespace)
                if resolved:
                    result.add(resolved)
                else:
                    # Fallback to the qualified name if resolution fails
                    result.add(alt.qualified_name)
            elif isinstance(alt, str) and not (alt.startswith('"') or alt.startswith("'")):
                # Unquoted string - resolve as type name
                resolved = self._resolve_type_ref(alt, defn.namespace)
                if resolved:
                    result.add(resolved)
                else:
                    result.add(alt)

        return result

    def _get_all_leaf_subtypes(self, type_name: str) -> set[str]:
        """Get all leaf subtypes of a union (recursively)."""
        if type_name in self._subtype_cache:
            return self._subtype_cache[type_name]

        defn = self.data_dictionary.definitions.get(type_name)
        if not defn or not defn.is_union:
            self._subtype_cache[type_name] = set()
            return set()

        result: set[str] = set()
        immediate = self._get_immediate_union_subtypes(type_name)

        for subtype in immediate:
            sub_defn = self.data_dictionary.definitions.get(subtype)
            if sub_defn and sub_defn.is_union and not self._is_enum_union(subtype):
                result.update(self._get_all_leaf_subtypes(subtype))
            else:
                result.add(subtype)

        self._subtype_cache[type_name] = result
        return result

    def _is_enum_union(self, type_name: str) -> bool:
        """Check if a type is an enum union (all quoted string alternatives)."""
        from designit.model.datadict import TypeRef, UnionType

        defn = self.data_dictionary.definitions.get(type_name)
        if not defn or not defn.is_union or not isinstance(defn.definition, UnionType):
            return False

        for alt in defn.definition.alternatives:
            if isinstance(alt, TypeRef):
                return False
            if isinstance(alt, str) and not (alt.startswith('"') or alt.startswith("'")):
                return False

        return True

    def _get_union_depth(self, type_name: str) -> int:
        """Get the depth of a union type (higher = more abstract)."""
        defn = self.data_dictionary.definitions.get(type_name)
        if not defn or not defn.is_union:
            return 0

        max_child_depth = 0
        for subtype in self._get_immediate_union_subtypes(type_name):
            child_depth = self._get_union_depth(subtype)
            max_child_depth = max(max_child_depth, child_depth)

        return max_child_depth + 1
