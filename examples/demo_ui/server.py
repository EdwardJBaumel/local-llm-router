"""Local browser demo for local-llm-router routing and compare POC."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Allow `python examples/demo_ui/server.py` without a pip install.
_PROJECT_SRC = Path(__file__).resolve().parents[2] / "src"
if _PROJECT_SRC.is_dir() and str(_PROJECT_SRC) not in sys.path:
    sys.path.insert(0, str(_PROJECT_SRC))

from local_llm_router.discovery import configure_models_dir, default_models_dir
from local_llm_router.poc_models import (
    DEFAULT_POC_STACK,
    list_quant_options,
    list_vram_options,
    stack_payload,
)
from local_llm_router.session import profile_for_vram_gb

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8765
DEFAULT_MODELS = ",".join(DEFAULT_POC_STACK)
DEMO_VERSION = 3


def _parse_models(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_POC_STACK)
    return [part.strip() for part in raw.split(",") if part.strip()]


def _stack_options_payload() -> dict:
    return {
        "ready": True,
        "vram_options": [{"gb": gb, "label": label} for gb, label in list_vram_options()],
        "quant_options": [{"id": qid, "label": label} for qid, label in list_quant_options()],
        "default_vram_gb": 16,
        "default_quant": "qat",
    }


def _parse_vram(raw: str | None) -> int:
    try:
        value = int(raw or "16")
    except ValueError:
        return 16
    if value in {8, 12, 16, 24, 32}:
        return value
    return 16


def _parse_quant(raw: str | None) -> str:
    return (raw or "qat").strip().lower() or "qat"


def _models_from_query(
    query: dict,
    *,
    base_url: str,
    source: str = "both",
) -> tuple[list[str], dict[str, object]]:
    models_raw = query.get("models", [None])[0]
    if models_raw:
        models = _parse_models(models_raw)
        payload = stack_payload(
            vram_gb=_parse_vram(query.get("vram_gb", ["16"])[0]),
            quant=_parse_quant(query.get("quant", ["qat"])[0]),
            base_url=base_url,
            source=source,
            models_override=models,
        )
        return models, payload
    vram_gb = _parse_vram(query.get("vram_gb", ["16"])[0])
    quant = _parse_quant(query.get("quant", ["qat"])[0])
    payload = stack_payload(
        vram_gb=vram_gb,
        quant=quant,
        base_url=base_url,
        source=source,
    )
    resolved = payload.get("resolved_models") or payload.get("models")
    return list(resolved), payload


def _json_response(handler: BaseHTTPRequestHandler, payload: dict, *, status: int = 200) -> None:
    body = json.dumps(payload).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length <= 0:
        return {}
    raw = handler.rfile.read(length)
    return json.loads(raw.decode("utf-8"))


def _compare_payload(
    *,
    models: list[str],
    live: bool,
    base_url: str,
) -> dict:
    from local_llm_router.compare import CompareRunError, run_compare

    try:
        report = run_compare(
            model_names=models,
            base_url=base_url,
            dry_run=not live,
        )
    except CompareRunError as exc:
        return {"ready": False, "error": str(exc)}
    except RuntimeError as exc:
        return {"ready": False, "error": str(exc)}

    return {
        "ready": True,
        "models": list(report.models),
        "rows": [asdict(row) for row in report.rows],
        "summary": asdict(report.summary),
    }


def _route_payload(
    *,
    prompt: str,
    models: list[str],
    hint: str | None,
    base_url: str,
) -> dict:
    from local_llm_router.hints import list_hints
    from local_llm_router.ollama_generate import route_prompt_json

    result = route_prompt_json(
        prompt,
        base_url=base_url,
        model_names=models,
        hint=hint,
    )
    hint_meta = next((item for item in list_hints() if item["id"] == (hint or "")), None)
    return {
        "ready": result.ready,
        "tier": result.tier,
        "model": result.model,
        "hint": hint,
        "hint_label": hint_meta["label"] if hint_meta else None,
        "error": result.error,
    }


def _models_payload(*, base_url: str, models_dir: str | None = None) -> dict:
    from local_llm_router.discovery import list_model_inventory

    inventory = list_model_inventory(base_url=base_url, manifests_root=models_dir)
    detected = default_models_dir()
    return {
        "ready": True,
        "api_models": list(inventory.api_models),
        "disk_models": list(inventory.disk_models),
        "manifest_roots": list(inventory.manifest_roots),
        "suggested_stack": list(inventory.suggested_stack),
        "note": inventory.note,
        "models_dir": models_dir or (str(detected) if detected else None),
        "models": list(inventory.disk_models or inventory.api_models),
    }


def _presets_payload(*, base_url: str, source: str = "both") -> dict:
    """Legacy alias — returns stack options + default 16 GB QAT payload."""
    payload = stack_payload(vram_gb=16, quant="qat", base_url=base_url, source=source)
    return {
        "ready": True,
        **_stack_options_payload(),
        "stack": payload,
    }


def _guide_payload(
    *,
    stack: list[str],
    base_url: str,
    source: str = "both",
    models_dir: str | None = None,
    vram_gb: int = 16,
    quant: str = "qat",
) -> dict:
    from local_llm_router.model_guide import build_model_guide
    from local_llm_router.poc_models import available_model_pool

    pool, note = available_model_pool(base_url=base_url, source=source)
    if not pool and models_dir:
        from local_llm_router.discovery import discover_models_from_disk

        pool = discover_models_from_disk(manifests_root=models_dir)
    profile = profile_for_vram_gb(vram_gb)
    guide = build_model_guide(stack, pool=pool or stack, profile=profile)
    payload = {
        "ready": True,
        "stack": list(guide.stack),
        "tiers": guide.tiers,
        "tier_labels": guide.tier_labels,
        "hint_routes": [asdict(item) for item in guide.hint_routes],
        "models": [asdict(item) for item in guide.models],
        "pool_size": len(pool),
        "note": note,
        "models_dir": models_dir,
        "vram_tier": guide.vram_tier,
        "vram_gb": vram_gb,
        "profile": profile,
        "quant": quant,
        "audit": guide.audit,
        "missing_recommended": list(guide.missing_recommended),
    }
    return payload


def _hints_payload() -> dict:
    from local_llm_router.hints import LEGACY_HINT_ALIASES, list_hints

    return {
        "hints": list(list_hints()),
        "legacy_aliases": LEGACY_HINT_ALIASES,
    }


class DemoHandler(BaseHTTPRequestHandler):
    base_url = "http://127.0.0.1:11434"
    models_dir: str | None = None

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        sys.stderr.write("%s - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), format % args))

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        query = parse_qs(parsed.query)

        if parsed.path == "/api/health":
            detected = default_models_dir()
            _json_response(
                self,
                {
                    "ready": True,
                    "version": DEMO_VERSION,
                    "models_dir": self.models_dir or (str(detected) if detected else None),
                    "endpoints": ["stack", "guide", "compare", "route", "models", "hints"],
                },
            )
            return

        if parsed.path == "/api/stack":
            base_url = query.get("base_url", [self.base_url])[0]
            source = query.get("source", ["both"])[0]
            vram_gb = _parse_vram(query.get("vram_gb", ["16"])[0])
            quant = _parse_quant(query.get("quant", ["qat"])[0])
            models_raw = query.get("models", [None])[0]
            models_override = _parse_models(models_raw) if models_raw else None
            payload = stack_payload(
                vram_gb=vram_gb,
                quant=quant,
                base_url=base_url,
                source=source,
                models_override=models_override,
            )
            payload.update(_stack_options_payload())
            _json_response(self, payload)
            return

        if parsed.path == "/api/stack-options":
            _json_response(self, _stack_options_payload())
            return

        if parsed.path == "/api/community":
            profile = query.get("profile", ["workstation_12gb"])[0]
            from local_llm_router.community_picks import build_community_guide

            _json_response(self, {"ready": True, **build_community_guide(profile=profile)})
            return

        if parsed.path == "/api/compare":
            base_url = query.get("base_url", [self.base_url])[0]
            source = query.get("source", ["both"])[0]
            models, _stack = _models_from_query(query, base_url=base_url, source=source)
            live = query.get("live", ["0"])[0] in ("1", "true", "yes")
            payload = _compare_payload(models=models, live=live, base_url=base_url)
            status = 200 if payload.get("ready", True) else 502
            _json_response(self, payload, status=status)
            return

        if parsed.path == "/api/guide":
            base_url = query.get("base_url", [self.base_url])[0]
            source = query.get("source", ["both"])[0]
            vram_gb = _parse_vram(query.get("vram_gb", ["16"])[0])
            quant = _parse_quant(query.get("quant", ["qat"])[0])
            models, stack_info = _models_from_query(query, base_url=base_url, source=source)
            stack = list(stack_info.get("resolved_models") or models)
            _json_response(
                self,
                _guide_payload(
                    stack=stack,
                    base_url=base_url,
                    source=source,
                    models_dir=self.models_dir,
                    vram_gb=vram_gb,
                    quant=quant,
                ),
            )
            return

        if parsed.path == "/api/models":
            base_url = query.get("base_url", [self.base_url])[0]
            _json_response(self, _models_payload(base_url=base_url, models_dir=self.models_dir))
            return

        if parsed.path == "/api/presets":
            base_url = query.get("base_url", [self.base_url])[0]
            source = query.get("source", ["both"])[0]
            _json_response(self, _presets_payload(base_url=base_url, source=source))
            return

        if parsed.path == "/api/hints":
            _json_response(self, _hints_payload())
            return

        if parsed.path in ("/", "/index.html"):
            self._serve_file(ROOT / "index.html", "text/html; charset=utf-8")
            return

        if parsed.path == "/styles.css":
            self._serve_file(ROOT / "styles.css", "text/css; charset=utf-8")
            return

        if parsed.path == "/app.js":
            self._serve_file(ROOT / "app.js", "application/javascript; charset=utf-8", cache=False)
            return

        self.send_error(404)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/api/route":
            self.send_error(404)
            return

        body = _read_json(self)
        prompt = (body.get("prompt") or "").strip()
        if not prompt:
            _json_response(self, {"ready": False, "error": "prompt is required"}, status=400)
            return

        base_url = body.get("base_url") or self.base_url
        source = body.get("source") or "both"
        models_raw = body.get("models")
        if models_raw:
            models = _parse_models(models_raw if isinstance(models_raw, str) else ",".join(models_raw))
        else:
            vram_gb = _parse_vram(str(body.get("vram_gb", 16)))
            quant = _parse_quant(body.get("quant"))
            stack_info = stack_payload(vram_gb=vram_gb, quant=quant, base_url=base_url, source=source)
            models = list(stack_info.get("resolved_models") or stack_info.get("models") or DEFAULT_POC_STACK)
        hint = body.get("hint") or None
        if hint == "":
            hint = None
        _json_response(
            self,
            _route_payload(prompt=prompt, models=models, hint=hint, base_url=base_url),
        )

    def _serve_file(self, path: Path, content_type: str, *, cache: bool = True) -> None:
        if not path.is_file():
            self.send_error(404)
            return
        data = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        if not cache:
            self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description="local-llm-router visual browser demo")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument(
        "--models-dir",
        help="Ollama models folder (contains manifests/). Auto-detected if omitted.",
    )
    args = parser.parse_args()

    models_dir = args.models_dir
    if not models_dir:
        detected = default_models_dir()
        if detected:
            models_dir = str(detected)

    if models_dir:
        configure_models_dir(models_dir)
        os.environ.setdefault("local_llm_router_OLLAMA_MODELS", models_dir)

    DemoHandler.base_url = args.base_url
    DemoHandler.models_dir = models_dir
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"local-llm-router demo UI at {url}")
    print(f"Default stack: {DEFAULT_MODELS}")
    if models_dir:
        print(f"Models dir: {models_dir}")
    else:
        print("Models dir: not found — set --models-dir or local_llm_router_OLLAMA_MODELS")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
