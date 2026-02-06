"""Semantic analyzer - transforms AST to semantic model."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from designit.model.base import (
    DesignDocument,
    ElementReference,
    ValidationMessage,
    ValidationSeverity,
)
from designit.model.datadict import (
    ArrayType,
    DataDefinition,
    DataDictionaryModel,
    FieldConstraint,
    FieldConstraintType,
    StructField,
    StructType,
    TypeRef,
    TypeReference,
    UnionType,
)
from designit.model.dfd import (
    DataFlow,
    Datastore,
    DFDFlowUnion,
    DFDModel,
    ExternalEntity,
    FlowKey,
    FlowType,
    FlowTypeRef,
    Process,
    RefinesRef,
)
from designit.model.erd import (
    Attribute,
    AttributeConstraint,
    Cardinality,
    ConstraintType,
    Entity,
    ERDModel,
    Relationship,
)
from designit.model.scd import (
    SCDDatastore,
    SCDExternalEntity,
    SCDFlow,
    SCDFlowTypeRef,
    SCDFlowUnion,
    SCDModel,
    System,
)
from designit.model.std import (
    State,
    STDModel,
    Transition,
)
from designit.model.structure import (
    Module,
    StructureModel,
)
from designit.parser.ast_nodes import (
    ArrayDefNode,
    AttributeNode,
    BlockNode,
    CardinalityNode,
    ConstraintNode,
    DataDefNode,
    DataDictNode,
    DataDictTypeRefNode,
    DFDNode,
    DocumentNode,
    EntityNode,
    ERDNode,
    FieldConstraintNode,
    FlowTypeRefNode,
    ModuleNode,
    PlaceholderNode,
    RelationshipNode,
    SCDNode,
    SimpleTypeRefNode,
    StateNode,
    STDNode,
    StructDefNode,
    StructFieldNode,
    StructureNode,
    SystemNode,
    TransitionNode,
    UnionDefNode,
)
from designit.semantic.resolver import resolve_imports


class SemanticError(Exception):
    """Raised when semantic analysis fails."""

    def __init__(
        self,
        message: str,
        element_name: str | None = None,
        file: str | None = None,
        line: int | None = None,
    ):
        self.message = message
        self.element_name = element_name
        self.file = file
        self.line = line
        super().__init__(message)


class SemanticAnalyzer:
    """Analyzes AST and builds semantic model."""

    def __init__(self) -> None:
        self.messages: list[ValidationMessage] = []
        self.current_file: str | None = None

    def _add_message(
        self,
        severity: ValidationSeverity,
        message: str,
        element_name: str | None = None,
        line: int | None = None,
    ) -> None:
        """Add a validation message."""
        self.messages.append(
            ValidationMessage(
                severity=severity,
                message=message,
                file=self.current_file,
                line=line,
                element_name=element_name,
            )
        )

    def _error(
        self, message: str, element_name: str | None = None, line: int | None = None
    ) -> None:
        self._add_message(ValidationSeverity.ERROR, message, element_name, line)

    def _warning(
        self, message: str, element_name: str | None = None, line: int | None = None
    ) -> None:
        self._add_message(ValidationSeverity.WARNING, message, element_name, line)

    def _info(self, message: str, element_name: str | None = None, line: int | None = None) -> None:
        self._add_message(ValidationSeverity.INFO, message, element_name, line)

    def _extract_properties(self, node: BlockNode | PlaceholderNode) -> dict[str, Any]:
        """Extract properties from a block node."""
        if isinstance(node, PlaceholderNode):
            return {}
        result: dict[str, Any] = {}
        for prop in node.properties:
            result[prop.name] = prop.value
        return result

    def _is_placeholder(self, node: BlockNode | PlaceholderNode) -> bool:
        """Check if a node is a placeholder."""
        if isinstance(node, PlaceholderNode):
            return True
        return node.is_placeholder

    def _convert_flow_type_ref(self, node: FlowTypeRefNode | None) -> FlowTypeRef | None:
        """Convert a FlowTypeRefNode to a FlowTypeRef model.

        Args:
            node: The AST node for the flow type reference.

        Returns:
            A FlowTypeRef model or None if no type ref.
        """
        if node is None:
            return None
        return FlowTypeRef(namespace=node.namespace, name=node.name)

    def _convert_scd_flow_type_ref(self, node: FlowTypeRefNode | None) -> SCDFlowTypeRef | None:
        """Convert a FlowTypeRefNode to an SCDFlowTypeRef model.

        Args:
            node: The AST node for the flow type reference.

        Returns:
            An SCDFlowTypeRef model or None if no type ref.
        """
        if node is None:
            return None
        return SCDFlowTypeRef(namespace=node.namespace, name=node.name)

    # ============================================
    # DFD Analysis
    # ============================================

    def _analyze_dfd(self, node: DFDNode, source_file: str | None) -> DFDModel:
        """Analyze a DFD AST node."""
        # Extract refines reference if present
        refines = None
        if node.refines:
            refines = RefinesRef(
                diagram_name=node.refines.diagram_name,
                element_name=node.refines.element_name,
                line=node.refines.location.line if node.refines.location else None,
            )

        model = DFDModel(
            name=node.name,
            source_file=source_file,
            refines=refines,
            line=node.location.line if node.location else None,
        )

        self._analyze_dfd_externals(node, model, source_file)
        self._analyze_dfd_processes(node, model, source_file)
        self._analyze_dfd_datastores(node, model, source_file)
        inbound_handlers = self._analyze_dfd_flows(node, model, source_file)
        self._analyze_dfd_flow_unions(node, model, source_file)

        # Store inbound handler counts in metadata for later validation
        model._inbound_flow_handlers = inbound_handlers  # type: ignore[attr-defined]

        return model

    def _analyze_dfd_externals(
        self, node: DFDNode, model: DFDModel, source_file: str | None
    ) -> None:
        """Analyze external entities in a DFD."""
        for ext in node.externals:
            props = self._extract_properties(ext.body)
            external = ExternalEntity(
                name=ext.name,
                description=props.get("description"),
                is_placeholder=self._is_placeholder(ext.body),
                source_file=source_file,
                line=ext.location.line if ext.location else None,
            )
            if ext.name in model.externals:
                self._warning(f"Duplicate external entity: {ext.name}", ext.name)
            model.externals[ext.name] = external

    def _analyze_dfd_processes(
        self, node: DFDNode, model: DFDModel, source_file: str | None
    ) -> None:
        """Analyze processes in a DFD."""
        for proc in node.processes:
            props = self._extract_properties(proc.body)
            process = Process(
                name=proc.name,
                description=props.get("description"),
                is_placeholder=self._is_placeholder(proc.body),
                source_file=source_file,
                line=proc.location.line if proc.location else None,
            )
            if proc.name in model.processes:
                self._warning(f"Duplicate process: {proc.name}", proc.name)
            model.processes[proc.name] = process

    def _analyze_dfd_datastores(
        self, node: DFDNode, model: DFDModel, source_file: str | None
    ) -> None:
        """Analyze datastores in a DFD."""
        for ds in node.datastores:
            props = self._extract_properties(ds.body)
            datastore = Datastore(
                name=ds.name,
                description=props.get("description"),
                is_placeholder=self._is_placeholder(ds.body),
                source_file=source_file,
                line=ds.location.line if ds.location else None,
            )
            if ds.name in model.datastores:
                self._warning(f"Duplicate datastore: {ds.name}", ds.name)
            model.datastores[ds.name] = datastore

    def _analyze_dfd_flows(
        self, node: DFDNode, model: DFDModel, source_file: str | None
    ) -> dict[str, list[str]]:
        """Analyze flows in a DFD. Returns inbound flow handlers map."""
        inbound_flow_handlers: dict[str, list[str]] = {}

        for flow in node.flows:
            flow_type, source_ref, target_ref = self._determine_flow_type(flow)

            # Track inbound handlers for duplicate detection
            if flow_type == "inbound" and flow.target:
                if flow.name not in inbound_flow_handlers:
                    inbound_flow_handlers[flow.name] = []
                inbound_flow_handlers[flow.name].append(flow.target.entity)

            data_flow = DataFlow(
                name=flow.name,
                source=source_ref,
                target=target_ref,
                flow_type=flow_type,
                type_ref=self._convert_flow_type_ref(flow.type_ref),
                parent_ref=flow.namespace,  # Parent diagram for inherited boundary flows
                source_file=source_file,
                line=flow.location.line if flow.location else None,
            )
            flow_key: FlowKey = (flow.name, flow_type)
            if flow_key in model.flows:
                self._warning(f"Duplicate flow: {flow.name} ({flow_type})", flow.name)
            model.flows[flow_key] = data_flow

        return inbound_flow_handlers

    def _analyze_dfd_flow_unions(
        self, node: DFDNode, model: DFDModel, source_file: str | None
    ) -> None:
        """Analyze flow unions in a DFD.

        Flow unions are analyzed after all flows, so we can look up member flows
        and move them from model.flows into the union's members list.
        """
        for union in node.flow_unions:
            # Resolve member flows - look up each member name
            # DFD flows use compound keys (name, flow_type), so we need to find all matching
            member_flows: list[DataFlow] = []
            for member_name in union.members:
                # Find all flows with this name (could be multiple with different types)
                found_flow = False
                for (flow_name, flow_type), flow in list(model.flows.items()):
                    if flow_name == member_name:
                        member_flows.append(flow)
                        found_flow = True
                # Check if it's another union (nested unions)
                if not found_flow and member_name in model.flow_unions:
                    nested_union = model.flow_unions[member_name]
                    member_flows.extend(nested_union.members)
                # Member not found - will be caught by validator

            flow_union = DFDFlowUnion(
                name=union.name,
                members=member_flows,
                requested_member_names=union.members,  # Store original names for validation
                source_file=source_file,
                line=union.location.line if union.location else None,
            )
            if union.name in model.flow_unions:
                self._warning(f"Duplicate flow union: {union.name}", union.name)
            model.flow_unions[union.name] = flow_union

            # Remove member flows from model.flows (they now live in the union)
            for member_name in union.members:
                # Remove all flows with this name
                keys_to_remove = [key for key in model.flows.keys() if key[0] == member_name]
                for key in keys_to_remove:
                    del model.flows[key]

    def _determine_flow_type(
        self, flow: Any
    ) -> tuple[FlowType, ElementReference | None, ElementReference | None]:
        """Determine flow type and create source/target references."""
        if flow.source is None and flow.target is not None:
            # Boundary inbound flow: -> Target
            return "inbound", None, ElementReference(name=flow.target.entity)
        elif flow.source is not None and flow.target is None:
            # Boundary outbound flow: Source ->
            return "outbound", ElementReference(name=flow.source.entity), None
        else:
            # Internal flow: Source -> Target
            source_ref = ElementReference(name=flow.source.entity) if flow.source else None
            target_ref = ElementReference(name=flow.target.entity) if flow.target else None
            return "internal", source_ref, target_ref

    # ============================================
    # ERD Analysis
    # ============================================

    def _analyze_constraint(self, node: ConstraintNode) -> AttributeConstraint:
        """Analyze a constraint node."""
        constraint_map = {
            "pk": ConstraintType.PRIMARY_KEY,
            "fk": ConstraintType.FOREIGN_KEY,
            "unique": ConstraintType.UNIQUE,
            "not_null": ConstraintType.NOT_NULL,
            "pattern": ConstraintType.PATTERN,
        }
        return AttributeConstraint(
            type=constraint_map.get(node.kind, ConstraintType.UNIQUE),
            target_entity=node.target_entity,
            target_attribute=node.target_attribute,
            pattern=node.pattern,
        )

    def _analyze_attribute(self, node: AttributeNode) -> Attribute:
        """Analyze an attribute node."""
        constraints = [self._analyze_constraint(c) for c in node.constraints]
        return Attribute(
            name=node.name,
            type_name=node.type_name,
            constraints=constraints,
        )

    def _analyze_entity(self, node: EntityNode, source_file: str | None) -> Entity:
        """Analyze an entity node."""
        attributes: dict[str, Attribute] = {}
        for attr in node.attributes:
            attributes[attr.name] = self._analyze_attribute(attr)

        return Entity(
            name=node.name,
            attributes=attributes,
            is_placeholder=node.has_placeholder,
            source_file=source_file,
            line=node.location.line if node.location else None,
        )

    def _analyze_cardinality(self, node: CardinalityNode) -> Cardinality:
        """Analyze a cardinality node."""
        return Cardinality(source=node.source, target=node.target)

    def _analyze_relationship(
        self, node: RelationshipNode, source_file: str | None
    ) -> Relationship:
        """Analyze a relationship node."""
        return Relationship(
            name=node.name,
            source_entity=node.source_entity,
            target_entity=node.target_entity,
            cardinality=self._analyze_cardinality(node.cardinality),
            source_file=source_file,
            line=node.location.line if node.location else None,
        )

    def _analyze_erd(self, node: ERDNode, source_file: str | None) -> ERDModel:
        """Analyze an ERD AST node."""
        model = ERDModel(name=node.name, source_file=source_file)

        for entity in node.entities:
            if entity.name in model.entities:
                self._warning(f"Duplicate entity: {entity.name}", entity.name)
            model.entities[entity.name] = self._analyze_entity(entity, source_file)

        for rel in node.relationships:
            if rel.name in model.relationships:
                self._warning(f"Duplicate relationship: {rel.name}", rel.name)
            model.relationships[rel.name] = self._analyze_relationship(rel, source_file)

        return model

    # ============================================
    # STD Analysis
    # ============================================

    def _analyze_state(
        self, node: StateNode, source_file: str | None, is_initial: bool = False
    ) -> State:
        """Analyze a state node."""
        props = self._extract_properties(node.body)
        return State(
            name=node.name,
            description=props.get("description"),
            is_initial=is_initial,
            entry_action=props.get("entry"),
            exit_action=props.get("exit"),
            is_placeholder=self._is_placeholder(node.body),
            source_file=source_file,
            line=node.location.line if node.location else None,
        )

    def _analyze_transition(self, node: TransitionNode, source_file: str | None) -> Transition:
        """Analyze a transition node."""
        props: dict[str, Any] = {}
        for prop in node.properties:
            props[prop.name] = prop.value

        return Transition(
            name=node.name,
            source_state=node.source_state,
            target_state=node.target_state,
            trigger=props.get("trigger"),
            guard=props.get("guard"),
            action=props.get("action"),
            source_file=source_file,
            line=node.location.line if node.location else None,
        )

    def _analyze_std(self, node: STDNode, source_file: str | None) -> STDModel:
        """Analyze an STD AST node."""
        model = STDModel(
            name=node.name,
            initial_state=node.initial_state,
            source_file=source_file,
        )

        for state in node.states:
            is_initial = state.name == node.initial_state
            if state.name in model.states:
                self._warning(f"Duplicate state: {state.name}", state.name)
            model.states[state.name] = self._analyze_state(state, source_file, is_initial)

        for trans in node.transitions:
            if trans.name in model.transitions:
                self._warning(f"Duplicate transition: {trans.name}", trans.name)
            model.transitions[trans.name] = self._analyze_transition(trans, source_file)

        return model

    # ============================================
    # Structure Chart Analysis
    # ============================================

    def _analyze_module(self, node: ModuleNode, source_file: str | None) -> Module:
        """Analyze a module node."""
        props: dict[str, Any] = {}
        for prop in node.properties:
            props[prop.name] = prop.value

        return Module(
            name=node.name,
            description=props.get("description"),
            calls=node.calls,
            data_couples=node.data_couples,
            control_couples=node.control_couples,
            is_placeholder=node.has_placeholder,
            source_file=source_file,
            line=node.location.line if node.location else None,
        )

    def _analyze_structure(self, node: StructureNode, source_file: str | None) -> StructureModel:
        """Analyze a structure chart AST node."""
        model = StructureModel(name=node.name, source_file=source_file)

        for module in node.modules:
            if module.name in model.modules:
                self._warning(f"Duplicate module: {module.name}", module.name)
            model.modules[module.name] = self._analyze_module(module, source_file)

        return model

    # ============================================
    # Data Dictionary Analysis
    # ============================================

    def _analyze_field_constraint(self, node: FieldConstraintNode) -> FieldConstraint:
        """Analyze a field constraint node."""
        constraint_map = {
            "pattern": FieldConstraintType.PATTERN,
            "optional": FieldConstraintType.OPTIONAL,
            "min": FieldConstraintType.MIN,
            "max": FieldConstraintType.MAX,
        }
        return FieldConstraint(
            type=constraint_map.get(node.kind, FieldConstraintType.OPTIONAL),
            value=node.value,
        )

    def _analyze_struct_field(self, node: StructFieldNode) -> StructField:
        """Analyze a struct field node."""
        constraints = [self._analyze_field_constraint(c) for c in node.constraints]
        type_ref = self._analyze_datadict_type_ref(node.type_ref)
        return StructField(
            name=node.name,
            type_ref=type_ref,
            constraints=constraints,
        )

    def _analyze_datadict_type_ref(self, node: DataDictTypeRefNode) -> TypeRef:
        """Convert AST DataDictTypeRefNode to semantic model TypeRef."""
        return TypeRef(namespace=node.namespace, name=node.name)

    def _analyze_union_alternatives(
        self, alternatives: list[str | DataDictTypeRefNode]
    ) -> list[str | TypeRef]:
        """Convert union alternatives from AST to semantic model."""
        result: list[str | TypeRef] = []
        for alt in alternatives:
            if isinstance(alt, DataDictTypeRefNode):
                result.append(self._analyze_datadict_type_ref(alt))
            else:
                result.append(alt)
        return result

    def _analyze_data_definition(
        self, node: DataDefNode, source_file: str | None, namespace: str | None = None
    ) -> DataDefinition:
        """Analyze a data definition node.

        Args:
            node: The data definition AST node.
            source_file: The source file path.
            namespace: The namespace for this definition (None for anonymous datadict).

        Returns:
            A DataDefinition model with the appropriate namespace set.
        """
        defn = node.definition

        if isinstance(defn, PlaceholderNode):
            return DataDefinition(
                name=node.name,
                namespace=namespace,
                is_placeholder=True,
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, StructDefNode):
            fields: dict[str, StructField] = {}
            for field in defn.fields:
                fields[field.name] = self._analyze_struct_field(field)
            return DataDefinition(
                name=node.name,
                namespace=namespace,
                definition=StructType(fields=fields),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, UnionDefNode):
            alternatives = self._analyze_union_alternatives(defn.alternatives)
            return DataDefinition(
                name=node.name,
                namespace=namespace,
                definition=UnionType(alternatives=alternatives),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, ArrayDefNode):
            element_type = self._analyze_datadict_type_ref(defn.element_type)
            return DataDefinition(
                name=node.name,
                namespace=namespace,
                definition=ArrayType(
                    element_type=element_type,
                    min_length=defn.min_length,
                    max_length=defn.max_length,
                ),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, SimpleTypeRefNode):
            return DataDefinition(
                name=node.name,
                namespace=namespace,
                definition=TypeReference(name=defn.name),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        else:
            return DataDefinition(
                name=node.name,
                namespace=namespace,
                is_placeholder=True,
                source_file=source_file,
                line=node.location.line if node.location else None,
            )

    def _analyze_datadict(self, node: DataDictNode, source_file: str | None) -> DataDictionaryModel:
        """Analyze a data dictionary AST node.

        Supports both anonymous datadicts (namespace=None) and named/namespaced datadicts.
        For named datadicts, types are stored with qualified keys (Namespace.TypeName).

        Args:
            node: The data dictionary AST node.
            source_file: The source file path.

        Returns:
            A DataDictionaryModel with definitions keyed by qualified name.
        """
        model = DataDictionaryModel(source_file=source_file)
        namespace = node.namespace  # May be None for anonymous datadict

        for defn in node.definitions:
            data_def = self._analyze_data_definition(defn, source_file, namespace)
            # Use qualified name as key (includes namespace if present)
            qualified_name = data_def.qualified_name
            if qualified_name in model.definitions:
                ns_info = f" in namespace '{namespace}'" if namespace else ""
                self._error(
                    f"Duplicate type definition '{data_def.name}'{ns_info}",
                    defn.name,
                    defn.location.line if defn.location else None,
                )
            model.definitions[qualified_name] = data_def

        return model

    # ============================================
    # SCD Analysis
    # ============================================

    def _analyze_system(self, node: SystemNode, source_file: str | None) -> System:
        """Analyze a system node."""
        props = self._extract_properties(node.body)
        return System(
            name=node.name,
            description=props.get("description"),
            is_placeholder=self._is_placeholder(node.body),
            source_file=source_file,
            line=node.location.line if node.location else None,
        )

    def _analyze_scd_flow_unions(
        self,
        node: SCDNode,
        model: SCDModel,
        source_file: str | None,
    ) -> None:
        """Process flow unions in an SCD.

        Flow unions are analyzed after all flows, so we can look up member flows
        and move them from model.flows into the union's members list.

        Args:
            node: The SCD AST node.
            model: The SCD model being built.
            source_file: The source file path.
        """
        for union in node.flow_unions:
            # Resolve member flows - look up each member name and get the actual flow
            member_flows: list[SCDFlow] = []
            for member_name in union.members:
                # Check if it's a direct flow
                if member_name in model.flows:
                    member_flows.append(model.flows[member_name])
                # Check if it's another union (nested unions)
                elif member_name in model.flow_unions:
                    # For nested unions, include all their members
                    nested_union = model.flow_unions[member_name]
                    member_flows.extend(nested_union.members)
                # Member not found - will be caught by validator

            flow_union = SCDFlowUnion(
                name=union.name,
                members=member_flows,
                requested_member_names=union.members,  # Store original names for validation
                source_file=source_file,
                line=union.location.line if union.location else None,
            )
            if union.name in model.flow_unions:
                self._warning(f"Duplicate flow union: {union.name}", union.name)
            model.flow_unions[union.name] = flow_union

            # Remove member flows from model.flows (they now live in the union)
            for member_name in union.members:
                if member_name in model.flows:
                    del model.flows[member_name]

    def _analyze_scd(self, node: SCDNode, source_file: str | None) -> SCDModel:
        """Analyze an SCD AST node."""
        model = SCDModel(name=node.name, source_file=source_file)

        # Process system (should be exactly one)
        if node.system:
            model.system = self._analyze_system(node.system, source_file)

        # Process externals
        for ext in node.externals:
            props = self._extract_properties(ext.body)
            external = SCDExternalEntity(
                name=ext.name,
                description=props.get("description"),
                is_placeholder=self._is_placeholder(ext.body),
                source_file=source_file,
                line=ext.location.line if ext.location else None,
            )
            if ext.name in model.externals:
                self._warning(f"Duplicate external entity: {ext.name}", ext.name)
            model.externals[ext.name] = external

        # Process datastores
        for ds in node.datastores:
            props = self._extract_properties(ds.body)
            datastore = SCDDatastore(
                name=ds.name,
                description=props.get("description"),
                is_placeholder=self._is_placeholder(ds.body),
                source_file=source_file,
                line=ds.location.line if ds.location else None,
            )
            if ds.name in model.datastores:
                self._warning(f"Duplicate datastore: {ds.name}", ds.name)
            model.datastores[ds.name] = datastore

        # Process flows
        for flow in node.flows:
            # Determine direction based on arrow type and endpoint order
            # flow.source is the left endpoint, flow.target is the right endpoint
            # flow.direction is "outbound" for ->, "bidirectional" for <->
            direction: Literal["inbound", "outbound", "bidirectional"]
            if flow.direction == "bidirectional":
                direction = "bidirectional"
            else:
                # For outbound arrow (->), source is left endpoint, target is right
                direction = "outbound"
                # If the system is the target, it's inbound to the system
                if model.system and flow.target == model.system.name:
                    direction = "inbound"

            scd_flow = SCDFlow(
                name=flow.name,
                source=ElementReference(name=flow.source),
                target=ElementReference(name=flow.target),
                direction=direction,
                type_ref=self._convert_scd_flow_type_ref(flow.type_ref),
                source_file=source_file,
                line=flow.location.line if flow.location else None,
            )
            if flow.name in model.flows:
                self._warning(f"Duplicate flow: {flow.name}", flow.name)
            model.flows[flow.name] = scd_flow

        # Process flow unions
        self._analyze_scd_flow_unions(node, model, source_file)

        return model

    # ============================================
    # Document Analysis
    # ============================================

    def analyze(self, doc: DocumentNode, source_file: str | None = None) -> DesignDocument:
        """Analyze a document AST and build a semantic model.

        Args:
            doc: The document AST to analyze.
            source_file: The source file path (for error messages).

        Returns:
            A DesignDocument model.
        """
        self.current_file = source_file
        self.messages.clear()

        design = DesignDocument(
            name=Path(source_file).stem if source_file else "unnamed",
            files=[source_file] if source_file else [],
        )

        self._analyze_all_dfds(doc, design, source_file)
        self._analyze_all_erds(doc, design, source_file)
        self._analyze_all_stds(doc, design, source_file)
        self._analyze_all_structures(doc, design, source_file)
        self._analyze_all_scds(doc, design, source_file)
        self._analyze_all_datadicts(doc, design, source_file)

        design.validation_messages = self.messages.copy()
        return design

    def _analyze_all_dfds(
        self, doc: DocumentNode, design: DesignDocument, source_file: str | None
    ) -> None:
        """Analyze all DFDs in the document."""
        for dfd in doc.dfds:
            model = self._analyze_dfd(dfd, source_file)
            if dfd.name in design.dfds:
                self._warning(f"Duplicate DFD: {dfd.name}", dfd.name)
            design.dfds[dfd.name] = model

    def _analyze_all_erds(
        self, doc: DocumentNode, design: DesignDocument, source_file: str | None
    ) -> None:
        """Analyze all ERDs in the document."""
        for erd in doc.erds:
            model = self._analyze_erd(erd, source_file)
            if erd.name in design.erds:
                self._warning(f"Duplicate ERD: {erd.name}", erd.name)
            design.erds[erd.name] = model

    def _analyze_all_stds(
        self, doc: DocumentNode, design: DesignDocument, source_file: str | None
    ) -> None:
        """Analyze all STDs in the document."""
        for std in doc.stds:
            model = self._analyze_std(std, source_file)
            if std.name in design.stds:
                self._warning(f"Duplicate STD: {std.name}", std.name)
            design.stds[std.name] = model

    def _analyze_all_structures(
        self, doc: DocumentNode, design: DesignDocument, source_file: str | None
    ) -> None:
        """Analyze all structure charts in the document."""
        for structure in doc.structures:
            model = self._analyze_structure(structure, source_file)
            if structure.name in design.structures:
                self._warning(f"Duplicate structure chart: {structure.name}", structure.name)
            design.structures[structure.name] = model

    def _analyze_all_scds(
        self, doc: DocumentNode, design: DesignDocument, source_file: str | None
    ) -> None:
        """Analyze all SCDs in the document."""
        for scd in doc.scds:
            model = self._analyze_scd(scd, source_file)
            if scd.name in design.scds:
                self._warning(f"Duplicate SCD: {scd.name}", scd.name)
            design.scds[scd.name] = model

    def _analyze_all_datadicts(
        self, doc: DocumentNode, design: DesignDocument, source_file: str | None
    ) -> None:
        """Analyze all data dictionaries and merge into one."""
        if doc.datadicts:
            merged_datadict = DataDictionaryModel()
            for dd in doc.datadicts:
                dd_model = self._analyze_datadict(dd, source_file)
                for name, defn in dd_model.definitions.items():
                    if name in merged_datadict.definitions:
                        ns_info = f" in namespace '{defn.namespace}'" if defn.namespace else ""
                        self._error(
                            f"Duplicate type definition '{defn.name}'{ns_info}",
                            name,
                            defn.line,
                        )
                    merged_datadict.definitions[name] = defn
            design.data_dictionary = merged_datadict


def analyze_file(filepath: str | Path, resolve_all_imports: bool = True) -> DesignDocument:
    """Analyze a DesignIt file and return a semantic model.

    Args:
        filepath: Path to the .dit file.
        resolve_all_imports: If True, resolve and merge all imports.

    Returns:
        A DesignDocument model.
    """
    analyzer = SemanticAnalyzer()

    if resolve_all_imports:
        doc, files = resolve_imports(filepath)
        design = analyzer.analyze(doc, str(filepath))
        design.files = files
    else:
        from designit.parser.parser import parse_file

        doc = parse_file(filepath)
        design = analyzer.analyze(doc, str(filepath))

    return design


def analyze_string(source: str, filename: str | None = None) -> DesignDocument:
    """Analyze a DesignIt source string and return a semantic model.

    Args:
        source: The source code to analyze.
        filename: Optional filename for error messages.

    Returns:
        A DesignDocument model.
    """
    from designit.parser.parser import parse_string

    doc = parse_string(source, filename)
    analyzer = SemanticAnalyzer()
    return analyzer.analyze(doc, filename)
