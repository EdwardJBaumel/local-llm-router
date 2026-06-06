# Split Stack — VS Code / Cursor companion (optional demo)

**Not the product.** This is a thin Quick Ask panel so professionals can try routing visually. The product is the Python library (`route_prompt`, `assign_tiers`) for agent-loop builders — see the [root README](../../README.md).

Pull-based Quick Ask panel for local Ollama Q&A with transparent tier routing.

**Works in VS Code and Cursor.** Cursor is a VS Code fork — load this extension the same way (F5 Extension Development Host, or install a built VSIX). No separate Cursor build required.

This extension is a thin client over the Python library. It does not reimplement routing logic and does not hook into Cursor chat.

## Prerequisites

1. Python 3.10+
2. From repo root: `python -m pip install -e ".[ollama]"`
3. Ollama running with at least one model pulled
4. Verify: `stack requirements local_assistant --check`

## Development

```bash
cd extension/vscode
npm install
npm run compile
```

Press F5 in VS Code to launch Extension Development Host.

## Usage

1. Command palette → **Split Stack: Quick Ask**
2. Type a question and click Ask
3. Panel shows tier, model, and answer

## Settings

| Setting | Default | Description |
| --- | --- | --- |
| `splitstack.pythonPath` | `python` | Python executable with split-stack installed |
| `splitstack.ollamaBaseUrl` | `http://127.0.0.1:11434` | Ollama base URL |

## Architecture

Extension spawns: `python -m split_stack ask --prompt "..." --json --base-url ...`

See root README and `docs/USER_STORIES.md`.
