"""Agent-loop Ollama benchmark: structured extract, reason, explain across models.

Maps to local-llm-router step hints (code/reason/explain). See docs/benchmark-evidence.md.
"""
from __future__ import annotations

import argparse
import json
import re
import statistics
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import date
from pathlib import Path

OLLAMA = "http://127.0.0.1:11434/api/generate"
RESULTS_PATH = Path(__file__).resolve().parent / "benchmark_results.json"
META_PATH = Path(__file__).resolve().parent / "benchmark_meta.json"

PARSE_PROMPT = """You are a job listing data extractor. Given the following text extracted from a job board, extract structured data.

Respond with ONLY a JSON object (no markdown, no explanation) with these keys:
- "title": job title (string or null). Must be a human-readable role name, never a recruiter tracking code like "RDQ226R484".
- "company": company name (string or null)
- "location": job location (string or null)
- "salary": salary info if present (string or null)
- "description": brief description/summary, max 200 words (string or null)
- "technologies": list of technologies/skills mentioned (array of strings)
- "seniority": one of "junior", "mid", "senior", "lead", "manager", "director", "unknown"
- "job_type": one of "full-time", "part-time", "contract", "intern", "unknown"
- "remote": one of "remote", "hybrid", "onsite", "unknown"
- "url": direct link to the job if present (string or null)

If a field cannot be determined, use null. Do not invent data. Do not include any HTML tags or entities in string values.

Text:
Senior Product Manager - AI Platform
Stripe · San Francisco, CA (Hybrid) · $185,000 - $240,000 USD
About the role: Own the roadmap for internal LLM tooling used by 2000+ engineers.
Requirements: 5+ years PM experience, Python familiarity, experience shipping ML/AI products,
strong stakeholder management, SQL, experimentation mindset.
Tech: Python, Kubernetes, LLM APIs, feature flags, A/B testing.
Apply: https://stripe.com/jobs/listing/senior-pm-ai-platform
"""

ANALYZE_PROMPT = """You are a career fit analyzer. Compare this candidate profile against the job listing and produce a structured fit-gap analysis.

CANDIDATE PROFILE:
Experienced Platform Product Manager at Deloitte Digital with 5 years in UI/UX platform work.
Currently managing UI Commons, a shared component library built on React and Storybook.
Strong technical background in React, WCAG accessibility, SQL, Python, and Tableau.
PSM I certified. Hands-on AI experience including building a PR review agent on the Anthropic API
and driving internal Claude Code adoption. Seeking AI Product Manager or Technical Product Manager roles.

JOB LISTING:
Title: Senior Product Manager - AI Platform
Company: Stripe
Description: Own the roadmap for internal LLM tooling used by 2000+ engineers. 5+ years PM,
Python familiarity, experience shipping ML/AI products, stakeholder management, SQL, experimentation.
Technologies: Python, Kubernetes, LLM APIs, feature flags, A/B testing

Respond with ONLY a JSON object (no markdown, no explanation):
{
  "matched_skills": ["skill1", "skill2"],
  "missing_skills": ["skill3", "skill4"],
  "match_percentage": <int 0-100>,
  "fit_summary": "<one sentence overall fit assessment>",
  "gaps": [
    {"skill": "skill name", "severity": "critical|moderate|minor", "mitigation": "how to close this gap quickly"}
  ],
  "talking_points": ["<strength to highlight in interview>", "<another strength>"],
  "study_recommendations": ["<specific thing to learn before applying>"]
}
"""

DIGEST_PROMPT = """You are a career intelligence analyst. Generate a concise weekly digest from this job search data. Write in a direct, analytical tone. No fluff.

TODAY'S DATE: {today}

DATA:
- Jobs discovered this cycle: 142
- Jobs above match threshold: 18
- Top companies by volume: Stripe(4), Datadog(3), Notion(2)
- Most common skill gaps: kubernetes(6), ml-platforms(4), payments-domain(3)
- Source breakdown: greenhouse: 88, lever: 31, ashby: 23
- Funnel metrics: {{"ingested": 142, "parsed": 138, "matched": 18, "analyzed": 8}}

Write a 150-word digest covering:
1. Volume and notable hiring velocity changes
2. Top matches worth applying to (company + title)
3. Skill gaps to prioritize closing
4. Source effectiveness
5. One actionable recommendation

Start with the exact line "Weekly Digest -- {today}" (no alteration - use the date exactly as provided). No markdown formatting. Do not invent a date.
"""

