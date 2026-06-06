# Backlog

Ideas not in scope for the current release.

## Local model freshness / QoL check

**Problem:** Users may not know if pulled Ollama tags are stale vs upstream (Unsloth QAT revs, new Qwen releases).

**Done (Layer 1 — offline):**

- `stack doctor --check-stack` and `split_stack.check_stack_health()`
- Missing recommended tags, duplicate folders, routing spread (< 2 models)

**Done (Layer 2 — quant honesty):**

- Same command flags — warns when `quant=qat|qat_mobile|bf16` but installed Gemma looks like library PTQ
- Uses `/api/tags` size + `quantization_level` + tag heuristics; WARN only

**Future (Layer 3 — upstream stale):**

- `stack doctor --check-updates --online` (proposed; not implemented)
- Prefer Ollama `POST /api/v1/model/upstream` when the server supports it
- Fallback: shipped `known_digests.json` per split-stack release
- See design notes in project discussions — version-gate on Ollama API

**Separate from routing.** Track here before opening an issue.

## Community picks

`community_picks.json` stays reference-only — not primary UI or routing input.
