"""
GroqRouter Middleware - Proxy-Agent para classificacao de tarefas.

Intercepta comandos antes da execucao, usa Groq llama3-70b-8192 para
classificar tarefas (REPETITIVE vs STRUCTURAL vs AMBIGUOUS) e resolve
as repetitivas localmente, escalando para Claude Code apenas mudancas
estruturais.
"""

import hashlib
import json
import logging
import time
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Cache defaults
CACHE_TTL_SECONDS = 300
CACHE_MAX_ENTRIES = 256


class TaskComplexity(str, Enum):
    REPETITIVE = "REPETITIVE"
    STRUCTURAL = "STRUCTURAL"
    AMBIGUOUS = "AMBIGUOUS"


class RouterRequest(BaseModel):
    """Requisicao de roteamento."""
    task_description: str
    task_type: str = "general"
    context: dict[str, Any] = Field(default_factory=dict)
    source: str = "unknown"


class RouterResponse(BaseModel):
    """Resposta do roteamento."""
    escalate: bool = False
    complexity: TaskComplexity = TaskComplexity.AMBIGUOUS
    reason: str = ""
    result: Optional[dict[str, Any]] = None
    confidence: float = Field(default=0.5, ge=0.0, le=1.0)
    model_used: str = ""
    latency_ms: float = 0.0


class _CacheEntry:
    """Entrada interna de cache com TTL."""
    __slots__ = ("response", "expires_at")

    def __init__(self, response: RouterResponse, ttl: float):
        self.response = response
        self.expires_at = time.monotonic() + ttl


class GroqRouter:
    """
    Middleware que classifica tarefas via Groq e resolve as repetitivas,
    escalando apenas tarefas estruturais para Claude Code.
    """

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        self.model = model
        self._cache: dict[str, _CacheEntry] = {}

    def route(self, request: RouterRequest) -> RouterResponse:
        """
        Entry point: cache check -> Groq call -> parse -> return.
        Qualquer falha resulta em escalation (safety).
        """
        cache_key = self._cache_key(request)

        # Cache hit?
        cached = self._cache_get(cache_key)
        if cached is not None:
            logger.debug(f"Router cache hit: {cache_key}")
            return cached

        # Call Groq
        try:
            response = self._call_groq(request)
        except Exception as e:
            logger.warning(f"Router Groq call failed: {e}")
            return self._fallback_response(request, e)

        # Cache non-escalated responses with results
        if not response.escalate and response.result is not None:
            self._cache_put(cache_key, response)

        return response

    def _call_groq(self, request: RouterRequest) -> RouterResponse:
        """Chama chat_completion com modelo configurado."""
        from src.utils.llm_client import chat_completion

        messages = [
            {"role": "system", "content": self._build_system_prompt()},
            {"role": "user", "content": self._build_user_message(request)},
        ]

        start = time.monotonic()
        raw = chat_completion(messages, model=self.model)
        latency_ms = (time.monotonic() - start) * 1000

        return self._parse_response(raw, request, latency_ms)

    @staticmethod
    def _build_system_prompt() -> str:
        """Prompt de classificacao com regras HANDLE vs ESCALATE."""
        return (
            "You are a task router. Classify the incoming task and respond with pure JSON (no markdown fences).\n"
            "\n"
            "HANDLE (escalate=false) - tasks you can resolve:\n"
            "- Status checks and monitoring\n"
            "- Form filling and data entry\n"
            "- Data transforms and formatting\n"
            "- Task queue operations (triage, reorder, filter)\n"
            "- Config validation and verification\n"
            "- Report generation and summaries\n"
            "- Monitoring and health checks\n"
            "\n"
            "ESCALATE (escalate=true) - tasks requiring human/Claude Code:\n"
            "- Code modification or generation\n"
            "- Architecture changes\n"
            "- Infrastructure changes\n"
            "- Test creation or modification\n"
            "- Dependency changes\n"
            "- Security-sensitive operations\n"
            "\n"
            "Response format (pure JSON, no markdown):\n"
            '{"escalate": bool, "complexity": "REPETITIVE"|"STRUCTURAL"|"AMBIGUOUS", '
            '"reason": "short explanation", "result": {<data if handled>} or null, '
            '"confidence": 0.0-1.0}'
        )

    @staticmethod
    def _build_user_message(request: RouterRequest) -> str:
        """Formata task + context para o modelo."""
        parts = [f"Task: {request.task_description}", f"Type: {request.task_type}"]
        if request.context:
            parts.append(f"Context: {json.dumps(request.context, default=str)}")
        parts.append(f"Source: {request.source}")
        return "\n".join(parts)

    def _parse_response(
        self, raw: str, request: RouterRequest, latency_ms: float = 0.0
    ) -> RouterResponse:
        """Parse JSON com fallback para texto livre."""
        try:
            # Strip markdown fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                # Remove first line (```json or ```) and last line (```)
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines).strip()

            data = json.loads(cleaned)

            # Validate complexity
            complexity_raw = data.get("complexity", "AMBIGUOUS")
            try:
                complexity = TaskComplexity(complexity_raw)
            except ValueError:
                complexity = TaskComplexity.AMBIGUOUS

            # Clamp confidence
            confidence = float(data.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))

            return RouterResponse(
                escalate=bool(data.get("escalate", True)),
                complexity=complexity,
                reason=str(data.get("reason", "")),
                result=data.get("result"),
                confidence=confidence,
                model_used=self.model,
                latency_ms=latency_ms,
            )
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Router parse failed ({e}), escalating")
            return self._fallback_response(request, e)

    def _fallback_response(self, request: RouterRequest, error: Exception) -> RouterResponse:
        """Qualquer falha Groq -> escalate=True (safety)."""
        return RouterResponse(
            escalate=True,
            complexity=TaskComplexity.AMBIGUOUS,
            reason=f"Fallback due to error: {error}",
            result=None,
            confidence=0.0,
            model_used=self.model,
            latency_ms=0.0,
        )

    # ---- Cache ----

    @staticmethod
    def _cache_key(request: RouterRequest) -> str:
        """SHA-256(description+type+source)[:16]."""
        raw = f"{request.task_description}|{request.task_type}|{request.source}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _cache_get(self, key: str) -> Optional[RouterResponse]:
        """Retorna resposta cacheada se valida (dentro do TTL)."""
        entry = self._cache.get(key)
        if entry is None:
            return None
        if time.monotonic() > entry.expires_at:
            del self._cache[key]
            return None
        return entry.response

    def _cache_put(self, key: str, response: RouterResponse) -> None:
        """Insere no cache com FIFO eviction."""
        # FIFO eviction se cheio
        while len(self._cache) >= CACHE_MAX_ENTRIES:
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]

        self._cache[key] = _CacheEntry(response, CACHE_TTL_SECONDS)
