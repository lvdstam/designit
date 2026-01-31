# DesignIt

A Domain-Specific Language (DSL) for creating Yourdon-style design documents.

DesignIt allows you to define system designs using a clean, text-based syntax that can be version-controlled, validated, and transformed into visual diagrams. It supports the classic structured analysis and design notations: Data Flow Diagrams (DFD), Entity-Relationship Diagrams (ERD), State Transition Diagrams (STD), Structure Charts, and Data Dictionaries.

## Features

- **Text-based design documents** - Version control friendly `.dit` files
- **Multi-file support** - Split large designs across multiple files with imports
- **Validation** - Catch errors and inconsistencies early
- **Diagram generation** - Export to Mermaid or Graphviz/DOT format
- **LSP support** - IDE integration with real-time error checking and completions
- **Placeholder support** - Use `...` or `TBD` for work-in-progress designs

## Installation

Requires Python 3.13 or higher.

```bash
# Using uv (recommended)
uv add designit

# Using pip
pip install designit
```

For development:

```bash
git clone https://github.com/yourusername/designit.git
cd designit
uv sync --dev
```

## Quick Start

Create a file named `system.dit`:

```
// Simple banking system example
dfd BankingSystem {
    external Customer {
        description: "Bank customer"
    }

    process ProcessTransaction {
        description: "Handles deposits and withdrawals"
    }

    datastore AccountDB {
        description: "Account information"
    }

    flow DepositRequest: Customer -> ProcessTransaction
    flow AccountUpdate: ProcessTransaction -> AccountDB
}
```

Validate and generate a diagram:

```bash
# Check for errors
designit check system.dit

# Generate Mermaid diagram
designit generate system.dit -f mermaid --stdout
```

## The DesignIt DSL

DesignIt files use the `.dit` extension and support five diagram types plus data dictionaries.

### Data Flow Diagrams (DFD)

DFDs show how data moves through a system between external entities, processes, and data stores.

```
dfd OrderSystem {
    // External entities - sources/sinks of data
    external Customer {
        description: "Places orders"
    }

    external Warehouse {
        description: "Fulfills orders"
    }

    // Processes - transform data
    process ValidateOrder {
        description: "Checks order validity"
        inputs: [OrderData]
        outputs: [ValidatedOrder, ValidationError]
    }

    process FulfillOrder {
        description: "Sends order to warehouse"
    }

    // Data stores - persist data
    datastore OrderDB {
        description: "Order records"
    }

    datastore InventoryDB {
        description: "Stock levels"
    }

    // Data flows - connect elements
    flow OrderData: Customer -> ValidateOrder
    flow ValidatedOrder: ValidateOrder -> OrderDB
    flow FulfillmentRequest: ValidateOrder -> FulfillOrder
    flow ShippingRequest: FulfillOrder -> Warehouse
    flow StockCheck: FulfillOrder -> InventoryDB
}
```

### Entity-Relationship Diagrams (ERD)

ERDs define data models with entities, attributes, and relationships.

```
erd UserModel {
    entity User {
        id: integer [pk]
        email: string [unique]
        username: string [unique]
        password_hash: string
        created_at: datetime
        status: string
    }

    entity Profile {
        id: integer [pk]
        user_id: integer [fk -> User.id]
        first_name: string
        last_name: string
        bio: string
        avatar_url: string
    }

    entity Post {
        id: integer [pk]
        author_id: integer [fk -> User.id]
        title: string
        content: string
        published_at: datetime
        status: string
    }

    // Relationships with cardinality
    relationship has_profile: User -1:1-> Profile
    relationship has_posts: User -1:n-> Post
}
```

**Supported types:** `string`, `integer`, `decimal`, `boolean`, `datetime`, `date`, `time`, `binary`

**Supported constraints:**
- `pk` - Primary key
- `fk -> Entity.field` - Foreign key reference
- `unique` - Unique constraint
- `not null` - Required field
- `pattern: "regex"` - Regex pattern validation

**Cardinality notation:**
- `1:1` - One to one
- `1:n` - One to many
- `n:n` - Many to many
- `0..1:n` - Zero or one to many

### State Transition Diagrams (STD)

STDs model the lifecycle states of an entity and transitions between them.

