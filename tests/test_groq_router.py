"""
Testes unitarios para o GroqRouter middleware.
Todos os testes usam chat_completion mockado (sem chamadas reais ao Groq).
"""

import json
import time
from unittest.mock import MagicMock, patch

import pytest

from src.middleware.groq_router import (
    TaskComplexity,
    RouterRequest,
    RouterResponse,
    GroqRouter,
    CACHE_TTL_SECONDS,
    CACHE_MAX_ENTRIES,
)


# ============================================================
# Helpers
# ============================================================

def _make_request(desc="Check status", task_type="status_check", source="test"):
    return RouterRequest(
        task_description=desc,
        task_type=task_type,
        context={"provider": "google"},
        source=source,
    )


def _groq_json_response(
    escalate=False,
    complexity="REPETITIVE",
    reason="handled",
    result=None,
    confidence=0.9,
):
    """Simula resposta JSON do Groq."""
    return json.dumps({
        "escalate": escalate,
        "complexity": complexity,
        "reason": reason,
        "result": result or {"status": "ok"},
        "confidence": confidence,
    })


# ============================================================
# TestModels
# ============================================================

class TestModels:
    def test_task_complexity_enum_values(self):
        assert TaskComplexity.REPETITIVE.value == "REPETITIVE"
        assert TaskComplexity.STRUCTURAL.value == "STRUCTURAL"
        assert TaskComplexity.AMBIGUOUS.value == "AMBIGUOUS"

    def test_router_request_defaults(self):
        req = RouterRequest(task_description="test")
        assert req.task_type == "general"
        assert req.context == {}
        assert req.source == "unknown"

    def test_router_response_defaults(self):
        resp = RouterResponse()
        assert resp.escalate is False
        assert resp.complexity == TaskComplexity.AMBIGUOUS
        assert resp.confidence == 0.5
        assert resp.result is None
        assert resp.model_used == ""

    def test_router_response_escalation_flag(self):
        resp = RouterResponse(escalate=True, complexity=TaskComplexity.STRUCTURAL)
        assert resp.escalate is True
        assert resp.complexity == TaskComplexity.STRUCTURAL

    def test_router_request_with_context(self):
        req = RouterRequest(
            task_description="Fill form",
            task_type="form_fill",
            context={"fields": ["email", "name"]},
            source="identity_manager",
        )
        assert req.context["fields"] == ["email", "name"]
        assert req.source == "identity_manager"


# ============================================================
# TestRouting
# ============================================================

class TestRouting:
    @patch("src.utils.llm_client.chat_completion")
    def test_repetitive_task_handled(self, mock_chat):
        mock_chat.return_value = _groq_json_response(
            escalate=False, complexity="REPETITIVE", confidence=0.95,
            result={"status": "all_ok", "pending": 0},
        )
        router = GroqRouter()
        req = _make_request("Check status of google provider")
        resp = router.route(req)

        assert resp.escalate is False
        assert resp.complexity == TaskComplexity.REPETITIVE
        assert resp.confidence == 0.95
        assert resp.result == {"status": "all_ok", "pending": 0}
        assert resp.model_used == "llama3-70b-8192"
        mock_chat.assert_called_once()

    @patch("src.utils.llm_client.chat_completion")
    def test_structural_task_escalated(self, mock_chat):
        mock_chat.return_value = _groq_json_response(
            escalate=True, complexity="STRUCTURAL", confidence=0.85,
            result=None,
        )
        router = GroqRouter()
        req = _make_request("Refactor authentication module", "code_change")
        resp = router.route(req)

        assert resp.escalate is True
        assert resp.complexity == TaskComplexity.STRUCTURAL
        mock_chat.assert_called_once()

    @patch("src.utils.llm_client.chat_completion")
    def test_groq_failure_escalates(self, mock_chat):
        mock_chat.side_effect = RuntimeError("Groq API down")
        router = GroqRouter()
        req = _make_request()
        resp = router.route(req)

        assert resp.escalate is True
        assert resp.confidence == 0.0
        assert "error" in resp.reason.lower()

    @patch("src.utils.llm_client.chat_completion")
    def test_malformed_json_escalates(self, mock_chat):
        mock_chat.return_value = "This is not JSON at all"
        router = GroqRouter()
        req = _make_request()
        resp = router.route(req)

        assert resp.escalate is True
        assert resp.confidence == 0.0

    @patch("src.utils.llm_client.chat_completion")
    def test_model_override(self, mock_chat):
        mock_chat.return_value = _groq_json_response()
        router = GroqRouter(model="llama-3.3-70b-versatile")
        req = _make_request()
        resp = router.route(req)

        assert resp.model_used == "llama-3.3-70b-versatile"
        # Verify model was passed to chat_completion
        call_args = mock_chat.call_args
        assert call_args[1].get("model") == "llama-3.3-70b-versatile" or \
               call_args[0][1] == "llama-3.3-70b-versatile"

    @patch("src.utils.llm_client.chat_completion")
    def test_latency_tracked(self, mock_chat):
        mock_chat.return_value = _groq_json_response()
        router = GroqRouter()
        req = _make_request()
        resp = router.route(req)

        assert resp.latency_ms >= 0


