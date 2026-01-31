import * as vscode from 'vscode';
import {
    LanguageClient,
    LanguageClientOptions,
    ServerOptions,
    TransportKind
} from 'vscode-languageclient/node';

let client: LanguageClient | undefined;

export async function activate(context: vscode.ExtensionContext): Promise<void> {
    const config = vscode.workspace.getConfiguration('designit');
    const serverPath = config.get<string>('server.path', 'designit');

    // Server options - run designit lsp command
    const serverOptions: ServerOptions = {
        run: {
            command: serverPath,
            args: ['lsp'],
            transport: TransportKind.stdio
        },
        debug: {
            command: serverPath,
            args: ['lsp'],
            transport: TransportKind.stdio
        }
    };

    // Client options
    const clientOptions: LanguageClientOptions = {
        documentSelector: [{ scheme: 'file', language: 'designit' }],
        synchronize: {
            fileEvents: vscode.workspace.createFileSystemWatcher('**/*.dit')
        },
        outputChannelName: 'DesignIt Language Server',
        traceOutputChannel: vscode.window.createOutputChannel('DesignIt LSP Trace')
    };

    // Create the language client
    client = new LanguageClient(
        'designit',
        'DesignIt Language Server',
        serverOptions,
        clientOptions
    );

    // Start the client (this also starts the server)
    try {
        await client.start();
        console.log('DesignIt Language Server started successfully');
    } catch (error) {
        const message = error instanceof Error ? error.message : String(error);
        
        // Check if it's a "command not found" type error
        if (message.includes('ENOENT') || message.includes('not found') || message.includes('spawn')) {
            const action = await vscode.window.showErrorMessage(
                `DesignIt language server not found. Make sure 'designit' is installed and available in your PATH.\n\nInstall with: pip install designit`,
                'Open Installation Guide',
                'Configure Path'
            );

            if (action === 'Open Installation Guide') {
                vscode.env.openExternal(vscode.Uri.parse('https://github.com/yourusername/designit#installation'));
            } else if (action === 'Configure Path') {
                vscode.commands.executeCommand('workbench.action.openSettings', 'designit.server.path');
            }
        } else {
            vscode.window.showErrorMessage(`Failed to start DesignIt Language Server: ${message}`);
        }
        
        throw error;
    }
}

export function deactivate(): Thenable<void> | undefined {
    if (!client) {
        return undefined;
    }
    return client.stop();
}
