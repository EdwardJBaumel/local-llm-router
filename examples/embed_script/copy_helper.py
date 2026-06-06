"""Embed local-llm-router in a small script (copy, outlines, quick research).

Usage:
    python copy_helper.py "suggest 5 hero taglines for a portfolio site"
    python copy_helper.py "outline a projects page structure"
"""

from __future__ import annotations

import argparse
import sys

from local_llm_router import UsageProfile, assign_tiers, discover_models, route_prompt, usage_requirements


def _check_ready() -> bool:
    report = usage_requirements(UsageProfile.LOCAL_ASSISTANT, check=True)
    if report.ready:
        return True
    print("Missing prerequisites for local copy helper:\n", file=sys.stderr)
    for item in report.prerequisites:
        if item.required and item.satisfied is False:
            print(f"  - {item.description}", file=sys.stderr)
            if item.install_command:
                print(f"    install: {item.install_command}", file=sys.stderr)
    print("\nRun: stack requirements local_assistant --check", file=sys.stderr)
    return False


def _generate(base_url: str, model: str, prompt: str, timeout: int = 90) -> str:
    import requests

    response = requests.post(
        f"{base_url.rstrip('/')}/api/generate",
        json={"model": model, "prompt": prompt, "stream": False},
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json() or {}
    return payload.get("response", "").strip()


def ask_local(
    prompt: str,
    *,
    base_url: str = "http://127.0.0.1:11434",
    timeout: int = 90,
) -> tuple[str, str, str]:
    """Return (tier, model, response_text) for a prompt."""
    tiers = assign_tiers(discover_models(base_url=base_url))
    tier, model = route_prompt(prompt, tiers)
    text = _generate(base_url, model, prompt, timeout=timeout)
    return tier.value, model, text


def main() -> int:
    parser = argparse.ArgumentParser(description="Minimal local-llm-router embed for side-project scripts")
    parser.add_argument("prompt", help="Question or copy request")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    args = parser.parse_args()

    if not _check_ready():
        return 1

    tier, model, text = ask_local(args.prompt, base_url=args.base_url)
    print(f"[local-llm-router] tier={tier} model={model}\n")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
