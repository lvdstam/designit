"""Semantic analyzer - transforms AST to semantic model."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from designit.parser.ast_nodes import (
    AttributeNode,
    BlockNode,
    CardinalityNode,
    ConstraintNode,
    DataDefNode,
    DataDictNode,
    DatastoreNode,
    DFDNode,
    DocumentNode,
    EntityNode,
    ERDNode,
    ExternalNode,
    FlowNode,
    ModuleNode,
    PlaceholderNode,
    ProcessNode,
    PropertyNode,
    RelationshipNode,
    SCDFlowNode,
    SCDNode,
    StateNode,
    STDNode,
    StructDefNode,
    StructFieldNode,
    StructureNode,
    SystemNode,
    TransitionNode,
    ArrayDefNode,
    UnionDefNode,
    TypeRefNode,
    FieldConstraintNode,
)
from designit.model.base import (
    DesignDocument,
    ElementReference,
    ValidationMessage,
    ValidationSeverity,
)
from designit.model.dfd import (
    DFDModel,
    DataFlow,
    Datastore,
    ExternalEntity,
    Process,
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
from designit.model.std import (
    State,
    STDModel,
    Transition,
)
from designit.model.structure import (
    Module,
    StructureModel,
)
from designit.model.datadict import (
    ArrayType,
    DataDefinition,
    DataDictionaryModel,
    FieldConstraint,
    FieldConstraintType,
    StructField,
    StructType,
    TypeReference,
    UnionType,
)
from designit.model.scd import (
    SCDDatastore,
    SCDExternalEntity,
    SCDFlow,
    SCDModel,
    System,
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

    def __init__(self):
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

    # ============================================
    # DFD Analysis
    # ============================================

    def _analyze_dfd(self, node: DFDNode, source_file: str | None) -> DFDModel:
        """Analyze a DFD AST node."""
        model = DFDModel(name=node.name, source_file=source_file)

        # Process externals
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

        # Process processes
        for proc in node.processes:
            props = self._extract_properties(proc.body)
            process = Process(
                name=proc.name,
                description=props.get("description"),
                inputs=props.get("inputs", []),
                outputs=props.get("outputs", []),
                is_placeholder=self._is_placeholder(proc.body),
                source_file=source_file,
                line=proc.location.line if proc.location else None,
            )
            if proc.name in model.processes:
                self._warning(f"Duplicate process: {proc.name}", proc.name)
            model.processes[proc.name] = process

        # Process datastores
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

        # Process flows
        for flow in node.flows:
            data_flow = DataFlow(
                name=flow.name,
                source=ElementReference(name=flow.source.entity),
                target=ElementReference(name=flow.target.entity),
                source_file=source_file,
                line=flow.location.line if flow.location else None,
            )
            if flow.name in model.flows:
                self._warning(f"Duplicate flow: {flow.name}", flow.name)
            model.flows[flow.name] = data_flow

        return model

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
        return StructField(
            name=node.name,
            type_name=node.type_name,
            constraints=constraints,
        )

    def _analyze_data_definition(
        self, node: DataDefNode, source_file: str | None
    ) -> DataDefinition:
        """Analyze a data definition node."""
        defn = node.definition

        if isinstance(defn, PlaceholderNode):
            return DataDefinition(
                name=node.name,
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
                definition=StructType(fields=fields),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, UnionDefNode):
            return DataDefinition(
                name=node.name,
                definition=UnionType(alternatives=defn.alternatives),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, ArrayDefNode):
            return DataDefinition(
                name=node.name,
                definition=ArrayType(
                    element_type=defn.element_type,
                    min_length=defn.min_length,
                    max_length=defn.max_length,
                ),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        elif isinstance(defn, TypeRefNode):
            return DataDefinition(
                name=node.name,
                definition=TypeReference(name=defn.name),
                source_file=source_file,
                line=node.location.line if node.location else None,
            )
        else:
            return DataDefinition(
                name=node.name,
                is_placeholder=True,
                source_file=source_file,
                line=node.location.line if node.location else None,
            )

    def _analyze_datadict(self, node: DataDictNode, source_file: str | None) -> DataDictionaryModel:
        """Analyze a data dictionary AST node."""
        model = DataDictionaryModel(source_file=source_file)

        for defn in node.definitions:
            if defn.name in model.definitions:
                self._warning(f"Duplicate data definition: {defn.name}", defn.name)
            model.definitions[defn.name] = self._analyze_data_definition(defn, source_file)

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
                source_file=source_file,
                line=flow.location.line if flow.location else None,
            )
            if flow.name in model.flows:
                self._warning(f"Duplicate flow: {flow.name}", flow.name)
            model.flows[flow.name] = scd_flow

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

        # Analyze DFDs
        for dfd in doc.dfds:
            model = self._analyze_dfd(dfd, source_file)
            if dfd.name in design.dfds:
                self._warning(f"Duplicate DFD: {dfd.name}", dfd.name)
            design.dfds[dfd.name] = model

        # Analyze ERDs
        for erd in doc.erds:
            model = self._analyze_erd(erd, source_file)
            if erd.name in design.erds:
                self._warning(f"Duplicate ERD: {erd.name}", erd.name)
            design.erds[erd.name] = model

        # Analyze STDs
        for std in doc.stds:
            model = self._analyze_std(std, source_file)
            if std.name in design.stds:
                self._warning(f"Duplicate STD: {std.name}", std.name)
            design.stds[std.name] = model

        # Analyze Structure Charts
        for structure in doc.structures:
            model = self._analyze_structure(structure, source_file)
            if structure.name in design.structures:
                self._warning(f"Duplicate structure chart: {structure.name}", structure.name)
            design.structures[structure.name] = model

        # Analyze SCDs
        for scd in doc.scds:
            model = self._analyze_scd(scd, source_file)
            if scd.name in design.scds:
                self._warning(f"Duplicate SCD: {scd.name}", scd.name)
            design.scds[scd.name] = model

        # Analyze Data Dictionaries (merge into one)
        if doc.datadicts:
            merged_datadict = DataDictionaryModel()
            for dd in doc.datadicts:
                dd_model = self._analyze_datadict(dd, source_file)
                for name, defn in dd_model.definitions.items():
                    if name in merged_datadict.definitions:
                        self._warning(f"Duplicate data definition: {name}", name)
                    merged_datadict.definitions[name] = defn
            design.data_dictionary = merged_datadict

        design.validation_messages = self.messages.copy()
        return design


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
