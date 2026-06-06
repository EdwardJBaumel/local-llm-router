"""Local browser demo for split-stack routing and compare POC."""

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

from split_stack.discovery import configure_models_dir, default_models_dir
from split_stack.poc_models import DEFAULT_POC_STACK, list_stack_presets, models_for_preset, resolve_installed_stack

ROOT = Path(__file__).resolve().parent
DEFAULT_PORT = 8765
DEFAULT_MODELS = ",".join(DEFAULT_POC_STACK)
DEMO_VERSION = 2


def _parse_models(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_POC_STACK)
    return [part.strip() for part in raw.split(",") if part.strip()]


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
    from split_stack.compare import CompareRunError, run_compare

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
    from split_stack.hints import list_hints
    from split_stack.ollama_generate import route_prompt_json

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
    from split_stack.discovery import list_model_inventory

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
    from split_stack.poc_models import available_model_pool

    pool, inventory_note = available_model_pool(base_url=base_url, source=source)

    presets = []
    for item in list_stack_presets():
        resolved, warning = resolve_installed_stack(
            pool,
            preset_id=item.id,
            base_url=base_url,
        )
        models = list(item.models)
        if item.id == "from_inventory":
            models = list(models_for_preset("from_inventory", base_url=base_url))
        presets.append(
            {
                "id": item.id,
                "label": item.label,
                "description": item.description,
                "models": models,
                "resolved_models": resolved,
                "warning": warning,
            }
        )
    return {
        "ready": True,
        "presets": presets,
        "pool": pool,
        "source": source,
        "inventory_note": inventory_note,
    }


def _hints_payload() -> dict:
    from split_stack.hints import LEGACY_HINT_ALIASES, list_hints

    return {
        "hints": list(list_hints()),
        "legacy_aliases": LEGACY_HINT_ALIASES,
    }


def _guide_payload(
    *,
    stack: list[str],
    base_url: str,
    source: str = "both",
    models_dir: str | None = None,
) -> dict:
    from split_stack.model_guide import build_model_guide
    from split_stack.poc_models import available_model_pool

    pool, note = available_model_pool(base_url=base_url, source=source)
    if not pool and models_dir:
        from split_stack.discovery import discover_models_from_disk

        pool = discover_models_from_disk(manifests_root=models_dir)
    guide = build_model_guide(stack, pool=pool or stack, profile="workstation_12gb")
    from split_stack.community_picks import build_community_guide

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
        "audit": guide.audit,
        "missing_recommended": list(guide.missing_recommended),
        "community": build_community_guide(profile="workstation_12gb"),
    }
    return payload


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
                    "endpoints": ["guide", "compare", "route", "models", "presets", "hints", "community"],
                },
            )
            return

        if parsed.path == "/api/community":
            profile = query.get("profile", ["workstation_12gb"])[0]
            from split_stack.community_picks import build_community_guide

            _json_response(self, {"ready": True, **build_community_guide(profile=profile)})
            return

        if parsed.path == "/api/compare":
            base_url = query.get("base_url", [self.base_url])[0]
            preset = query.get("preset", [None])[0]
            models_raw = query.get("models", [None])[0]
            if models_raw:
                models = _parse_models(models_raw)
            elif preset:
                models = models_for_preset(preset, base_url=base_url)
            else:
                models = _parse_models(None)
            live = query.get("live", ["0"])[0] in ("1", "true", "yes")
            payload = _compare_payload(models=models, live=live, base_url=base_url)
            status = 200 if payload.get("ready", True) else 502
            _json_response(self, payload, status=status)
            return

        if parsed.path == "/api/guide":
            base_url = query.get("base_url", [self.base_url])[0]
            source = query.get("source", ["both"])[0]
            models_raw = query.get("models", [None])[0]
            stack = _parse_models(models_raw)
            _json_response(
                self,
                _guide_payload(
                    stack=stack,
                    base_url=base_url,
                    source=source,
                    models_dir=self.models_dir,
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

        models = _parse_models(body.get("models"))
        hint = body.get("hint") or None
        if hint == "":
            hint = None
        base_url = body.get("base_url") or self.base_url
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

    parser = argparse.ArgumentParser(description="split-stack visual browser demo")
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
        os.environ.setdefault("SPLIT_STACK_OLLAMA_MODELS", models_dir)

    DemoHandler.base_url = args.base_url
    DemoHandler.models_dir = models_dir
    server = ThreadingHTTPServer((args.host, args.port), DemoHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"split-stack demo UI at {url}")
    print(f"Default stack: {DEFAULT_MODELS}")
    if models_dir:
        print(f"Models dir: {models_dir}")
    else:
        print("Models dir: not found — set --models-dir or SPLIT_STACK_OLLAMA_MODELS")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