```
std OrderLifecycle {
    initial: Draft

    state Draft {
        description: "Order being prepared"
    }

    state Submitted {
        description: "Order submitted for processing"
    }

    state Approved {
        description: "Order approved, ready for fulfillment"
    }

    state Shipped {
        description: "Order shipped to customer"
    }

    state Delivered {
        description: "Order delivered"
    }

    state Cancelled {
        description: "Order cancelled"
    }

    transition submit: Draft -> Submitted {
        trigger: "customer_submits"
    }

    transition approve: Submitted -> Approved {
        trigger: "manager_approves"
        guard: "inventory_available"
    }

    transition ship: Approved -> Shipped {
        trigger: "warehouse_ships"
    }

    transition deliver: Shipped -> Delivered {
        trigger: "delivery_confirmed"
    }

    transition cancel: Draft -> Cancelled {
        trigger: "customer_cancels"
    }

    transition reject: Submitted -> Cancelled {
        trigger: "manager_rejects"
    }
}
```

### Structure Charts

Structure charts show the hierarchical decomposition of modules and their coupling.

```
structure PaymentProcessor {
    module Main {
        description: "Entry point"
        calls: [Initialize, ProcessPayments, Shutdown]
    }

    module Initialize {
        description: "System startup"
        calls: [LoadConfig, ConnectGateway]
    }

    module LoadConfig {
        data_couple: ConfigData
    }

    module ConnectGateway {
        data_couple: GatewayCredentials
        control_couple: ConnectionStatus
    }

    module ProcessPayments {
        description: "Main processing loop"
        calls: [ValidatePayment, ExecutePayment, RecordTransaction]
    }

    module ValidatePayment {
        data_couple: PaymentData
        control_couple: ValidationResult
    }

    module ExecutePayment {
        data_couple: PaymentRequest
        control_couple: PaymentStatus
    }

    module RecordTransaction {
        data_couple: TransactionRecord
    }

    module Shutdown {
        description: "Graceful shutdown"
        calls: [SaveState, Disconnect]
    }

    module SaveState {
        data_couple: SystemState
    }

    module Disconnect {
        control_couple: DisconnectStatus
    }
}
```

### Data Dictionary

Data dictionaries define reusable data types, structures, and enumerations.

```
datadict {
    // Enumeration (union of string literals)
    OrderStatus = "draft" | "submitted" | "approved" | "shipped" | "delivered" | "cancelled"

    PaymentMethod = "credit_card" | "debit_card" | "bank_transfer" | "paypal"

    // Structured types
    Address = {
        street: string
        city: string
        state: string [optional]
        postal_code: string [pattern: "[0-9]{5}(-[0-9]{4})?"]
        country: string
    }

    Money = {
        amount: decimal [min: 0]
        currency: string [pattern: "[A-Z]{3}"]
    }

    OrderItem = {
        product_id: integer
        quantity: integer [min: 1]
        unit_price: Money
        discount: decimal [optional, min: 0, max: 100]
    }

    // Array types with constraints
    OrderItems = OrderItem[] [min: 1, max: 100]

    // Reference other types
    Order = {
        id: integer
        customer_id: integer
        status: OrderStatus
        items: OrderItems
        shipping_address: Address
        billing_address: Address
        total: Money
        created_at: datetime
    }

    // Placeholder for types to be defined later
    ShippingOptions = TBD
}
```

**Field constraints:**
- `optional` - Field is not required
- `pattern: "regex"` - Must match pattern
- `min: N` - Minimum value (for numbers) or length (for arrays)
- `max: N` - Maximum value or length

### Multi-File Projects

Split large designs across multiple files using imports:

```
// main.dit
import "./models/user.dit"
import "./models/order.dit"
import "./flows/checkout.dit"

dfd MainSystem {
    // Can reference entities from imported files
    ...
}
```

### Placeholders

Use `...` or `TBD` to mark incomplete sections:

```
dfd IncompleteSystem {
    process PaymentGateway {
        ...  // Details to be added
    }

    process ShippingIntegration {
        description: "Integration with shipping providers"
        TBD
    }
}

datadict {
    FutureFeature = TBD
}
```

List all placeholders in a design:

```bash
designit placeholders mydesign.dit
```

## CLI Reference

### Parse a file

Display the parsed structure of a design file:

```bash
designit parse design.dit

# Without resolving imports
designit parse design.dit --no-imports
```

### Validate a file

Check a design for errors and warnings:

```bash
designit check design.dit

# Treat warnings as errors
designit check design.dit --strict

# Without resolving imports
designit check design.dit --no-imports
```

### Generate diagrams

Export designs to diagram formats:

```bash
# Generate all diagrams as Mermaid (default)
designit generate design.dit -f mermaid

# Generate as Graphviz DOT
designit generate design.dit -f dot

# Output to specific directory
designit generate design.dit -o ./diagrams

# Generate specific diagram only
designit generate design.dit -d BankingSystem

# Print to stdout instead of files
designit generate design.dit -f mermaid --stdout

# Exclude placeholder elements
designit generate design.dit --no-placeholders
```

