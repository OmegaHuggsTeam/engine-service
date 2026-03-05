"""
Tests for SentinelBridge - Active anomaly alert service.

All Neo4j interactions are mocked. No live database needed.
"""

import threading
import time
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.services.sentinel_bridge import SentinelBridge
from src.neural_link.telemetry.provider import (
    EventType,
    TelemetryEvent,
    TelemetryHub,
)


# ==================================================================
# Fixtures
# ==================================================================


@pytest.fixture
def mock_graph():
    """Mock GraphManager with verify_connectivity and execute_read."""
    gm = MagicMock()
    gm.verify_connectivity.return_value = True
    gm.execute_read.return_value = []
    return gm


@pytest.fixture
def hub():
    return TelemetryHub()


@pytest.fixture
def sentinel(mock_graph, hub):
    """SentinelBridge with short interval for fast tests."""
    return SentinelBridge(
        graph_manager=mock_graph,
        hub=hub,
        interval=0.05,
        quality_threshold=5.0,
        minutes_window=10,
    )


def _make_anomaly_row(
    agent_id="agent_1",
    agent_name="TestAgent",
    task_id="task_001",
    quality_score=2.5,
    success_rate=0.6,
    feedback="Poor output",
):
    """Helper to build a row matching GET_PERFORMANCE_ANOMALIES shape."""
    return {
        "agent_id": agent_id,
        "agent_name": agent_name,
        "task_id": task_id,
        "quality_score": quality_score,
        "success_rate": success_rate,
        "feedback": feedback,
        "evaluated_at": "2026-03-03T12:00:00",
    }


# ==================================================================
# TestSentinelInit
# ==================================================================


class TestSentinelInit:
    """Constructor defaults and provider interface properties."""

    def test_defaults(self, sentinel):
        assert sentinel._interval == 0.05
        assert sentinel._quality_threshold == 5.0
        assert sentinel._minutes_window == 10
        assert sentinel._running is False
        assert sentinel._buffer == []
        assert sentinel._seen_task_ids == set()

    def test_provider_id_and_display_name(self, sentinel):
        assert sentinel.provider_id == "sentinel"
        assert sentinel.display_name == "Sentinel Anomaly Monitor"

    def test_health_check_delegates_to_graph(self, sentinel, mock_graph):
        assert sentinel.health_check() is True
        mock_graph.verify_connectivity.assert_called_once()

        mock_graph.verify_connectivity.return_value = False
        assert sentinel.health_check() is False

    def test_health_check_no_graph(self, hub):
        s = SentinelBridge(graph_manager=None, hub=hub)
        assert s.health_check() is False


# ==================================================================
# TestPollOnce
# ==================================================================


class TestPollOnce:
    """Unit tests for _poll_once (single poll cycle)."""

    def test_detects_anomaly_creates_event(self, sentinel, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(task_id="t1", quality_score=3.0),
        ]
        events = sentinel._poll_once()
        assert len(events) == 1
        assert events[0].event_type == EventType.CRITICAL_ANOMALY
        assert events[0].source == "sentinel"
        assert "3.0" in events[0].message
        assert events[0].data["task_id"] == "t1"
        assert events[0].data["quality_score"] == 3.0

    def test_deduplicates_seen_task_ids(self, sentinel, mock_graph):
        row = _make_anomaly_row(task_id="t1")
        mock_graph.execute_read.return_value = [row]

        first = sentinel._poll_once()
        assert len(first) == 1

        second = sentinel._poll_once()
        assert len(second) == 0

    def test_no_anomalies_no_events(self, sentinel, mock_graph):
        mock_graph.execute_read.return_value = []
        events = sentinel._poll_once()
        assert events == []

    def test_neo4j_error_handled_gracefully(self, sentinel, mock_graph):
        mock_graph.execute_read.side_effect = RuntimeError("Connection lost")
        events = sentinel._poll_once()
        assert events == []

    def test_event_payload_fields(self, sentinel, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(
                agent_id="a42",
                agent_name="Reviewer",
                task_id="t99",
                quality_score=1.5,
                success_rate=0.3,
                feedback="Incomplete analysis",
            ),
        ]
        events = sentinel._poll_once()
        assert len(events) == 1
        d = events[0].data
        assert d["agent_id"] == "a42"
        assert d["agent_name"] == "Reviewer"
        assert d["task_id"] == "t99"
        assert d["quality_score"] == 1.5
        assert d["success_rate"] == 0.3
        assert d["feedback"] == "Incomplete analysis"

    def test_no_graph_returns_empty(self, hub):
        s = SentinelBridge(graph_manager=None, hub=hub)
        assert s._poll_once() == []

    def test_events_buffered(self, sentinel, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(task_id="t1"),
        ]
        sentinel._poll_once()
        # Events should be in buffer, not yet drained
        assert len(sentinel._buffer) == 1

    def test_poll_drains_buffer(self, sentinel, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(task_id="t1"),
        ]
        sentinel._poll_once()
        drained = sentinel.poll()
        assert len(drained) == 1
        assert sentinel._buffer == []


