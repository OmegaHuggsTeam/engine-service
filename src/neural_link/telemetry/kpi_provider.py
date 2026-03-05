"""
KpiProvider — TelemetryProvider for KPI anomaly events.

Integrates with the TelemetryHub to broadcast KPI_ANOMALY_DETECTED events
when the MetricsTimeSeries detects regressions.
"""

import logging
import threading
from typing import Any

from .provider import TelemetryProvider, TelemetryEvent, EventType

logger = logging.getLogger(__name__)


class KpiProvider(TelemetryProvider):
    """
    Buffer-based KPI anomaly provider.
    MetricsTimeSeries pushes anomaly events here;
    TelemetryHub polls and broadcasts them.
    """

    def __init__(self) -> None:
        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()

    @property
    def provider_id(self) -> str:
        return "kpi"

    @property
    def display_name(self) -> str:
        return "KPI Intelligence"

    def push_anomaly(self, anomaly: dict) -> None:
        """Push a KPI anomaly event into the buffer."""
        with self._lock:
            self._buffer.append(TelemetryEvent(
                event_type=EventType.KPI_ANOMALY_DETECTED,
                source=self.provider_id,
                message=f"KPI anomaly: {anomaly.get('type', 'unknown')} in {anomaly.get('value', '?')}",
                data=anomaly,
            ))

    def push_anomalies(self, anomalies: list[dict]) -> None:
        """Push multiple anomaly events."""
        for a in anomalies:
            self.push_anomaly(a)

    def poll(self) -> list[TelemetryEvent]:
        """Drain buffer and return pending events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        return True
