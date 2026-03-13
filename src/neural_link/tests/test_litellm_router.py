"""
Tests for LiteLLMRouter — Wrapper para roteamento inteligente de modelos LLM.

Covers:
- Config loading from YAML
- Model tier routing (fast/standard/complex)
- Fallback when litellm not installed
- Cost stats aggregation
- Singleton pattern (from_env, reset)
- resolve_tier mapping
- Integration with chat_completion (LiteLLM delegation)
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

import pytest
import yaml

from src.utils.litellm_router import (
    LiteLLMRouter,
    MODEL_TO_TIER,
    _litellm_available,
    DEFAULT_CONFIG_PATH,
)


# ==================================================================
# Fixtures
# ==================================================================

SAMPLE_CONFIG = {
    "model_list": [
        {
            "model_name": "fast",
            "litellm_params": {
                "model": "groq/llama-3.3-70b-versatile",
                "api_key": "os.environ/GROQ_API_KEY",
            },
        },
        {
            "model_name": "standard",
            "litellm_params": {
                "model": "openai/gpt-4o-mini",
                "api_key": "os.environ/OPENAI_API_KEY",
            },
        },
        {
            "model_name": "complex",
            "litellm_params": {
                "model": "anthropic/claude-sonnet-4-20250514",
                "api_key": "os.environ/ANTHROPIC_API_KEY",
            },
        },
    ],
    "router_settings": {
        "routing_strategy": "latency-based-routing",
        "num_retries": 3,
        "retry_after": 5,
        "timeout": 30,
        "fallbacks": [
            {"fast": ["standard"]},
            {"standard": ["fast"]},
            {"complex": ["standard"]},
        ],
        "enable_pre_call_checks": True,
    },
}


@pytest.fixture
def config_file(tmp_path):
    """Cria arquivo YAML de config temporario."""
    config_path = tmp_path / "litellm_models.yaml"
    with open(config_path, "w") as f:
        yaml.dump(SAMPLE_CONFIG, f)
    return config_path


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton entre testes."""
    LiteLLMRouter.reset_instance()
    yield
    LiteLLMRouter.reset_instance()


# ==================================================================
# TestConfigLoading
# ==================================================================


