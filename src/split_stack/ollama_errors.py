"""Actionable error messages for Ollama HTTP failures."""

from __future__ import annotations


def format_ollama_error(
    exc: BaseException,
    *,
    model: str,
    base_url: str = "http://127.0.0.1:11434",
) -> str:
    """Turn requests/Ollama failures into short fix hints."""
    try:
        import requests
    except ImportError:
        return str(exc)

    if isinstance(exc, requests.Timeout):
        return f"Ollama request timed out for model '{model}' at {base_url}."

    if isinstance(exc, requests.ConnectionError):
        return f"Ollama not reachable at {base_url}. Start Ollama first."

    if isinstance(exc, requests.HTTPError) and exc.response is not None:
        status = exc.response.status_code
        if status == 404:
            return f"Model '{model}' not found. Run: ollama pull {model}"
        return f"Ollama HTTP {status} for model '{model}': {exc.response.reason}"

    return str(exc)
