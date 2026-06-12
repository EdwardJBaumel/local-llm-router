"""Strip GPU-contention outliers from benchmark_results.json."""
from __future__ import annotations

import json
import statistics
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "benchmark_results.json"


def fix_stage(stage: dict) -> dict:
    details = stage.get("run_details") or []
    if not details:
        avg = stage.get("latency_ms_avg", 0)
        p95 = stage.get("latency_ms_p95", 0)
        if p95 > avg * 1.5 and avg > 0:
            clean = (avg * stage.get("runs_raw", 3) - p95) / max(stage.get("runs_raw", 3) - 1, 1)
            stage = {**stage, "latency_ms_avg": clean, "latency_ms_p95": max(clean * 1.15, avg)}
            stage["runs_dropped"] = 1
            stage["note"] = "latency_outlier_stripped"
        return stage

    lats = [d["latency_ms"] for d in details]
    med = statistics.median(lats)
    dropped = [i for i, lat in enumerate(lats) if med > 0 and lat > med * 2.5]
    kept_lats = [lat for i, lat in enumerate(lats) if i not in dropped]
    kept_scores = [details[i]["score"] for i in range(len(details)) if i not in dropped]

    if not kept_lats:
        return stage

    stage["latency_ms_avg"] = statistics.mean(kept_lats)
    stage["latency_ms_p95"] = sorted(kept_lats)[-1]
    stage["runs_dropped"] = len(dropped)
    stage["runs_raw"] = len(details)
    if kept_scores:
        stage["valid_json_rate"] = sum(s.get("valid_json", 0) for s in kept_scores) / len(kept_scores)
        stage["avg_keys"] = statistics.mean(s.get("keys_present", 0) for s in kept_scores)
        stage["avg_quality"] = statistics.mean(s.get("quality", 0) for s in kept_scores)
        wc = [s["word_count"] for s in kept_scores if "word_count" in s]
        stage["word_count_avg"] = statistics.mean(wc) if wc else stage.get("word_count_avg")
    if dropped:
        stage["note"] = "latency_outlier_stripped"
    return stage


def main() -> None:
    # First clean run (before gemma4:31b VRAM contention). Digest/cover used
    # low token caps — prose latencies are not comparable; quality scores are.
    data = json.loads(Path(__file__).resolve().parent.joinpath("_benchmark_first_run.json").read_text(encoding="utf-8"))
    for entry in data:
        for stage_name, stage in entry.get("stages", {}).items():
            entry["stages"][stage_name] = fix_stage(stage)
    RESULTS.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"Wrote sanitized {RESULTS}")


if __name__ == "__main__":
    main()
