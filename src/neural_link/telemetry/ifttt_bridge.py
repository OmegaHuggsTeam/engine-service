"""
IFTTTBridge - TelemetryProvider wrapper for IFTTTConnector.

Integrates IFTTT Maker Webhooks into the TelemetryHub pipeline,
tracking ping status for Obsidian visibility.
"""

import logging
import threading
from datetime import datetime

from src.neural_link.telemetry.ifttt_connector import IFTTTConnector
from src.neural_link.telemetry.provider import (
    EventType,
    TelemetryEvent,
    TelemetryProvider,
)

logger = logging.getLogger(__name__)


class IFTTTBridge(TelemetryProvider):
    """
    Wraps IFTTTConnector as a TelemetryProvider.

    Dispatches telemetry events as IFTTT webhook triggers and tracks
    ping status for Obsidian Connected Services visibility.
    """

    def __init__(self, webhook_key: str, event_name: str = "bunker_alert"):
        self._connector = IFTTTConnector(
            webhook_key=webhook_key,
            event_name=event_name,
        )
        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()
        self._last_ping_ok: bool | None = None
        self._last_ping_ts: str | None = None

    @property
    def provider_id(self) -> str:
        return "ifttt"

    @property
    def display_name(self) -> str:
        return "IFTTT Webhooks (Telegram)"

    def dispatch(self, event: TelemetryEvent) -> bool:
        """
        Format a TelemetryEvent into value1/value2/value3 and send via IFTTT.

        Para CRITICAL_ANOMALY: anexa URL da evidência visual em value3
        (Evidence Server: http://localhost:5000/evidence/last_fail.png).

        Returns True if the webhook call succeeded.
        """
        data = event.data if isinstance(event.data, dict) else {}
        value1 = data.get("agent_name", data.get("agent_id", event.source))
        value2 = data.get("status", event.event_type.value if hasattr(event.event_type, "value") else str(event.event_type))
        value3 = data.get("action", event.message)

        # CRITICAL_ANOMALY: value3 = URL da evidência visual
        if event.event_type == EventType.CRITICAL_ANOMALY:
            try:
                from src.neural_link.services.evidence_server import get_evidence_url
                value3 = get_evidence_url()
            except ImportError:
                pass

        ok = self._connector.send_trigger(value1, value2, value3)

        now = datetime.now().isoformat()
        self._last_ping_ok = ok
        if ok:
            self._last_ping_ts = now

        sync_event = TelemetryEvent(
            event_type=EventType.SYNC_COMPLETED if ok else EventType.SYNC_TRIGGERED,
            source=self.provider_id,
            message=f"IFTTT dispatch {'ok' if ok else 'failed'}: {value1}",
            timestamp=now,
            data={
                "value1": value1,
                "value2": value2,
                "value3": value3,
                "success": ok,
            },
        )
        with self._lock:
            self._buffer.append(sync_event)

        return ok

    def poll(self) -> list[TelemetryEvent]:
        """Drain the buffer and return all pending events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        """
        Return True if the provider is operational.
        None (pre-first-use) is treated as healthy.
        """
        if self._last_ping_ok is None:
            return True
        return self._last_ping_ok

    def ping_status(self) -> dict:
        """Return status dict for Obsidian Connected Services section."""
        active = self._last_ping_ok if self._last_ping_ok is not None else True
        return {
            "active": active,
            "last_ping": self._last_ping_ts,
            "event_name": self._connector.event_name,
        }
