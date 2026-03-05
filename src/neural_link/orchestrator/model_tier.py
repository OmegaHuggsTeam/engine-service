"""
ModelTier - Tiered model selection for cost optimization.

Routes tasks to the cheapest model capable of handling them:
- FAST (8b): queries, triage, evaluation, synthesis
- STANDARD (70b): generation, analysis, repair, complex tasks
"""

import os
from enum import Enum

# Model IDs per tier
_DEFAULT_FAST_MODEL = "llama-3.1-8b-instant"
_DEFAULT_STANDARD_MODEL = "llama-3.3-70b-versatile"


class ModelTier(str, Enum):
    FAST = "fast"
    STANDARD = "standard"


TIER_MODELS = {
    ModelTier.FAST: os.getenv("LLM_MODEL_FAST", _DEFAULT_FAST_MODEL),
    ModelTier.STANDARD: os.getenv("LLM_MODEL_STANDARD", _DEFAULT_STANDARD_MODEL),
}

# Default tier per task type
TASK_TYPE_TIERS = {
    "query": ModelTier.FAST,
    "analysis": ModelTier.STANDARD,
    "generation": ModelTier.STANDARD,
    "automation": ModelTier.FAST,
    "repair": ModelTier.STANDARD,
}

# Internal operations use FAST tier (structured output, classification)
EVALUATION_TIER = ModelTier.FAST
DECOMPOSITION_TIER = ModelTier.FAST
SYNTHESIS_TIER = ModelTier.FAST

# Max tokens per operation type
MAX_TOKENS = {
    "evaluation": 200,
    "refinement": 300,
    "synthesis": 500,
    "decomposition": 400,
}


def select_model(task_type: str, complexity_score: float = 0.5) -> str:
    """
    Select the appropriate model for a task.

    Args:
        task_type: Type of task (query, analysis, generation, automation, repair).
        complexity_score: 0.0-1.0 score. Above 0.7 forces STANDARD tier.

    Returns:
        Model ID string.
    """
    tier = TASK_TYPE_TIERS.get(task_type, ModelTier.STANDARD)

    # High complexity always uses STANDARD
    if complexity_score > 0.7:
        tier = ModelTier.STANDARD

    return TIER_MODELS[tier]


def get_tier_model(tier: ModelTier) -> str:
    """Get model ID for a specific tier."""
    return TIER_MODELS[tier]


def get_operation_model(operation: str) -> str:
    """Get model for internal operations (evaluation, decomposition, synthesis)."""
    tier_map = {
        "evaluation": EVALUATION_TIER,
        "refinement": EVALUATION_TIER,
        "decomposition": DECOMPOSITION_TIER,
        "synthesis": SYNTHESIS_TIER,
    }
    tier = tier_map.get(operation, ModelTier.STANDARD)
    return TIER_MODELS[tier]


def get_max_tokens(operation: str) -> int | None:
    """Get max_tokens limit for an operation. None = no limit."""
    return MAX_TOKENS.get(operation)
