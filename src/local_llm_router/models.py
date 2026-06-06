from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ComplexityTier(str, Enum):
    SIMPLE = "simple"
    MEDIUM = "medium"
    COMPLEX = "complex"
    REASONING = "reasoning"


class RouteMode(str, Enum):
    CHAT = "chat"
    AGENT = "agent"


class StepKind(str, Enum):
    LOOKUP = "lookup"
    EXPLAIN = "explain"
    DESIGN = "design"
    CODE = "code"
    REASON = "reason"
    # Deprecated aliases (still parse)
    WORK = "work"
    BUILD = "build"


@dataclass(frozen=True)
class TierMap:
    simple: str
    medium: str
    complex: str
    reasoning: str
    code: str | None = None
    complex_alt: str | None = None

    def for_tier(self, tier: ComplexityTier) -> str:
        lookup = {
            ComplexityTier.SIMPLE: self.simple,
            ComplexityTier.MEDIUM: self.medium,
            ComplexityTier.COMPLEX: self.complex,
            ComplexityTier.REASONING: self.reasoning,
        }
        return lookup[tier]


@dataclass(frozen=True)
class RouteDecision:
    """Full routing outcome for logging, CLI explain, and agent-loop telemetry."""

    tier: ComplexityTier
    model: str
    hint: str | None
    step_kind: str | None
    tier_source: str
    model_source: str
    reasons: tuple[str, ...]
    tiers: dict[str, str | None]
    mode: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "tier": self.tier.value,
            "model": self.model,
            "hint": self.hint,
            "step_kind": self.step_kind,
            "tier_source": self.tier_source,
            "model_source": self.model_source,
            "reasons": list(self.reasons),
            "tiers": self.tiers,
            "mode": self.mode,
        }

    def as_tuple(self) -> tuple[ComplexityTier, str]:
        return self.tier, self.model


@dataclass(frozen=True)
class StackAdvice:
    cursor_model: str
    prose_path: str
    local_path: str
    warn_cursor_override: bool
