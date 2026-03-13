"""
LiteLLM Router — Wrapper para roteamento inteligente de modelos LLM.

Substitui o roteamento manual do llm_client.py com:
- Latency-based routing entre modelos do mesmo tier
- Fallback automatico entre tiers
- Cost tracking agregado
- Retry com backoff nativo

Tiers:
  "fast"     → Groq (custo zero, alta velocidade)
  "standard" → GPT-4o-mini / Gemini Flash
  "complex"  → Claude / GPT-4o

Backward compatible: se litellm nao estiver instalado, log warning e noop.
"""

import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config" / "litellm_models.yaml"

# Singleton
_instance: "LiteLLMRouter | None" = None
_instance_lock = threading.Lock()

# Model tier aliases — mapeia nomes de modelos conhecidos para tiers
MODEL_TO_TIER: dict[str, str] = {
    # Groq → fast
    "llama-3.3-70b-versatile": "fast",
    "llama-3.1-8b-instant": "fast",
    "groq/llama-3.3-70b-versatile": "fast",
    "groq/llama-3.1-8b-instant": "fast",
    # OpenAI → standard / complex
    "gpt-4o-mini": "standard",
    "openai/gpt-4o-mini": "standard",
    "gpt-4o": "complex",
    "openai/gpt-4o": "complex",
    # Gemini → standard
    "gemini-1.5-flash": "standard",
    "gemini/gemini-1.5-flash": "standard",
    # Anthropic → complex
    "claude-sonnet-4-20250514": "complex",
    "anthropic/claude-sonnet-4-20250514": "complex",
}


def _litellm_available() -> bool:
    """Verifica se litellm esta instalado."""
    try:
        import litellm  # noqa: F401
        return True
    except ImportError:
        return False


