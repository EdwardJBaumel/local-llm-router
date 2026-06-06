"""Quantization assumptions for VRAM sizing — not per-prompt routing.

Ollama tags (``gemma4:e4b``) do not encode quant. ``quant=`` tells local-llm-router which
pull format you use so VRAM filters and QAT-aware stack suggestions stay honest.
"""

from __future__ import annotations

import os

QUANT_MODES: tuple[str, ...] = ("default", "qat", "qat_mobile", "bf16")

# Runtime memory (GB) from Unsloth Gemma 4 QAT docs — UD-Q4_K_XL, not naive Q4_0.
_GEMMA4_QAT_RUNTIME_GB: dict[str, int] = {
    "gemma4:e2b": 3,
    ":e2b": 3,
    "gemma4:e4b": 5,
    ":e4b": 5,
    "gemma4:12b": 7,
    "gemma4:26b-a4b": 15,
    "gemma4:26b": 15,
    "gemma4:31b": 18,
}

# Google mobile mixture QAT (UD-Q2_K_XL class).
_GEMMA4_QAT_MOBILE_RUNTIME_GB: dict[str, int] = {
    "gemma4:e2b": 3,
    ":e2b": 3,
    "gemma4:e4b": 4,
    ":e4b": 4,
}

# BF16 original sizes (Unsloth table, rounded up for filter headroom).
_GEMMA4_BF16_RUNTIME_GB: dict[str, int] = {
    "gemma4:e2b": 10,
    ":e2b": 10,
    "gemma4:e4b": 16,
    ":e4b": 16,
    "gemma4:12b": 24,
    "gemma4:26b-a4b": 51,
    "gemma4:26b": 51,
    "gemma4:31b": 62,
}

# Extra models that fit when Gemma pulls use QAT int4 (Unsloth hardware table).
QAT_STACK_ADDITIONS: dict[str, tuple[str, ...]] = {
    "workstation_16gb": ("gemma4:26b-a4b",),
    "workstation_24gb": ("gemma4:31b",),
}


def normalize_quant_mode(name: str | None) -> str:
    if not name:
        return "default"
    lowered = name.strip().lower().replace("-", "_")
    aliases = {
        "off": "default",
        "none": "default",
        "q4": "qat",
        "q4_qat": "qat",
        "qat_q4": "qat",
        "mobile": "qat_mobile",
        "qat_mobile_mixture": "qat_mobile",
        "fp16": "bf16",
        "full": "bf16",
    }
    lowered = aliases.get(lowered, lowered)
    if lowered not in QUANT_MODES:
        valid = ", ".join(QUANT_MODES)
        raise ValueError(f"Unknown quant mode '{name}'. Valid modes: {valid}")
    return lowered


def quant_from_env() -> str | None:
    raw = os.environ.get("local_llm_router_QUANT", "").strip()
    return raw or None


def _lookup_table_vram(name: str, table: dict[str, int]) -> int | None:
    lowered = name.lower()
    best_gb: int | None = None
    best_len = -1
    for key, gb in table.items():
        if key in lowered and len(key) > best_len:
            best_gb = gb
            best_len = len(key)
    return best_gb


def adjust_vram_for_quant(
    name: str,
    base_vram_gb: int | None,
    quant_mode: str | None,
) -> int | None:
    """Return effective VRAM for feasibility checks; does not change routing weight."""
    mode = normalize_quant_mode(quant_mode)
    if mode == "default":
        return base_vram_gb
    tables = {
        "qat": _GEMMA4_QAT_RUNTIME_GB,
        "qat_mobile": _GEMMA4_QAT_MOBILE_RUNTIME_GB,
        "bf16": _GEMMA4_BF16_RUNTIME_GB,
    }
    matched = _lookup_table_vram(name, tables[mode])
    if matched is not None:
        return matched
    return base_vram_gb


def expand_models_for_quant(models: list[str], profile: str, quant_mode: str | None) -> list[str]:
    """Add QAT-feasible models to a recommended stack (Gemma 4 only today)."""
    if normalize_quant_mode(quant_mode) != "qat":
        return models
    profile_name = profile.strip().lower()
    extras = QAT_STACK_ADDITIONS.get(profile_name, ())
    out = list(models)
    for name in extras:
        if name not in out:
            out.append(name)
    return out


def pull_guidance_lines(quant_mode: str | None) -> list[str]:
    """Short pull hints for docs/CLI — not import-time spam."""
    mode = normalize_quant_mode(quant_mode)
    if mode == "default":
        return []
    if mode == "qat":
        return [
            "Gemma 4 QAT: prefer Unsloth UD-Q4_K_XL GGUF over naive Google Q4_0 for llama.cpp/Ollama imports.",
            "Collections: google/gemma-4-qat-q4_0, unsloth/gemma-4-qat — see docs/local-models.md",
        ]
    if mode == "qat_mobile":
        return [
            "Gemma 4 mobile mixture QAT: google/gemma-4-qat-mobile (UD-Q2_K_XL on E2B/E4B).",
        ]
    return ["Gemma 4 BF16 pulls need datacenter profile or custom vram_gb in config."]
