# DesignIt Requirements

This document specifies the detailed requirements for the DesignIt DSL project. Requirements are organized by functional area and include acceptance criteria and implementation references.

**Status Legend:**
- [DONE] - Fully implemented and tested
- [PARTIAL] - Partially implemented
- [TODO] - Not yet implemented

---

## 1. DSL Grammar & Parsing

### 1.1 File Format

#### REQ-GRAM-001: File Extension [DONE]
DesignIt files shall use the `.dit` file extension.

**Acceptance Criteria:**
- Parser accepts files with `.dit` extension
- CLI commands work with `.dit` files
- IDE extensions recognize `.dit` files

**Implementation:** `src/designit/parser/parser.py:parse_file()`

---

#### REQ-GRAM-002: Comments [DONE]
The DSL shall support line comments and block comments.

**Acceptance Criteria:**
- Line comments start with `//` and continue to end of line
- Block comments start with `/*` and end with `*/`
- Comments are ignored during parsing
- Nested block comments are not supported

**Implementation:** `src/designit/grammar/designit.lark` (COMMENT, BLOCK_COMMENT terminals)

---

#### REQ-GRAM-003: Import Statements [DONE]
The DSL shall support importing other `.dit` files to enable multi-file projects.

**Acceptance Criteria:**
- Import syntax: `import "path/to/file.dit"`
- Relative paths resolved from importing file's directory
- Absolute paths supported
- Circular imports detected and reported as errors
- Imported definitions merged into single document model

**Implementation:** `src/designit/semantic/resolver.py:ImportResolver`

---

### 1.2 Diagram Types

#### REQ-GRAM-005: System Context Diagrams (SCD) [DONE]
The DSL shall support System Context Diagram definitions using the `scd` keyword. The SCD is the top-level diagram in Structured Analysis that depicts the system in its context.

**Acceptance Criteria:**
- SCD declared with `scd Name { ... }`
- Support for system declaration: `system Name { ... }` (required, exactly one per SCD)
- Support for external entities: `external Name { ... }`
- Support for data stores: `datastore Name { ... }`
- Support for directional data flows with arrow notation:
  - Inbound: `flow Name: External -> System`
  - Outbound: `flow Name: System -> External`
  - Bidirectional: `flow Name: External <-> System`
- Elements support property blocks with key-value pairs