COVER_PROMPT = """You are writing a cover letter for a real job application. Ground every
claim in the candidate profile below. Do not invent experience, companies,
dates, or numbers that aren't present. If something's missing, skip it.

CANDIDATE PROFILE
Platform Product Manager at Deloitte Digital, 5 years. Built UI Commons (React/Storybook).
React, WCAG, SQL, Python, Tableau. PSM I. Built a PR review agent on Anthropic API.
Candidate name: Alex Chen

JOB POSTING
Title: Senior Product Manager - AI Platform
Company: Stripe
Location: San Francisco, CA (Hybrid)
Seniority: senior
Technologies: Python, Kubernetes, LLM APIs, feature flags, A/B testing
Description:
Own the roadmap for internal LLM tooling used by 2000+ engineers. 5+ years PM,
Python familiarity, experience shipping ML/AI products, stakeholder management.

TONE: Calm, clear, and specific. No jargon, no hype.

RULES
- 3 to 4 short paragraphs. ~250 to 350 words total.
- First paragraph: why this role at this company specifically, grounded
  in one concrete thing from the JD.
- Middle paragraph(s): two or three specific matches between the
  candidate's actual experience and the JD. Name the technology,
  domain, or outcome each time.
- Closing: one clear sentence of interest plus availability / next step.
- Do NOT invent metrics, former employers, or credentials not in the
  profile. If the profile has numbers, you may reuse them verbatim.
- Do NOT use the phrase "I am writing to apply" or any similar filler.
- No bullet points. No headers. Plain prose only.
- Write in British English (e.g. 'organise', 'optimise', no Oxford commas).
- Do not use em dashes.

Output ONLY the letter body. No preamble, no signature block, no
subject line. Start with the salutation ("Dear Hiring Team," is fine
when the posting doesn't name one)."""

STAGES = {
    "parse": {"prompt": PARSE_PROMPT, "num_predict": 1024, "runs": 3},
    "analyze": {"prompt": ANALYZE_PROMPT, "num_predict": 2048, "runs": 3},
    "digest": {"prompt": None, "num_predict": 1024, "runs": 2},
    "cover": {"prompt": COVER_PROMPT, "num_predict": 1536, "runs": 2},
}

PARSE_KEYS = {
    "title", "company", "location", "salary", "description", "technologies",
    "seniority", "job_type", "remote", "url",
}
ANALYZE_KEYS = {
    "matched_skills", "missing_skills", "match_percentage", "fit_summary",
    "gaps", "talking_points", "study_recommendations",
}

DEFAULT_MODELS = [
    "qwen3:8b",
    "qwen3:14b",
    "gemma4:e4b",
    "deepseek-r1:8b",
    "gemma4:12b",
    "gemma4:26b",
    "gemma4:31b",
]


def list_ollama_models() -> list[str]:
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=10) as resp:
            data = json.loads(resp.read().decode())
        return [m["name"] for m in data.get("models", [])]
    except Exception:
        return []


def gpu_snapshot() -> dict:
    try:
        out = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,memory.free",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            timeout=10,
        ).strip()
        parts = [p.strip() for p in out.split(",")]
        if len(parts) >= 4:
            return {
                "name": parts[0],
                "vram_total_mb": int(parts[1]),
                "vram_used_mb": int(parts[2]),
                "vram_free_mb": int(parts[3]),
            }
    except Exception as e:
        return {"error": str(e)}
    return {}


def call_ollama(model: str, prompt: str, num_predict: int) -> dict:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": num_predict},
    }
    req = urllib.request.Request(
        OLLAMA,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.perf_counter()
    with urllib.request.urlopen(req, timeout=600) as resp:
        body = json.loads(resp.read().decode())
    return {
        "response": body.get("response", ""),
        "elapsed_ms": (time.perf_counter() - t0) * 1000,
        "eval_count": body.get("eval_count"),
        "prompt_eval_count": body.get("prompt_eval_count"),
        "load_duration_ns": body.get("load_duration"),
        "vram_after": gpu_snapshot(),
    }


def extract_json(text: str) -> tuple[dict | None, str | None]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text), None
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None, "no_json_object"
    try:
        return json.loads(m.group()), None
    except json.JSONDecodeError as e:
        return None, str(e)


