import * as vscode from "vscode";
import { QuickAskPanel } from "./quickAskPanel";

export function activate(context: vscode.ExtensionContext): void {
  context.subscriptions.push(
    vscode.commands.registerCommand("localLlmRouter.quickAsk", () => {
      QuickAskPanel.createOrShow(context.extensionUri);
    })
  );
}

export function deactivate(): void {}
