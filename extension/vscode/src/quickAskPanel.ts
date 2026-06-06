import { execFile } from "child_process";
import * as vscode from "vscode";
import { promisify } from "util";

const execFileAsync = promisify(execFile);

export interface AskResponse {
  tier: string;
  model: string;
  text: string;
  ready: boolean;
  error?: string | null;
}

export async function runStackAsk(prompt: string): Promise<AskResponse> {
  const config = vscode.workspace.getConfiguration("splitstack");
  const pythonPath = config.get<string>("pythonPath", "python");
  const baseUrl = config.get<string>("ollamaBaseUrl", "http://127.0.0.1:11434");

  try {
    const { stdout } = await execFileAsync(
      pythonPath,
      ["-m", "split_stack", "ask", "--prompt", prompt, "--json", "--base-url", baseUrl],
      { maxBuffer: 10 * 1024 * 1024, windowsHide: true }
    );
    return JSON.parse(stdout.trim()) as AskResponse;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return {
      tier: "",
      model: "",
      text: "",
      ready: false,
      error: `Failed to run split-stack. Check pythonPath and pip install -e ".[ollama]". ${message}`,
    };
  }
}

export class QuickAskPanel {
  public static currentPanel: QuickAskPanel | undefined;
  private readonly panel: vscode.WebviewPanel;
  private disposables: vscode.Disposable[] = [];

  public static createOrShow(extensionUri: vscode.Uri): void {
    if (QuickAskPanel.currentPanel) {
      QuickAskPanel.currentPanel.panel.reveal(vscode.ViewColumn.Beside);
      return;
    }

    const panel = vscode.window.createWebviewPanel(
      "splitstackQuickAsk",
      "Split Stack Quick Ask",
      vscode.ViewColumn.Beside,
      { enableScripts: true, retainContextWhenHidden: true }
    );

    QuickAskPanel.currentPanel = new QuickAskPanel(panel, extensionUri);
  }

  private constructor(panel: vscode.WebviewPanel, extensionUri: vscode.Uri) {
    this.panel = panel;
    this.panel.webview.html = this.getHtml();
    this.panel.onDidDispose(() => this.dispose(), null, this.disposables);

    this.panel.webview.onDidReceiveMessage(
      async (message: { command: string; prompt?: string }) => {
        if (message.command !== "ask" || !message.prompt?.trim()) {
          return;
        }
        this.postMessage({ command: "loading" });
        const result = await runStackAsk(message.prompt.trim());
        this.postMessage({ command: "result", result });
      },
      null,
      this.disposables
    );
  }

  private postMessage(payload: unknown): void {
    void this.panel.webview.postMessage(payload);
  }

  private getHtml(): string {
    return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <style>
    body { font-family: var(--vscode-font-family); padding: 16px; color: var(--vscode-foreground); }
    textarea { width: 100%; min-height: 120px; box-sizing: border-box; }
    button { margin-top: 8px; }
    #meta { margin-top: 12px; color: var(--vscode-descriptionForeground); }
    #output { margin-top: 12px; white-space: pre-wrap; }
    #error { margin-top: 12px; color: var(--vscode-errorForeground); white-space: pre-wrap; }
  </style>
</head>
<body>
  <p>Local quick ask via split-stack + Ollama. Opens on demand — no chat interception.</p>
  <textarea id="prompt" placeholder="Ask a work question..."></textarea>
  <br />
  <button id="ask">Ask</button>
  <div id="meta"></div>
  <div id="output"></div>
  <div id="error"></div>
  <script>
    const vscode = acquireVsCodeApi();
    const promptEl = document.getElementById("prompt");
    const metaEl = document.getElementById("meta");
    const outputEl = document.getElementById("output");
    const errorEl = document.getElementById("error");
    document.getElementById("ask").addEventListener("click", () => {
      metaEl.textContent = "";
      outputEl.textContent = "";
      errorEl.textContent = "";
      vscode.postMessage({ command: "ask", prompt: promptEl.value });
    });
    window.addEventListener("message", (event) => {
      const message = event.data;
      if (message.command === "loading") {
        metaEl.textContent = "Routing and generating...";
        return;
      }
      if (message.command !== "result") {
        return;
      }
      const result = message.result;
      if (!result.ready) {
        errorEl.textContent = (result.error || "Unknown error") +
          "\\n\\nTry: stack requirements local_assistant --check";
        return;
      }
      metaEl.textContent = "Routed to " + result.model + " (" + result.tier + ")";
      outputEl.textContent = result.text || "";
    });
  </script>
</body>
</html>`;
  }

  private dispose(): void {
    QuickAskPanel.currentPanel = undefined;
    this.panel.dispose();
    while (this.disposables.length) {
      const item = this.disposables.pop();
      if (item) {
        item.dispose();
      }
    }
  }
}
