from __future__ import annotations

from dataclasses import dataclass

from local_llm_router.discovery import discover_models
from local_llm_router.local_models import list_local_models
from local_llm_router.ollama_errors import format_ollama_error
from local_llm_router.routing import route_prompt
from local_llm_router.tiering import assign_tiers


@dataclass(frozen=True)
class RouteResult:
    tier: str
    model: str
    ready: bool
    error: str | None = None


@dataclass(frozen=True)
class AskResult:
    tier: str
    model: str
    text: str
    ready: bool
    error: str | None = None


def _resolve_model_names(
    *,
    base_url: str,
    model_names: list[str] | None,
    config_path: str | None = None,
    only_vram_ok: bool = True,
) -> tuple[list[str], str | None]:
    if model_names:
        return model_names, None
    resolved, warning = list_local_models(
        base_url=base_url,
        config_path=config_path,
        only_vram_ok=only_vram_ok,
    )
    if resolved:
        return [item.name for item in resolved], warning
    return discover_models(base_url=base_url), warning


def route_prompt_json(
    prompt: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    model_names: list[str] | None = None,
    config_path: str | None = None,
    only_vram_ok: bool = True,
    hint: str | None = None,
    mode: str | None = None,
) -> RouteResult:
    try:
        names, _warning = _resolve_model_names(
            base_url=base_url,
            model_names=model_names,
            config_path=config_path,
            only_vram_ok=only_vram_ok,
        )
        if not names:
            return RouteResult(tier="", model="", ready=False, error="No models available")
        tiers = assign_tiers(names)
        tier, model = route_prompt(prompt, tiers, hint=hint, mode=mode)
        return RouteResult(tier=tier.value, model=model, ready=True)
    except Exception as exc:
        return RouteResult(tier="", model="", ready=False, error=str(exc))


def generate_text(
    model: str,
    prompt: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    timeout_seconds: int = 60,
) -> str:
    try:
        import requests
    except ImportError as exc:
        raise RuntimeError(
            "generate_text requires optional dependency: pip install local-llm-router[ollama]"
        ) from exc

    try:
        response = requests.post(
            f"{base_url.rstrip('/')}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=timeout_seconds,
        )
        response.raise_for_status()
    except Exception as exc:
        raise RuntimeError(format_ollama_error(exc, model=model, base_url=base_url)) from exc
    payload = response.json() or {}
    return payload.get("response", "").strip()


def ask_prompt_json(
    prompt: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    model_names: list[str] | None = None,
    timeout_seconds: int = 60,
    config_path: str | None = None,
    only_vram_ok: bool = True,
    hint: str | None = None,
) -> AskResult:
    routed = route_prompt_json(
        prompt,
        base_url=base_url,
        model_names=model_names,
        config_path=config_path,
        only_vram_ok=only_vram_ok,
        hint=hint,
    )
    if not routed.ready:
        return AskResult(tier="", model="", text="", ready=False, error=routed.error)
    try:
        text = generate_text(
            routed.model,
            prompt,
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        return AskResult(tier=routed.tier, model=routed.model, text=text, ready=True)
    except Exception as exc:
        return AskResult(
            tier=routed.tier,
            model=routed.model,
            text="",
            ready=False,
            error=str(exc),
        )
