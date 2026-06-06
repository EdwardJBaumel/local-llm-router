# Naming conventions

## Product and package names

- Repo name: `split-stack` (kebab-case for URLs)
- Python package: `split_stack` (snake_case import style)
- CLI command: `stack` (short and consistent)

## Module names

Use lowercase snake_case nouns by responsibility:

- `models.py`: shared dataclasses and enums
- `tiering.py`: model tier assignment logic
- `complexity.py`: prompt complexity scoring
- `advice.py`: split-stack recommendations and warnings
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

- Export public API through `split_stack.__init__`
- Keep `cli.py` as a consumer, not a source of business logic
- Keep optional integrations (Ollama, emitters) out of core logic paths

## Monorepo layout

- Python library: `src/split_stack/`
- VS Code companion: `extension/vscode/`
- Extension command IDs: `splitstack.*` (e.g. `splitstack.quickAsk`)
- Extension settings: `splitstack.pythonPath`, `splitstack.ollamaBaseUrl`