class LiteLLMRouter:
    """
    Wrapper thread-safe para litellm.Router com singleton pattern.
    Matching GraphManager.from_env() pattern.
    """

    def __init__(self, config_path: str | Path | None = None):
        self._config_path = Path(config_path) if config_path else DEFAULT_CONFIG_PATH
        self._router = None
        self._config: dict[str, Any] = {}
        self._lock = threading.Lock()
        self._cost_tracker: dict[str, dict[str, float]] = {}
        self._cost_lock = threading.Lock()
        self._initialized = False

        self._load_config()
        self._init_router()

    def _load_config(self) -> None:
        """Carrega config do YAML."""
        if not self._config_path.exists():
            logger.warning(
                "LiteLLM config not found: %s — router will not be available",
                self._config_path,
            )
            return

        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                self._config = yaml.safe_load(f) or {}
            logger.info("LiteLLM config loaded from %s", self._config_path)
        except Exception as e:
            logger.error("Failed to load LiteLLM config: %s", e)
            self._config = {}

    def _init_router(self) -> None:
        """Inicializa litellm.Router a partir da config."""
        if not self._config.get("model_list"):
            logger.warning("No model_list in LiteLLM config — router disabled")
            return

        if not _litellm_available():
            logger.warning(
                "litellm not installed — LiteLLMRouter disabled. "
                "Install with: pip install litellm>=1.40.0"
            )
            return

        try:
            from litellm import Router

            router_settings = self._config.get("router_settings", {})
            fallbacks = router_settings.pop("fallbacks", None)

            self._router = Router(
                model_list=self._config["model_list"],
                fallbacks=fallbacks or [],
                num_retries=router_settings.get("num_retries", 3),
                retry_after=router_settings.get("retry_after", 5),
                timeout=router_settings.get("timeout", 30),
                routing_strategy=router_settings.get(
                    "routing_strategy", "latency-based-routing"
                ),
                enable_pre_call_checks=router_settings.get(
                    "enable_pre_call_checks", True
                ),
            )
            self._initialized = True
            logger.info(
                "LiteLLM Router initialized — %d model deployments, strategy=%s",
                len(self._config["model_list"]),
                router_settings.get("routing_strategy", "latency-based-routing"),
            )
        except Exception as e:
            logger.error("Failed to initialize LiteLLM Router: %s", e)
            self._router = None
            self._initialized = False

    @classmethod
    def from_env(cls, config_path: str | Path | None = None) -> "LiteLLMRouter":
        """Cria LiteLLMRouter singleton a partir da config YAML."""
        global _instance
        with _instance_lock:
            if _instance is None:
                _instance = cls(config_path=config_path)
            return _instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset singleton (para testes)."""
        global _instance
        with _instance_lock:
            _instance = None

    @property
    def is_available(self) -> bool:
        """Retorna True se o router esta inicializado e pronto."""
        return self._initialized and self._router is not None

    # ── Completion Methods ──

    async def completion(
        self,
        prompt: str,
        model_tier: str = "fast",
        temperature: float = 0.3,
        max_tokens: int = 2048,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Completion com prompt simples. Converte para messages internamente.

        Args:
            prompt: Texto do prompt (role=user)
            model_tier: "fast", "standard" ou "complex"
            temperature: 0.0 - 1.0
            max_tokens: Limite de tokens na resposta
            system_prompt: System message opcional

        Returns:
            {content, model, usage: {prompt_tokens, completion_tokens, total_cost}, latency_ms}
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return await self.completion_with_messages(
            messages=messages,
            model_tier=model_tier,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    async def completion_with_messages(
        self,
        messages: list[dict[str, str]],
        model_tier: str = "fast",
        temperature: float = 0.3,
        max_tokens: int = 2048,
    ) -> dict[str, Any]:
        """
        Completion com lista de messages (chat format).

        Args:
            messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
            model_tier: "fast", "standard" ou "complex"
            temperature: 0.0 - 1.0
            max_tokens: Limite de tokens na resposta

        Returns:
            {content, model, usage: {prompt_tokens, completion_tokens, total_cost}, latency_ms}
        """
        if not self.is_available:
            raise RuntimeError(
                "LiteLLM Router not available. "
                "Check config and litellm installation."
            )

        start = time.perf_counter()

        try:
            response = await self._router.acompletion(
                model=model_tier,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            latency_ms = (time.perf_counter() - start) * 1000

            # Extrai info da response
            content = response.choices[0].message.content or ""
            model_used = getattr(response, "model", model_tier)
            usage = getattr(response, "usage", None)

            prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else 0
            completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0

            # Estima custo via litellm.completion_cost
            total_cost = 0.0
            try:
                from litellm import completion_cost

                total_cost = completion_cost(completion_response=response) or 0.0
            except Exception:
                pass

            # Registra no cost tracker
            self._record_cost(model_used, prompt_tokens, completion_tokens, total_cost, latency_ms)

            # Registra no cost_context se disponivel
            self._record_cost_context(model_used, prompt_tokens, completion_tokens, latency_ms)

            result = {
                "content": content.strip(),
                "model": model_used,
                "usage": {
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_cost": total_cost,
                },
                "latency_ms": round(latency_ms, 2),
            }

            logger.debug(
                "LiteLLM completion: tier=%s model=%s tokens=%d+%d cost=$%.6f latency=%.0fms",
                model_tier, model_used, prompt_tokens, completion_tokens,
                total_cost, latency_ms,
            )

            return result

        except Exception as e:
            latency_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "LiteLLM completion failed: tier=%s error=%s latency=%.0fms",
                model_tier, e, latency_ms,
            )
            raise

    # ── Cost Tracking ──

    def _record_cost(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost: float,
        latency_ms: float,
    ) -> None:
        """Registra custo no tracker interno (thread-safe)."""
        with self._cost_lock:
            if model not in self._cost_tracker:
                self._cost_tracker[model] = {
                    "calls": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                    "total_cost": 0.0,
                    "total_latency_ms": 0.0,
                }
            stats = self._cost_tracker[model]
            stats["calls"] += 1
            stats["prompt_tokens"] += prompt_tokens
            stats["completion_tokens"] += completion_tokens
            stats["total_cost"] += cost
            stats["total_latency_ms"] += latency_ms

    def _record_cost_context(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
    ) -> None:
        """Registra no cost_context global se disponivel (compatibilidade com pipeline)."""
        try:
            from src.utils.cost_context import get_cost_profile

            profile = get_cost_profile()
            if profile and hasattr(profile, "record_llm_call_with_latency"):
                profile.record_llm_call_with_latency(model, prompt_tokens, completion_tokens, latency_ms)
            elif profile and hasattr(profile, "record_llm_call"):
                profile.record_llm_call(model, prompt_tokens, completion_tokens)
        except ImportError:
            pass

    def get_cost_stats(self) -> dict[str, Any]:
        """
        Retorna estatisticas agregadas de custo.

        Returns:
            {
                total_cost: float,
                total_calls: int,
                total_tokens: int,
                by_model: {model: {calls, prompt_tokens, completion_tokens, total_cost, avg_latency_ms}},
            }
        """
        with self._cost_lock:
            total_cost = 0.0
            total_calls = 0
            total_tokens = 0
            by_model = {}

            for model, stats in self._cost_tracker.items():
                total_cost += stats["total_cost"]
                total_calls += stats["calls"]
                total_tokens += stats["prompt_tokens"] + stats["completion_tokens"]
                avg_latency = (
                    stats["total_latency_ms"] / stats["calls"]
                    if stats["calls"] > 0
                    else 0.0
                )
                by_model[model] = {
                    "calls": stats["calls"],
                    "prompt_tokens": stats["prompt_tokens"],
                    "completion_tokens": stats["completion_tokens"],
                    "total_cost": round(stats["total_cost"], 6),
                    "avg_latency_ms": round(avg_latency, 2),
                }

            return {
                "total_cost": round(total_cost, 6),
                "total_calls": total_calls,
                "total_tokens": total_tokens,
                "by_model": by_model,
            }

    # ── Model Info ──

    def get_available_models(self) -> list[dict[str, Any]]:
        """
        Retorna lista de modelos disponiveis com info de saude.

        Returns:
            [{model_name, litellm_model, tier, healthy, avg_latency_ms}]
        """
        if not self.is_available:
            return []

        models = []
        for deployment in self._config.get("model_list", []):
            model_name = deployment.get("model_name", "unknown")
            litellm_model = deployment.get("litellm_params", {}).get("model", "unknown")

            # Latency do cost tracker
            avg_latency = 0.0
            with self._cost_lock:
                stats = self._cost_tracker.get(litellm_model, {})
                if stats and stats.get("calls", 0) > 0:
                    avg_latency = stats["total_latency_ms"] / stats["calls"]

            models.append({
                "model_name": model_name,
                "litellm_model": litellm_model,
                "tier": model_name,
                "healthy": True,  # litellm gerencia health internamente
                "avg_latency_ms": round(avg_latency, 2),
            })

        return models

    @staticmethod
    def resolve_tier(model: str | None) -> str:
        """
        Resolve um nome de modelo para tier.
        Usado pelo llm_client para mapear parametros antigos.

        Args:
            model: Nome do modelo (ex: "gpt-4o-mini") ou None

        Returns:
            "fast", "standard" ou "complex"
        """
        if model is None:
            return "fast"
        return MODEL_TO_TIER.get(model, "standard")
