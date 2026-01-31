"""Parser for the DesignIt DSL using Lark."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

from lark import Lark, Token, Transformer, v_args
from lark.exceptions import UnexpectedInput

from designit.parser.ast_nodes import (
    ArrayDefNode,
    ASTNode,
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
    FieldConstraintNode,
    FlowEndpointNode,
    FlowNode,
    ImportNode,
    ModuleNode,
    PlaceholderNode,
    ProcessNode,
    PropertyNode,
    RelationshipNode,
    SCDFlowNode,
    SCDNode,
    SourceLocation,
    StateNode,
    STDNode,
    StructDefNode,
    StructFieldNode,
    StructureNode,
    SystemNode,
    TransitionNode,
    TypeRefNode,
    UnionDefNode,
)

# Path to the grammar file
GRAMMAR_PATH = Path(__file__).parent.parent / "grammar" / "designit.lark"


class ParseError(Exception):
    """Raised when parsing fails."""

    def __init__(self, message: str, line: int | None = None, column: int | None = None):
        self.message = message
        self.line = line
        self.column = column
        super().__init__(f"{message} at line {line}, column {column}" if line else message)


def _get_location(meta: Any) -> SourceLocation | None:
    """Extract source location from Lark meta information."""
    if meta and hasattr(meta, "line"):
        return SourceLocation(
            line=meta.line,
            column=meta.column,
            end_line=getattr(meta, "end_line", None),
            end_column=getattr(meta, "end_column", None),
        )
    return None


def _strip_quotes(s: str) -> str:
    """Remove surrounding quotes from a string literal."""
    if s and len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    return s


@v_args(inline=False)
class DesignItTransformer(Transformer[Token, Any]):
    """Transform Lark parse tree into AST nodes."""

    def __init__(self) -> None:
        super().__init__()

    # ============================================
    # Terminals
    # ============================================

    def IDENTIFIER(self, token: Token) -> str:
        return str(token)

    # Handle all keyword tokens that can appear as identifiers
    def STATE(self, token: Token) -> str:
        return str(token)

    def PROCESS(self, token: Token) -> str:
        return str(token)

    def EXTERNAL(self, token: Token) -> str:
        return str(token)

    def DATASTORE(self, token: Token) -> str:
        return str(token)

    def FLOW(self, token: Token) -> str:
        return str(token)

    def ENTITY(self, token: Token) -> str:
        return str(token)

    def RELATIONSHIP(self, token: Token) -> str:
        return str(token)

    def TRANSITION(self, token: Token) -> str:
        return str(token)

    def MODULE(self, token: Token) -> str:
        return str(token)

    def STRUCTURE(self, token: Token) -> str:
        return str(token)

    def DFD(self, token: Token) -> str:
        return str(token)

    def ERD(self, token: Token) -> str:
        return str(token)

    def STD(self, token: Token) -> str:
        return str(token)

    def SCD(self, token: Token) -> str:
        return str(token)

    def SYSTEM(self, token: Token) -> str:
        return str(token)

    def BIDI_ARROW(self, token: Token) -> str:
        return str(token)

    def DATADICT(self, token: Token) -> str:
        return str(token)

    def IMPORT(self, token: Token) -> str:
        return str(token)

    def INITIAL(self, token: Token) -> str:
        return str(token)

    def CALLS(self, token: Token) -> str:
        return str(token)

    def DATA_COUPLE(self, token: Token) -> str:
        return str(token)

    def CONTROL_COUPLE(self, token: Token) -> str:
        return str(token)

    def PK(self, token: Token) -> str:
        return str(token)

    def FK(self, token: Token) -> str:
        return str(token)

    def UNIQUE(self, token: Token) -> str:
        return str(token)

    def NOT(self, token: Token) -> str:
        return str(token)

    def NULL(self, token: Token) -> str:
        return str(token)

    def PATTERN(self, token: Token) -> str:
        return str(token)

    def OPTIONAL(self, token: Token) -> str:
        return str(token)

    def MIN(self, token: Token) -> str:
        return str(token)

    def MAX(self, token: Token) -> str:
        return str(token)

    def STRING_TYPE(self, token: Token) -> str:
        return str(token)

    def INTEGER_TYPE(self, token: Token) -> str:
        return str(token)

    def DECIMAL_TYPE(self, token: Token) -> str:
        return str(token)

    def BOOLEAN_TYPE(self, token: Token) -> str:
        return str(token)

    def DATETIME_TYPE(self, token: Token) -> str:
        return str(token)

    def DATE_TYPE(self, token: Token) -> str:
        return str(token)

    def TIME_TYPE(self, token: Token) -> str:
        return str(token)

    def BINARY_TYPE(self, token: Token) -> str:
        return str(token)

    def identifier(self, items: list[Any]) -> str:
        """Handle identifier rule which can be IDENTIFIER or any keyword token."""
        return items[0] if items else ""

    def STRING(self, token: Token) -> str:
        return _strip_quotes(str(token))

    def NUMBER(self, token: Token) -> int | float:
        s = str(token)
        return float(s) if "." in s else int(s)

    def BOOLEAN(self, token: Token) -> bool:
        return str(token) == "true"

    def CARDINALITY_FULL(self, token: Token) -> str:
        return str(token)

    # ============================================
    # Placeholders
    # ============================================

    def placeholder(self, items: list[Any]) -> PlaceholderNode:
        # items will be empty for ... or TBD
        return PlaceholderNode()

    # ============================================
    # Common Elements
    # ============================================

    def property_value(self, items: list[Any]) -> Any:
        if len(items) == 1:
            return items[0]
        return items

    def value_list(self, items: list[Any]) -> list[Any]:
        return list(items)

    def property_decl(self, items: list[Any]) -> PropertyNode:
        name = items[0]
        value = items[1] if len(items) > 1 else None
        return PropertyNode(name=name, value=value)

    def properties(self, items: list[Any]) -> list[PropertyNode]:
        return [item for item in items if isinstance(item, PropertyNode)]

    def block_body(self, items: list[Any]) -> PropertyNode | PlaceholderNode:
        return items[0] if items else PlaceholderNode()

    def block(self, items: list[Any]) -> BlockNode | PlaceholderNode:
        if len(items) == 1 and isinstance(items[0], PlaceholderNode):
            return items[0]

        properties = []
        placeholder = None
        for item in items:
            if isinstance(item, PropertyNode):
                properties.append(item)
            elif isinstance(item, PlaceholderNode):
                placeholder = item

        return BlockNode(
            properties=properties,
            is_placeholder=placeholder is not None,
            placeholder=placeholder,
        )

    # ============================================
    # Type expressions
    # ============================================

    def string_type(self, items: list[Any]) -> str:
        return "string"

    def integer_type(self, items: list[Any]) -> str:
        return "integer"

    def decimal_type(self, items: list[Any]) -> str:
        return "decimal"

    def boolean_type(self, items: list[Any]) -> str:
        return "boolean"

    def datetime_type(self, items: list[Any]) -> str:
        return "datetime"

    def date_type(self, items: list[Any]) -> str:
        return "date"

    def time_type(self, items: list[Any]) -> str:
        return "time"

    def binary_type(self, items: list[Any]) -> str:
        return "binary"

    def base_type(self, items: list[Any]) -> str:
        return items[0]

    def type_expr(self, items: list[Any]) -> str:
        return items[0] if items else "unknown"

    # ============================================
    # Import
    # ============================================

    def import_decl(self, items: list[Any]) -> ImportNode:
        # items: [IMPORT, STRING] - skip the keyword
        path = items[1] if len(items) > 1 else items[0]
        return ImportNode(path=path)

    # ============================================
    # DFD Elements
    # ============================================

    def flow_endpoint(self, items: list[Any]) -> FlowEndpointNode:
        entity = items[0]
        port = items[1] if len(items) > 1 else None
        return FlowEndpointNode(entity=entity, port=port)

    def external_decl(self, items: list[Any]) -> ExternalNode:
        # items: [EXTERNAL, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return ExternalNode(name=name, body=body)

    def process_decl(self, items: list[Any]) -> ProcessNode:
        # items: [PROCESS, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return ProcessNode(name=name, body=body)

    def datastore_decl(self, items: list[Any]) -> DatastoreNode:
        # items: [DATASTORE, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return DatastoreNode(name=name, body=body)

    def flow_decl(self, items: list[Any]) -> FlowNode:
        # items: [FLOW, IDENTIFIER, flow_endpoint, flow_endpoint, properties?] - skip the keyword
        name = items[1]
        source = items[2]
        target = items[3]
        properties = items[4] if len(items) > 4 else []
        return FlowNode(name=name, source=source, target=target, properties=properties)

    def dfd_body(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def dfd_decl(self, items: list[Any]) -> DFDNode:
        # items: [DFD, IDENTIFIER, ...elements] - skip the keyword
        name = items[1]
        externals = []
        processes = []
        datastores = []
        flows = []

        for item in items[2:]:
            if isinstance(item, ExternalNode):
                externals.append(item)
            elif isinstance(item, ProcessNode):
                processes.append(item)
            elif isinstance(item, DatastoreNode):
                datastores.append(item)
            elif isinstance(item, FlowNode):
                flows.append(item)

        return DFDNode(
            name=name,
            externals=externals,
            processes=processes,
            datastores=datastores,
            flows=flows,
        )

    # ============================================
    # SCD Elements
    # ============================================

    def system_decl(self, items: list[Any]) -> SystemNode:
        # items: [SYSTEM, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return SystemNode(name=name, body=body)

    def scd_external_decl(self, items: list[Any]) -> ExternalNode:
        # Reuse ExternalNode from DFD
        # items: [EXTERNAL, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return ExternalNode(name=name, body=body)

    def scd_datastore_decl(self, items: list[Any]) -> DatastoreNode:
        # Reuse DatastoreNode from DFD
        # items: [DATASTORE, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return DatastoreNode(name=name, body=body)

    def scd_flow_endpoint(self, items: list[Any]) -> str:
        return items[0] if items else ""

    def outbound_arrow(self, items: list[Any]) -> str:
        return "outbound"

    def bidi_arrow(self, items: list[Any]) -> str:
        return "bidirectional"

    def scd_flow_arrow(self, items: list[Any]) -> str:
        return items[0] if items else "outbound"

    def scd_flow_decl(self, items: list[Any]) -> SCDFlowNode:
        # items: [FLOW, IDENTIFIER, source, arrow_direction, target, properties?]
        name = items[1]
        source = items[2]
        arrow = items[3]  # "outbound" or "bidirectional"
        target = items[4]
        properties = items[5] if len(items) > 5 else []

        # Determine direction based on arrow type
        # For "A -> B": direction is "outbound" (from source to target)
        # For "A <-> B": direction is "bidirectional"
        # Actual inbound/outbound relative to system is determined during semantic analysis
        direction: Literal["inbound", "outbound", "bidirectional"] = (
            "bidirectional" if arrow == "bidirectional" else "outbound"
        )

        return SCDFlowNode(
            name=name,
            source=source,
            target=target,
            direction=direction,
            properties=properties,
        )

    def scd_body(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def scd_decl(self, items: list[Any]) -> SCDNode:
        # items: [SCD, IDENTIFIER, ...elements] - skip the keyword
        name = items[1]
        system = None
        externals: list[ExternalNode] = []
        datastores: list[DatastoreNode] = []
        flows: list[SCDFlowNode] = []

        for item in items[2:]:
            if isinstance(item, SystemNode):
                system = item
            elif isinstance(item, ExternalNode):
                externals.append(item)
            elif isinstance(item, DatastoreNode):
                datastores.append(item)
            elif isinstance(item, SCDFlowNode):
                flows.append(item)

        return SCDNode(
            name=name,
            system=system,
            externals=externals,
            datastores=datastores,
            flows=flows,
        )

    # ============================================
    # ERD Elements
    # ============================================

    def pk_constraint(self, items: list[Any]) -> ConstraintNode:
        return ConstraintNode(kind="pk")

    def fk_constraint(self, items: list[Any]) -> ConstraintNode:
        # items: [FK, IDENTIFIER, IDENTIFIER] - skip the FK keyword
        return ConstraintNode(
            kind="fk",
            target_entity=items[1],
            target_attribute=items[2],
        )

    def unique_constraint(self, items: list[Any]) -> ConstraintNode:
        return ConstraintNode(kind="unique")

    def not_null_constraint(self, items: list[Any]) -> ConstraintNode:
        return ConstraintNode(kind="not_null")

    def pattern_constraint(self, items: list[Any]) -> ConstraintNode | FieldConstraintNode:
        # This can be used in both attribute and field contexts
        pattern = items[0] if items else None
        return ConstraintNode(kind="pattern", pattern=pattern)

    def constraint(self, items: list[Any]) -> ConstraintNode:
        return items[0]

    def attribute_constraints(self, items: list[Any]) -> list[ConstraintNode]:
        return list(items)

    def attribute_decl(self, items: list[Any]) -> AttributeNode:
        name = items[0]
        type_name = items[1]
        constraints = items[2] if len(items) > 2 else []
        return AttributeNode(name=name, type_name=type_name, constraints=constraints)

    def entity_body(self, items: list[Any]) -> AttributeNode | PlaceholderNode:
        return items[0] if items else PlaceholderNode()

    def entity_decl(self, items: list[Any]) -> EntityNode:
        # items: [ENTITY, IDENTIFIER, ...attributes] - skip the keyword
        name = items[1]
        attributes = []
        has_placeholder = False

        for item in items[2:]:
            if isinstance(item, AttributeNode):
                attributes.append(item)
            elif isinstance(item, PlaceholderNode):
                has_placeholder = True

        return EntityNode(name=name, attributes=attributes, has_placeholder=has_placeholder)

    def cardinality(self, items: list[Any]) -> CardinalityNode:
        if len(items) == 1:
            # Simple cardinality like -1:n->
            spec = items[0]
            if ":" in spec:
                parts = spec.split(":")
                return CardinalityNode(source=parts[0], target=parts[1])
            return CardinalityNode(source="1", target=spec)
        else:
            # Two specs
            return CardinalityNode(source=items[0], target=items[1])

    def relationship_decl(self, items: list[Any]) -> RelationshipNode:
        # items: [RELATIONSHIP, IDENTIFIER, IDENTIFIER, cardinality, IDENTIFIER, properties?]
        # Skip the keyword
        name = items[1]
        source_entity = items[2]
        cardinality = items[3]
        target_entity = items[4]
        properties = items[5] if len(items) > 5 else []
        return RelationshipNode(
            name=name,
            source_entity=source_entity,
            target_entity=target_entity,
            cardinality=cardinality,
            properties=properties,
        )

    def erd_body(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def erd_decl(self, items: list[Any]) -> ERDNode:
        # items: [ERD, IDENTIFIER, ...elements] - skip the keyword
        name = items[1]
        entities = []
        relationships = []

        for item in items[2:]:
            if isinstance(item, EntityNode):
                entities.append(item)
            elif isinstance(item, RelationshipNode):
                relationships.append(item)

        return ERDNode(name=name, entities=entities, relationships=relationships)

    # ============================================
    # STD Elements
    # ============================================

    def initial_state_decl(self, items: list[Any]) -> tuple[str, str]:
        # items: [INITIAL, IDENTIFIER] - skip the keyword
        return ("initial", items[1])

    def state_decl(self, items: list[Any]) -> StateNode:
        # items: [STATE, IDENTIFIER, block] - skip the keyword
        name = items[1]
        body = items[2] if len(items) > 2 else BlockNode()
        return StateNode(name=name, body=body)

    def transition_decl(self, items: list[Any]) -> TransitionNode:
        # items: [TRANSITION, IDENTIFIER, IDENTIFIER, IDENTIFIER, properties?] - skip the keyword
        name = items[1]
        source = items[2]
        target = items[3]
        properties = items[4] if len(items) > 4 else []
        return TransitionNode(
            name=name,
            source_state=source,
            target_state=target,
            properties=properties,
        )

    def std_body(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def std_decl(self, items: list[Any]) -> STDNode:
        # items: [STD, IDENTIFIER, ...elements] - skip the keyword
        name = items[1]
        initial_state = None
        states = []
        transitions = []

        for item in items[2:]:
            if isinstance(item, tuple) and item[0] == "initial":
                initial_state = item[1]
            elif isinstance(item, StateNode):
                states.append(item)
            elif isinstance(item, TransitionNode):
                transitions.append(item)

        return STDNode(
            name=name,
            initial_state=initial_state,
            states=states,
            transitions=transitions,
        )

    # ============================================
    # Structure Chart Elements
    # ============================================

    def identifier_list(self, items: list[Any]) -> list[str]:
        return list(items)

    def calls_decl(self, items: list[Any]) -> tuple[str, list[str]]:
        # items: [CALLS, identifier_list] - skip the keyword
        return ("calls", items[1] if len(items) > 1 else [])

    def data_couple_decl(self, items: list[Any]) -> tuple[str, str]:
        # items: [DATA_COUPLE, IDENTIFIER] - skip the keyword
        return ("data_couple", items[1] if len(items) > 1 else "")

    def control_couple_decl(self, items: list[Any]) -> tuple[str, str]:
        # items: [CONTROL_COUPLE, IDENTIFIER] - skip the keyword
        return ("control_couple", items[1] if len(items) > 1 else "")

    def module_body(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def module_decl(self, items: list[Any]) -> ModuleNode:
        # items: [MODULE, IDENTIFIER, ...module_body] - skip the keyword
        name = items[1]
        calls: list[str] = []
        data_couples: list[str] = []
        control_couples: list[str] = []
        properties: list[PropertyNode] = []
        has_placeholder = False

        for item in items[2:]:
            if isinstance(item, tuple):
                if item[0] == "calls":
                    calls = item[1]
                elif item[0] == "data_couple":
                    data_couples.append(item[1])
                elif item[0] == "control_couple":
                    control_couples.append(item[1])
            elif isinstance(item, PropertyNode):
                properties.append(item)
            elif isinstance(item, PlaceholderNode):
                has_placeholder = True

        return ModuleNode(
            name=name,
            calls=calls,
            data_couples=data_couples,
            control_couples=control_couples,
            properties=properties,
            has_placeholder=has_placeholder,
        )

    def structure_body(self, items: list[Any]) -> Any:
        return items[0] if items else None

    def structure_decl(self, items: list[Any]) -> StructureNode:
        # items: [STRUCTURE, IDENTIFIER, ...modules] - skip the keyword
        name = items[1]
        modules = [item for item in items[2:] if isinstance(item, ModuleNode)]
        return StructureNode(name=name, modules=modules)

    # ============================================
    # Data Dictionary Elements
    # ============================================

    def optional_constraint(self, items: list[Any]) -> FieldConstraintNode:
        return FieldConstraintNode(kind="optional")

    def min_constraint(self, items: list[Any]) -> FieldConstraintNode:
        return FieldConstraintNode(kind="min", value=items[0])

    def max_constraint(self, items: list[Any]) -> FieldConstraintNode:
        return FieldConstraintNode(kind="max", value=items[0])

    def array_min_constraint(self, items: list[Any]) -> tuple[str, int]:
        return ("min", items[0])

    def array_max_constraint(self, items: list[Any]) -> tuple[str, int]:
        return ("max", items[0])

    def field_constraint(self, items: list[Any]) -> FieldConstraintNode:
        return items[0]

    def field_constraints(self, items: list[Any]) -> list[FieldConstraintNode]:
        return list(items)

    def struct_field(self, items: list[Any]) -> StructFieldNode:
        name = items[0]
        type_name = items[1]
        constraints = items[2] if len(items) > 2 else []
        # Handle case where constraint is a ConstraintNode (from pattern_constraint)
        field_constraints = []
        for c in constraints:
            if isinstance(c, ConstraintNode):
                field_constraints.append(
                    FieldConstraintNode(kind=c.kind, value=c.pattern)  # type: ignore[arg-type]
                )
            else:
                field_constraints.append(c)
        return StructFieldNode(name=name, type_name=type_name, constraints=field_constraints)

    def struct_def(self, items: list[Any]) -> StructDefNode:
        fields = [item for item in items if isinstance(item, StructFieldNode)]
        return StructDefNode(fields=fields)

    def union_first(self, items: list[Any]) -> str:
        return items[0] if items else ""

    def union_alt(self, items: list[Any]) -> str:
        return items[0] if items else ""

    def union_def(self, items: list[Any]) -> UnionDefNode:
        return UnionDefNode(alternatives=list(items))

    def array_element_type(self, items: list[Any]) -> str:
        return items[0] if items else "unknown"

    def array_def(self, items: list[Any]) -> ArrayDefNode:
        element_type = items[0]
        min_length = None
        max_length = None

        for item in items[1:]:
            if isinstance(item, tuple):
                if item[0] == "min":
                    min_length = item[1]
                elif item[0] == "max":
                    max_length = item[1]

        return ArrayDefNode(element_type=element_type, min_length=min_length, max_length=max_length)

    def array_constraints(self, items: list[Any]) -> list[tuple[str, int]]:
        return list(items)

    def simple_type_ref(self, items: list[Any]) -> TypeRefNode:
        # Can be a base type name or identifier
        name = items[0] if items else "unknown"
        return TypeRefNode(name=name)

    def data_definition(self, items: list[Any]) -> Any:
        return items[0] if items else PlaceholderNode()

    def datadef_decl(self, items: list[Any]) -> DataDefNode:
        name = items[0]
        definition = items[1] if len(items) > 1 else PlaceholderNode()
        return DataDefNode(name=name, definition=definition)

    def datadict_body(self, items: list[Any]) -> DataDefNode:
        return items[0]

    def datadict_decl(self, items: list[Any]) -> DataDictNode:
        definitions = [item for item in items if isinstance(item, DataDefNode)]
        return DataDictNode(definitions=definitions)

    # ============================================
    # Document
    # ============================================

    def declaration(self, items: list[Any]) -> ASTNode:
        return items[0]

    def start(self, items: list[Any]) -> DocumentNode:
        imports = []
        scds = []
        dfds = []
        erds = []
        stds = []
        structures = []
        datadicts = []

        for item in items:
            if isinstance(item, ImportNode):
                imports.append(item)
            elif isinstance(item, SCDNode):
                scds.append(item)
            elif isinstance(item, DFDNode):
                dfds.append(item)
            elif isinstance(item, ERDNode):
                erds.append(item)
            elif isinstance(item, STDNode):
                stds.append(item)
            elif isinstance(item, StructureNode):
                structures.append(item)
            elif isinstance(item, DataDictNode):
                datadicts.append(item)

        return DocumentNode(
            imports=imports,
            scds=scds,
            dfds=dfds,
            erds=erds,
            stds=stds,
            structures=structures,
            datadicts=datadicts,
        )


# Create the Lark parser instance
def _create_parser() -> Lark:
    """Create a Lark parser for the DesignIt grammar."""
    grammar_text = GRAMMAR_PATH.read_text()
    return Lark(
        grammar_text,
        start="start",
        parser="lalr",
        lexer="basic",
        transformer=DesignItTransformer(),
        propagate_positions=True,
    )


# Global parser instance (lazy loaded)
_parser: Lark | None = None


def _get_parser() -> Lark:
    """Get or create the global parser instance."""
    global _parser
    if _parser is None:
        _parser = _create_parser()
    return _parser


def parse_string(source: str, filename: str | None = None) -> DocumentNode:
    """Parse a DesignIt source string into an AST.

    Args:
        source: The source code to parse.
        filename: Optional filename for error messages.

    Returns:
        The root DocumentNode of the AST.

    Raises:
        ParseError: If parsing fails.
    """
    parser = _get_parser()
    try:
        result = parser.parse(source)
        if isinstance(result, DocumentNode):
            return result
        # Should not happen with our transformer
        raise ParseError("Parser did not return a DocumentNode")
    except UnexpectedInput as e:
        raise ParseError(
            message=str(e),
            line=e.line,
            column=e.column,
        ) from e


def parse_file(filepath: str | Path) -> DocumentNode:
    """Parse a DesignIt file into an AST.

    Args:
        filepath: Path to the .dit file.

    Returns:
        The root DocumentNode of the AST.

    Raises:
        ParseError: If parsing fails.
        FileNotFoundError: If the file doesn't exist.
    """
    path = Path(filepath)
    source = path.read_text()
    doc = parse_string(source, filename=str(path))
    # Set file location on the document
    if doc.location:
        doc.location.file = str(path)
    return doc