# ==================================================================
# TestStartStop
# ==================================================================


class TestStartStop:
    """Lifecycle: thread spawning, stopping, max_cycles."""

    def test_start_spawns_daemon_thread(self, sentinel):
        sentinel._max_cycles = 1
        sentinel.start()
        assert sentinel._thread is not None
        assert sentinel._thread.daemon is True
        sentinel._thread.join(timeout=2)

    def test_stop_joins_cleanly(self, sentinel):
        sentinel._max_cycles = 1
        sentinel.start()
        sentinel.stop()
        assert sentinel._running is False
        assert sentinel._thread is None

    def test_max_cycles_exits_loop(self, sentinel, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(task_id="t1"),
        ]
        sentinel._max_cycles = 3
        sentinel.start()
        sentinel._thread.join(timeout=2)
        # After 3 cycles, thread should have exited
        assert not sentinel._thread.is_alive()
        # First poll finds t1, next 2 see it deduplicated
        assert len(sentinel._buffer) == 1

    def test_start_is_idempotent(self, sentinel):
        sentinel._max_cycles = 1
        sentinel.start()
        thread1 = sentinel._thread
        sentinel.start()  # second call should be no-op
        assert sentinel._thread is thread1
        sentinel.stop()

    def test_registers_with_hub(self, sentinel, hub):
        sentinel._max_cycles = 1
        sentinel.start()
        assert "sentinel" in hub.provider_ids
        sentinel.stop()


# ==================================================================
# TestHubIntegration
# ==================================================================


class TestHubIntegration:
    """Integration with TelemetryHub pipeline."""

    def test_hub_poll_all_drains_sentinel_events(self, sentinel, hub, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(task_id="t1"),
        ]
        sentinel._poll_once()
        hub.register(sentinel)
        events = hub.poll_all()
        assert len(events) == 1
        assert events[0].event_type == EventType.CRITICAL_ANOMALY

    def test_subscribers_receive_critical_anomaly(self, sentinel, hub, mock_graph):
        received = []
        hub.subscribe(lambda e: received.append(e))
        hub.register(sentinel)

        mock_graph.execute_read.return_value = [
            _make_anomaly_row(task_id="t1"),
        ]
        sentinel._poll_once()
        hub.poll_all()

        assert len(received) == 1
        assert received[0].event_type == EventType.CRITICAL_ANOMALY
        assert received[0].data["task_id"] == "t1"

    def test_multiple_anomalies_different_agents(self, sentinel, hub, mock_graph):
        mock_graph.execute_read.return_value = [
            _make_anomaly_row(agent_id="a1", agent_name="Alpha", task_id="t1"),
            _make_anomaly_row(agent_id="a2", agent_name="Beta", task_id="t2"),
        ]
        hub.register(sentinel)
        sentinel._poll_once()
        events = hub.poll_all()
        assert len(events) == 2
        agent_names = {e.data["agent_name"] for e in events}
        assert agent_names == {"Alpha", "Beta"}

    def test_empty_poll_returns_nothing(self, sentinel, hub, mock_graph):
        mock_graph.execute_read.return_value = []
        hub.register(sentinel)
        sentinel._poll_once()
        events = hub.poll_all()
        assert events == []
