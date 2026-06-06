# Decision log

This file captures core product and architecture decisions for portfolio context and future onboarding.

## 2026-05-25 - Chosen direction: library-first

### Decision
Build `split-stack` as an importable Python library first, with CLI and docs as wrappers.

### Why
- Existing router products already compete on full proxy UX (CodeRouter, 9Router, kani, LiteLLM ecosystem).
- Library primitives are reusable and operationally lighter.
- Better fit for a niche audience (tool builders) and stronger portfolio signal for product judgement.

### Tradeoff
- Smaller addressable audience than a broad end-user app.
- Requires clear docs so non-builders still get value without installing anything.

## 2026-05-25 - Primary user: tool builders

### Decision
Primary user is a Python developer embedding routing logic into their own gateway or agent runner.

### Why
- They directly benefit from importable primitives (`score_prompt`, `assign_tiers`).
- They can integrate without adopting a monolithic proxy product.

### Secondary users
- End users who only need guidance consume docs and may never install the package.

## 2026-05-25 - Keep Ollama optional

### Decision
Do not require Ollama in the happy path.

### Why
- Mandatory local infra increases onboarding friction.
- Core API can be useful with provider model-name lists only.

### Implementation consequence
- `assign_tiers(model_names)` works without network calls.
- `discover_models()` is optional convenience for local-first workflows.

## 2026-05-25 - Free positioning

### Decision
MIT licence and no hosted billing product in v0.x.

### Why
- Fast developer adoption
- Clear differentiation vs paid router SaaS
- Keeps scope focused on composable primitives over platform operations

### Clarification
"Free" means this tooling is free. Upstream inference may still cost money (Cursor seat, cloud API keys, compute, electricity).

## 2026-05-25 - Split-stack policy stance

### Decision
Default guidance keeps Cursor native for agentic coding, with routing library usage for scripts and tools.

### Why
- Reduces risk of degraded agent/tool-call behaviour through generic proxy layers
- Preserves Cursor-native capabilities where reliability matters most

## 2026-05-25 - Example app choice: local work assistant

### Decision
Ship a concrete example app that routes everyday work prompts (quick Q&A, design, debugging) across local Ollama tiers.

### Why
- Demonstrates the product in the shortest path from install to value
- Shows transparent prompt-to-model routing decisions per request
- Matches the "split stack" policy: local routing for direct questions, Cursor native for agentic coding

### Tradeoff
- Example is intentionally local-first and does not represent cloud multi-provider routing

## 2026-05-25 - Monorepo: library + optional VS Code demo

### Decision
Ship one repo with Python library (`src/split_stack/`) and an optional pull-based VS Code extension (`extension/vscode/`).

### Why
- Library is the product; extension proves routing without duplicating logic
- Extension consumes library via `stack ask --json` (no duplicated routing logic in TypeScript)
- Builders integrate via imports; extension is a secondary demo path

### Tradeoff
- Extension requires Python + Ollama on the user's machine
- Two toolchains (pip + npm) in one repo — README must keep extension demoted so marketing stays library-first

## 2026-05-25 - No proactive nudge in extension

### Decision
Extension offers command-palette Quick Ask only. No chat interception, no "this question is easy" popups.

### Why
- Professionals find proactive coaching patronising
- Preserves Cursor Agent reliability (no proxy override)

### Implementation consequence
- No hooks into Cursor/VS Code chat APIs
- Panel opens only when user runs `Split Stack: Quick Ask`
- Same extension package runs in VS Code and Cursor (VS Code fork compatibility)

## 2026-05-26 - Builder-first pivot (brutal scope)

### Decision
Primary product story is agent-loop routing for builders, not human terminal UX or IDE nudge flows.

### Why
- Human-facing use (pip + Ollama + terminal/F5) is too much friction to prove value
- Builders integrate once (`route_prompt` per step); humans should use host apps that embed it
- Credibility requires evidence: fixed benchmark + agent runner demo

### Implementation consequence
- Hero demo: `examples/agent_runner/run.py`
- `stack benchmark` for 10-prompt routing table (CI-safe, no inference)
- LiteLLM integration recipe doc, not a full plugin
- Extension demoted to optional demo footnote in README