# ============================================================
# TestParsing
# ============================================================

class TestParsing:
    def test_valid_json(self):
        router = GroqRouter()
        raw = _groq_json_response(
            escalate=False, complexity="REPETITIVE", confidence=0.8,
            result={"data": "value"},
        )
        req = _make_request()
        resp = router._parse_response(raw, req, latency_ms=42.0)

        assert resp.escalate is False
        assert resp.complexity == TaskComplexity.REPETITIVE
        assert resp.confidence == 0.8
        assert resp.result == {"data": "value"}
        assert resp.latency_ms == 42.0

    def test_markdown_fences_stripped(self):
        router = GroqRouter()
        raw = '```json\n{"escalate": false, "complexity": "REPETITIVE", "reason": "ok", "result": {"x": 1}, "confidence": 0.9}\n```'
        req = _make_request()
        resp = router._parse_response(raw, req)

        assert resp.escalate is False
        assert resp.complexity == TaskComplexity.REPETITIVE
        assert resp.result == {"x": 1}

    def test_invalid_complexity_falls_back_to_ambiguous(self):
        router = GroqRouter()
        raw = json.dumps({
            "escalate": False,
            "complexity": "UNKNOWN_VALUE",
            "reason": "test",
            "result": None,
            "confidence": 0.5,
        })
        req = _make_request()
        resp = router._parse_response(raw, req)

        assert resp.complexity == TaskComplexity.AMBIGUOUS

    def test_confidence_clamped_high(self):
        router = GroqRouter()
        raw = json.dumps({
            "escalate": False,
            "complexity": "REPETITIVE",
            "reason": "test",
            "result": {"ok": True},
            "confidence": 1.5,  # Over max
        })
        req = _make_request()
        resp = router._parse_response(raw, req)

        assert resp.confidence == 1.0

    def test_confidence_clamped_low(self):
        router = GroqRouter()
        raw = json.dumps({
            "escalate": False,
            "complexity": "REPETITIVE",
            "reason": "test",
            "result": {"ok": True},
            "confidence": -0.5,  # Under min
        })
        req = _make_request()
        resp = router._parse_response(raw, req)

        assert resp.confidence == 0.0

    def test_missing_fields_use_defaults(self):
        router = GroqRouter()
        raw = json.dumps({"escalate": False})
        req = _make_request()
        resp = router._parse_response(raw, req)

        assert resp.escalate is False
        assert resp.complexity == TaskComplexity.AMBIGUOUS
        assert resp.confidence == 0.5


# ============================================================
# TestCache
# ============================================================

