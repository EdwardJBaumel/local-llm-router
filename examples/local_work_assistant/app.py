from __future__ import annotations

import argparse
from dataclasses import dataclass

from split_stack import assign_tiers, discover_models, route_prompt
from split_stack.models import TierMap


@dataclass
class RoutedResponse:
    tier: str
    model: str
    text: str


class LocalWorkAssistant:
    def __init__(self, ollama_base_url: str = "http://127.0.0.1:11434", timeout_seconds: int = 60):
        self.ollama_base_url = ollama_base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds
        self.tiers = self._load_tiers()

    def _load_tiers(self) -> TierMap:
        models = discover_models(base_url=self.ollama_base_url)
        return assign_tiers(models)

    def _generate(self, model: str, prompt: str) -> str:
        try:
            import requests
        except ImportError as exc:
            raise RuntimeError("This app requires requests. Install with: pip install split-stack[ollama]") from exc

        response = requests.post(
            f"{self.ollama_base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
            },
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json() or {}
        return payload.get("response", "").strip()

    def ask(self, prompt: str) -> RoutedResponse:
        tier, model = route_prompt(prompt, self.tiers)
        text = self._generate(model, prompt)
        return RoutedResponse(tier=tier.value, model=model, text=text)


def _print_tiers(tiers: TierMap) -> None:
    print("Loaded model tiers")
    print(f"  SIMPLE:    {tiers.simple}")
    print(f"  MEDIUM:    {tiers.medium}")
    print(f"  COMPLEX:   {tiers.complex}")
    print(f"  REASONING: {tiers.reasoning}")
    print("")


def _interactive_mode(assistant: LocalWorkAssistant) -> int:
    _print_tiers(assistant.tiers)
    print("Ask work questions. Type 'exit' to quit.\n")
    while True:
        prompt = input("> ").strip()
        if not prompt:
            continue
        if prompt.lower() in {"exit", "quit"}:
            return 0
        response = assistant.ask(prompt)
        print(f"\nRouted to {response.model} ({response.tier})")
        print(response.text)
        print("")


def main() -> int:
    parser = argparse.ArgumentParser(description="Local work assistant using split-stack routing")
    parser.add_argument("--prompt", type=str, help="Single prompt to run")
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:11434", help="Ollama base URL")
    parser.add_argument("--timeout", type=int, default=60, help="Request timeout in seconds")
    args = parser.parse_args()

    assistant = LocalWorkAssistant(ollama_base_url=args.base_url, timeout_seconds=args.timeout)

    if args.prompt:
        response = assistant.ask(args.prompt)
        print(f"Routed to {response.model} ({response.tier})")
        print(response.text)
        return 0

    return _interactive_mode(assistant)


if __name__ == "__main__":
    raise SystemExit(main())