**Example:**
```
scd OrderProcessing {
    system OrderSystem { description: "Processes customer orders" }
    
    external Customer { description: "Places orders" }
    external PaymentGateway { description: "Handles payments" }
    datastore OrderDB { description: "Order storage" }
    
    flow OrderRequest: Customer -> OrderSystem
    flow Confirmation: OrderSystem -> Customer
    flow PaymentData: OrderSystem <-> PaymentGateway
    flow OrderData: OrderSystem -> OrderDB
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (scd_decl, system_decl, scd_flow_decl)
- AST: `src/designit/parser/ast_nodes.py` (SCDNode, SystemNode, SCDFlowNode)
- Model: `src/designit/model/scd.py`

---

#### REQ-GRAM-010: Data Flow Diagrams (DFD) [DONE]
The DSL shall support Data Flow Diagram definitions using the `dfd` keyword.

**Acceptance Criteria:**
- DFD declared with `dfd Name { ... }`
- Support for external entities: `external Name { ... }`
- Support for processes: `process Name { ... }`
- Support for data stores: `datastore Name { ... }`
- Support for data flows: `flow Name: Source -> Target`
- Flow endpoints can specify ports: `Entity.port`
- Elements support property blocks with key-value pairs

**Example:**
```
dfd OrderSystem {
    external Customer { description: "Places orders" }
    process ValidateOrder { description: "Validates order data" }
    datastore OrderDB { description: "Order records" }
    flow OrderData: Customer -> ValidateOrder
    flow SaveOrder: ValidateOrder -> OrderDB
}
```

**Implementation:** 
- Grammar: `src/designit/grammar/designit.lark` (dfd_def, external_def, process_def, datastore_def, flow_def)
- AST: `src/designit/parser/ast_nodes.py` (DFDNode, ExternalNode, ProcessNode, DatastoreNode, FlowNode)
- Model: `src/designit/model/dfd.py`

---

#### REQ-GRAM-020: Entity-Relationship Diagrams (ERD) [DONE]
The DSL shall support Entity-Relationship Diagram definitions using the `erd` keyword.

**Acceptance Criteria:**
- ERD declared with `erd Name { ... }`
- Support for entities: `entity Name { ... }`
- Entities contain typed attributes: `attribute_name: type`
- Attributes support constraints in brackets: `[pk]`, `[unique]`, `[not null]`
- Foreign key constraints: `[fk -> Entity.attribute]`
- Pattern constraints: `[pattern: "regex"]`
- Support for relationships: `relationship Name: Entity1 -cardinality-> Entity2`
- Cardinality notation: `1:1`, `1:n`, `n:n`, `0..1:n`, `0..1:0..1`, etc.

**Example:**
```
erd UserModel {
    entity User {
        id: integer [pk]
        email: string [unique, not null]
        created_at: datetime
    }
    entity Profile {
        id: integer [pk]
        user_id: integer [fk -> User.id]
        bio: string
    }
    relationship has_profile: User -1:1-> Profile
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (erd_def, entity_def, attribute_def, relationship_def)
- AST: `src/designit/parser/ast_nodes.py` (ERDNode, EntityNode, AttributeNode, RelationshipNode, CardinalityNode, ConstraintNode)
- Model: `src/designit/model/erd.py`

---

#### REQ-GRAM-030: State Transition Diagrams (STD) [DONE]
The DSL shall support State Transition Diagram definitions using the `std` keyword.

**Acceptance Criteria:**
- STD declared with `std Name { ... }`
- Initial state declaration: `initial: StateName`
- State definitions: `state Name { ... }`
- Transition definitions: `transition Name: SourceState -> TargetState { ... }`
- Transitions support properties: `trigger`, `guard`, `action`

**Example:**
```
std OrderLifecycle {
    initial: Draft
    state Draft { description: "Order being prepared" }
    state Submitted { description: "Order submitted" }
    state Cancelled { description: "Order cancelled" }
    transition submit: Draft -> Submitted {
        trigger: "customer_submits"
        guard: "order_valid"
    }
    transition cancel: Draft -> Cancelled {
        trigger: "customer_cancels"
    }
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (std_def, initial_state, state_def, transition_def)
- AST: `src/designit/parser/ast_nodes.py` (STDNode, StateNode, TransitionNode)
- Model: `src/designit/model/std.py`

---

#### REQ-GRAM-040: Structure Charts [DONE]
The DSL shall support Structure Chart definitions using the `structure` keyword.

**Acceptance Criteria:**
- Structure chart declared with `structure Name { ... }`
- Module definitions: `module Name { ... }`
- Module calls: `calls: [Module1, Module2, ...]`
- Data coupling: `data_couple: DataName`
- Control coupling: `control_couple: FlagName`
- Modules support description and other properties

**Example:**
```
structure PaymentProcessor {
    module Main {
        description: "Entry point"
        calls: [Initialize, ProcessPayments]
    }
    module Initialize {
        calls: [LoadConfig]
        data_couple: ConfigData
    }
    module LoadConfig {
        data_couple: ConfigFile
        control_couple: LoadStatus
    }
    module ProcessPayments {
        description: "Main processing loop"
    }
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (structure_def, module_def)
- AST: `src/designit/parser/ast_nodes.py` (StructureNode, ModuleNode)
- Model: `src/designit/model/structure.py`

---

#### REQ-GRAM-050: Data Dictionary [DONE]
The DSL shall support Data Dictionary definitions using the `datadict` keyword.

**Acceptance Criteria:**
- Data dictionary declared with `datadict { ... }`
- Type definitions: `TypeName = definition`
- Struct types: `{ field1: type1, field2: type2, ... }`
- Struct fields are separated by commas (required)
- Trailing commas in structs are not allowed
- Empty structs are valid: `{ }`
- Union types come in two mutually exclusive forms:
  - **Enum literals**: `"literal1" | "literal2"` - quoted strings representing discrete values
  - **Type unions**: `TypeA | TypeB` - unquoted identifiers representing a choice between types
  - Mixing quoted and unquoted alternatives in a single union is not allowed
- Array types: `ElementType[]` with optional constraints `[min: N, max: M]`
- Type references: `OtherTypeName`
- Field constraints: `optional`, `pattern: "regex"`, `min: N`, `max: N`

**Example:**
```
datadict {
    // Enum literals (quoted strings)
    OrderStatus = "draft" | "submitted" | "shipped" | "delivered"
    
    // Type union (unquoted identifiers)
    PaymentMethod = CreditCard | BankTransfer | Cash
    
    Address = {
        street: string,
        city: string,
        postal_code: string [pattern: "[0-9]{5}"],
        country: string
    }
    
    Money = {
        amount: decimal [min: 0],
        currency: string [pattern: "[A-Z]{3}"]
    }
    
    // Single-line struct
    Point = { x: integer, y: integer }
    
    // Empty struct
    Placeholder = { }
    
    OrderItems = OrderItem[] [min: 1, max: 100]
    
    // Type alias
    Currency = string
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (datadict_def, data_def, struct_def, union_def, array_def)
- AST: `src/designit/parser/ast_nodes.py` (DataDictNode, DataDefNode, StructDefNode, UnionDefNode, ArrayDefNode, TypeRefNode, StructFieldNode, FieldConstraintNode)
- Model: `src/designit/model/datadict.py`

---

#### REQ-GRAM-051: Named Data Dictionary [DONE]
The DSL shall support optional names for datadict blocks that serve as namespaces.

**Acceptance Criteria:**
- Anonymous syntax (existing): `datadict { ... }`
- Named syntax (new): `datadict NamespaceName { ... }`
- Namespace name follows identifier rules
- Multiple datadict blocks with the same name are merged
- Multiple anonymous datadict blocks are merged

**Example:**
```
// Anonymous datadict - types usable without qualification
datadict {
    Money = { amount: decimal, currency: string }
}

// Named datadict - types must be qualified as PaymentGateway.X
datadict PaymentGateway {
    GetStatusRequest = { transaction_id: string }
    GetStatusResponse = { status: string, amount: Money }
}

// Same namespace in another block (merged)
datadict PaymentGateway {
    RefundRequest = { transaction_id: string, reason: string }
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (datadict_decl with optional IDENTIFIER)
- AST: `src/designit/parser/ast_nodes.py` (DataDictNode.namespace)
- Parser: `src/designit/parser/parser.py` (datadict_decl transformer)

---

#### REQ-GRAM-052: Qualified Type References in Flows [DONE]
Flow declarations shall support qualified type references using dot notation.

**Acceptance Criteria:**
- Unqualified syntax (existing): `flow TypeName: Source -> Target`
- Qualified syntax (new): `flow Namespace.TypeName: Source -> Target`
- Applies to SCD flows and DFD flows (all variants: internal, inbound, outbound)

**Example:**
```
scd BankingContext {
    system BankingSystem { ... }
    external PaymentGw { ... }
    
    // Unqualified - references anonymous datadict type
    flow Money: BankingSystem -> SomeProcess
    
    // Qualified - references namespaced type
    flow PaymentGateway.GetStatusRequest: BankingSystem -> PaymentGw
    flow PaymentGateway.GetStatusResponse: PaymentGw -> BankingSystem
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (flow_type_ref rule)
- AST: `src/designit/parser/ast_nodes.py` (FlowTypeRef model)
- Parser: `src/designit/parser/parser.py` (flow declaration transformers)

---

### 1.3 Data Types & Constraints

#### REQ-GRAM-100: Built-in Data Types [DONE]
The DSL shall support a set of built-in data types for entity attributes and data dictionary fields.

**Acceptance Criteria:**
- `string` - Text data
- `integer` - Whole numbers
- `decimal` - Decimal numbers
- `boolean` - True/false values
- `datetime` - Date and time combined
- `date` - Date only
- `time` - Time only
- `binary` - Binary data

**Implementation:** `src/designit/grammar/designit.lark` (TYPE terminal), `src/designit/lsp/server.py` (TYPE_COMPLETIONS)

---

#### REQ-GRAM-101: Attribute Constraints [DONE]
Entity attributes shall support constraints specified in square brackets.

**Acceptance Criteria:**
- `pk` - Primary key constraint
- `fk -> Entity.attribute` - Foreign key reference
- `unique` - Unique value constraint
- `not null` - Required (non-nullable) constraint
- `pattern: "regex"` - Regular expression pattern validation
- Multiple constraints can be combined: `[pk, not null]`

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (constraint, fk_constraint, pattern_constraint)
- AST: `src/designit/parser/ast_nodes.py` (ConstraintNode)

---

#### REQ-GRAM-102: Field Constraints [DONE]
Data dictionary struct fields shall support constraints specified in square brackets.

**Acceptance Criteria:**
- `optional` - Field is not required
- `min: N` - Minimum value (numbers) or length (arrays)
- `max: N` - Maximum value or length
- `pattern: "regex"` - Regular expression pattern validation
- Multiple constraints can be combined: `[optional, min: 0, max: 100]`

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (field_constraint)
- AST: `src/designit/parser/ast_nodes.py` (FieldConstraintNode)

---

### 1.4 Placeholders

#### REQ-GRAM-200: Placeholder Support [DONE]
The DSL shall support placeholders for incomplete sections during iterative design.

**Acceptance Criteria:**
- `...` (ellipsis) marks a section as incomplete
- `TBD` keyword marks a section as "to be determined"
- Placeholders valid in any block body
- Placeholders valid as type definitions in data dictionary
- Placeholders tracked and reportable via CLI
- Placeholders rendered with distinct styling in generated diagrams

**Example:**
```
dfd IncompleteSystem {
    process PaymentGateway {
        ...  // Details to be added
    }
    process ShippingIntegration {
        TBD
    }
}

datadict {
    FutureFeature = TBD
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (placeholder)
- AST: `src/designit/parser/ast_nodes.py` (PlaceholderNode)
- CLI: `src/designit/cli.py` (placeholders command)

---

## 2. Semantic Analysis

### 2.1 AST to Model Transformation

#### REQ-SEM-001: Semantic Model Construction [DONE]
The system shall transform the parsed AST into a rich semantic model.

**Acceptance Criteria:**
- AST nodes converted to semantic model objects
- Properties extracted and stored in model
- Placeholder nodes tracked in model
- Source location information preserved
- Model suitable for validation and code generation

**Implementation:** `src/designit/semantic/analyzer.py:SemanticAnalyzer`

---

#### REQ-SEM-002: Validation Message Source Location [DONE]
All validation messages shall include accurate source location information.

**Acceptance Criteria:**
- Validation ERROR messages include line number of the problematic element
- Validation WARNING messages include line number of the problematic element
- Line numbers are derived from AST node locations captured during parsing
- LSP diagnostics point to the correct source line (0-based indexing)
- Multiple validation errors on different lines have distinct line numbers

**Implementation:**
- Parser: `src/designit/parser/parser.py` (transformer methods must set location)
- Validator: `src/designit/semantic/validator.py` (passes location to messages)
- LSP: `src/designit/lsp/server.py:_get_diagnostics()` (converts to LSP range)

---

### 2.2 Validation Rules

#### REQ-SEM-005: SCD System Validation [DONE]
Each SCD shall have exactly one system declaration.

**Acceptance Criteria:**
- ERROR if no system is declared in SCD
- ERROR if more than one system is declared in SCD

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_scds()`

---

#### REQ-SEM-006: SCD Flow Endpoint Validation [DONE]
SCD flow endpoints shall reference existing elements.

**Acceptance Criteria:**
- ERROR if flow source references non-existent element
- ERROR if flow target references non-existent element
- Valid endpoints: system, externals, datastores

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_scds()`

---

#### REQ-SEM-007: SCD Orphan Element Warning [DONE]
Elements not connected by any flow shall generate a warning.

**Acceptance Criteria:**
- WARNING if external has no incoming or outgoing flows
- WARNING if datastore has no incoming or outgoing flows

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_scds()`

---

#### REQ-SEM-010: DFD Flow Endpoint Validation [DONE]
Data flow endpoints shall be validated to reference existing elements.

**Acceptance Criteria:**
- ERROR if flow source references non-existent element
- ERROR if flow target references non-existent element
- Valid endpoints: externals, processes, datastores

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfds()`

---

#### REQ-SEM-011: DFD Orphan Element Warning [DONE]
Elements not connected by any flow shall generate a warning.

**Acceptance Criteria:**
- WARNING if external has no incoming or outgoing flows
- WARNING if process has no incoming or outgoing flows
- WARNING if datastore has no incoming or outgoing flows

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfds()`

---

#### REQ-SEM-020: ERD Relationship Entity Validation [DONE]
Relationships shall reference existing entities.

**Acceptance Criteria:**
- ERROR if relationship source entity does not exist
- ERROR if relationship target entity does not exist

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_erds()`

---

#### REQ-SEM-021: ERD Foreign Key Validation [DONE]
Foreign key constraints shall reference existing entities.

**Acceptance Criteria:**
- ERROR if FK target entity does not exist
- ERROR if FK target attribute does not exist in target entity

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_erds()`

---

#### REQ-SEM-022: ERD Primary Key Warning [DONE]
Entities without a primary key shall generate a warning.

**Acceptance Criteria:**
- WARNING if entity has no attribute with `pk` constraint
- Warning includes entity name and ERD name

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_erds()`

---

#### REQ-SEM-030: STD Transition State Validation [DONE]
Transitions shall reference existing states.

**Acceptance Criteria:**
- ERROR if transition source state does not exist
- ERROR if transition target state does not exist

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_stds()`

---

#### REQ-SEM-031: STD Initial State Validation [DONE]
The declared initial state shall exist.

**Acceptance Criteria:**
- ERROR if initial state references non-existent state
- Validation message includes STD name

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_stds()`

---

#### REQ-SEM-032: STD Unreachable State Warning [DONE]
States not reachable from the initial state shall generate a warning.

**Acceptance Criteria:**
- WARNING for each state not reachable via transitions from initial state
- Reachability computed via graph traversal

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_stds()`

---

#### REQ-SEM-040: Structure Chart Call Validation [DONE]
Module calls shall reference existing modules.

**Acceptance Criteria:**
- ERROR if called module does not exist in structure chart

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_structures()`

---

#### REQ-SEM-041: Structure Chart Cycle Warning [DONE]
Cyclic call chains shall generate a warning.

**Acceptance Criteria:**
- WARNING if module call graph contains cycles
- Cycle detection via depth-first search

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_structures()`

---

#### REQ-SEM-050: Data Dictionary Type Reference Validation [DONE]
Type references in struct fields, array element types, and type aliases shall reference existing types or built-in types.

**Acceptance Criteria:**
- WARNING if referenced type not defined in data dictionary
- Built-in types (string, integer, etc.) are always valid
- Applies to: struct field types, array element types, type aliases

Note: Type union validation is covered by REQ-SEM-069.

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_datadict()`

---

#### REQ-SEM-061: SCD Flow Data Dictionary Validation [DONE]
SCD flow names shall be validated against the data dictionary.

**Acceptance Criteria:**
- ERROR if SCD flow name is not defined in data dictionary
- Error message format: `Flow '<flow_name>' in SCD '<scd_name>' is not defined in data dictionary`
- Error includes source file and line number of the flow definition
- Validation applies regardless of whether data dictionary is empty or absent

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_cross_references()`

---

#### REQ-SEM-062: DFD Flow Data Dictionary Validation [DONE]
DFD flow names shall be validated against the data dictionary with ERROR severity.

**Acceptance Criteria:**
- ERROR if DFD flow name is not defined in data dictionary
- Error message format: `Flow '<flow_name>' in DFD '<dfd_name>' is not defined in data dictionary`
- Error includes source file and line number of the flow definition
- Consistent with SCD flow validation (REQ-SEM-061)

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_cross_references()`

---

#### REQ-SEM-063: Namespaced Type Qualification Requirement [DONE]
Types defined in named datadicts shall always require qualification when referenced in flows.

**Acceptance Criteria:**
- ERROR if unqualified name references a type that exists only in named datadict(s)
- Error message suggests the qualified name(s): `"Flow 'X' must be qualified. Did you mean: Namespace.X?"`
- Unqualified references to anonymous datadict types remain valid
- Qualified references to namespaced types are valid

**Example:**
```
datadict PaymentGateway {
    Request = { id: string }
}

// ERROR: "Flow 'Request' must be qualified. Did you mean: PaymentGateway.Request?"
flow Request: System -> Gateway

// OK
flow PaymentGateway.Request: System -> Gateway
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_cross_references()`

---

#### REQ-SEM-064: Cross-Namespace Reference Restriction [DONE]
Types in named datadicts shall only reference types from the same namespace or from anonymous datadicts.

**Acceptance Criteria:**
- OK if a namespaced type references another type in the same namespace
- OK if a namespaced type references an anonymous type
- OK if a namespaced type references built-in types
- ERROR if a namespaced type references a type from a different namespace

**Example:**
```
datadict {
    Money = { amount: decimal, currency: string }  // Anonymous
}

datadict PaymentGateway {
    Request = { 
        amount: Money       // OK: references anonymous type
        status: string      // OK: built-in type
    }
    
    ExtendedRequest = {
        base: Request       // OK: references same namespace
        extra: string
    }
}

datadict OrderService {
    Request = {
        payment: PaymentGateway.Request  // ERROR: cannot reference different namespace
    }
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_datadict()`

---

#### REQ-SEM-065: Datadict Namespace Merging [DONE]
Multiple datadict blocks with the same name (or multiple anonymous blocks) shall be merged.

**Acceptance Criteria:**
- Definitions from all blocks with same namespace are combined
- ERROR if duplicate type name within same namespace (across blocks)
- Merging works across imported files
- Order of definition does not matter

**Example:**
```
datadict PaymentGateway {
    Request = { id: string }
}

datadict PaymentGateway {
    Response = { status: string }  // OK: merged with above
    Request = { ... }              // ERROR: duplicate in namespace
}
```

**Implementation:**
- `src/designit/semantic/analyzer.py`
- `src/designit/semantic/resolver.py`

---

#### REQ-SEM-066: Namespace Shadowing Warning [DONE]
When a datadict namespace name matches a global (anonymous) type name, a WARNING shall be emitted.

**Acceptance Criteria:**
- WARNING when namespace name equals a global type name
- Message includes both the namespace name and the conflicting global type's location
- Does not prevent compilation, only warns about potential ambiguity

**Example:**
```
datadict {
    Request = { id: string }      // Global type "Request"
}

datadict Request {                // WARNING: shadows global type
    Payload = { data: string }
}
```

**Warning message:**
`Namespace 'Request' shadows global type 'Request' (defined at file.dit:3). Use qualified references to avoid ambiguity.`

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_namespace_shadowing()`

---

#### REQ-SEM-067: Type Resolution with Namespace-First Lookup [DONE]
When resolving type references within namespaced datadicts, the same namespace shall be searched first before falling back to global types.

**Acceptance Criteria:**
- For simple type reference `X` within namespace `N`:
  1. First look for `N.X` (same namespace)
  2. Then look for `X` (global/anonymous type)
- For qualified type reference `A.B`:
  - Always resolve to `A.B` exactly (no fallback)
- If not found: ERROR for undefined type

**Example:**
```
datadict {
    Common = { id: string }
}

datadict ServiceA {
    Request = { data: string }
    Response = {
        req: Request     // Resolves to ServiceA.Request (same namespace first)
        common: Common   // Resolves to global Common (not in ServiceA)
    }
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._resolve_type_ref()`

---

#### REQ-SEM-068: Union Type Consistency
Union types shall not mix enum literals with type references.

**Acceptance Criteria:**
- ERROR if a union contains both quoted strings (enum literals) and unquoted identifiers (type references)
- Pure enum unions (all quoted): valid
- Pure type unions (all unquoted): valid
- Mixed unions: error
- Error message: `Union type 'X' mixes enum literals with type references`

**Example:**
```
datadict {
    // Valid: pure enum literals
    Status = "pending" | "approved" | "rejected"
    
    // Valid: pure type union
    PaymentMethod = CreditCard | BankTransfer | Cash
    
    // Invalid: mixed
    Invalid = "pending" | SomeType  // ERROR
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_datadict()`

---

#### REQ-SEM-069: Union Type Reference Validation
Type references in union types shall be validated against existing types.

**Acceptance Criteria:**
- ERROR if a type union references an undefined type
- Built-in types (string, integer, etc.) in unions are always valid
- Enum literals (quoted strings) are not validated as type references
- All union alternatives must be resolvable for flow type decomposition (REQ-SEM-090) to work

**Example:**
```
datadict {
    // ERROR: 'UndefinedType' is not defined
    Result = Success | UndefinedType
    
    // No error: built-in types are valid
    Value = string | integer
    
    // No error: enum literals are not type references
    Status = "active" | "inactive"
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_datadict()`

---

#### REQ-SEM-070: Placeholder Reporting [DONE]
All placeholders shall be reported as informational messages.

**Acceptance Criteria:**
- INFO message for each placeholder found
- Message includes location and context (diagram name, element name)

**Implementation:** `src/designit/semantic/validator.py:Validator._report_placeholders()`

---

### 2.2.1 DFD Hierarchical Decomposition

#### REQ-SEM-080: DFD Refinement Declaration [DONE]
Every DFD shall declare what parent element it refines using the `refines` keyword.

**Acceptance Criteria:**
- Syntax: `dfd Name { refines: DiagramName.ElementName ... }`
- Parent element must be either a `system` in an SCD or a `process` in another DFD
- ERROR (parse-time) if DFD does not have a `refines` declaration
- `refines` declaration must appear at the start of the DFD body

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark`
- AST: `src/designit/parser/ast_nodes.py`
- Parser: `src/designit/parser/parser.py`

---

#### REQ-SEM-081: Refinement Parent Resolution [DONE]
The parent reference in a `refines` declaration shall be resolved and validated.

**Acceptance Criteria:**
- ERROR if referenced diagram does not exist
- ERROR if referenced element does not exist in diagram
- ERROR if element type is not refinable (only `system` and `process` are refinable)
- Resolution works across imports

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-082: Refinement Inbound Flow Coverage [DONE]
Each inbound flow to the parent element must be handled by exactly one process in the child DFD.

**Acceptance Criteria:**
- ERROR if an inbound parent flow is not handled by any process
- ERROR if an inbound parent flow is handled by multiple processes
- Flow matching is by name
- Inbound boundary flow syntax: `flow Name: -> ProcessName`

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-083: Refinement Outbound Flow Coverage [DONE]
Each outbound flow from the parent element may be handled by zero or more processes in the child DFD.

**Acceptance Criteria:**
- Outbound flows MAY originate from zero, one, or multiple processes (all valid)
- No ERROR for unused outbound flows
- Flow matching is by name
- Outbound boundary flow syntax: `flow Name: ProcessName ->`

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-084: DFD Boundary Flow Syntax [DONE]
DFDs shall support boundary flows with a single endpoint.

**Acceptance Criteria:**
- Inbound boundary flow: `flow Name: -> Endpoint`
- Outbound boundary flow: `flow Name: Endpoint ->`
- Endpoint must be a process or local datastore within the DFD
- Boundary flow name must match a flow in the parent diagram
- Flow direction must be consistent with parent (inbound in parent = inbound in child)
- Bidirectional parent flows can be decomposed into separate inbound and outbound boundary flows

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark`
- AST: `src/designit/parser/ast_nodes.py`
- Validator: `src/designit/semantic/validator.py`

---

#### REQ-SEM-085: DFD Local Datastores [DONE]
DFDs may declare local datastores that are internal to that abstraction level.

**Acceptance Criteria:**
- Local datastore syntax: `datastore Name { ... }`
- Local datastore name must not conflict with any element in the parent tree
- Local datastores are accessible to child DFDs that refine processes in this DFD
- Flows to/from local datastores are internal flows (both endpoints specified)

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-086: DFD Datastore Inheritance [DONE]
Child DFDs can reference datastores from the entire parent tree via boundary flows.

**Acceptance Criteria:**
- SCD datastores are accessible as boundary elements to all descendant DFDs
- Ancestor DFD local datastores are accessible to descendant DFDs
- Access is via boundary flow syntax (datastore not declared in child, just referenced in flow)
- Flow name must match a flow in an ancestor that connects to that datastore

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-087: No Duplicate Element Names [DONE]
Element names must be unique across the entire import tree.

**Acceptance Criteria:**
- ERROR if two elements share the same name in the merged document
- Applies to: systems, externals, datastores, processes
- Prevents ambiguity when referencing elements across diagrams

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_unique_names()`

---

#### REQ-SEM-088: DFD Contains No External Entities [DONE]
DFDs shall not declare external entities.

**Acceptance Criteria:**
- ERROR (parse-time) if a DFD contains an `external` declaration
- External entities exist only at the SCD level
- DFD boundary flows implicitly connect to parent's externals

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (remove external_decl from dfd_body)

---

#### REQ-SEM-089: Datadict Type Name Conflicts [DONE]
Datadict type names must not conflict with diagram element names.

**Acceptance Criteria:**
- Anonymous datadict types must not share names with any: system, external, datastore, process
- Namespaced datadict types must not share names with elements in same-named SCD or DFD
- Datadict namespace names are allowed to match SCD/DFD/external names (for terminator interfaces and DFD-specific types)
- Severity: ERROR

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_datadict_name_conflicts()`

---

#### REQ-SEM-090: Flow Type Decomposition in Refinements
When a parent flow has a union type, the child DFD may decompose that flow into separate flows for each union alternative (subtype) instead of using the parent type directly.

**Acceptance Criteria:**
- Child DFD may use parent flow type directly (existing behavior)
- Child DFD may use all subtypes of a union type instead of the parent type
- If decomposition is used, ALL subtypes must be covered (for inbound flows)
- Subtypes follow the same coverage rules as parent types:
  - Inbound subtypes: exactly one process must handle each (per REQ-SEM-082)
  - Outbound subtypes: zero or more processes may handle each (per REQ-SEM-083)
- Decomposition applies equally to inbound, outbound, and bidirectional flows

**Example:**
```
datadict {
    CreditCard = { number: string }
    BankTransfer = { iban: string }
    Cash = { amount: decimal }
    PaymentMethod = CreditCard | BankTransfer | Cash
}

scd Context {
    system PaymentSystem {}
    external Customer {}
    flow PaymentMethod: Customer -> PaymentSystem
}

// Valid: using parent type directly
dfd DirectUse {
    refines: Context.PaymentSystem
    process HandlePayment {}
    flow PaymentMethod: -> HandlePayment
}

// Valid: decomposed into all subtypes
dfd Decomposed {
    refines: Context.PaymentSystem
    process ProcessCards {}
    process ProcessBank {}
    process ProcessCash {}
    flow CreditCard: -> ProcessCards
    flow BankTransfer: -> ProcessBank
    flow Cash: -> ProcessCash
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-091: Flow Type Decomposition Mixing Prohibition
A child DFD shall not mix a parent flow type with its subtypes in the same refinement.

**Acceptance Criteria:**
- ERROR if child uses both parent type AND any of its subtypes
- Error message: `Flow type 'X' cannot be mixed with its subtype 'Y' in refinement of 'Parent.Element'`
- This applies at each level of union nesting

**Example:**
```
datadict {
    CreditCard = { number: string }
    BankTransfer = { iban: string }
    PaymentMethod = CreditCard | BankTransfer
}

scd Context {
    system PaymentSystem {}
    external Customer {}
    flow PaymentMethod: Customer -> PaymentSystem
}

// ERROR: mixes parent type with subtype
dfd InvalidMixed {
    refines: Context.PaymentSystem
    process HandleAll {}
    process HandleCards {}
    flow PaymentMethod: -> HandleAll    // Uses parent type
    flow CreditCard: -> HandleCards     // AND uses subtype - ERROR
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

#### REQ-SEM-092: Nested Union Type Decomposition
When decomposing a union type, the child DFD may stop at any level of the union hierarchy, but must not mix levels within the same parent type.

**Acceptance Criteria:**
- Decomposition may stop at intermediate union types (not required to go to leaf types)
- All alternatives at the chosen level must be covered (for inbound flows)
- Mixing levels within the same parent flow is an error (per REQ-SEM-091)

**Example:**
```
datadict {
    CreditCard = { number: string }
    DebitCard = { number: string }
    CardPayment = CreditCard | DebitCard
    BankTransfer = { iban: string }
    PaymentMethod = CardPayment | BankTransfer
}

scd Context {
    system PaymentSystem {}
    external Customer {}
    flow PaymentMethod: Customer -> PaymentSystem
}

// Valid: decompose to first level (CardPayment, BankTransfer)
dfd Level1 {
    refines: Context.PaymentSystem
    process ProcessCards {}
    process ProcessBank {}
    flow CardPayment: -> ProcessCards
    flow BankTransfer: -> ProcessBank
}

// Valid: decompose to leaf level (CreditCard, DebitCard, BankTransfer)
dfd LeafLevel {
    refines: Context.PaymentSystem
    process ProcessCredit {}
    process ProcessDebit {}
    process ProcessBank {}
    flow CreditCard: -> ProcessCredit
    flow DebitCard: -> ProcessDebit
    flow BankTransfer: -> ProcessBank
}

// ERROR: mixes levels (CardPayment with CreditCard)
dfd MixedLevels {
    refines: Context.PaymentSystem
    process ProcessCards {}
    process ProcessCredit {}
    process ProcessBank {}
    flow CardPayment: -> ProcessCards   // Level 1
    flow CreditCard: -> ProcessCredit   // Level 2 - ERROR: mixes with CardPayment
    flow BankTransfer: -> ProcessBank
}
```

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_dfd_refinements()`

---

### 2.3 Import Resolution

#### REQ-SEM-100: Import Path Resolution [DONE]
Import statements shall resolve file paths correctly.

**Acceptance Criteria:**
- Relative paths resolved from importing file's directory
- Absolute paths used as-is
- File not found produces clear error message

**Implementation:** `src/designit/semantic/resolver.py:ImportResolver.resolve()`

---

#### REQ-SEM-101: Circular Import Detection [DONE]
Circular imports shall be detected and reported as errors.

**Acceptance Criteria:**
- ERROR if file A imports B and B imports A (direct cycle)
- ERROR if file A imports B imports C imports A (indirect cycle)
- Error message shows import chain

**Implementation:** `src/designit/semantic/resolver.py:ImportResolver` (CircularImportError)

---

#### REQ-SEM-102: Document Merging [DONE]
Imported documents shall be merged into a single document model.

**Acceptance Criteria:**
- All diagrams from imported files available in merged document
- Depth-first post-order merge (dependencies before dependents)
- Duplicate diagram names from different files preserved

**Implementation:** `src/designit/semantic/resolver.py:ImportResolver.resolve()`

---

## 3. Code Generation

### 3.1 Mermaid Output

#### REQ-GEN-001: Mermaid File Generation [DONE]
The system shall generate Mermaid diagram files.

**Acceptance Criteria:**
- Output files use `.mmd` extension
- Valid Mermaid syntax generated
- Title frontmatter included: `---\ntitle: Name\n---`

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator`

---

#### REQ-GEN-002: Mermaid DFD Generation [DONE]
DFDs shall be generated as Mermaid flowcharts.

**Acceptance Criteria:**
- Flowchart direction: LR (left to right)
- Externals: rectangle shape `["label"]`
- Processes: circle shape `(("label"))`
- Datastores: cylinder shape `[("label")]`
- Flows: arrows with labels

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator.generate_dfd()`

---

#### REQ-GEN-003: Mermaid ERD Generation [DONE]
ERDs shall be generated as Mermaid ER diagrams.

**Acceptance Criteria:**
- Uses `erDiagram` syntax
- Entities with attributes listed
- Relationships with cardinality notation
- Cardinality converted to Mermaid notation (`||`, `o{`, `}|`, etc.)

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator.generate_erd()`

---

#### REQ-GEN-004: Mermaid STD Generation [DONE]
STDs shall be generated as Mermaid state diagrams.

**Acceptance Criteria:**
- Uses `stateDiagram-v2` syntax
- Initial state marker: `[*] --> InitialState`
- States with descriptions as notes
- Transitions with labels (trigger, guard, action)

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator.generate_std()`

---

#### REQ-GEN-005: Mermaid Structure Chart Generation [DONE]
Structure charts shall be generated as Mermaid flowcharts.

**Acceptance Criteria:**
- Flowchart direction: TB
- Modules as boxes
- Calls as arrows between modules
- Data/control couples shown as labels or notes

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator.generate_structure()`

---

#### REQ-GEN-007: Mermaid SCD Generation [DONE]
SCDs shall be generated as Mermaid flowcharts.

**Acceptance Criteria:**
- Flowchart direction: LR (left to right) - see REQ-GEN-008
- System: stadium shape `[[label]]` with distinct styling (bold border)
- Externals: rectangle shape `["label"]`
- Datastores: cylinder shape `[("label")]`
- Inbound flows: arrows pointing to system
- Outbound flows: arrows pointing from system
- Bidirectional flows: `<-->` arrows

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator.generate_scd()`

---

#### REQ-GEN-008: Mermaid SCD Layout [DONE]
SCDs in Mermaid shall use left-to-right layout with the system as the focal point.

**Acceptance Criteria:**
- Flowchart direction: LR (left to right)
- System declared first to appear on left side
- External entities and datastores connect to system from right
- Provides clear visual hierarchy with system as central element

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator._write_scd()`

---

#### REQ-GEN-006: Mermaid Placeholder Styling [DONE]
Placeholder elements shall be visually distinct in generated diagrams.

**Acceptance Criteria:**
- Placeholder elements have dashed border style
- Style: `stroke-dasharray: 5 5`
- Distinguishes incomplete elements from complete ones

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator` (placeholder styling in all generate methods)

---

### 3.2 GraphViz Output

#### REQ-GEN-050: GraphViz File Generation [DONE]
The system shall generate GraphViz DOT files.

**Acceptance Criteria:**
- Output files use `.dot` extension
- Valid DOT syntax generated
- Graph attributes set (fontname: Helvetica)

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator`

---

#### REQ-GEN-051: GraphViz DFD Generation [DONE]
DFDs shall be generated as GraphViz directed graphs.

**Acceptance Criteria:**
- Layout engine: `neato` (force-directed) with `overlap=false` and `splines=true`
- Externals: `shape=box`
- Processes: `shape=circle`
- Datastores: `shape=cylinder`
- Flows as labeled edges

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator.generate_dfd()`

---

#### REQ-GEN-052: GraphViz ERD Generation [DONE]
ERDs shall be generated as GraphViz directed graphs.

**Acceptance Criteria:**
- Entities as record shapes with attribute list
- Relationships as labeled edges
- Cardinality shown on edges

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator.generate_erd()`

---

#### REQ-GEN-053: GraphViz STD Generation [DONE]
STDs shall be generated as GraphViz directed graphs.

**Acceptance Criteria:**
- States with rounded box shape
- Initial state marker as point node
- Transitions as labeled edges

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator.generate_std()`

---

#### REQ-GEN-054: GraphViz Structure Chart Generation [DONE]
Structure charts shall be generated as GraphViz directed graphs.

**Acceptance Criteria:**
- Modules as box shapes
- Call relationships as edges
- Hierarchical layout

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator.generate_structure()`

---

#### REQ-GEN-056: GraphViz SCD Generation [DONE]
SCDs shall be generated as GraphViz directed graphs.

**Acceptance Criteria:**
- Uses radial layout with system centered - see REQ-GEN-057
- System as doublecircle shape with bold border
- Externals as rectangles: `shape=box`
- Datastores as cylinders: `shape=cylinder`
- Arrow direction matches flow direction
- Bidirectional flows: `dir=both`

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator.generate_scd()`

---

#### REQ-GEN-057: GraphViz SCD Radial Layout [DONE]
SCDs in GraphViz shall use a radial layout with the system centered.

**Acceptance Criteria:**
- Uses neato layout engine for radial distribution
- System node pinned at center position (0,0)
- System depicted as doublecircle shape
- External entities and datastores distributed around system
- `overlap=false` to prevent node collision
- `splines=true` for curved edges

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator._write_scd()`

---

#### REQ-GEN-055: GraphViz Placeholder Styling [DONE]
Placeholder elements shall be visually distinct in generated diagrams.

**Acceptance Criteria:**
- Placeholder elements have dashed border: `style="dashed"`
- Gray color: `color="gray"`
- Distinguishes incomplete elements from complete ones

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator` (placeholder styling in all generate methods)

---

### 3.3 DFD Boundary Flow Rendering

#### REQ-GEN-010: DFD Boundary Flow Rendering [DONE]
DFD boundary flows shall be rendered with invisible boundary marker nodes.

**Acceptance Criteria:**
- Inbound boundary flows (`flow Name: -> Target`) rendered with invisible source node
- Outbound boundary flows (`flow Name: Source ->`) rendered with invisible target node
- Boundary nodes use minimal styling (small point/circle)
- Boundary nodes styled distinctly (dashed stroke, gray color)
- Internal flows (both endpoints present) rendered normally as before

**Implementation:**
- `src/designit/generators/mermaid.py:MermaidGenerator._write_dfd()`
- `src/designit/generators/graphviz.py:GraphVizGenerator._write_dfd()`

---

#### REQ-GEN-011: Mermaid DFD Boundary Node Styling [DONE]
Mermaid DFD boundary nodes shall use consistent minimal styling.

**Acceptance Criteria:**
- Boundary nodes use small circle shape: `(( ))`
- Boundary nodes assigned CSS class: `:::boundary`
- Class definition: `classDef boundary fill:none,stroke:#666,stroke-dasharray:3`
- Node IDs prefixed with `_boundary_` to avoid conflicts

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator._write_dfd()`

---

#### REQ-GEN-012: GraphViz DFD Boundary Node Styling [DONE]
GraphViz DFD boundary nodes shall be invisible.

**Acceptance Criteria:**
- Boundary nodes are invisible: `style=invis`
- Boundary nodes have no label: `label=""`
- Node IDs prefixed with `_boundary_` to avoid conflicts

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator._write_dfd()`

---

#### REQ-GEN-013: Bidirectional Boundary Flow Rendering [SUPERSEDED by REQ-GEN-070]
When the same process handles both inbound and outbound boundary flows for the same flow name, generators shall render a single bidirectional edge.

*This requirement has been superseded by REQ-GEN-070, which provides comprehensive flow aggregation including direction aggregation.*

**Original Acceptance Criteria:**
- Detect when same process is target of inbound AND source of outbound for same flow name
- Render single boundary node (not two)
- Mermaid: Render as `_boundary_FlowName <-->|"FlowName"| Process`
- GraphViz: Render as single edge with `dir=both`
- Label shows flow name once
- When different processes handle in/out, render as two separate edges

**Implementation:** `src/designit/semantic/aggregator.py:aggregate_flows()`

---

#### REQ-GEN-070: Flow Aggregation [DONE]
When generating diagrams, flows shall be aggregated based on union type coverage and direction.

**Type Aggregation** occurs when:
1. The flows cover **all subtypes** of a union type defined in the data dictionary
2. The flows have the **same direction**
3. The flows have the **same endpoints**:
   - **SCD flows**: Same source and target elements
   - **DFD boundary flows**: Same process endpoint
   - **DFD internal flows**: Same source AND same target elements

**Direction Aggregation** occurs when:
1. After type aggregation, two flows exist between the same endpoints with opposite directions
2. The flows have the same label (type name)

**Aggregation Order:**
1. First: Type aggregation (subtypes → parent type, grouped by direction and endpoints)
2. Second: Direction aggregation (opposite directions → bidirectional)

**Acceptance Criteria:**
- Flows covering all subtypes of a union render as single arrow with parent type label
- Opposite-direction flows with same label and endpoints render as bidirectional arrow
- Enum unions (quoted string literals) are NOT type-aggregated
- Aggregation is enabled by default
- Applies to both Mermaid and GraphViz generators
- Applies to both SCD and DFD diagrams

**Examples:**

*SCD type aggregation:*
```
datadict { PaymentMethod = CreditCard | BankTransfer }
scd Context {
    system Sys {}
    external Customer {}
    flow CreditCard: Customer -> Sys
    flow BankTransfer: Customer -> Sys
}
```
Renders as: `PaymentMethod: Customer -> Sys`

*DFD boundary type aggregation:*
```
dfd Payments {
    process Handler {}
    flow CreditCard: -> Handler
    flow BankTransfer: -> Handler
}
```
Renders as: `PaymentMethod: -> Handler`

*DFD internal type + direction aggregation:*
```
dfd Payments {
    process Validate {}
    process Process {}
    flow CreditCard: Validate -> Process
    flow BankTransfer: Validate -> Process
    flow CreditCard: Process -> Validate
    flow BankTransfer: Process -> Validate
}
```
Renders as: `PaymentMethod: Validate <-> Process`

**Implementation:** `src/designit/semantic/aggregator.py:aggregate_flows()`

---

#### REQ-GEN-071: Highest-Level Type Aggregation [DONE]
Type aggregation shall aggregate to the highest union level where complete coverage exists.

**Acceptance Criteria:**
- For nested unions, aggregation proceeds from leaf types upward
- Aggregation stops at the highest level where all subtypes are covered
- Partial coverage at a level prevents aggregation at that level

**Example:**
```
datadict {
    CreditCard = { number: string }
    DebitCard = { number: string }
    BankTransfer = { iban: string }
    CardPayment = CreditCard | DebitCard
    PaymentMethod = CardPayment | BankTransfer
}
scd Context {
    system Sys {}
    external Customer {}
    flow CreditCard: Customer -> Sys
    flow DebitCard: Customer -> Sys
    flow BankTransfer: Customer -> Sys
}
```
Aggregation steps:
1. `CreditCard + DebitCard → CardPayment`
2. `CardPayment + BankTransfer → PaymentMethod`

Renders as: `PaymentMethod: Customer -> Sys`

**Implementation:** `src/designit/semantic/aggregator.py:aggregate_flows()`

---

#### REQ-GEN-072: Partial Coverage No Aggregation [DONE]
When not all subtypes of a union are covered by flows, no aggregation shall occur at that level.

**Acceptance Criteria:**
- Missing subtypes prevent aggregation to parent type
- Each flow renders individually with its own label
- Partial coverage at nested levels still allows aggregation at lower complete levels

**Example (no aggregation - missing BankTransfer):**
```
datadict { PaymentMethod = CreditCard | BankTransfer }
scd Context {
    system Sys {}
    external Customer {}
    flow CreditCard: Customer -> Sys
}
```
Renders as: `CreditCard: Customer -> Sys` (no aggregation)

**Example (partial nested aggregation):**
```
datadict {
    CardPayment = CreditCard | DebitCard
    PaymentMethod = CardPayment | BankTransfer
}
scd Context {
    system Sys {}
    external Customer {}
    flow CreditCard: Customer -> Sys
    flow DebitCard: Customer -> Sys
    // BankTransfer missing
}
```
Renders as: `CardPayment: Customer -> Sys` (aggregates cards, but not to PaymentMethod)

**Implementation:** `src/designit/semantic/aggregator.py:aggregate_flows()`

---

#### REQ-GEN-073: Cross-Direction Type Aggregation [DONE]
When subtypes of a union flow in opposite directions between the same elements, they shall aggregate into a bidirectional flow with the parent type name.

**Acceptance Criteria:**
- Flows with different names but same union parent aggregate across directions
- Inbound and outbound subtypes merge into bidirectional parent
- Works with namespaced types (e.g., `PICiX.SubType` -> `PICiX.ParentType`)
- Nested unions aggregate to the highest covering level
- Partial coverage (missing subtypes) prevents aggregation
- Applies to both SCD flows and DFD boundary/internal flows

**Example (SCD cross-direction aggregation):**
```
datadict PICiX {
    IPICiX = PICiX_to_System | System_to_PICiX
    PICiX_to_System = { data: string }
    System_to_PICiX = { result: string }
}
scd Context {
    system Sys {}
    external PICiX {}
    flow PICiX.PICiX_to_System: PICiX -> Sys
    flow PICiX.System_to_PICiX: Sys -> PICiX
}
```
Renders as: `PICiX.IPICiX: PICiX <-> Sys` (bidirectional with parent type)

**Example (DFD boundary cross-direction):**
```
dfd Level0 {
    refines: Context.Sys
    process Handler {}
    flow PICiX.PICiX_to_System: -> Handler
    flow PICiX.System_to_PICiX: Handler ->
}
```
Renders as: `PICiX.IPICiX: <-> Handler` (bidirectional boundary flow)

**Implementation:** `src/designit/semantic/aggregator.py:_aggregate_scd_cross_direction_types()`, `_aggregate_dfd_boundary_cross_direction()`, `_aggregate_dfd_internal_cross_direction()`

---

### 3.4 Model Requirements

#### REQ-MODEL-010: DFD Flow Compound Key Storage [DONE]
DFD flows shall be stored using a compound key of (name, flow_type) to allow multiple flows with the same name but different directions.

**Acceptance Criteria:**
- Flow key is tuple of (flow_name, flow_type)
- `FlowType` type alias defined as `Literal["internal", "inbound", "outbound"]`
- `FlowKey` type alias defined as `tuple[str, FlowType]`
- Two boundary flows with same name but different types coexist in the dictionary
- Example: `("I_PicIX", "inbound")` and `("I_PicIX", "outbound")` are distinct keys

**Implementation:**
- `src/designit/model/dfd.py:DFDModel.flows`
- `src/designit/semantic/analyzer.py:SemanticAnalyzer._analyze_dfd()`

---

#### REQ-MODEL-011: DFD Flow Helper Methods [DONE]
DFDModel shall provide helper methods for convenient flow access.

**Acceptance Criteria:**
- `get_flow(name, flow_type)` returns a single flow or None
- `get_flows_by_name(name)` returns all flows with that name (list)
- Helper methods abstract the compound key implementation

**Implementation:** `src/designit/model/dfd.py:DFDModel`

---

## 4. Command Line Interface

### 4.1 Commands

#### REQ-CLI-001: Parse Command [DONE]
The CLI shall provide a `parse` command to display parsed document structure.

**Acceptance Criteria:**
- Command: `designit parse FILE`
- Displays list of included files (when imports resolved)
- Displays summary table (count of DFDs, ERDs, STDs, etc.)
- Displays placeholder summary

**Implementation:** `src/designit/cli.py:parse_cmd()`

---

#### REQ-CLI-002: Check Command [DONE]
The CLI shall provide a `check` command to validate design files.

**Acceptance Criteria:**
- Command: `designit check FILE`
- Displays errors, warnings, and info messages
- Messages include file:line location
- Exit code 0 if no errors, 1 if errors

**Implementation:** `src/designit/cli.py:check_cmd()`

---

#### REQ-CLI-003: Generate Command [DONE]
The CLI shall provide a `generate` command to export diagrams.

**Acceptance Criteria:**
- Command: `designit generate FILE`
- Generates diagram files in specified format
- Creates output directory if needed
- Reports generated file paths

**Implementation:** `src/designit/cli.py:generate_cmd()`

---

#### REQ-CLI-004: Placeholders Command [DONE]
The CLI shall provide a `placeholders` command to list incomplete sections.

**Acceptance Criteria:**
- Command: `designit placeholders FILE`
- Displays table of all placeholders
- Shows location (diagram, element) for each

**Implementation:** `src/designit/cli.py:placeholders_cmd()`

---

#### REQ-CLI-005: LSP Command [DONE]
The CLI shall provide an `lsp` command to start the language server.

**Acceptance Criteria:**
- Command: `designit lsp`
- Starts LSP server on stdin/stdout
- Server runs until client disconnects

**Implementation:** `src/designit/cli.py:lsp_cmd()`

---

### 4.2 Options

#### REQ-CLI-010: No Imports Flag [DONE]
Parse and check commands shall support skipping import resolution.

**Acceptance Criteria:**
- Flag: `--no-imports`
- When set, import statements are not resolved
- Only the specified file is processed

**Implementation:** `src/designit/cli.py` (parse_cmd, check_cmd)

---

#### REQ-CLI-011: Strict Flag [DONE]
Check command shall support treating warnings as errors.

**Acceptance Criteria:**
- Flag: `--strict`
- When set, warnings cause non-zero exit code
- Useful for CI/CD pipelines

**Implementation:** `src/designit/cli.py:check_cmd()`

---

#### REQ-CLI-020: Format Option [DONE]
Generate command shall support output format selection.

**Acceptance Criteria:**
- Option: `-f/--format FORMAT`
- Text formats: `mermaid`, `dot`
- Graphic formats: `svg` (default), `png`, `jpg`, `tiff`, `webp`
- Graphic formats invoke GraphViz `neato` to render output

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-021: Output Diagram Directory Option [DONE]
Generate command shall support specifying diagram output directory.

**Acceptance Criteria:**
- Option: `--output-diagram-dir DIR`
- Creates directory if it doesn't exist
- Default: `./generated/diagrams`

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-022: Diagram Filter Option [DONE]
Generate command shall support filtering specific diagrams.

**Acceptance Criteria:**
- Option: `-d/--diagram NAME`
- Can be specified multiple times
- Only generates diagrams matching specified names

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-023: No Placeholders Flag [DONE]
Generate command shall support excluding placeholder elements.

**Acceptance Criteria:**
- Flag: `--no-placeholders`
- When set, placeholder elements are not included in output
- Useful for generating "clean" diagrams

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-024: Stdout Flag [REMOVED]
*This requirement has been removed. The --stdout flag is no longer supported.*

---

#### REQ-CLI-026: No Check Flag [DONE]
Generate command shall validate by default and support skipping validation.

**Acceptance Criteria:**
- By default, `generate` runs validation before generating diagrams
- If validation errors exist, generation fails with exit code 1
- Flag: `--no-check`
- When set, validation is skipped and diagrams are generated even with errors
- Validation messages (errors, warnings, info) are printed before failing
- Hint about `--no-check` is shown when generation fails due to validation

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-027: No Aggregate Flows Flag [DONE]
Generate command shall support disabling flow aggregation.

**Acceptance Criteria:**
- Flag: `--no-aggregate-flows`
- When set, all flows render individually without aggregation
- Type aggregation and direction aggregation both disabled
- Useful for debugging or when explicit flow visibility is needed

**Implementation:** `src/designit/cli.py:generate()`, `src/designit/semantic/aggregator.py`

---

#### REQ-CLI-028: Output Markdown Option [DONE]
Generate command shall support specifying markdown output file path.

**Acceptance Criteria:**
- Option: `--output-markdown/-m PATH`
- PATH is the full file path (directory + filename)
- Default: `./generated/<SystemName>.md` where `<SystemName>` comes from the SCD's system name
- Creates parent directory if it doesn't exist
- Only used when markdown blocks exist in the .dit file

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-029: No Markdown Flag [DONE]
Generate command shall support disabling markdown generation.

**Acceptance Criteria:**
- Flag: `--no-markdown`
- When set, markdown document is not generated even if markdown blocks exist
- Diagrams are still generated normally
- Useful when only diagrams are needed

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-CLI-025: GraphViz Rendering [DONE]
Generate command shall render graphic formats using GraphViz.

**Acceptance Criteria:**
- Auto-detects layout engine based on DOT content:
  - Uses `neato` when DOT contains `layout=neato` (SCD diagrams)
  - Uses `dot` for all other diagrams (DFD, ERD, STD, Structure)
- Intermediate `.dot` files written to temp directory
- Temp files cleaned up after rendering
- Helpful error message if GraphViz (`dot` or `neato`) not installed

**Implementation:** `src/designit/cli.py:_render_graphviz()`, `_get_graphviz_engine()`

---

### 4.3 Error Handling

#### REQ-CLI-030: Improved Parse Error Messages [DONE]
Parse error messages shall clearly identify the problematic token and list valid alternatives.

**Acceptance Criteria:**
- Error messages show the actual problematic text from source (e.g., `dfda` not `a`)
- Keyword typos are reported with the full misspelled word
- Expected keywords are listed in the error message
- Error location (line, column) is accurate

**Example:**
```
Error: Unexpected token 'dfda' at line 1, column 1.
Expected one of: dfd, erd, std, structure, datadict, import
```

**Implementation:** 
- Grammar: `src/designit/grammar/designit.lark` (basic lexer mode with terminal priorities)
- Parser: `src/designit/parser/parser.py:_create_parser()` (lexer="basic")

---

## 5. Language Server Protocol

### 5.1 Diagnostics

#### REQ-LSP-001: Diagnostics on Open [DONE]
LSP server shall validate documents when opened.

**Acceptance Criteria:**
- Responds to `textDocument/didOpen` notification
- Parses and validates document
- Publishes diagnostics to client

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_DID_OPEN)

---

#### REQ-LSP-002: Diagnostics on Change [DONE]
LSP server shall validate documents when content changes.

**Acceptance Criteria:**
- Responds to `textDocument/didChange` notification
- Re-parses and validates document
- Publishes updated diagnostics

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_DID_CHANGE)

---

#### REQ-LSP-003: Diagnostics on Save [DONE]
LSP server shall validate documents when saved.

**Acceptance Criteria:**
- Responds to `textDocument/didSave` notification
- Re-validates document
- Publishes updated diagnostics

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_DID_SAVE)

---

#### REQ-LSP-004: Clear Diagnostics on Close [DONE]
LSP server shall clear diagnostics when document is closed.

**Acceptance Criteria:**
- Responds to `textDocument/didClose` notification
- Publishes empty diagnostics for closed document

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_DID_CLOSE)

---

#### REQ-LSP-005: Diagnostic Severity Mapping [DONE]
Validation messages shall be mapped to LSP diagnostic severities.

**Acceptance Criteria:**
- ERROR -> DiagnosticSeverity.Error
- WARNING -> DiagnosticSeverity.Warning
- INFO -> DiagnosticSeverity.Information

**Implementation:** `src/designit/lsp/server.py:validate_document()`

---

### 5.2 Completion

#### REQ-LSP-010: Context-Aware Completions [DONE]
LSP server shall provide context-aware code completions.

**Acceptance Criteria:**
- Responds to `textDocument/completion` request
- Analyzes cursor context to determine completion type
- Returns appropriate completion items

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_COMPLETION)

---

#### REQ-LSP-011: Type Completions [DONE]
LSP server shall provide type completions after colon.

**Acceptance Criteria:**
- When cursor follows `:`, suggest data types
- Types: string, integer, decimal, boolean, datetime, date, time, binary

**Implementation:** `src/designit/lsp/server.py` (TYPE_COMPLETIONS)

---

#### REQ-LSP-012: Constraint Completions [DONE]
LSP server shall provide constraint completions inside brackets.

**Acceptance Criteria:**
- When cursor is inside `[]`, suggest constraints
- Constraints: pk, fk, unique, not null, optional, pattern, min, max

**Implementation:** `src/designit/lsp/server.py` (CONSTRAINT_COMPLETIONS)

---

#### REQ-LSP-013: Keyword Completions [DONE]
LSP server shall provide keyword completions in general context.

**Acceptance Criteria:**
- Suggest DSL keywords: dfd, erd, std, structure, datadict, etc.
- Include descriptions for each keyword

**Implementation:** `src/designit/lsp/server.py` (KEYWORD_COMPLETIONS)

---

### 5.3 Hover

#### REQ-LSP-020: Diagram Type Documentation [DONE]
LSP server shall provide hover documentation for diagram types.

**Acceptance Criteria:**
- Responds to `textDocument/hover` request
- Returns markdown documentation for dfd, erd, std, structure, datadict
- Documentation includes syntax examples

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_HOVER, HOVER_DOCS)

---

#### REQ-LSP-021: Keyword Descriptions [DONE]
LSP server shall provide hover descriptions for keywords.

**Acceptance Criteria:**
- Returns description for recognized keywords
- Descriptions explain purpose and usage

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_HOVER)

---

### 5.4 Document Symbols

#### REQ-LSP-030: Document Symbol Tree [DONE]
LSP server shall provide document outline/symbol tree.

**Acceptance Criteria:**
- Responds to `textDocument/documentSymbol` request
- Returns hierarchical symbol structure
- Enables IDE outline view

**Implementation:** `src/designit/lsp/server.py` (@server.feature TEXT_DOCUMENT_DOCUMENT_SYMBOL)

---

#### REQ-LSP-031: DFD Symbols [DONE]
DFD elements shall be represented as document symbols.

**Acceptance Criteria:**
- DFD as Module symbol
- Externals as Interface symbols
- Processes as Function symbols

**Implementation:** `src/designit/lsp/server.py:document_symbols()`

---

#### REQ-LSP-032: ERD Symbols [DONE]
ERD elements shall be represented as document symbols.

**Acceptance Criteria:**
- ERD as Module symbol
- Entities as Class symbols

**Implementation:** `src/designit/lsp/server.py:document_symbols()`

---

#### REQ-LSP-033: STD Symbols [DONE]
STD elements shall be represented as document symbols.

**Acceptance Criteria:**
- STD as Module symbol
- States as Enum symbols

**Implementation:** `src/designit/lsp/server.py:document_symbols()`

---

## 6. VS Code Extension

### 6.1 Language Support

#### REQ-VSC-001: File Type Registration [DONE]
The extension shall register the `.dit` file type.

**Acceptance Criteria:**
- Files with `.dit` extension recognized as DesignIt
- Language ID: `designit`
- File icon associated (if provided)

**Implementation:** `vscode-extension/package.json` (contributes.languages)

---

#### REQ-VSC-002: Syntax Highlighting [DONE]
The extension shall provide syntax highlighting via TextMate grammar.

**Acceptance Criteria:**
- Keywords highlighted (dfd, erd, process, entity, etc.)
- Types highlighted (string, integer, etc.)
- Constraints highlighted (pk, unique, etc.)
- Comments highlighted (// and /* */)
- Strings highlighted

**Implementation:** `vscode-extension/syntaxes/designit.tmLanguage.json`

---

#### REQ-VSC-003: Bracket Matching [DONE]
The extension shall support bracket matching.

**Acceptance Criteria:**
- Curly braces `{}` matched
- Square brackets `[]` matched
- Parentheses `()` matched

**Implementation:** `vscode-extension/language-configuration.json` (brackets)

---

#### REQ-VSC-004: Comment Toggling [DONE]
The extension shall support comment toggling.

**Acceptance Criteria:**
- Line comment toggle: `//`
- Block comment toggle: `/* */`
- Works with VS Code comment commands

**Implementation:** `vscode-extension/language-configuration.json` (comments)

---

### 6.2 LSP Client

#### REQ-VSC-010: LSP Server Connection [DONE]
The extension shall connect to the DesignIt LSP server.

**Acceptance Criteria:**
- Spawns `designit lsp` process
- Communicates via stdio
- Reconnects on server restart

**Implementation:** `vscode-extension/src/extension.ts`

---

#### REQ-VSC-011: Diagnostic Display [DONE]
The extension shall display LSP diagnostics.

**Acceptance Criteria:**
- Errors shown with red underline
- Warnings shown with yellow underline
- Info shown with blue underline
- Problems panel shows all diagnostics

**Implementation:** `vscode-extension/src/extension.ts` (via LSP client)

---

#### REQ-VSC-012: Completion Integration [DONE]
The extension shall provide code completions from LSP.

**Acceptance Criteria:**
- Completions triggered by Ctrl+Space
- Completions appear as user types
- Completion items show descriptions

**Implementation:** `vscode-extension/src/extension.ts` (via LSP client)

---

#### REQ-VSC-013: Hover Integration [DONE]
The extension shall show hover documentation from LSP.

**Acceptance Criteria:**
- Hover on keywords shows documentation
- Documentation rendered as markdown
- Syntax examples displayed in code blocks

**Implementation:** `vscode-extension/src/extension.ts` (via LSP client)

---

#### REQ-VSC-014: Document Outline [DONE]
The extension shall show document outline from LSP.

**Acceptance Criteria:**
- Outline view shows diagram structure
- Symbols navigable by clicking
- Breadcrumb navigation works

**Implementation:** `vscode-extension/src/extension.ts` (via LSP client)

---

### 6.3 Configuration

#### REQ-VSC-020: Server Path Setting [DONE]
The extension shall support configuring the server executable path.

**Acceptance Criteria:**
- Setting: `designit.server.path`
- Default: `"designit"`
- Allows using custom installation path

**Implementation:** `vscode-extension/package.json` (contributes.configuration)

---

#### REQ-VSC-021: Trace Setting [DONE]
The extension shall support configuring LSP trace level.

**Acceptance Criteria:**
- Setting: `designit.trace.server`
- Values: `"off"`, `"messages"`, `"verbose"`
- Enables debugging LSP communication

**Implementation:** `vscode-extension/package.json` (contributes.configuration)

---

### 6.4 Packaging

#### REQ-VSC-030: VSIX Package [DONE]
The extension shall be packageable as a VSIX file.

**Acceptance Criteria:**
- `npm run package` creates VSIX file
- VSIX installable in VS Code
- All required files included

**Implementation:** `vscode-extension/package.json` (vsce package script)

---

#### REQ-VSC-031: MIT License [DONE]
The extension shall be licensed under MIT license.

**Acceptance Criteria:**
- LICENSE file present
- License field in package.json

**Implementation:** `vscode-extension/LICENSE`, `vscode-extension/package.json`

---

## 7. Document Generation

### 7.1 Markdown Block Syntax

#### REQ-DOC-001: Markdown Block Declaration [DONE]
The DSL shall support markdown blocks for embedding documentation alongside model definitions.

**Acceptance Criteria:**
- Markdown blocks declared with `markdown { ... }`
- Content between braces is raw markdown text
- Multiple markdown blocks allowed per file
- Markdown blocks can appear at top level (not inside diagram definitions)
- Backslash escapes single characters: `\{` produces `{`, `\}` produces `}`
- The closing `}` of the markdown block is identified as an unescaped `}` at the appropriate brace nesting level. This works because: (1) template expressions use double braces `{{...}}` which are self-balancing, and (2) any literal single brace in markdown content must be escaped. This allows the grammar to reliably find the block boundary without ambiguity.

**Example:**
```
scd Context {
    system OrderSystem {}
    external Customer {}
    flow OrderRequest: Customer -> OrderSystem
}

markdown {
    ## System Context
    
    The order processing system handles customer requests.
    
    {{diagram:Context}}
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark`
- AST: `src/designit/parser/ast_nodes.py` (MarkdownNode)

---

#### REQ-DOC-002: Markdown Block Ordering [DONE]
Markdown blocks shall appear in output in depth-first pre-order (top-down).

**Acceptance Criteria:**
- Root file's markdown blocks appear first
- Then recursively: for each import (in source order), that file's markdown blocks appear, followed by its imports
- This ensures the main document introduction appears at the top, with imported details following in logical reading order

**Example import tree:**
```
main.dit (imports A, B)
├── A.dit (imports C)
│   └── C.dit
└── B.dit
```
**Output order:** main → A → C → B

**Implementation:** `src/designit/semantic/resolver.py`

---

#### REQ-DOC-003: Markdown Block in Same File as Model [DONE]
Markdown blocks may appear in the same `.dit` file as the model elements they reference.

**Acceptance Criteria:**
- A single file can contain both model definitions and markdown blocks
- Model elements defined after a markdown block are still accessible via references
- Allows keeping documentation close to the model it describes

**Example:**
```
// Single file with both model and documentation
scd Context {
    system API {}
    external Client {}
    flow Request: Client -> API
}

markdown {
    ## API Overview
    {{diagram:Context}}
    
    The {{Context.API.name}} handles requests from {{Context.Client.name}}.
}
```

**Implementation:** `src/designit/parser/parser.py`

---

### 7.2 Template Expressions

#### REQ-DOC-010: Diagram Insertion [DONE]
Markdown blocks shall support inserting generated diagrams using template syntax.

**Acceptance Criteria:**
- Syntax: `{{diagram:DiagramName}}`
- Diagram name must exactly match an SCD, DFD, ERD, STD, or Structure Chart name
- ERROR if referenced diagram does not exist
- Diagram format determined by CLI `--format` option (reuses existing generate command option)

**Example:**
```
markdown {
    ## System Context
    {{diagram:OrderContext}}
    
    ## Order Processing Details  
    {{diagram:OrderProcessingDFD}}
}
```

**Implementation:** `src/designit/generators/markdown.py`

---

#### REQ-DOC-011: Element Property Access [DONE]
Markdown blocks shall support accessing model element properties using dot notation.

**Acceptance Criteria:**
- Syntax: `{{DiagramName.ElementName.property}}`
- Supported properties include: `name`, `description`, and other element-specific properties
- ERROR if diagram, element, or property does not exist
- Element names are unique within their diagram (per REQ-SEM-087)

**Example:**
```
markdown {
    The {{Context.OrderSystem.name}} system: {{Context.OrderSystem.description}}
}
```

**Implementation:** `src/designit/generators/markdown.py`

---

#### REQ-DOC-012: Collection Iteration [DONE]
Markdown blocks shall support iterating over collections of elements.

**Acceptance Criteria:**
- Syntax: `{{#each DiagramName.collection}}...{{/each}}`
- Inside the block, element properties accessed directly: `{{name}}`, `{{description}}`
- Supported collections by diagram type:
  - SCD: `externals`, `datastores`, `flows`
  - DFD: `processes`, `datastores`, `flows`
  - ERD: `entities`, `relationships`
  - STD: `states`, `transitions`
  - Structure: `modules`
  - DataDict: `definitions`
- ERROR if diagram or collection does not exist

**Example:**
```
markdown {
    ### External Entities
    
    {{#each Context.externals}}
    - **{{name}}**: {{description}}
    {{/each}}
}
```

**Implementation:** `src/designit/generators/markdown.py`

---

#### REQ-DOC-013: Nested Iteration [DONE]
Iteration blocks shall support nesting to iterate over nested structures.

**Acceptance Criteria:**
- Nested `{{#each}}` blocks allowed
- Inner block has access to outer block's current element via qualified names
- Useful for iterating over diagram elements and their sub-elements

**Example:**
```
markdown {
    {{#each Context.externals}}
    ## {{name}}
    
    {{description}}
    {{/each}}
}
```

**Implementation:** `src/designit/generators/markdown.py`

---

#### REQ-DOC-014: Top-Level Collection Access [POSTPONE]
Template expressions shall support accessing top-level diagram collections.

**Note:** Postponed for future implementation.

---

### 7.3 Document Generation Pipeline

#### REQ-DOC-020: Template Validation [DONE]
All template expressions shall be validated against the semantic model before rendering.

**Acceptance Criteria:**
- ERROR if `{{diagram:X}}` references non-existent diagram
- ERROR if `{{X.Y.property}}` references non-existent diagram, element, or property
- ERROR if `{{#each X.collection}}` references non-existent diagram or collection
- Validation errors include source location (line number in markdown block)
- Report all errors found, stopping after maximum count (10 errors)
- All errors reported before rendering begins

**Implementation:** `src/designit/semantic/validator.py`

---

#### REQ-DOC-021: Document Generation Pipeline [DONE]
The document generation process shall follow a defined pipeline.

**Acceptance Criteria:**
1. Parse all `.dit` files (model + markdown blocks)
2. Resolve imports (depth-first pre-order for markdown ordering)
3. Build semantic model
4. Validate model (existing validation rules)
5. Validate template expressions in markdown blocks
6. Generate required diagrams (based on `{{diagram:X}}` references)
7. Render markdown with resolved templates
8. Output combined markdown document

**Implementation:** `src/designit/generators/markdown.py:generate_document()`

---

### 7.4 CLI Integration

*Note: The `doc` command has been consolidated into the `generate` command. Markdown documentation is now automatically generated when markdown blocks are present in the .dit file.*

#### REQ-DOC-030: Integrated Documentation Generation [DONE]
The `generate` command shall automatically generate markdown documentation when markdown blocks are present.

**Acceptance Criteria:**
- Markdown is generated automatically when `.dit` file contains `markdown { }` blocks
- Uses the same `--format/-f` option as diagram generation
- Validates model and templates before generation
- Generates combined markdown output with embedded diagrams
- Reports errors if validation fails
- Use `--no-markdown` to disable automatic markdown generation

**Example:**
```bash
# Generate diagrams and markdown (when markdown blocks exist)
designit generate design.dit

# Generate only diagrams (skip markdown)
designit generate design.dit --no-markdown
```

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-DOC-031: Markdown Output Path Option [DONE]
The generate command shall support specifying markdown output file path.

**Acceptance Criteria:**
- Option: `--output-markdown/-m PATH` - full file path (directory + filename)
- Default: `./generated/<scd.system.name>.md` (derived from the SCD's system name)
- Creates directory if needed

**Example:**
```bash
designit generate design.dit -m docs/architecture.md
```

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-DOC-032: Diagram Format for Documentation [DONE]
The generate command uses the same format option for both diagrams and documentation.

**Acceptance Criteria:**
- Option: `-f/--format FORMAT` (same as diagram format)
- Supported formats for documentation: `svg` (default), `png`, `mermaid`
- For `svg`/`png`: embeds as image reference
- For `mermaid`: writes `.mmd` files and references them

**Example:**
```bash
# SVG diagrams (default)
designit generate design.dit

# Mermaid format
designit generate design.dit -f mermaid
```

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-DOC-033: Diagram Directory for Documentation [DONE]
The generate command uses the same diagram directory for documentation.

**Acceptance Criteria:**
- Option: `--output-diagram-dir DIR`
- Default: `./generated/diagrams`
- Diagram files written to this directory for all formats (svg, png, mmd)
- Markdown uses relative paths from markdown file to diagram directory
- Creates directory if needed

**Example:**
```bash
designit generate design.dit --output-diagram-dir docs/images -m docs/design.md
```

**Implementation:** `src/designit/cli.py:generate()`

---

#### REQ-DOC-034: SCD Required for Document Generation [DONE]
Document generation shall require exactly one SCD with a system definition.

**Acceptance Criteria:**
- ERROR if markdown blocks exist but no SCD exists in the model
- ERROR if markdown blocks exist but SCD has no system defined
- Error message: `"Markdown generation requires an SCD with a system definition"`
- Without markdown blocks, diagrams can be generated without this requirement

**Implementation:** `src/designit/cli.py:generate()`

---

### 7.5 Output Formatting

#### REQ-DOC-040: SVG Diagram Embedding [DONE]
When diagram format is `svg`, diagrams shall be embedded as image references.

**Acceptance Criteria:**
- SVG files written to diagram directory
- Markdown includes: `![DiagramName](relative/path/to/diagram.svg)`
- File names derived from diagram names (sanitized for filesystem)
- Relative path calculated from markdown file location to diagram directory

**Implementation:** `src/designit/generators/markdown.py`

---

#### REQ-DOC-041: PNG Diagram Embedding [DONE]
When diagram format is `png`, diagrams shall be embedded as image references.

**Acceptance Criteria:**
- PNG files written to diagram directory
- Markdown includes: `![DiagramName](relative/path/to/diagram.png)`
- Requires GraphViz for rendering

**Implementation:** `src/designit/generators/markdown.py`

---

#### REQ-DOC-042: Mermaid File Embedding [DONE]
When diagram format is `mmd`, diagrams shall be written as `.mmd` files and referenced in markdown.

**Acceptance Criteria:**
- Mermaid files written to diagram directory with `.mmd` extension
- Markdown includes: `![DiagramName](relative/path/to/diagram.mmd)`
- Consistent with SVG and PNG embedding approach
- Note: Native rendering depends on markdown renderer support for `.mmd` files

**Implementation:** `src/designit/generators/markdown.py`

---

## Backlog: Diagram Appearance Improvements

These are lower priority improvements identified during development:

#### REQ-GEN-060: DFD Process Circle Shape [DONE]
DFD processes shall be rendered as circles that adapt to content.

**Acceptance Criteria:**
- GraphViz: Use `shape=circle` (adapts to label size)
- Mermaid: Use `(("label"))` syntax (adapts to label size)
- Process name displayed inside circle

**Implementation:**
- `src/designit/generators/mermaid.py:MermaidGenerator._write_dfd_processes()`
- `src/designit/generators/graphviz.py:GraphVizGenerator._write_dfd_processes()`

---

#### REQ-GEN-061: SCD External Box Shape Without Description [DONE]
SCD external entities shall be rendered as simple boxes without embedded descriptions.

**Acceptance Criteria:**
- External rendered as rectangle with name only
- Description not shown inside the shape
- Description available via document generation (REQ-DOC-011)

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator._write_scd_externals()`

---

#### REQ-GEN-062: SCD System Box Shape Without Description [DONE]
SCD system shall be rendered as a box without embedded description.

**Acceptance Criteria:**
- System rendered with name only (no description in diagram)
- Description available via document generation

**Implementation:**
- `src/designit/generators/mermaid.py:MermaidGenerator._write_scd_system()`
- `src/designit/generators/graphviz.py:GraphVizGenerator._write_scd_system()`

---

#### REQ-GEN-063: DFD Process Without Description [DONE]
DFD processes shall be rendered without embedded descriptions.

**Acceptance Criteria:**
- Process rendered with name only
- Description available via document generation

**Implementation:**
- `src/designit/generators/mermaid.py:MermaidGenerator._write_dfd_processes()`
- `src/designit/generators/graphviz.py:GraphVizGenerator._write_dfd_processes()`

---

#### REQ-GEN-064: SCD Datastore Without Description [DONE]
SCD datastores shall be rendered without embedded descriptions.

**Acceptance Criteria:**
- Datastore rendered as cylinder with name only
- Description not shown inside the shape
- Description available via document generation (REQ-DOC-011)

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator._write_scd_datastores()`

---

## Test Coverage Summary

### Parser Tests (`tests/test_parser.py`)
- Empty document parsing
- Comment-only document
- Import statement parsing
- SCD parsing (system, externals, datastores, directional flows)
- DFD parsing (full and with placeholders)
- ERD parsing (entities, attributes, constraints, relationships)
- STD parsing (states, transitions)
- Structure chart parsing (modules, calls, couples)
- Data dictionary parsing (all definition types)
- Parse error handling (invalid syntax, unclosed blocks)

### Semantic Tests (`tests/test_semantic.py`)
- SCD semantic analysis
- SCD system validation (required, unique)
- SCD flow endpoint validation
- SCD orphan element warning
- DFD semantic analysis
- ERD semantic analysis with primary key detection
- Placeholder detection and tracking
- Valid document produces no errors
- Invalid flow endpoint produces error
- Invalid state reference produces error
- Invalid entity reference produces error
- Orphan element produces warning
- Missing primary key produces warning

### Document Generation Tests (`tests/test_doc.py`)
- Markdown block parsing (simple, with template expressions, with escaped braces)
- Markdown node location tracking
- Template parser (diagram expressions, property expressions, each blocks)
- Escaped braces not parsed as template expressions
- Template validator (diagram references, element properties, collections)
- Per-diagram-type collection validation (SCD, DFD, ERD, STD, Structure, DataDict)
- Markdown generator (diagram rendering, property values, each iteration)
- Escaped braces surrounding template expressions render correctly
- Unescape braces utility function
- Document generation pipeline (full integration)
- Error handling (unknown diagrams, invalid properties, unmatched each blocks)

### Example Tests (`tests/test_examples.py`)
- Banking example parses with all imports resolved
- Banking example has no validation errors
- SCD structure validation (system, externals, datastores, flows)
- SCD flow direction validation (inbound, outbound, bidirectional)
- Context file standalone parsing

---

## Appendix: File Reference

| File | Purpose |
|------|---------|
| `src/designit/grammar/designit.lark` | Lark grammar definition |
| `src/designit/parser/parser.py` | Lark parser and AST transformer |
| `src/designit/parser/ast_nodes.py` | AST node class definitions |
| `src/designit/semantic/analyzer.py` | AST to semantic model transformation |
| `src/designit/semantic/validator.py` | Validation rules |
| `src/designit/semantic/resolver.py` | Multi-file import resolution |
| `src/designit/model/base.py` | Base model classes |
| `src/designit/model/scd.py` | SCD semantic model |
| `src/designit/model/dfd.py` | DFD semantic model |
| `src/designit/model/erd.py` | ERD semantic model |
| `src/designit/model/std.py` | STD semantic model |
| `src/designit/model/structure.py` | Structure chart model |
| `src/designit/model/datadict.py` | Data dictionary model |
| `src/designit/generators/mermaid.py` | Mermaid diagram generator |
| `src/designit/generators/graphviz.py` | GraphViz DOT generator |
| `src/designit/generators/markdown.py` | Markdown document generator |
| `src/designit/lsp/server.py` | LSP server implementation |
| `src/designit/cli.py` | CLI entry point |
| `vscode-extension/` | VS Code extension |
| `tests/test_parser.py` | Parser unit tests |
| `tests/test_semantic.py` | Semantic analysis tests |
| `tests/test_doc.py` | Document generation tests |