### List placeholders

Find all TBD/placeholder sections:

```bash
designit placeholders design.dit
```

### Start LSP server

Start the Language Server Protocol server (used by editors):

```bash
designit lsp
```

## IDE Integration

### Visual Studio Code

A VS Code extension is included in the `vscode-extension/` directory.

#### Installation from VSIX

1. Build the extension (or download from releases):
   ```bash
   cd vscode-extension
   npm install
   npm run package
   ```

2. Install the generated `.vsix` file:
   ```bash
   code --install-extension vscode-extension/designit-0.1.0.vsix
   ```

   Or in VS Code: Extensions (Ctrl+Shift+X) > `...` menu > "Install from VSIX..."

3. Open any `.dit` file - language support activates automatically.

#### Features

- Syntax highlighting
- Real-time error diagnostics
- Code completion (Ctrl+Space)
- Hover documentation
- Document outline

#### Requirements

The extension requires `designit` to be installed and available in your PATH:

```bash
pip install designit
# or
pipx install designit
```

#### Configuration

- `designit.server.path`: Custom path to the `designit` executable (default: `"designit"`)
- `designit.trace.server`: LSP trace level for debugging (`"off"`, `"messages"`, `"verbose"`)

See the [extension README](vscode-extension/README.md) for more details.
-extension
### IntelliJ IDEA / WebStorm / PyCharm

#### Option 1: LSP Support via Plugin

1. Install the [LSP4IJ](https://plugins.jetbrains.com/plugin/23257-lsp4ij) plugin from the JetBrains Marketplace.

2. Go to **Settings/Preferences > Languages & Frameworks > Language Server Protocol > Server Definitions**.

3. Click **+** to add a new server:
   - **Name:** DesignIt
   - **Command:** `designit`
   - **Arguments:** `lsp`
   - **File patterns:** `*.dit`

4. Apply and restart the IDE.

#### Option 2: External Tools Integration

If LSP isn't available, you can still integrate DesignIt as an external tool:

1. Go to **Settings/Preferences > Tools > External Tools**.

2. Click **+** to add new tools:

**Validate DesignIt File:**
- Name: `DesignIt Check`
- Program: `designit`
- Arguments: `check $FilePath$`
- Working directory: `$ProjectFileDir$`

**Generate Mermaid Diagram:**
- Name: `DesignIt Generate Mermaid`
- Program: `designit`
- Arguments: `generate $FilePath$ -f mermaid -o $FileDir$`
- Working directory: `$ProjectFileDir$`

3. Access these tools via **Tools > External Tools** or assign keyboard shortcuts.

#### File Type Association

1. Go to **Settings/Preferences > Editor > File Types**.

2. Click **+** to add a new file type:
   - Name: `DesignIt`
   - Line comment: `//`
   - Block comment start: `/*`
   - Block comment end: `*/`

3. Add `*.dit` to the registered patterns.

4. Optionally, add keywords for basic syntax highlighting in the file type configuration.

### Other Editors

DesignIt's LSP server follows the Language Server Protocol standard, so it can work with any editor that supports LSP:

- **Neovim:** Use [nvim-lspconfig](https://github.com/neovim/nvim-lspconfig) with a custom configuration
- **Emacs:** Use [lsp-mode](https://github.com/emacs-lsp/lsp-mode) or [eglot](https://github.com/joaotavora/eglot)
- **Sublime Text:** Use [LSP](https://packagecontrol.io/packages/LSP) package
- **Helix:** Add to `languages.toml`

Example for Neovim with nvim-lspconfig:

```lua
local lspconfig = require('lspconfig')
local configs = require('lspconfig.configs')

configs.designit = {
    default_config = {
        cmd = { 'designit', 'lsp' },
        filetypes = { 'designit' },
        root_dir = lspconfig.util.root_pattern('.git', 'pyproject.toml'),
        settings = {},
    },
}

lspconfig.designit.setup{}
```

## Examples

The `examples/` directory contains complete examples:

- `examples/banking/` - A multi-file banking system design with DFDs, ERDs, STDs, and structure charts

Run the examples:

```bash
# Parse the main file (includes imports)
designit parse examples/banking/main.dit

# Validate
designit check examples/banking/main.dit

# Generate all diagrams
designit generate examples/banking/main.dit -f mermaid -o ./output

# List placeholders
designit placeholders examples/banking/main.dit
```

## License

MIT License - see LICENSE file for details.

## Contributing

Contributions are welcome! Please feel free to submit issues and pull requests.

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `uv run pytest tests/ -v`
5. Submit a pull request
