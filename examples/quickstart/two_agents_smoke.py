"""Smoke demo: two agent loops sharing split-stack routing (dry-run, no Ollama required)."""

from __future__ import annotations

from split_stack import assign_recommended_tiers, route_prompt

STACK_12 = assign_recommended_tiers("workstation_12gb")
STACK_16 = assign_recommended_tiers("workstation_16gb")

RESEARCH_AGENT_STEPS = (
    ("lookup", "what is idempotency?", "lookup"),
    ("compare", "compare at-least-once vs exactly-once delivery", "explain"),
    ("design", "design a webhook retry policy for a billing API", "design"),
)

CODE_AGENT_STEPS = (
    ("plan", "outline tests for a Flask webhook handler", "explain"),
    ("implement", "refactor this handler for clearer error paths", "code"),
    ("verify", "debug duplicate charge rows after webhook retries", "code"),
)


def run_agent(name: str, steps: tuple[tuple[str, str, str], ...], tiers) -> None:
    print(f"\n=== {name} ===")
    for step_name, prompt, hint in steps:
        tier, model = route_prompt(prompt, tiers, hint=hint)
        print(f"  [{step_name}] hint={hint:7} tier={tier.value:9} -> {model}")
        print(f"           prompt: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")


def main() -> int:
    print("split-stack two-agent smoke (routing only)")
    print("Stack A (research, 12 GB):", "gemma4:e4b / qwen3:8b / qwen3:14b / deepseek-r1:8b")
    print("Stack B (code, 16 GB): adds deepseek-coder:6.7b for code hints")

    run_agent("Agent A — product research", RESEARCH_AGENT_STEPS, STACK_12)
    run_agent("Agent B — implementation", CODE_AGENT_STEPS, STACK_16)

    print("\nIn production each line above becomes:")
    print("  model = route_prompt(...)[1]")
    print("  text  = ollama.generate(model, prompt)  # or LiteLLM, vLLM, etc.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
