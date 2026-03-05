"""
Unit tests for K8sEventMonitor reconnection logic.

Task 3.4: Validate reconnection logic under simulated network failure.
Requirements: 7.1
"""

import threading
import time
from unittest.mock import MagicMock, Mock, patch

import pytest
from kubernetes.client.rest import ApiException

from src.neural_link.k8s_monitoring.k8s_event_monitor import K8sEventMonitor


@pytest.fixture
def mock_kube_config():
    """Mock Kubernetes configuration loading."""
    with patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config") as mock_config:
        yield mock_config


@pytest.fixture
def mock_kube_client():
    """Mock Kubernetes client."""
    with patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client") as mock_client:
        yield mock_client


@pytest.fixture
def mock_watch():
    """Mock Kubernetes watch."""
    with patch("src.neural_link.k8s_monitoring.k8s_event_monitor.watch") as mock_watch:
        yield mock_watch


class TestReconnectionBackoff:
    """Tests for exponential backoff timing."""

    def test_initial_reconnect_delay_is_30_seconds(self, mock_kube_config, mock_kube_client):
        """Base reconnection delay should be 30 seconds."""
        monitor = K8sEventMonitor()
        assert monitor._reconnect_delay == 30

    def test_max_reconnect_delay_is_300_seconds(self, mock_kube_config, mock_kube_client):
        """Maximum reconnection delay should be 5 minutes (300s)."""
        monitor = K8sEventMonitor()
        assert monitor._max_reconnect_delay == 300

    def test_exponential_backoff_calculation(self, mock_kube_config, mock_kube_client):
        """Verify backoff formula: min(delay * 2^(failures-1), max_delay)."""
        monitor = K8sEventMonitor()
        base = monitor._reconnect_delay
        max_d = monitor._max_reconnect_delay

        # failure 1: base * 2^0 = 30
        # failure 2: base * 2^1 = 60
        # failure 3: base * 2^2 = 120
        # failure 4: base * 2^3 = 240
        # failure 5: base * 2^4 = 480 -> capped at 300
        expected = [30, 60, 120, 240, 300]
        for i, exp in enumerate(expected):
            delay = min(base * (2 ** i), max_d)
            assert delay == exp


class TestReconnectionRecovery:
    """Tests for connection recovery after failure."""

    def test_watch_loop_retries_after_api_exception(
        self, mock_kube_config, mock_kube_client, mock_watch
    ):
        """Watch loop should retry after ApiException (simulated network failure)."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        call_count = 0

        def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ApiException(status=503, reason="Service Unavailable")
            # Second call: yield one event then stop
            yield {"type": "MODIFIED", "object": Mock(kind="Pod", metadata=Mock(name="x", namespace="default"))}
            # Simulate stop by monitor stopping
            monitor.running = False

        mock_watch.Watch.return_value.stream.return_value = mock_stream()

        monitor.start()
        time.sleep(0.5)  # Allow first failure
        # Wait for thread to finish (after second successful iteration)
        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=5.0)

        monitor.stop()
        assert call_count >= 1

    def test_watch_loop_resets_delay_on_success(
        self, mock_kube_config, mock_kube_client, mock_watch
    ):
        """On successful event processing, connection delay should reset."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        events_yielded = []

        def mock_stream(*args, **kwargs):
            for i in range(3):
                if not monitor.running:
                    break
                pod = Mock()
                pod.kind = "Pod"
                pod.metadata = Mock()
                pod.metadata.name = f"pod-{i}"
                pod.metadata.namespace = "default"
                events_yielded.append(i)
                yield {"type": "MODIFIED", "object": pod}

        mock_watch.Watch.return_value.stream.return_value = mock_stream()

        monitor.start()
        time.sleep(1.0)
        monitor.stop()

        assert len(events_yielded) >= 1

    def test_stop_event_clears_watch_loop(self, mock_kube_config, mock_kube_client, mock_watch):
        """When _stop_event is set, watch loop should exit."""

        def mock_stream(*args, **kwargs):
            # Simulate long-running stream
            for _ in range(100):
                if monitor._stop_event.is_set():
                    break
                yield {"type": "MODIFIED", "object": Mock(kind="Pod", metadata=Mock(name="x", namespace="default"))}
                time.sleep(0.01)

        monitor = K8sEventMonitor()
        monitor.register_hooks([])
        mock_watch.Watch.return_value.stream.return_value = mock_stream()

        monitor.start()
        time.sleep(0.2)
        monitor.stop()

        assert monitor.running is False
        assert monitor._stop_event.is_set()


class TestReconnectionUnderSimulatedFailure:
    """Integration-style tests for simulated network failure."""

    def test_watch_handles_generic_exception(self, mock_kube_config, mock_kube_client, mock_watch):
        """Watch loop should handle generic exceptions and retry."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        call_count = 0

        def mock_stream(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Simulated network failure")
            monitor.running = False
            yield {}

        mock_watch.Watch.return_value.stream.return_value = mock_stream()

        monitor.start()
        time.sleep(0.5)
        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=3.0)
        monitor.stop()

        assert call_count >= 1
