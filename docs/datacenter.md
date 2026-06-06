# Datacenter deployment

local-llm-router is builder-first: it picks a model **name** from your catalog. Your gateway or inference service generates text. Workstation users get VRAM presets; datacenter teams bring a custom catalog.

## When to use `datacenter`

Use `deployment_profile: datacenter` when:

- Models run on a private fleet (vLLM, TGI, internal Ollama, LiteLLM proxy, etc.)
- VRAM on the operator laptop is irrelevant
- You maintain your own model naming and weight table

VRAM hints in config are optional labels only. Nothing is filtered out.

## Config

Copy the template:

```bash
cp config/models.datacenter.example.json local-llm-router.models.json
```

Minimum shape:

```json
{
  "deployment_profile": "datacenter",
  "models": [
    { "match": "prod-small", "weight": 4000, "family": "internal" },
    { "match": "prod-large", "weight": 30000, "family": "internal" }
  ]
}
```

`match` is a substring on discovered model names. `weight` ranks tiers (higher = bigger). Add `vram_gb` if you want documentation in `llm-router models` output; it does not affect routing.

## CLI

```bash
llm-router profiles
llm-router models --profile datacenter
llm-router doctor --profile datacenter
```

With a datacenter config file, profile is inferred automatically:

```bash
llm-router models --json
```

## Wiring inference

local-llm-router does not call your datacenter API directly. Typical pattern:

1. `llm-router route --prompt "..." --json --models prod-small,prod-large,...`
2. Pass `model` from JSON into LiteLLM, an OpenAI-compatible client, or your gateway
3. See [`integrations/litellm.md`](integrations/litellm.md) for a router recipe

Point `--base-url` at any Ollama-compatible discovery endpoint if you use tag listing for fleet inventory.

## Workstation presets (for comparison)

| Profile | assumed_vram_gb | VRAM filter |
| --- | --- | --- |
| `workstation_8gb` | 8 | on |
| `workstation_12gb` | 12 | on (default) |
| `workstation_16gb` | 16 | on |
| `workstation_24gb` | 24 | on |
| `workstation_32gb` | 32 | on |
| `datacenter` | n/a | off |

Aliases: `8gb`, `12gb`, `16gb`, `24gb`, `32gb`, `workstation` → `workstation_12gb`.

Dual-GPU, A6000, Apple unified 48 GB+ and fleet cards: no preset. Use `datacenter` or set `assumed_vram_gb` in config.

Override on the CLI without editing config:

```bash
llm-router models --profile workstation_16gb
```
