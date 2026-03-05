"""
Tests for IFTTTBridge - IFTTT Maker Webhooks as TelemetryProvider.

All HTTP calls are mocked; no real IFTTT requests are made.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.neural_link.telemetry.ifttt_bridge import IFTTTBridge
from src.neural_link.telemetry.provider import (
    TelemetryEvent,
    TelemetryHub,
    EventType,
)


@pytest.fixture
def bridge():
    """IFTTTBridge with a test key."""
    return IFTTTBridge(webhook_key="test_key_123", event_name="bunker_alert")


def _make_event(**overrides):
    """Helper to create a TelemetryEvent with sensible defaults."""
    defaults = {
        "event_type": EventType.CRITICAL_ANOMALY,
        "source": "sentinel",
        "message": "Agent Reviewer scored 2.0/10 on task t99",
        "data": {
            "agent_name": "Reviewer",
            "status": "CRITICAL - Score 2.0/10",
            "action": "Recovery initiated for task t99",
        },
    }
    defaults.update(overrides)
    return TelemetryEvent(**defaults)


# ============================================================
# TestIFTTTBridgeInit
# ============================================================


class TestIFTTTBridgeInit:
    """Tests for IFTTTBridge initialization and identity."""

    def test_defaults(self, bridge):
        """Bridge initializes with correct defaults."""
        assert bridge._last_ping_ok is None
        assert bridge._last_ping_ts is None
        assert bridge._buffer == []

    def test_provider_id(self, bridge):
        """provider_id returns 'ifttt'."""
        assert bridge.provider_id == "ifttt"

    def test_display_name(self, bridge):
        """display_name returns human-readable label."""
        assert bridge.display_name == "IFTTT Webhooks (Telegram)"

    def test_health_check_before_any_ping(self, bridge):
        """health_check returns True before any dispatch (pre-first-use)."""
        assert bridge.health_check() is True


# ============================================================
# TestDispatch
# ============================================================


class TestDispatch:
    """Tests for dispatch() method."""

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_successful_dispatch(self, mock_urlopen, bridge):
        """Successful dispatch updates ping status and buffers SYNC_COMPLETED."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        event = _make_event()
        result = bridge.dispatch(event)

        assert result is True
        assert bridge._last_ping_ok is True
        assert bridge._last_ping_ts is not None

        buffered = bridge.poll()
        assert len(buffered) == 1
        assert buffered[0].event_type == EventType.SYNC_COMPLETED
        assert buffered[0].data["success"] is True

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_failed_dispatch(self, mock_urlopen, bridge):
        """Failed dispatch buffers SYNC_TRIGGERED with error info."""
        mock_urlopen.side_effect = Exception("connection refused")

        event = _make_event()
        result = bridge.dispatch(event)

        assert result is False
        assert bridge._last_ping_ok is False

        buffered = bridge.poll()
        assert len(buffered) == 1
        assert buffered[0].event_type == EventType.SYNC_TRIGGERED
        assert buffered[0].data["success"] is False

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_formats_values_from_event_data(self, mock_urlopen, bridge):
        """dispatch extracts value1/value2; CRITICAL_ANOMALY usa value3=evidence URL."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        event = _make_event(data={
            "agent_name": "TestAgent",
            "status": "OK",
            "action": "deploy started",
        })
        bridge.dispatch(event)

        buffered = bridge.poll()
        assert buffered[0].data["value1"] == "TestAgent"
        assert buffered[0].data["value2"] == "OK"
        # CRITICAL_ANOMALY: value3 = evidence URL (Visual Evidence Uploader)
        assert "evidence/last_fail.png" in buffered[0].data["value3"]

    def test_empty_webhook_key_handled(self):
        """Bridge with empty key returns False on dispatch without crashing."""
        b = IFTTTBridge(webhook_key="", event_name="test")
        event = _make_event()
        result = b.dispatch(event)
        assert result is False
        assert b._last_ping_ok is False

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_dispatch_records_timestamp(self, mock_urlopen, bridge):
        """Successful dispatch records ISO timestamp."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        bridge.dispatch(_make_event())
        assert bridge._last_ping_ts is not None
        assert "T" in bridge._last_ping_ts  # ISO format


# ============================================================
# TestPollDrain
# ============================================================


class TestPollDrain:
    """Tests for poll() buffer drain."""

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_poll_drains_buffer(self, mock_urlopen, bridge):
        """poll() returns buffered events and clears buffer."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        bridge.dispatch(_make_event())
        bridge.dispatch(_make_event())

        events = bridge.poll()
        assert len(events) == 2

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_poll_returns_empty_after_drain(self, mock_urlopen, bridge):
        """Second poll() returns empty after drain."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        bridge.dispatch(_make_event())
        bridge.poll()
        assert bridge.poll() == []


# ============================================================
# TestPingStatus
# ============================================================


class TestPingStatus:
    """Tests for ping_status() dict."""

    def test_status_dict_shape(self, bridge):
        """ping_status returns dict with expected keys."""
        status = bridge.ping_status()
        assert "active" in status
        assert "last_ping" in status
        assert "event_name" in status

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_active_after_success(self, mock_urlopen, bridge):
        """ping_status shows active after successful dispatch."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        bridge.dispatch(_make_event())
        status = bridge.ping_status()
        assert status["active"] is True
        assert status["last_ping"] is not None
        assert status["event_name"] == "bunker_alert"

    def test_inactive_after_failure(self):
        """ping_status shows inactive after failed dispatch."""
        b = IFTTTBridge(webhook_key="", event_name="test")
        b.dispatch(_make_event())
        status = b.ping_status()
        assert status["active"] is False


# ============================================================
# TestHubIntegration
# ============================================================


class TestHubIntegration:
    """Tests for IFTTTBridge registered with TelemetryHub."""

    def test_registers_with_hub(self, bridge):
        """IFTTTBridge can be registered in TelemetryHub."""
        hub = TelemetryHub()
        hub.register(bridge)
        assert "ifttt" in hub.provider_ids

    @patch("src.neural_link.telemetry.ifttt_connector.urllib.request.urlopen")
    def test_hub_poll_all_returns_dispatch_events(self, mock_urlopen, bridge):
        """hub.poll_all() collects IFTTTBridge dispatch buffer events."""
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        hub = TelemetryHub()
        hub.register(bridge)

        bridge.dispatch(_make_event())
        events = hub.poll_all()
        assert len(events) == 1
        assert events[0].source == "ifttt"
        assert events[0].event_type == EventType.SYNC_COMPLETED
