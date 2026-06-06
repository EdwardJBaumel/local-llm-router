from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from typing import Callable


class UsageProfile(str, Enum):
    """Supported ways to use local-llm-router."""

    CORE = "core"
    OLLAMA_DISCOVERY = "ollama_discovery"
    LOCAL_ASSISTANT = "local_assistant"
    CLI_DOCTOR = "cli_doctor"


@dataclass(frozen=True)
class Prerequisite:
    id: str
    description: str
    kind: str
    required: bool
    install_command: str | None = None
    verify_hint: str | None = None
    satisfied: bool | None = None


@dataclass(frozen=True)
class ProfileRequirements:
    profile: UsageProfile
    title: str
    summary: str
    prerequisites: tuple[Prerequisite, ...]

    @property
    def ready(self) -> bool:
        return all(item.satisfied is not False for item in self.prerequisites if item.required)


def _python_ok() -> bool:
    return sys.version_info >= (3, 10)


def _requests_ok() -> bool:
    try:
        import requests  # noqa: F401
    except ImportError:
        return False
    return True


def _ollama_ok(base_url: str = "http://127.0.0.1:11434") -> bool:
    if not _requests_ok():
        return False
    try:
        import requests

        response = requests.get(f"{base_url.rstrip('/')}/api/tags", timeout=2)
        response.raise_for_status()
        payload = response.json() or {}
        return bool(payload.get("models"))
    except Exception:
        return False


def _catalog() -> dict[UsageProfile, tuple[Prerequisite, ...]]:
    return {
        UsageProfile.CORE: (
            Prerequisite(
                id="python",
                description="Python 3.10 or newer",
                kind="runtime",
                required=True,
                install_command="https://www.python.org/downloads/",
                verify_hint="python --version",
            ),
            Prerequisite(
                id="local_llm_router",
                description="local-llm-router package installed",
                kind="package",
                required=True,
                install_command="python -m pip install local-llm-router",
                verify_hint="python -c \"import local_llm_router\"",
            ),
            Prerequisite(
                id="model_names",
                description="A list of model names for assign_tiers() (from config or your provider)",
                kind="input",
                required=True,
                verify_hint='assign_tiers(["qwen3:4b", "qwen3:8b"])',
            ),
        ),
        UsageProfile.OLLAMA_DISCOVERY: (
            Prerequisite(
                id="python",
                description="Python 3.10 or newer",
                kind="runtime",
                required=True,
                install_command="https://www.python.org/downloads/",
                verify_hint="python --version",
            ),
            Prerequisite(
                id="local_llm_router",
                description="local-llm-router package installed",
                kind="package",
                required=True,
                install_command="python -m pip install local-llm-router",
                verify_hint="python -c \"import local_llm_router\"",
            ),
            Prerequisite(
                id="requests",
                description="requests library (optional extra)",
                kind="package",
                required=True,
                install_command="python -m pip install local-llm-router[ollama]",
                verify_hint="python -c \"import requests\"",
            ),
            Prerequisite(
                id="ollama",
                description="Ollama installed and running on localhost:11434",
                kind="service",
                required=True,
                install_command="https://ollama.com/download",
                verify_hint="ollama list",
            ),
            Prerequisite(
                id="ollama_models",
                description="At least one model pulled in Ollama (e.g. ollama pull qwen3:8b)",
                kind="input",
                required=True,
                verify_hint="ollama list",
            ),
        ),
        UsageProfile.LOCAL_ASSISTANT: (
            Prerequisite(
                id="python",
                description="Python 3.10 or newer",
                kind="runtime",
                required=True,
                install_command="https://www.python.org/downloads/",
                verify_hint="python --version",
            ),
            Prerequisite(
                id="local_llm_router",
                description="local-llm-router installed in editable mode from repo checkout",
                kind="package",
                required=True,
                install_command="python -m pip install -e .",
                verify_hint="python -c \"import local_llm_router\"",
            ),
            Prerequisite(
                id="requests",
                description="requests library for Ollama HTTP calls",
                kind="package",
                required=True,
                install_command="python -m pip install local-llm-router[ollama]",
                verify_hint="python -c \"import requests\"",
            ),
            Prerequisite(
                id="ollama",
                description="Ollama installed and running on localhost:11434",
                kind="service",
                required=True,
                install_command="https://ollama.com/download",
                verify_hint="ollama serve",
            ),
            Prerequisite(
                id="ollama_models",
                description="Two or more models recommended so tiers differ (small + large)",
                kind="input",
                required=True,
                verify_hint="ollama pull qwen3:4b && ollama pull qwen3:14b",
            ),
            Prerequisite(
                id="gpu_ram",
                description="Enough VRAM/RAM to run your largest pulled model",
                kind="hardware",
                required=True,
                verify_hint="Start with smaller models if inference is slow or fails",
            ),
        ),
        UsageProfile.CLI_DOCTOR: (
            Prerequisite(
                id="python",
                description="Python 3.10 or newer",
                kind="runtime",
                required=True,
                install_command="https://www.python.org/downloads/",
                verify_hint="python --version",
            ),
            Prerequisite(
                id="local_llm_router",
                description="local-llm-router package installed (includes stack CLI)",
                kind="package",
                required=True,
                install_command="python -m pip install local-llm-router",
                verify_hint="stack doctor",
            ),
            Prerequisite(
                id="requests",
                description="requests library for Ollama tier detection",
                kind="package",
                required=False,
                install_command="python -m pip install local-llm-router[ollama]",
                verify_hint="python -c \"import requests\"",
            ),
            Prerequisite(
                id="ollama",
                description="Ollama running locally (optional; doctor skips if unavailable)",
                kind="service",
                required=False,
                install_command="https://ollama.com/download",
                verify_hint="ollama list",
            ),
        ),
    }


