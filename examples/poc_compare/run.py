"""Compare POC: local-llm-router routing vs always-largest on the 5-step agent loop."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict

from local_llm_router.compare import format_compare_text, run_compare


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Compare local-llm-router routing vs always-largest baseline",
    )
    parser.add_argument("--live", action="store_true", help="Call Ollama per step (slow)")
    parser.add_argument("--json", action="store_true", help="Print JSON results")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--models",
        default="gemma4:e4b,qwen3:8b,qwen3:14b",
        help="Comma-separated model stack",
    )
    parser.add_argument("--timeout", type=int, default=90, help="Ollama request timeout in seconds")
    args = parser.parse_args()

    model_names = [part.strip() for part in args.models.split(",") if part.strip()]
    report = run_compare(
        model_names=model_names,
        base_url=args.base_url,
        dry_run=not args.live,
        timeout_seconds=args.timeout,
    )

    if args.json:
        payload = {
            "models": list(report.models),
            "rows": [asdict(row) for row in report.rows],
            "summary": asdict(report.summary),
        }
        print(json.dumps(payload, indent=2))
    else:
        print(format_compare_text(report))

    if not args.live:
        print("\nDry run only (routing). Re-run with --live to measure Ollama latency per step.")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
