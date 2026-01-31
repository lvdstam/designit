# DesignIt VS Code Extension

Language support for the DesignIt DSL - a language for creating Yourdon-style design documents.

## Features

- **Syntax Highlighting** - Full syntax highlighting for `.dit` files
- **Error Diagnostics** - Real-time error checking and validation
- **Code Completion** - Intelligent suggestions for keywords, types, and constraints
- **Hover Documentation** - Documentation on hover for keywords and constructs
- **Document Outline** - Navigate your design with the document outline view

## Prerequisites

This extension requires the DesignIt CLI to be installed on your system:

```bash
# Using pip
pip install designit

# Using uv
uv add designit

# Using pipx (recommended for CLI tools)
pipx install designit
```

Verify the installation:

```bash
designit --version
```

## Installation

### From VSIX File

1. Download the latest `designit-x.x.x.vsix` file from the [releases page](https://github.com/yourusername/designit/releases)

2. Install via command line:
   ```bash
   code --install-extension designit-x.x.x.vsix
   ```

   Or install via VS Code:
   - Open VS Code
   - Go to Extensions (Ctrl+Shift+X)
   - Click the `...` menu at the top
   - Select "Install from VSIX..."
   - Choose the downloaded file

### From Source (Development)

```bash
cd vscode-extension
npm install
npm run compile
npm run package
```

This creates a `.vsix` file in the `vscode-extension` directory.

## Usage

1. Open a `.dit` file in VS Code
2. The extension activates automatically
3. You'll see:
   - Syntax highlighting
   - Error squiggles for issues
   - Code completion (Ctrl+Space)
   - Hover information on keywords

## Extension Settings

This extension contributes the following settings:

- `designit.server.path`: Path to the `designit` executable (default: `"designit"`)
- `designit.trace.server`: Trace level for LSP communication (`"off"`, `"messages"`, `"verbose"`)

## Troubleshooting

### "DesignIt language server not found"

This error means the `designit` command is not available in your PATH. Solutions:

1. **Install DesignIt**: `pip install designit`

2. **Check your PATH**: Make sure the Python scripts directory is in your PATH:
   ```bash
   # Find where pip installs scripts
   python -m site --user-base
   # Add the bin/Scripts subdirectory to your PATH
   ```

3. **Configure custom path**: If `designit` is installed elsewhere, configure the path:
   - Open VS Code Settings (Ctrl+,)
   - Search for "designit.server.path"
   - Set the full path to the `designit` executable

### Extension not activating

- Make sure you're opening a file with the `.dit` extension
- Check the Output panel (View > Output) and select "DesignIt Language Server"

## Example

Create a file `example.dit`:

```designit
// Simple Data Flow Diagram
dfd OrderSystem {
    external Customer {
        description: "Places orders"
    }

    process ProcessOrder {
        description: "Validates and processes orders"
    }

    datastore OrderDB {
        description: "Order storage"
    }

    flow OrderRequest: Customer -> ProcessOrder
    flow OrderRecord: ProcessOrder -> OrderDB
}
```

## License

MIT License - see the main [DesignIt repository](https://github.com/yourusername/designit) for details.