class TestConfigLoading:
    """Config loading from YAML."""

    def test_loads_valid_config(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        assert router._config is not None
        assert len(router._config["model_list"]) == 3

    def test_missing_config_file(self, tmp_path):
        missing = tmp_path / "nonexistent.yaml"
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=missing)

        assert router._config == {}
        assert not router.is_available

    def test_default_config_path(self):
        assert DEFAULT_CONFIG_PATH.name == "litellm_models.yaml"
        assert "config" in str(DEFAULT_CONFIG_PATH)

    def test_loads_model_list(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        tiers = [m["model_name"] for m in router._config["model_list"]]
        assert "fast" in tiers
        assert "standard" in tiers
        assert "complex" in tiers

    def test_loads_router_settings(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        settings = router._config.get("router_settings", {})
        assert settings["num_retries"] == 3
        assert settings["timeout"] == 30

    def test_invalid_yaml_handles_gracefully(self, tmp_path):
        bad_file = tmp_path / "bad.yaml"
        bad_file.write_text("{{invalid yaml: [")
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=bad_file)

        # Should not crash, config should be empty
        assert not router.is_available


# ==================================================================
# TestSingletonPattern
# ==================================================================


class TestSingletonPattern:
    """Singleton via from_env() matching GraphManager pattern."""

    def test_from_env_returns_same_instance(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            r1 = LiteLLMRouter.from_env(config_path=config_file)
            r2 = LiteLLMRouter.from_env(config_path=config_file)

        assert r1 is r2

    def test_reset_instance_clears_singleton(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            r1 = LiteLLMRouter.from_env(config_path=config_file)
            LiteLLMRouter.reset_instance()
            r2 = LiteLLMRouter.from_env(config_path=config_file)

        assert r1 is not r2


# ==================================================================
# TestResolveTier
# ==================================================================


class TestResolveTier:
    """resolve_tier() maps model names to tiers."""

    def test_none_resolves_to_fast(self):
        assert LiteLLMRouter.resolve_tier(None) == "fast"

    def test_groq_models_resolve_to_fast(self):
        assert LiteLLMRouter.resolve_tier("llama-3.3-70b-versatile") == "fast"
        assert LiteLLMRouter.resolve_tier("llama-3.1-8b-instant") == "fast"
        assert LiteLLMRouter.resolve_tier("groq/llama-3.3-70b-versatile") == "fast"

    def test_gpt4o_mini_resolves_to_standard(self):
        assert LiteLLMRouter.resolve_tier("gpt-4o-mini") == "standard"
        assert LiteLLMRouter.resolve_tier("openai/gpt-4o-mini") == "standard"

    def test_gemini_resolves_to_standard(self):
        assert LiteLLMRouter.resolve_tier("gemini-1.5-flash") == "standard"
        assert LiteLLMRouter.resolve_tier("gemini/gemini-1.5-flash") == "standard"

    def test_gpt4o_resolves_to_complex(self):
        assert LiteLLMRouter.resolve_tier("gpt-4o") == "complex"
        assert LiteLLMRouter.resolve_tier("openai/gpt-4o") == "complex"

    def test_claude_resolves_to_complex(self):
        assert LiteLLMRouter.resolve_tier("claude-sonnet-4-20250514") == "complex"

    def test_unknown_model_defaults_to_standard(self):
        assert LiteLLMRouter.resolve_tier("some-random-model") == "standard"


# ==================================================================
# TestModelToTierMapping
# ==================================================================


class TestModelToTierMapping:
    """MODEL_TO_TIER constant is complete and correct."""

    def test_has_groq_models(self):
        groq_models = [k for k, v in MODEL_TO_TIER.items() if v == "fast"]
        assert len(groq_models) >= 2

    def test_has_standard_models(self):
        standard_models = [k for k, v in MODEL_TO_TIER.items() if v == "standard"]
        assert len(standard_models) >= 2

    def test_has_complex_models(self):
        complex_models = [k for k, v in MODEL_TO_TIER.items() if v == "complex"]
        assert len(complex_models) >= 2

    def test_all_tiers_represented(self):
        tiers = set(MODEL_TO_TIER.values())
        assert tiers == {"fast", "standard", "complex"}


# ==================================================================
# TestIsAvailable
# ==================================================================


class TestIsAvailable:
    """is_available reflects router state correctly."""

    def test_not_available_without_litellm(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        assert not router.is_available

    def test_not_available_without_config(self, tmp_path):
        missing = tmp_path / "missing.yaml"
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=missing)

        assert not router.is_available


# ==================================================================
# TestCompletion
# ==================================================================


class TestCompletion:
    """completion() and completion_with_messages() behavior."""

    def test_raises_when_not_available(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        with pytest.raises(RuntimeError, match="not available"):
            asyncio.run(router.completion("test prompt"))

    def test_raises_with_messages_when_not_available(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        messages = [{"role": "user", "content": "test"}]
        with pytest.raises(RuntimeError, match="not available"):
            asyncio.run(router.completion_with_messages(messages))

    def test_completion_delegates_to_router(self, config_file):
        """Mock litellm.Router and verify delegation."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Hello from LiteLLM"
        mock_response.model = "groq/llama-3.3-70b-versatile"
        mock_usage = MagicMock()
        mock_usage.prompt_tokens = 10
        mock_usage.completion_tokens = 20
        mock_response.usage = mock_usage

        mock_router_instance = MagicMock()
        mock_router_instance.acompletion = AsyncMock(return_value=mock_response)

        with patch("src.utils.litellm_router._litellm_available", return_value=True), \
             patch("src.utils.litellm_router.Router", return_value=mock_router_instance):
            # Force fresh import to use patched Router
            router = LiteLLMRouter(config_path=config_file)
            router._router = mock_router_instance
            router._initialized = True

            result = asyncio.run(router.completion("test prompt", model_tier="fast"))

        assert result["content"] == "Hello from LiteLLM"
        assert result["model"] == "groq/llama-3.3-70b-versatile"
        assert result["usage"]["prompt_tokens"] == 10
        assert result["usage"]["completion_tokens"] == 20
        assert "latency_ms" in result

    def test_completion_with_system_prompt(self, config_file):
        """System prompt is included in messages."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Response"
        mock_response.model = "test-model"
        mock_response.usage = MagicMock(prompt_tokens=5, completion_tokens=5)

        mock_router_instance = MagicMock()
        mock_router_instance.acompletion = AsyncMock(return_value=mock_response)

        with patch("src.utils.litellm_router._litellm_available", return_value=True):
            router = LiteLLMRouter(config_path=config_file)
            router._router = mock_router_instance
            router._initialized = True

            asyncio.run(
                router.completion(
                    "user prompt",
                    system_prompt="You are helpful",
                    model_tier="fast",
                )
            )

        call_args = mock_router_instance.acompletion.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[0]["content"] == "You are helpful"
        assert messages[1]["role"] == "user"
        assert messages[1]["content"] == "user prompt"


# ==================================================================
# TestCostStats
# ==================================================================


class TestCostStats:
    """get_cost_stats() aggregation."""

    def test_empty_stats(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        stats = router.get_cost_stats()
        assert stats["total_cost"] == 0.0
        assert stats["total_calls"] == 0
        assert stats["total_tokens"] == 0
        assert stats["by_model"] == {}

    def test_records_single_call(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        router._record_cost("groq/llama-3.3-70b-versatile", 100, 50, 0.001, 42.5)

        stats = router.get_cost_stats()
        assert stats["total_cost"] == 0.001
        assert stats["total_calls"] == 1
        assert stats["total_tokens"] == 150
        assert "groq/llama-3.3-70b-versatile" in stats["by_model"]

    def test_records_multiple_calls(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        router._record_cost("model_a", 100, 50, 0.001, 40.0)
        router._record_cost("model_a", 200, 100, 0.002, 60.0)
        router._record_cost("model_b", 50, 25, 0.0005, 30.0)

        stats = router.get_cost_stats()
        assert stats["total_calls"] == 3
        assert stats["total_cost"] == 0.0035
        assert stats["total_tokens"] == 525

        assert stats["by_model"]["model_a"]["calls"] == 2
        assert stats["by_model"]["model_a"]["prompt_tokens"] == 300
        assert stats["by_model"]["model_a"]["avg_latency_ms"] == 50.0

        assert stats["by_model"]["model_b"]["calls"] == 1

    def test_cost_stats_rounding(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        router._record_cost("model_x", 10, 5, 0.0000001, 1.0)

        stats = router.get_cost_stats()
        # total_cost rounded to 6 decimals
        assert stats["total_cost"] == 0.0
        assert stats["by_model"]["model_x"]["total_cost"] == 0.0


# ==================================================================
# TestGetAvailableModels
# ==================================================================


class TestGetAvailableModels:
    """get_available_models() returns model info."""

    def test_returns_empty_when_not_available(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        assert router.get_available_models() == []

    def test_returns_models_when_available(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=True):
            router = LiteLLMRouter(config_path=config_file)
            # Fake availability
            router._initialized = True
            router._router = MagicMock()

        models = router.get_available_models()
        assert len(models) == 3

        tiers = [m["tier"] for m in models]
        assert "fast" in tiers
        assert "standard" in tiers
        assert "complex" in tiers

    def test_model_entry_structure(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=True):
            router = LiteLLMRouter(config_path=config_file)
            router._initialized = True
            router._router = MagicMock()

        models = router.get_available_models()
        entry = models[0]

        assert "model_name" in entry
        assert "litellm_model" in entry
        assert "tier" in entry
        assert "healthy" in entry
        assert "avg_latency_ms" in entry

    def test_includes_latency_from_tracker(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=True):
            router = LiteLLMRouter(config_path=config_file)
            router._initialized = True
            router._router = MagicMock()

        # Record some calls
        router._record_cost("groq/llama-3.3-70b-versatile", 10, 5, 0.0, 100.0)
        router._record_cost("groq/llama-3.3-70b-versatile", 10, 5, 0.0, 200.0)

        models = router.get_available_models()
        fast_model = [m for m in models if m["litellm_model"] == "groq/llama-3.3-70b-versatile"]
        assert len(fast_model) == 1
        assert fast_model[0]["avg_latency_ms"] == 150.0


# ==================================================================
# TestFallbackWithoutLiteLLM
# ==================================================================


class TestFallbackWithoutLiteLLM:
    """Behavior when litellm is not installed."""

    def test_litellm_available_detection(self):
        # This test validates the function exists and returns bool
        result = _litellm_available()
        assert isinstance(result, bool)

    def test_router_disabled_without_litellm(self, config_file):
        with patch("src.utils.litellm_router._litellm_available", return_value=False):
            router = LiteLLMRouter(config_path=config_file)

        assert not router.is_available
        assert router._router is None

    def test_chat_completion_falls_back_when_litellm_unavailable(self):
        """chat_completion() falls back to manual routing when LiteLLM not available."""
        with patch("src.utils.llm_client._get_litellm_router", return_value=None), \
             patch("src.utils.llm_client._chat_groq", return_value="groq response") as mock_groq:

            from src.utils.llm_client import chat_completion

            result = chat_completion(
                messages=[{"role": "user", "content": "test"}],
            )

            assert result == "groq response"
            mock_groq.assert_called_once()


# ==================================================================
# TestChatCompletionIntegration
# ==================================================================


class TestChatCompletionIntegration:
    """Integration: chat_completion() delegates to LiteLLMRouter."""

    def test_delegates_to_litellm_when_available(self):
        """When LiteLLMRouter is available, chat_completion delegates to it."""
        mock_router = MagicMock()
        mock_router.is_available = True

        async def mock_completion(**kwargs):
            return {"content": "litellm response", "model": "test", "usage": {}, "latency_ms": 10.0}

        mock_router.completion_with_messages = AsyncMock(side_effect=mock_completion)

        with patch("src.utils.llm_client._get_litellm_router", return_value=mock_router), \
             patch("src.utils.litellm_router.LiteLLMRouter.resolve_tier", return_value="fast"):

            from src.utils.llm_client import chat_completion

            result = chat_completion(
                messages=[{"role": "user", "content": "test"}],
            )

            assert result == "litellm response"

    def test_falls_back_on_litellm_error(self):
        """When LiteLLM raises, falls back to manual routing."""
        mock_router = MagicMock()
        mock_router.is_available = True
        mock_router.completion_with_messages = AsyncMock(side_effect=RuntimeError("LiteLLM boom"))

        with patch("src.utils.llm_client._get_litellm_router", return_value=mock_router), \
             patch("src.utils.llm_client._chat_groq", return_value="groq fallback") as mock_groq:

            from src.utils.llm_client import chat_completion

            result = chat_completion(
                messages=[{"role": "user", "content": "test"}],
            )

            assert result == "groq fallback"
            mock_groq.assert_called_once()

    def test_skips_litellm_when_api_key_override(self):
        """When api_key is explicitly provided, skip LiteLLM."""
        with patch("src.utils.llm_client._get_litellm_router") as mock_get_router, \
             patch("src.utils.llm_client._chat_groq", return_value="direct response"):

            from src.utils.llm_client import chat_completion

            result = chat_completion(
                messages=[{"role": "user", "content": "test"}],
                api_key="explicit-key",
            )

            # _get_litellm_router should NOT have been called
            mock_get_router.assert_not_called()

    def test_tier_mapping_in_delegation(self):
        """Model names are correctly mapped to tiers."""
        mock_router = MagicMock()
        mock_router.is_available = True

        async def capture_tier(**kwargs):
            return {
                "content": f"tier={kwargs.get('model_tier', 'unknown')}",
                "model": "test",
                "usage": {},
                "latency_ms": 1.0,
            }

        mock_router.completion_with_messages = AsyncMock(side_effect=capture_tier)

        with patch("src.utils.llm_client._get_litellm_router", return_value=mock_router):
            from src.utils.llm_client import chat_completion

            # gpt-4o-mini → standard
            result = chat_completion(
                messages=[{"role": "user", "content": "test"}],
                model="gpt-4o-mini",
            )

            call_kwargs = mock_router.completion_with_messages.call_args.kwargs
            assert call_kwargs["model_tier"] == "standard"
