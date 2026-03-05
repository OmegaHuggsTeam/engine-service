"""
SentinelBridge - Active anomaly alert service.

Polls Neo4j for performance anomalies on a cadence and emits
CRITICAL_ANOMALY events into the TelemetryHub, making anomalies
visible to all subscribers (ObsidianBridge, Jitbit, etc.).
"""

import logging
import threading
import time

from ..graph import queries as q
from ..telemetry.provider import (
    EventType,
    TelemetryEvent,
    TelemetryHub,
    TelemetryProvider,
)

logger = logging.getLogger(__name__)


class SentinelBridge(TelemetryProvider):
    """
    Background monitor that detects agent quality anomalies via Neo4j
    and feeds CRITICAL_ANOMALY events into the TelemetryHub pipeline.

    Implements TelemetryProvider so it plugs directly into TelemetryHub.
    """

    def __init__(
        self,
        graph_manager,
        hub: TelemetryHub,
        interval: float = 60.0,
        quality_threshold: float = 5.0,
        minutes_window: int = 10,
    ):
        self._graph = graph_manager
        self._hub = hub
        self._interval = interval
        self._quality_threshold = quality_threshold
        self._minutes_window = minutes_window

        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()
        self._seen_task_ids: set[str] = set()
        self._running = False
        self._thread: threading.Thread | None = None
        self._max_cycles: int = 0  # 0 = unlimited; >0 for testing

    # ------------------------------------------------------------------
    # TelemetryProvider interface
    # ------------------------------------------------------------------

    @property
    def provider_id(self) -> str:
        return "sentinel"

    @property
    def display_name(self) -> str:
        return "Sentinel Anomaly Monitor"

    def poll(self) -> list[TelemetryEvent]:
        """Drain the buffer and return all pending events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        """Delegate to graph_manager connectivity check."""
        if not self._graph:
            return False
        try:
            return self._graph.verify_connectivity()
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Spawn daemon thread and register with TelemetryHub."""
        if self._running:
            return
        self._running = True
        self._hub.register(self)
        self._thread = threading.Thread(
            target=self._run_loop, name="sentinel-bridge", daemon=True
        )
        self._thread.start()
        logger.info(
            "SentinelBridge started (interval=%.1fs, threshold=%.1f, window=%dm)",
            self._interval,
            self._quality_threshold,
            self._minutes_window,
        )

    def stop(self) -> None:
        """Signal the loop to exit and wait for the thread."""
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 2)
            self._thread = None
        logger.info("SentinelBridge stopped")

    # ------------------------------------------------------------------
    # Core loop
    # ------------------------------------------------------------------

    def _run_loop(self) -> None:
        """Main polling loop (runs inside daemon thread)."""
        cycle = 0
        while self._running:
            cycle += 1
            self._poll_once()
            if self._max_cycles and cycle >= self._max_cycles:
                break
            time.sleep(self._interval)

    def _poll_once(self) -> list[TelemetryEvent]:
        """
        Execute GET_PERFORMANCE_ANOMALIES, deduplicate, and buffer events.
        Returns newly created events (useful for testing).
        """
        if not self._graph:
            return []

        try:
            rows = self._graph.execute_read(
                q.GET_PERFORMANCE_ANOMALIES,
                {
                    "quality_threshold": self._quality_threshold,
                    "minutes_window": self._minutes_window,
                },
            )
        except Exception as e:
            logger.warning("SentinelBridge poll failed: %s", e)
            return []

        new_events: list[TelemetryEvent] = []
        for row in rows:
            task_id = row.get("task_id", "")
            if not task_id or task_id in self._seen_task_ids:
                continue
            self._seen_task_ids.add(task_id)

            event = TelemetryEvent(
                event_type=EventType.CRITICAL_ANOMALY,
                source=self.provider_id,
                message=(
                    f"Agent {row.get('agent_name', 'unknown')} scored "
                    f"{row.get('quality_score', '?')}/10 on task {task_id}"
                ),
                data={
                    "agent_id": row.get("agent_id", ""),
                    "agent_name": row.get("agent_name", ""),
                    "task_id": task_id,
                    "quality_score": row.get("quality_score", 0),
                    "success_rate": row.get("success_rate", 0),
                    "feedback": row.get("feedback", ""),
                },
            )
            new_events.append(event)

        if new_events:
            with self._lock:
                self._buffer.extend(new_events)
            logger.info("SentinelBridge detected %d new anomalies", len(new_events))

        return new_events


# ======================================================================
# CLI entry point:  python -m src.neural_link.services.sentinel_bridge
# ======================================================================

def _main() -> None:
    import signal
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    from ..graph.manager import GraphManager

    gm = GraphManager.from_env()
    hub = TelemetryHub()
    sentinel = SentinelBridge(gm, hub, interval=60.0)

    def _shutdown(sig, frame):
        print("\n[sentinel] Shutting down...")
        sentinel.stop()
        gm.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[sentinel] SentinelBridge running -- Ctrl+C to stop")
    sentinel.start()

    # Keep main thread alive
    while True:
        time.sleep(1)


if __name__ == "__main__":
    _main()
