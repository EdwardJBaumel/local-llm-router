# User stories

## Epic A — Tool builder (library primary user)

| ID | Story | Acceptance |
| --- | --- | --- |
| A1 | As a **tool builder**, I want to call `route_prompt(prompt, tiers)` with my own model list, so that I can pick a model without a SaaS router. | Works offline; pytest passes; no network required |
| A2 | As a **tool builder**, I want `assign_tiers(model_names)` to rank models by name heuristics, so that I do not hand-maintain tier maps. | Empty list raises; ordering tested in `tests/test_tiering.py` |
| A3 | As a **tool builder**, I want `usage_requirements(profile, check=True)`, so that I know what to install before integrating Ollama. | CLI + API return same catalog |
| A4 | As a **tool builder**, I want a stable public API exported from `local_llm_router.__init__`, so that I can depend on semver later. | `__all__` documented in README |

## Epic B — Professional dev (extension secondary user)

| ID | Story | Acceptance |
| --- | --- | --- |
| B1 | As a **professional in VS Code or Cursor**, I want **Local LLM Router: Quick Ask** in the command palette, so that I can get a local answer without leaving the editor. | Command registered; opens panel |
| B2 | As a **professional**, I want to type a question and see **tier + model + answer**, so that routing is transparent (not a black box). | Panel shows `Routed to qwen3:4b (simple)` before answer |
| B3 | As a **professional**, I want to configure Ollama URL in settings, so that non-default installs work. | `localLlmRouter.ollamaBaseUrl` setting |
| B4 | As a **professional**, I want a clear error when Ollama is down, so that I am not stuck silent-failing. | Actionable message + hint to run `stack requirements local_assistant --check` |
| B5 | As a **professional**, I do **not** want popups telling me my Cursor question is "easy", so that the tool stays out of my way. | No chat hooks; no proactive nudge |

## Epic C — Maintainer / resume

| ID | Story | Acceptance |
| --- | --- | --- |
| C1 | As **Eddie**, I want **local-llm-router** to stand alone as a routing library on my resume, with Local Recruiting Ops linked only as a separate sibling project. | Root README leads with library positioning; related-project table at bottom; no merged repo story |
| C2 | As **Eddie**, I want CI green on library tests, so that cloud agents can contribute safely. | GitHub Actions pytest job |
| C3 | As **Eddie**, I want a 30-second demo path, so that README shows agent-runner routing (extension optional). | Hero demo: `examples/agent_runner/run.py`; extension demoted to optional footnote |
