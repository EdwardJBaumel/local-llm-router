from local_llm_router.advice import stack_recommendation
from local_llm_router.benchmark import format_markdown_table, run_benchmark
from local_llm_router.complexity import resolve_tier, score_prompt
from local_llm_router.hints import list_hints, normalize_step_kind
from local_llm_router.discovery import discover_models
from local_llm_router.local_models import assign_tiers_from_local, list_local_models
from local_llm_router.model_registry import (
    DeploymentProfileSpec,
    ModelEntry,
    ModelRegistry,
    list_deployment_profiles,
    load_registry,
    model_weight,
    normalize_deployment_profile,
)
from local_llm_router.models import ComplexityTier, RouteDecision, StackAdvice, StepKind, TierMap
from local_llm_router.presets import (
    assign_recommended_tiers,
    list_recommended_stacks,
    recommended_models,
)
from local_llm_router.requirements import (
    Prerequisite,
    ProfileRequirements,
    UsageProfile,
    list_usage_profiles,
    usage_requirements,
)
from local_llm_router.quantization import (
    QUANT_MODES,
    adjust_vram_for_quant,
    expand_models_for_quant,
    normalize_quant_mode,
    pull_guidance_lines,
    quant_from_env,
)
from local_llm_router.routing import explain_route, route_prompt
from local_llm_router.session import (
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
from local_llm_router.stack_health import check_stack_health, format_stack_health
from local_llm_router.startup_tips import emit_import_tips, model_recommendation_report
from local_llm_router.tiering import assign_tiers, describe_tiers
from local_llm_router.validation import validate_tier_map

__version__ = "0.4.1"

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
    "check_stack_health",
    "format_stack_health",
    "usage_requirements",
    "validate_tier_map",
    "__version__",
]

# Embedded library use: no import-time stderr. Use ``stack tips`` or ``local_llm_router_IMPORT_TIPS=on``.
