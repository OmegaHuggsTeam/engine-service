"""
Tests for TelegramPhotoProvider - Telegram Bot API photo sender.

All HTTP calls are mocked; no real Telegram requests are made.
Screenshot files use tmp_path fixtures.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.neural_link.telemetry.telegram_photo_provider import (
    TelegramPhotoProvider,
    _build_caption,
    _validate_photo,
    MAX_PHOTO_SIZE_BYTES,
)
from src.neural_link.telemetry.provider import (
    TelemetryEvent,
    TelemetryHub,
    EventType,
    JitbitConnector,
)


@pytest.fixture
def provider():
    """TelegramPhotoProvider with test credentials."""
    return TelegramPhotoProvider(
        bot_token="123456:ABC-DEF",
        chat_id="-100999",
        vault_name="TestVault",
    )


@pytest.fixture
def screenshot(tmp_path):
    """Creates a small fake screenshot file."""
    p = tmp_path / "anchor_fail.png"
    p.write_bytes(b"\x89PNG" + b"\x00" * 100)
    return str(p)


def _anchoring_event(screenshot_path: str, **overrides) -> TelemetryEvent:
    """Helper: CRITICAL_ANOMALY with NOT_DETECTED + screenshot."""
    defaults = {
        "event_type": EventType.CRITICAL_ANOMALY,
        "source": "sentinel",
        "message": "Anchoring failed for agent X",
        "data": {
            "agent_name": "SentinelEye",
            "task_id": "t42",
            "quality_score": 1.5,
            "detection_status": "NOT_DETECTED",
            "screenshot_path": screenshot_path,
        },
    }
    if overrides:
        defaults["data"] = {**defaults["data"], **overrides}
    return TelemetryEvent(**{k: v for k, v in defaults.items()})


def _normal_anomaly_event() -> TelemetryEvent:
    """Helper: CRITICAL_ANOMALY without NOT_DETECTED (score anomaly, not anchoring)."""
    return TelemetryEvent(
        event_type=EventType.CRITICAL_ANOMALY,
        source="sentinel",
        message="Low score for agent Y",
        data={
            "agent_name": "AgentY",
            "task_id": "t10",
            "quality_score": 3.0,
        },
    )


def _log_event() -> TelemetryEvent:
    """Helper: plain LOG event."""
    return TelemetryEvent(
        event_type=EventType.LOG,
        source="jitbit",
        message="routine log",
    )


# ============================================================
# TestInit
# ============================================================


class TestInit:
    """Tests for TelegramPhotoProvider initialization."""

    def test_defaults(self, provider):
        """Provider initializes with correct defaults."""
        assert provider._last_send_ok is None
        assert provider._last_send_ts is None
        assert provider._photos_sent == 0
        assert provider._photos_rejected == 0
        assert provider._buffer == []

    def test_provider_id(self, provider):
        assert provider.provider_id == "telegram_photo"

    def test_display_name(self, provider):
        assert provider.display_name == "Telegram Photo (Bot API)"

    def test_health_check_before_any_send(self, provider):
        """health_check returns True before any dispatch."""
        assert provider.health_check() is True


# ============================================================
# TestBuildCaption
# ============================================================


class TestBuildCaption:
    """Tests for _build_caption() helper."""

    def test_contains_agent_and_score(self):
        caption = _build_caption("SentinelEye", 1.5, "vault", "Agents/SentinelEye")
        assert "SentinelEye" in caption
        assert "1.5/10" in caption

    def test_contains_obsidian_link(self):
        caption = _build_caption("X", 2.0, "MyVault", "Agents/X")
        assert "obsidian://open?vault=MyVault&file=Agents/X" in caption

    def test_vault_name_url_encoded(self):
        caption = _build_caption("X", 2.0, "My Vault", "Agents/X")
        assert "vault=My%20Vault" in caption

    def test_anchoring_error_label(self):
        caption = _build_caption("X", 2.0, "v", "Agents/X")
        assert "ALERTA VISUAL" in caption
        assert "Anchoring Error" in caption


# ============================================================
# TestValidatePhoto (Privacy Filter)
# ============================================================


class TestValidatePhoto:
    """Tests for _validate_photo() privacy filter."""

    def test_valid_file(self, screenshot):
        """Small existing file passes validation."""
        assert _validate_photo(screenshot) is None

    def test_file_not_found(self):
        """Non-existent file is rejected."""
        result = _validate_photo("/nonexistent/fake.png")
        assert result is not None
        assert "nao encontrado" in result

    def test_not_a_file(self, tmp_path):
        """Directory path is rejected."""
        d = tmp_path / "subdir"
        d.mkdir()
        result = _validate_photo(str(d))
        assert result is not None
        assert "nao e um arquivo" in result

    def test_file_too_large(self, tmp_path):
        """File exceeding 10 MB is rejected."""
        big = tmp_path / "huge.png"
        big.write_bytes(b"\x00" * (MAX_PHOTO_SIZE_BYTES + 1))
        result = _validate_photo(str(big))
        assert result is not None
        assert "excede 10 MB" in result

    def test_file_exactly_10mb_passes(self, tmp_path):
        """File exactly at 10 MB limit passes."""
        exact = tmp_path / "exact.png"
        exact.write_bytes(b"\x00" * MAX_PHOTO_SIZE_BYTES)
        assert _validate_photo(str(exact)) is None


# ============================================================
# TestIsAnchoringError (Event Filter)
# ============================================================


class TestIsAnchoringError:
    """Tests for _is_anchoring_error() filter logic."""

    def test_valid_anchoring_error(self, screenshot):
        """CRITICAL_ANOMALY + NOT_DETECTED + screenshot = True."""
        ev = _anchoring_event(screenshot)
        assert TelegramPhotoProvider._is_anchoring_error(ev) is True

    def test_rejects_normal_anomaly(self):
        """CRITICAL_ANOMALY without NOT_DETECTED is not an anchoring error."""
        assert TelegramPhotoProvider._is_anchoring_error(_normal_anomaly_event()) is False

    def test_rejects_log_event(self):
        """LOG event is not an anchoring error."""
        assert TelegramPhotoProvider._is_anchoring_error(_log_event()) is False

    def test_rejects_no_screenshot(self):
        """NOT_DETECTED without screenshot_path is not an anchoring error."""
        ev = TelemetryEvent(
            event_type=EventType.CRITICAL_ANOMALY,
            source="sentinel",
            message="fail",
            data={
                "agent_name": "X",
                "detection_status": "NOT_DETECTED",
            },
        )
        assert TelegramPhotoProvider._is_anchoring_error(ev) is False

    def test_rejects_kill_switch(self):
        """KILL_SWITCH_TRIGGERED is not an anchoring error."""
        ev = TelemetryEvent(
            event_type=EventType.KILL_SWITCH_TRIGGERED,
            source="ks",
            message="halt",
        )
        assert TelegramPhotoProvider._is_anchoring_error(ev) is False


# ============================================================
# TestSendPhoto
# ============================================================


class TestSendPhoto:
    """Tests for send_photo() method."""

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_successful_send(self, mock_post, provider, screenshot):
        """Successful API call returns True and increments counter."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True, "result": {}}),
        )
        result = provider.send_photo(screenshot, "test caption")
        assert result is True
        assert provider._photos_sent == 1
        mock_post.assert_called_once()

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_api_error_returns_false(self, mock_post, provider, screenshot):
        """Non-200 response returns False."""
        mock_post.return_value = MagicMock(
            status_code=403,
            text="Forbidden",
        )
        result = provider.send_photo(screenshot, "test")
        assert result is False
        assert provider._photos_sent == 0

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_network_error_returns_false(self, mock_post, provider, screenshot):
        """requests.RequestException returns False."""
        import requests as req
        mock_post.side_effect = req.ConnectionError("network down")
        result = provider.send_photo(screenshot, "test")
        assert result is False

    def test_empty_bot_token_returns_false(self, screenshot):
        """Empty bot_token skips send."""
        p = TelegramPhotoProvider(bot_token="", chat_id="-100")
        assert p.send_photo(screenshot, "test") is False

    def test_empty_chat_id_returns_false(self, screenshot):
        """Empty chat_id skips send."""
        p = TelegramPhotoProvider(bot_token="tok", chat_id="")
        assert p.send_photo(screenshot, "test") is False

    def test_nonexistent_file_rejected(self, provider):
        """Privacy filter rejects missing file."""
        result = provider.send_photo("/fake/no.png", "test")
        assert result is False
        assert provider._photos_rejected == 1

    def test_oversized_file_rejected(self, provider, tmp_path):
        """Privacy filter rejects file > 10 MB."""
        big = tmp_path / "huge.png"
        big.write_bytes(b"\x00" * (MAX_PHOTO_SIZE_BYTES + 1))
        result = provider.send_photo(str(big), "test")
        assert result is False
        assert provider._photos_rejected == 1

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_sends_correct_params(self, mock_post, provider, screenshot):
        """POST includes chat_id, caption, and file."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        provider.send_photo(screenshot, "my caption")

        call_kwargs = mock_post.call_args
        assert call_kwargs.kwargs["data"]["chat_id"] == "-100999"
        assert call_kwargs.kwargs["data"]["caption"] == "my caption"
        assert "photo" in call_kwargs.kwargs["files"]


# ============================================================
# TestDispatch
# ============================================================


class TestDispatch:
    """Tests for dispatch() event routing."""

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_anchoring_error_dispatched(self, mock_post, provider, screenshot):
        """Anchoring error event triggers send_photo and buffers result."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        ev = _anchoring_event(screenshot)
        result = provider.dispatch(ev)

        assert result is True
        assert provider._last_send_ok is True
        assert provider._last_send_ts is not None

        buffered = provider.poll()
        assert len(buffered) == 1
        assert buffered[0].event_type == EventType.SYNC_COMPLETED
        assert buffered[0].source == "telegram_photo"
        assert buffered[0].data["success"] is True

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_failed_dispatch_buffers_error(self, mock_post, provider, screenshot):
        """Failed send buffers SYNC_TRIGGERED with success=False."""
        mock_post.return_value = MagicMock(status_code=500, text="Internal Error")
        ev = _anchoring_event(screenshot)
        result = provider.dispatch(ev)

        assert result is False
        buffered = provider.poll()
        assert buffered[0].event_type == EventType.SYNC_TRIGGERED
        assert buffered[0].data["success"] is False

    def test_normal_anomaly_ignored(self, provider):
        """Non-anchoring CRITICAL_ANOMALY is silently ignored."""
        result = provider.dispatch(_normal_anomaly_event())
        assert result is False
        assert provider.poll() == []

    def test_log_event_ignored(self, provider):
        """LOG events are silently ignored."""
        result = provider.dispatch(_log_event())
        assert result is False
        assert provider.poll() == []

    def test_kill_switch_ignored(self, provider):
        """KILL_SWITCH events are silently ignored."""
        ev = TelemetryEvent(
            event_type=EventType.KILL_SWITCH_TRIGGERED,
            source="ks",
            message="halt",
        )
        result = provider.dispatch(ev)
        assert result is False
        assert provider.poll() == []

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_caption_contains_agent_and_score(self, mock_post, provider, screenshot):
        """Caption sent to Telegram includes agent_id and score."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        ev = _anchoring_event(screenshot)
        provider.dispatch(ev)

        call_kwargs = mock_post.call_args
        caption = call_kwargs.kwargs["data"]["caption"]
        assert "SentinelEye" in caption
        assert "1.5/10" in caption
        assert "obsidian://open" in caption


# ============================================================
# TestPollDrain
# ============================================================


class TestPollDrain:
    """Tests for poll() buffer drain."""

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_poll_drains_buffer(self, mock_post, provider, screenshot):
        """poll() returns buffered events and clears buffer."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        provider.dispatch(_anchoring_event(screenshot))
        provider.dispatch(_anchoring_event(screenshot))
        events = provider.poll()
        assert len(events) == 2

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_poll_empty_after_drain(self, mock_post, provider, screenshot):
        """Second poll() returns empty after drain."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        provider.dispatch(_anchoring_event(screenshot))
        provider.poll()
        assert provider.poll() == []


# ============================================================
# TestPingStatus
# ============================================================


class TestPingStatus:
    """Tests for ping_status() dict."""

    def test_status_dict_shape(self, provider):
        status = provider.ping_status()
        assert "active" in status
        assert "last_ping" in status
        assert "photos_sent" in status
        assert "photos_rejected" in status

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_active_after_success(self, mock_post, provider, screenshot):
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        provider.dispatch(_anchoring_event(screenshot))
        status = provider.ping_status()
        assert status["active"] is True
        assert status["photos_sent"] == 1

    def test_counters_after_rejection(self, provider):
        """Privacy filter rejection increments photos_rejected."""
        provider.send_photo("/nonexistent.png", "test")
        status = provider.ping_status()
        assert status["photos_rejected"] == 1
        assert status["photos_sent"] == 0


# ============================================================
# TestHubIntegration
# ============================================================


class TestHubIntegration:
    """Tests for TelegramPhotoProvider registered with TelemetryHub."""

    def test_registers_with_hub(self, provider):
        hub = TelemetryHub()
        hub.register(provider)
        assert "telegram_photo" in hub.provider_ids

    def test_coexists_with_other_providers(self, provider):
        """Multiple providers registered without conflict."""
        hub = TelemetryHub()
        hub.register(JitbitConnector())
        hub.register(provider)
        assert "jitbit" in hub.provider_ids
        assert "telegram_photo" in hub.provider_ids

    @patch("src.neural_link.telemetry.telegram_photo_provider.requests.post")
    def test_hub_poll_all_drains_dispatch_events(self, mock_post, provider, screenshot):
        """hub.poll_all() collects TelegramPhotoProvider buffer events."""
        mock_post.return_value = MagicMock(
            status_code=200,
            json=MagicMock(return_value={"ok": True}),
        )
        hub = TelemetryHub()
        hub.register(provider)

        provider.dispatch(_anchoring_event(screenshot))
        events = hub.poll_all()
        assert len(events) == 1
        assert events[0].source == "telegram_photo"
        assert events[0].event_type == EventType.SYNC_COMPLETED

    def test_health_reported_in_hub(self, provider):
        """Hub health() includes telegram_photo."""
        hub = TelemetryHub()
        hub.register(provider)
        h = hub.health()
        assert h["telegram_photo"] is True