_PROFILE_META: dict[UsageProfile, tuple[str, str]] = {
    UsageProfile.CORE: (
        "Core library",
        "Use score_prompt(), assign_tiers(), and route_prompt() with your own model list.",
    ),
    UsageProfile.OLLAMA_DISCOVERY: (
        "Ollama discovery",
        "Call discover_models() to read model tags from a local Ollama instance.",
    ),
    UsageProfile.LOCAL_ASSISTANT: (
        "Local work assistant example",
        "Run examples/local_work_assistant/app.py for auto-tiered local Q&A.",
    ),
    UsageProfile.CLI_DOCTOR: (
        "CLI doctor",
        "Run stack doctor for local-llm-router guidance and optional Ollama tier output.",
    ),
}


def list_usage_profiles() -> list[UsageProfile]:
    return list(UsageProfile)


_CHECKERS: dict[str, Callable[[], bool]] = {
    "python": _python_ok,
    "local_llm_router": lambda: True,
    "requests": _requests_ok,
    "ollama": _ollama_ok,
    "ollama_models": _ollama_ok,
}


def usage_requirements(
    profile: UsageProfile = UsageProfile.CORE,
    *,
    check: bool = False,
) -> ProfileRequirements:
    """Return prerequisites for a usage profile.

    Set check=True to probe the local machine (Python version, requests, Ollama).
    """
    title, summary = _PROFILE_META[profile]
    catalog = _catalog()[profile]
    prerequisites: list[Prerequisite] = []

    for item in catalog:
        satisfied = None
        if check and item.id in _CHECKERS:
            satisfied = _CHECKERS[item.id]()
        prerequisites.append(
            Prerequisite(
                id=item.id,
                description=item.description,
                kind=item.kind,
                required=item.required,
                install_command=item.install_command,
                verify_hint=item.verify_hint,
                satisfied=satisfied,
            )
        )

    return ProfileRequirements(
        profile=profile,
        title=title,
        summary=summary,
        prerequisites=tuple(prerequisites),
    )