def score_parse(data: dict | None) -> dict:
    if not data:
        return {"valid_json": 0, "keys_present": 0, "quality": 0}
    keys = sum(1 for k in PARSE_KEYS if k in data and data[k] is not None)
    quality = 0
    title = (data.get("title") or "").lower()
    if "senior" in title and "product" in title:
        quality += 1
    if (data.get("company") or "").lower() == "stripe":
        quality += 1
    if isinstance(data.get("technologies"), list) and len(data["technologies"]) >= 2:
        quality += 1
    if data.get("seniority") in {"senior", "lead", "manager"}:
        quality += 1
    if data.get("remote") in {"remote", "hybrid", "onsite"}:
        quality += 1
    return {"valid_json": 1, "keys_present": keys, "quality": quality}


def score_analyze(data: dict | None) -> dict:
    if not data:
        return {"valid_json": 0, "keys_present": 0, "quality": 0}
    keys = sum(1 for k in ANALYZE_KEYS if k in data and data[k] is not None)
    quality = 0
    pct = data.get("match_percentage")
    if isinstance(pct, int) and 50 <= pct <= 95:
        quality += 1
    matched = data.get("matched_skills") or []
    if isinstance(matched, list) and len(matched) >= 2:
        quality += 1
    gaps = data.get("gaps") or []
    if isinstance(gaps, list) and gaps and isinstance(gaps[0], dict) and "severity" in gaps[0]:
        quality += 1
    summary = (data.get("fit_summary") or "").strip()
    if 20 <= len(summary) <= 300:
        quality += 1
    talking = data.get("talking_points") or []
    if isinstance(talking, list) and len(talking) >= 2:
        quality += 1
    return {"valid_json": 1, "keys_present": keys, "quality": quality}


def score_digest(text: str, today: str) -> dict:
    words = len(text.split())
    quality = 0
    if text.strip().startswith(f"Weekly Digest -- {today}"):
        quality += 2
    if 120 <= words <= 220:
        quality += 1
    if "stripe" in text.lower():
        quality += 1
    if "kubernetes" in text.lower() or "skill" in text.lower():
        quality += 1
    if not re.search(r"^#|\*\*|\[.+\]\(.+\)", text, re.MULTILINE):
        quality += 1
    return {"valid_json": 1, "keys_present": 5, "quality": quality, "word_count": words}


def score_cover(text: str) -> dict:
    words = len(text.split())
    quality = 0
    if text.strip().lower().startswith("dear"):
        quality += 1
    if 220 <= words <= 420:
        quality += 1
    if "stripe" in text.lower() and "python" in text.lower():
        quality += 1
    if "i am writing to apply" not in text.lower():
        quality += 1
    if "•" not in text and not re.search(r"^\s*[-*]\s", text, re.MULTILINE):
        quality += 1
    if "—" not in text:
        quality += 1
    return {"valid_json": 1, "keys_present": 6, "quality": quality, "word_count": words}


def score_stage(stage: str, response: str, today: str) -> dict:
    if stage == "parse":
        data, err = extract_json(response)
        out = score_parse(data)
        out["error"] = err
        return out
    if stage == "analyze":
        data, err = extract_json(response)
        out = score_analyze(data)
        out["error"] = err
        return out
    if stage == "digest":
        return score_digest(response, today)
    if stage == "cover":
        return score_cover(response)
    raise ValueError(stage)


def prompt_for(stage: str, today: str) -> str:
    if stage == "digest":
        return DIGEST_PROMPT.format(today=today)
    return STAGES[stage]["prompt"]


def _drop_latency_outliers(lats: list[float]) -> tuple[list[float], list[int]]:
    """Drop runs >2.5x median when another process was using the GPU."""
    if len(lats) < 3:
        return lats, []
    med = statistics.median(lats)
    if med <= 0:
        return lats, []
    kept, dropped = [], []
    for i, lat in enumerate(lats):
        if lat > med * 2.5:
            dropped.append(i)
        else:
            kept.append(lat)
    return (kept if kept else lats), dropped


