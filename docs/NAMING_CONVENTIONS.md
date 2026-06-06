# Naming conventions

## Product and package names

- Repo name: `local-llm-router` (kebab-case for URLs; legacy folder `split-stack` may still exist on disk)
- Python package: `local_llm_router` (snake_case import style)
- PyPI distribution: `local-llm-router`
- CLI command: `llm-router` (primary); `stack` is a deprecated alias

## Module names

Use lowercase snake_case nouns by responsibility:

- `models.py`: shared dataclasses and enums
- `tiering.py`: model tier assignment logic
- `complexity.py`: prompt complexity scoring
- `advice.py`: Local LLM Router recommendations and warnings
- `discovery.py`: optional external model discovery (Ollama)
- `requirements.py`: usage profiles and prerequisite catalog
- `benchmark.py`: fixed prompt benchmark for routing evidence
- `model_registry.py`: local model table, weights, VRAM hints
- `local_models.py`: discover + filter models for routing
- `ollama_generate.py`: Ollama generate helper for CLI `ask` command
- `cli.py`: argument parsing and user-facing output only

## Symbol names

- Classes: PascalCase (`TierMap`, `StackAdvice`)
- Functions: snake_case (`assign_tiers`, `score_prompt`)
- Enum members: UPPER_SNAKE_CASE (`SIMPLE`, `MEDIUM`, `COMPLEX`, `REASONING`)
- Constants: UPPER_SNAKE_CASE (`DEFAULT_PROFILE`)

## API boundaries

- Export public API through `local_llm_router.__init__`
- Keep `cli.py` as a consumer, not a source of business logic
- Keep optional integrations (Ollama, emitters) out of core logic paths

## Monorepo layout

- Python library: `src/local_llm_router/`
- VS Code companion: `extension/vscode/`
- Extension command IDs: `localLlmRouter.*` (e.g. `localLlmRouter.quickAsk`)
- Extension settings: `localLlmRouter.pythonPath`, `localLlmRouter.ollamaBaseUrl`

## Legacy names (do not use in new code)

| Legacy | Replacement |
| --- | --- |
| `split-stack` (PyPI) | `local-llm-router` |
| `split_stack` (import) | `local_llm_router` |
| `stack` (CLI only) | `llm-router` |
| `splitstack.*` (VS Code) | `localLlmRouter.*` |
| `SPLIT_STACK_MODELS_CONFIG` | `LOCAL_LLM_ROUTER_MODELS_CONFIG` |
| `split-stack.models.json` | `local-llm-router.models.json` |
