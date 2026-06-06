from split_stack.advice import stack_recommendation
from split_stack.benchmark import format_markdown_table, run_benchmark
from split_stack.complexity import resolve_tier, score_prompt
from split_stack.hints import list_hints, normalize_step_kind
from split_stack.discovery import discover_models
from split_stack.local_models import assign_tiers_from_local, list_local_models
from split_stack.model_registry import (
    DeploymentProfileSpec,
    ModelEntry,
    ModelRegistry,
    list_deployment_profiles,
    load_registry,
    model_weight,
    normalize_deployment_profile,
)
from split_stack.models import ComplexityTier, RouteDecision, StackAdvice, StepKind, TierMap
from split_stack.presets import (
    assign_recommended_tiers,
    list_recommended_stacks,
    recommended_models,
)
from split_stack.requirements import (
    Prerequisite,
    ProfileRequirements,
    UsageProfile,
    list_usage_profiles,
    usage_requirements,
)
from split_stack.quantization import (
    QUANT_MODES,
    adjust_vram_for_quant,
    expand_models_for_quant,
    normalize_quant_mode,
    pull_guidance_lines,
    quant_from_env,
)
from split_stack.routing import explain_route, route_prompt
from split_stack.session import (
    Session,
    configure,
    default_profile_from_env,
    describe_session,
    explain,
    get_session,
    profile_for_vram_gb,
    route,
    session_warnings,
)
from split_stack.startup_tips import emit_import_tips, model_recommendation_report
from split_stack.tiering import assign_tiers, describe_tiers
from split_stack.validation import validate_tier_map

__version__ = "0.2.0"

__all__ = [
    "ComplexityTier",
    "DeploymentProfileSpec",
    "ModelRegistry",
    "Prerequisite",
    "ProfileRequirements",
    "QUANT_MODES",
    "StackAdvice",
    "StepKind",
    "RouteDecision",
    "Session",
    "TierMap",
    "UsageProfile",
    "assign_recommended_tiers",
    "assign_tiers",
    "assign_tiers_from_local",
    "adjust_vram_for_quant",
    "configure",
    "default_profile_from_env",
    "describe_session",
    "describe_tiers",
    "discover_models",
    "explain",
    "explain_route",
    "format_markdown_table",
    "get_session",
    "list_local_models",
    "list_deployment_profiles",
    "list_recommended_stacks",
    "load_registry",
    "normalize_quant_mode",
    "normalize_step_kind",
    "normalize_deployment_profile",
    "list_usage_profiles",
    "model_recommendation_report",
    "model_weight",
    "profile_for_vram_gb",
    "pull_guidance_lines",
    "quant_from_env",
    "recommended_models",
    "route",
    "route_prompt",
    "resolve_tier",
    "score_prompt",
    "session_warnings",
    "stack_recommendation",
    "usage_requirements",
    "validate_tier_map",
    "__version__",
]

# Embedded library use: no import-time stderr. Use ``stack tips`` or ``SPLIT_STACK_IMPORT_TIPS=on``.
