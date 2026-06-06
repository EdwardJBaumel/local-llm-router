"""Deprecated import path — use ``local_llm_router`` (PyPI: local-llm-router)."""

from __future__ import annotations

import warnings

warnings.warn(
    "split_stack is deprecated; pip install local-llm-router and import local_llm_router",
    DeprecationWarning,
    stacklevel=2,
)

from local_llm_router import *  # noqa: F403
