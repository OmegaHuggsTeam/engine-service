"""
Testes para IFTTTConnector - Notificações externas via Webhooks.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.neural_link.telemetry.ifttt_connector import (
    IFTTTConnector,
    _build_payload,
    IFTTT_MAKER_URL,
)


class TestIFTTTPayloadFormat:
    """Verifica que o payload JSON segue o padrão exigido pelo IFTTT."""

    def test_build_payload_has_value1_value2_value3(self):
        """Payload deve conter exatamente value1, value2, value3."""
        p = _build_payload("a", "b", "c")
        assert "value1" in p
        assert "value2" in p
        assert "value3" in p
        assert set(p.keys()) == {"value1", "value2", "value3"}

    def test_build_payload_values_are_strings(self):
        """IFTTT exige valores como strings."""
        p = _build_payload("agent_1", "erro x", "macros/refresh.json")
        assert p["value1"] == "agent_1"
        assert p["value2"] == "erro x"
        assert p["value3"] == "macros/refresh.json"
        assert all(isinstance(v, str) for v in p.values())

    def test_build_payload_empty_defaults(self):
        """Valores omitidos viram string vazia."""
        p = _build_payload()
        assert p == {"value1": "", "value2": "", "value3": ""}

    def test_build_payload_json_serializable(self):
        """Payload deve ser JSON serializável no formato IFTTT."""
        p = _build_payload("agent", "error msg", "/path/macro.json")
        s = json.dumps(p)
        parsed = json.loads(s)
        assert parsed == p
        assert parsed["value1"] == "agent"
        assert parsed["value2"] == "error msg"
        assert parsed["value3"] == "/path/macro.json"


class TestIFTTTConnector:
    """Testes do IFTTTConnector."""

    def test_send_trigger_posts_correct_url(self):
        """POST para URL maker.ifttt.com/trigger/{event}/with/key/{key}."""
        conn = IFTTTConnector(webhook_key="abc123", event_name="critical_anomaly")
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.status = 200
            conn.send_trigger("v1", "v2", "v3")
            call_args = mock_open.call_args
            req = call_args[0][0]
            assert "maker.ifttt.com" in req.full_url
            assert "critical_anomaly" in req.full_url
            assert "abc123" in req.full_url

    def test_send_trigger_posts_json_payload(self):
        """Body do POST deve ser JSON com value1, value2, value3 (padrão IFTTT)."""
        conn = IFTTTConnector(webhook_key="key", event_name="ev")
        with patch("urllib.request.urlopen") as mock_open:
            mock_open.return_value.__enter__.return_value.status = 200
            conn.send_trigger("agent_x", "erro encontrado", "macros/refresh.json")

            req = mock_open.call_args[0][0]
            body = req.data.decode("utf-8")
            payload = json.loads(body)
            assert payload["value1"] == "agent_x"
            assert payload["value2"] == "erro encontrado"
            assert payload["value3"] == "macros/refresh.json"

    def test_send_trigger_empty_key_returns_false(self):
        """Webhook key vazia não envia e retorna False."""
        conn = IFTTTConnector(webhook_key="", event_name="ev")
        with patch("urllib.request.urlopen") as mock_open:
            ok = conn.send_trigger("a", "b", "c")
            assert ok is False
            mock_open.assert_not_called()
