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
- Struct types: `{ field: type, ... }`
- Union types (enumerations): `"literal1" | "literal2" | TypeRef`
- Array types: `ElementType[]` with optional constraints `[min: N, max: M]`
- Type references: `OtherTypeName`
- Field constraints: `optional`, `pattern: "regex"`, `min: N`, `max: N`

**Example:**
```
datadict {
    OrderStatus = "draft" | "submitted" | "shipped" | "delivered"
    
    Address = {
        street: string
        city: string
        postal_code: string [pattern: "[0-9]{5}"]
        country: string
    }
    
    Money = {
        amount: decimal [min: 0]
        currency: string [pattern: "[A-Z]{3}"]
    }
    
    OrderItems = OrderItem[] [min: 1, max: 100]
}
```

**Implementation:**
- Grammar: `src/designit/grammar/designit.lark` (datadict_def, data_def, struct_def, union_def, array_def)
- AST: `src/designit/parser/ast_nodes.py` (DataDictNode, DataDefNode, StructDefNode, UnionDefNode, ArrayDefNode, TypeRefNode, StructFieldNode, FieldConstraintNode)
- Model: `src/designit/model/datadict.py`

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
Type references shall reference existing types or built-in types.

**Acceptance Criteria:**
- WARNING if referenced type not defined in data dictionary
- Built-in types (string, integer, etc.) are always valid

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_datadict()`

---

#### REQ-SEM-060: Cross-Diagram Reference Info [DONE]
Flow names not defined in data dictionary shall generate an informational message.

**Acceptance Criteria:**
- INFO if DFD flow name not found in data dictionary
- Encourages documenting data types

**Implementation:** `src/designit/semantic/validator.py:Validator._validate_cross_references()`

---

#### REQ-SEM-070: Placeholder Reporting [DONE]
All placeholders shall be reported as informational messages.

**Acceptance Criteria:**
- INFO message for each placeholder found
- Message includes location and context (diagram name, element name)

**Implementation:** `src/designit/semantic/validator.py:Validator._report_placeholders()`

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
- Flowchart direction: TB (top to bottom)
- Externals: rectangle shape `["label"]`
- Processes: rounded shape `("label")`
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
- Flowchart direction: TB (top to bottom)
- System: stadium shape `([label])` with distinct styling (bold border)
- Externals: rectangle shape `["label"]`
- Datastores: cylinder shape `[("label")]`
- Inbound flows: arrows pointing to system
- Outbound flows: arrows pointing from system
- Bidirectional flows: `<-->` arrows

**Implementation:** `src/designit/generators/mermaid.py:MermaidGenerator.generate_scd()`

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
- Externals: `shape=box`
- Processes: `shape=ellipse`
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
- System with bold border: `penwidth=2`
- Externals as rectangles: `shape=box`
- Datastores as cylinders: `shape=cylinder`
- Arrow direction matches flow direction
- Bidirectional flows: `dir=both`

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator.generate_scd()`

---

#### REQ-GEN-055: GraphViz Placeholder Styling [DONE]
Placeholder elements shall be visually distinct in generated diagrams.

**Acceptance Criteria:**
- Placeholder elements have dashed border: `style="dashed"`
- Gray color: `color="gray"`
- Distinguishes incomplete elements from complete ones

**Implementation:** `src/designit/generators/graphviz.py:GraphVizGenerator` (placeholder styling in all generate methods)

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
- Formats: `mermaid` (default), `graphviz`, `dot` (alias for graphviz)

**Implementation:** `src/designit/cli.py:generate_cmd()`

---

#### REQ-CLI-021: Output Directory Option [DONE]
Generate command shall support specifying output directory.

**Acceptance Criteria:**
- Option: `-o/--output DIR`
- Creates directory if it doesn't exist
- Default: current directory

**Implementation:** `src/designit/cli.py:generate_cmd()`

---

#### REQ-CLI-022: Diagram Filter Option [DONE]
Generate command shall support filtering specific diagrams.

**Acceptance Criteria:**
- Option: `-d/--diagram NAME`
- Can be specified multiple times
- Only generates diagrams matching specified names

**Implementation:** `src/designit/cli.py:generate_cmd()`

---

#### REQ-CLI-023: No Placeholders Flag [DONE]
Generate command shall support excluding placeholder elements.

**Acceptance Criteria:**
- Flag: `--no-placeholders`
- When set, placeholder elements are not included in output
- Useful for generating "clean" diagrams

**Implementation:** `src/designit/cli.py:generate_cmd()`

---

#### REQ-CLI-024: Stdout Flag [DONE]
Generate command shall support printing output to stdout.

**Acceptance Criteria:**
- Flag: `--stdout`
- When set, diagram content printed to stdout
- No files created
- Useful for piping to other tools

**Implementation:** `src/designit/cli.py:generate_cmd()`

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
| `src/designit/lsp/server.py` | LSP server implementation |
| `src/designit/cli.py` | CLI entry point |
| `vscode-extension/` | VS Code extension |
| `tests/test_parser.py` | Parser unit tests |
| `tests/test_semantic.py` | Semantic analysis tests |
