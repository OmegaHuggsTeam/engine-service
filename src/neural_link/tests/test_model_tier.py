"""
Tests for ModelTier — Layer 3: Tiered model selection.

Covers select_model for each task type, complexity override, tier mapping,
get_operation_model, and get_max_tokens.
"""

import pytest

from src.neural_link.orchestrator.model_tier import (
    ModelTier,
    TIER_MODELS,
    TASK_TYPE_TIERS,
    MAX_TOKENS,
    select_model,
    get_operation_model,
    get_max_tokens,
)


# ==================================================================
# TestModelTierEnum
# ==================================================================


class TestModelTierEnum:
    """ModelTier enum values."""

    def test_fast_tier(self):
        assert ModelTier.FAST == "fast"

    def test_standard_tier(self):
        assert ModelTier.STANDARD == "standard"

    def test_tier_models_mapping(self):
        assert "8b" in TIER_MODELS[ModelTier.FAST]
        assert "70b" in TIER_MODELS[ModelTier.STANDARD]


# ==================================================================
# TestSelectModel
# ==================================================================


class TestSelectModel:
    """select_model() returns correct model for task type and complexity."""

    def test_query_gets_fast(self):
        model = select_model("query")
        assert model == TIER_MODELS[ModelTier.FAST]

    def test_automation_gets_fast(self):
        model = select_model("automation")
        assert model == TIER_MODELS[ModelTier.FAST]

    def test_generation_gets_standard(self):
        model = select_model("generation")
        assert model == TIER_MODELS[ModelTier.STANDARD]

    def test_analysis_gets_standard(self):
        model = select_model("analysis")
        assert model == TIER_MODELS[ModelTier.STANDARD]

    def test_repair_gets_standard(self):
        model = select_model("repair")
        assert model == TIER_MODELS[ModelTier.STANDARD]

    def test_unknown_type_defaults_to_standard(self):
        model = select_model("unknown_type")
        assert model == TIER_MODELS[ModelTier.STANDARD]

    def test_high_complexity_overrides_to_standard(self):
        model = select_model("query", complexity_score=0.8)
        assert model == TIER_MODELS[ModelTier.STANDARD]

    def test_low_complexity_keeps_fast(self):
        model = select_model("query", complexity_score=0.3)
        assert model == TIER_MODELS[ModelTier.FAST]


# ==================================================================
# TestOperationModel
# ==================================================================


class TestOperationModel:
    """get_operation_model() returns correct model for each operation."""

    def test_evaluation_uses_fast(self):
        model = get_operation_model("evaluation")
        assert model == TIER_MODELS[ModelTier.FAST]

    def test_decomposition_uses_fast(self):
        model = get_operation_model("decomposition")
        assert model == TIER_MODELS[ModelTier.FAST]

    def test_synthesis_uses_fast(self):
        model = get_operation_model("synthesis")
        assert model == TIER_MODELS[ModelTier.FAST]

    def test_refinement_uses_fast(self):
        model = get_operation_model("refinement")
        assert model == TIER_MODELS[ModelTier.FAST]

    def test_unknown_operation_returns_standard(self):
        model = get_operation_model("unknown")
        assert model == TIER_MODELS[ModelTier.STANDARD]


# ==================================================================
# TestMaxTokens
# ==================================================================


class TestMaxTokens:
    """get_max_tokens() returns configured limits per operation."""

    def test_evaluation_max_tokens(self):
        assert get_max_tokens("evaluation") == MAX_TOKENS["evaluation"]

    def test_synthesis_max_tokens(self):
        assert get_max_tokens("synthesis") == MAX_TOKENS["synthesis"]

    def test_refinement_max_tokens(self):
        assert get_max_tokens("refinement") == MAX_TOKENS["refinement"]

    def test_decomposition_max_tokens(self):
        assert get_max_tokens("decomposition") == MAX_TOKENS["decomposition"]

    def test_unknown_returns_none(self):
        assert get_max_tokens("unknown") is None


# ==================================================================
# TestTaskTypeTiers
# ==================================================================


class TestTaskTypeTiers:
    """TASK_TYPE_TIERS mapping is complete."""

    def test_all_expected_types_mapped(self):
        expected = {"query", "automation", "analysis", "generation", "repair"}
        assert set(TASK_TYPE_TIERS.keys()) == expected

    def test_fast_types(self):
        fast_types = [k for k, v in TASK_TYPE_TIERS.items() if v == ModelTier.FAST]
        assert "query" in fast_types
        assert "automation" in fast_types

    def test_standard_types(self):
        std_types = [k for k, v in TASK_TYPE_TIERS.items() if v == ModelTier.STANDARD]
        assert "generation" in std_types
        assert "repair" in std_types
        assert "analysis" in std_types