def bench_stage(model: str, stage: str, today: str) -> dict:
    cfg = STAGES[stage]
    scores, lats, toks, errors, run_records = [], [], [], [], []
    for run_idx in range(cfg["runs"]):
        try:
            r = call_ollama(model, prompt_for(stage, today), cfg["num_predict"])
            sc = score_stage(stage, r["response"], today)
            scores.append(sc)
            lats.append(r["elapsed_ms"])
            if r.get("eval_count"):
                toks.append(r["eval_count"])
            if sc.get("error"):
                errors.append(sc["error"])
            run_records.append({"run": run_idx, "latency_ms": r["elapsed_ms"], "score": sc})
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")
            errors.append(f"http_{e.code}: {body[:200]}")
            scores.append({"valid_json": 0, "keys_present": 0, "quality": 0})
            lats.append(0)
            run_records.append({"run": run_idx, "latency_ms": 0, "dropped": False, "error": body[:200]})
        except Exception as e:
            errors.append(str(e))
            scores.append({"valid_json": 0, "keys_present": 0, "quality": 0})
            lats.append(0)
            run_records.append({"run": run_idx, "latency_ms": 0, "dropped": False, "error": str(e)})

    clean_lats, dropped_idx = _drop_latency_outliers(lats)
    clean_scores = [s for i, s in enumerate(scores) if i not in dropped_idx]
    clean_toks = [t for i, t in enumerate(toks) if i not in dropped_idx] if toks else []
    for i in dropped_idx:
        if i < len(run_records):
            run_records[i]["dropped"] = True

    return {
        "valid_json_rate": sum(s["valid_json"] for s in clean_scores) / max(len(clean_scores), 1),
        "avg_keys": statistics.mean(s["keys_present"] for s in clean_scores),
        "avg_quality": statistics.mean(s["quality"] for s in clean_scores),
        "latency_ms_avg": statistics.mean(clean_lats) if clean_lats else 0,
        "latency_ms_p95": sorted(clean_lats)[-1] if clean_lats else 0,
        "tokens_avg": statistics.mean(clean_toks) if clean_toks else None,
        "errors": errors,
        "word_count_avg": statistics.mean(s["word_count"] for s in clean_scores if "word_count" in s)
        if any("word_count" in s for s in clean_scores)
        else None,
        "runs_raw": len(scores),
        "runs_dropped": len(dropped_idx),
        "run_details": run_records,
    }


def bench_model(model: str, stages: list[str], today: str) -> dict:
    out = {"model": model, "stages": {}}
    for stage in stages:
        print(f"  {stage}...", flush=True)
        out["stages"][stage] = bench_stage(model, stage, today)
    return out


def print_table(results: list[dict], stages: list[str]) -> None:
    print("\n=== OLLAMA AGENT-LOOP BENCHMARK ===\n")
    header = f"{'Model':<16} {'Stage':<8} {'OK%':>5} {'Qual':>5} {'ms':>8} {'tok':>6}"
    print(header)
    print("-" * len(header))
    for r in results:
        if r.get("error"):
            print(f"{r['model']:<16} SKIP: {r['error']}")
            continue
        for stage in stages:
            s = r["stages"][stage]
            tok = f"{s['tokens_avg']:.0f}" if s.get("tokens_avg") else "n/a"
            print(
                f"{r['model']:<16} {stage:<8} "
                f"{s['valid_json_rate']*100:>4.0f}% "
                f"{s['avg_quality']:>5.1f} "
                f"{s['latency_ms_avg']:>8.0f} "
                f"{tok:>6}"
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--models", nargs="*", default=None)
    parser.add_argument("--stages", nargs="*", default=list(STAGES))
    parser.add_argument("--pull-missing", action="store_true")
    args = parser.parse_args()

    available = set(list_ollama_models())
    models = args.models or DEFAULT_MODELS
    today = date.today().isoformat()
    meta = {
        "date": today,
        "gpu": gpu_snapshot(),
        "available_models": sorted(available),
        "stages": args.stages,
    }
    META_PATH.write_text(json.dumps(meta, indent=2), encoding="utf-8")

    results = []
    for model in models:
        if model not in available:
            if args.pull_missing:
                print(f"Pulling {model}...", flush=True)
                subprocess.run(["ollama", "pull", model], check=False)
                available = set(list_ollama_models())
            if model not in available:
                results.append({"model": model, "error": "not_installed"})
                continue
        print(f"Benchmarking {model}...", flush=True)
        try:
            results.append(bench_model(model, args.stages, today))
        except Exception as e:
            results.append({"model": model, "error": str(e)})

    print_table(results, args.stages)
    RESULTS_PATH.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\nWrote {RESULTS_PATH}")
    print(f"Wrote {META_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