class TestCache:
    @patch("src.utils.llm_client.chat_completion")
    def test_cache_hit_single_api_call(self, mock_chat):
        mock_chat.return_value = _groq_json_response(
            escalate=False, result={"cached": True},
        )
        router = GroqRouter()
        req = _make_request("Check status")

        resp1 = router.route(req)
        resp2 = router.route(req)

        assert mock_chat.call_count == 1  # Only 1 API call
        assert resp1.result == resp2.result

    @patch("src.utils.llm_client.chat_completion")
    def test_escalation_not_cached(self, mock_chat):
        mock_chat.return_value = _groq_json_response(
            escalate=True, complexity="STRUCTURAL",
        )
        router = GroqRouter()
        req = _make_request("Modify code")

        router.route(req)
        router.route(req)

        assert mock_chat.call_count == 2  # Both calls hit API

    @patch("src.utils.llm_client.chat_completion")
    def test_null_result_not_cached(self, mock_chat):
        mock_chat.return_value = json.dumps({
            "escalate": False,
            "complexity": "REPETITIVE",
            "reason": "ok",
            "result": None,
            "confidence": 0.9,
        })
        router = GroqRouter()
        req = _make_request("Do something")

        router.route(req)
        router.route(req)

        assert mock_chat.call_count == 2

    def test_cache_key_determinism(self):
        router = GroqRouter()
        req = _make_request("Same task", "type_a", "src_1")
        k1 = router._cache_key(req)
        k2 = router._cache_key(req)
        assert k1 == k2

    def test_cache_key_uniqueness(self):
        router = GroqRouter()
        req_a = _make_request("Task A", "type_a", "src_1")
        req_b = _make_request("Task B", "type_a", "src_1")
        assert router._cache_key(req_a) != router._cache_key(req_b)

    def test_cache_key_length(self):
        router = GroqRouter()
        req = _make_request("Any task")
        key = router._cache_key(req)
        assert len(key) == 16

    @patch("src.utils.llm_client.chat_completion")
    def test_cache_eviction_fifo(self, mock_chat):
        mock_chat.return_value = _groq_json_response(
            escalate=False, result={"ok": True},
        )
        router = GroqRouter()

        # Fill cache beyond max
        for i in range(CACHE_MAX_ENTRIES + 5):
            req = _make_request(f"Task {i}", source=f"src_{i}")
            router.route(req)

        assert len(router._cache) <= CACHE_MAX_ENTRIES


# ============================================================
# TestFallback
# ============================================================

class TestFallback:
    def test_fallback_always_escalates(self):
        router = GroqRouter()
        req = _make_request()
        resp = router._fallback_response(req, RuntimeError("test error"))

        assert resp.escalate is True
        assert resp.confidence == 0.0
        assert resp.result is None
        assert "error" in resp.reason.lower()

    def test_fallback_preserves_model(self):
        router = GroqRouter(model="custom-model")
        req = _make_request()
        resp = router._fallback_response(req, ValueError("fail"))

        assert resp.model_used == "custom-model"

    def test_fallback_complexity_is_ambiguous(self):
        router = GroqRouter()
        req = _make_request()
        resp = router._fallback_response(req, Exception("x"))

        assert resp.complexity == TaskComplexity.AMBIGUOUS


# ============================================================
# TestIntegration (constructor acceptance)
# ============================================================

class TestIntegration:
    def test_identity_manager_accepts_router(self):
        from src.services.identity_manager import IdentityManager

        router = GroqRouter()
        im = IdentityManager(router=router)
        assert im._router is router

    def test_identity_manager_router_default_none(self):
        from src.services.identity_manager import IdentityManager

        im = IdentityManager()
        assert im._router is None

    def test_maestro_service_accepts_router(self):
        from src.automation.maestro_service import MaestroService

        router = GroqRouter()
        ms = MaestroService(router=router)
        assert ms._router is router

    def test_maestro_service_router_default_none(self):
        from src.automation.maestro_service import MaestroService

        ms = MaestroService()
        assert ms._router is None
