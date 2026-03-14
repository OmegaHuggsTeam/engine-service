"""Unit tests for K8sEventMonitor class."""

import threading
import time
from unittest.mock import Mock, patch

import pytest
from kubernetes.client import V1ObjectMeta, V1Pod

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


class TestK8sEventMonitorInit:
    """Tests for K8sEventMonitor initialization."""

    def test_init_with_kubeconfig_path(self, mock_kube_config, mock_kube_client):
        """Test initialization with explicit kubeconfig path."""
        monitor = K8sEventMonitor(kubeconfig_path="/path/to/kubeconfig")

        mock_kube_config.load_kube_config.assert_called_once_with(config_file="/path/to/kubeconfig")
        assert monitor.hooks == []
        assert monitor.running is False

    def test_init_with_incluster_config(self, mock_kube_config, mock_kube_client):
        """Test initialization with in-cluster config."""
        monitor = K8sEventMonitor(kubeconfig_path=None)

        mock_kube_config.load_incluster_config.assert_called_once()
        assert monitor.hooks == []
        assert monitor.running is False

    def test_init_fallback_to_default_config(self, mock_kube_config, mock_kube_client):
        """Test fallback to default kubeconfig when in-cluster fails."""

        # Create a proper ConfigException class
        class ConfigException(Exception):
            pass

        mock_kube_config.ConfigException = ConfigException
        mock_kube_config.load_incluster_config.side_effect = ConfigException("Not in cluster")

        monitor = K8sEventMonitor(kubeconfig_path=None)

        mock_kube_config.load_incluster_config.assert_called_once()
        mock_kube_config.load_kube_config.assert_called_once()
        assert monitor.hooks == []
        assert monitor.running is False


class TestK8sEventMonitorHooks:
    """Tests for hook registration."""

    def test_register_hooks_empty_list(self, mock_kube_config, mock_kube_client):
        """Test registering empty hook list."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        assert monitor.hooks == []

    def test_register_hooks_single_hook(self, mock_kube_config, mock_kube_client):
        """Test registering a single hook."""
        monitor = K8sEventMonitor()
        hooks = [
            {
                "resource_type": "Pod",
                "namespace": "*",
                "event_types": ["MODIFIED"],
                "handler": "handle_pod_event",
            }
        ]
        monitor.register_hooks(hooks)

        assert monitor.hooks == hooks
        assert len(monitor.hooks) == 1

    def test_register_hooks_multiple_hooks(self, mock_kube_config, mock_kube_client):
        """Test registering multiple hooks."""
        monitor = K8sEventMonitor()
        hooks = [
            {
                "resource_type": "Pod",
                "namespace": "default",
                "event_types": ["ADDED"],
                "handler": "handle_pod_added",
            },
            {
                "resource_type": "Service",
                "namespace": "bunker",
                "event_types": ["DELETED"],
                "handler": "handle_service_deleted",
            },
        ]
        monitor.register_hooks(hooks)

        assert monitor.hooks == hooks
        assert len(monitor.hooks) == 2


class TestK8sEventMonitorStartStop:
    """Tests for start and stop functionality."""

    def test_start_creates_thread(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test that start creates a background thread."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        # Mock the watch loop to prevent actual watching
        with patch.object(monitor, "_watch_loop") as mock_loop:
            monitor.start()

            assert monitor.running is True
            assert monitor._watch_thread is not None

            # Give thread a moment to start
            time.sleep(0.1)

            # Verify thread was created (may have already finished if mock returns immediately)
            assert mock_loop.called

            monitor.stop()

    def test_start_when_already_running(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test that starting when already running logs warning."""
        monitor = K8sEventMonitor()

        with patch.object(monitor, "_watch_loop"):
            monitor.start()
            assert monitor.running is True

            # Try to start again
            monitor.start()
            assert monitor.running is True

            monitor.stop()

    def test_stop_when_not_running(self, mock_kube_config, mock_kube_client):
        """Test that stopping when not running logs warning."""
        monitor = K8sEventMonitor()
        assert monitor.running is False

        monitor.stop()
        assert monitor.running is False

    def test_stop_gracefully(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test graceful shutdown."""
        monitor = K8sEventMonitor()

        with patch.object(monitor, "_watch_loop"):
            monitor.start()
            assert monitor.running is True

            monitor.stop()
            assert monitor.running is False
            assert monitor._stop_event.is_set()


class TestK8sEventMonitorEventMatching:
    """Tests for event matching logic."""

    def test_match_event_resource_type(self, mock_kube_config, mock_kube_client):
        """Test matching by resource type."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is True

    def test_match_event_wrong_resource_type(self, mock_kube_config, mock_kube_client):
        """Test non-matching resource type."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Service",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "handle_service",
        }

        assert monitor._match_event(event, hook) is False

    def test_match_event_type(self, mock_kube_config, mock_kube_client):
        """Test matching by event type."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "ADDED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["ADDED", "MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is True

    def test_match_event_wrong_event_type(self, mock_kube_config, mock_kube_client):
        """Test non-matching event type."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "DELETED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["ADDED", "MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is False

    def test_match_event_namespace_wildcard(self, mock_kube_config, mock_kube_client):
        """Test namespace wildcard matching."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="any-namespace"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is True

    def test_match_event_specific_namespace(self, mock_kube_config, mock_kube_client):
        """Test specific namespace matching."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="bunker"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "bunker",
            "event_types": ["MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is True

    def test_match_event_wrong_namespace(self, mock_kube_config, mock_kube_client):
        """Test non-matching namespace."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "bunker",
            "event_types": ["MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is False

    def test_match_event_no_object(self, mock_kube_config, mock_kube_client):
        """Test event without object."""
        monitor = K8sEventMonitor()

        event = {"type": "MODIFIED", "object": None}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is False


class TestK8sEventMonitorEventDispatch:
    """Tests for event dispatching."""

    def test_dispatch_event_with_handler(self, mock_kube_config, mock_kube_client):
        """Test dispatching event to handler."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "handle_pod_event",
        }

        # Should not raise exception
        monitor._dispatch_event(event, hook)

    def test_dispatch_event_without_handler(self, mock_kube_config, mock_kube_client):
        """Test dispatching event without handler logs warning."""
        monitor = K8sEventMonitor()

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
        }

        # Should not raise exception
        monitor._dispatch_event(event, hook)

    def test_dispatch_event_calls_registered_handler(self, mock_kube_config, mock_kube_client):
        """Test that registered handler is actually called."""
        monitor = K8sEventMonitor()

        # Register a mock handler
        mock_handler = Mock()
        monitor.register_handler("test_handler", mock_handler)

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "test_handler",
        }

        monitor._dispatch_event(event, hook)

        # Verify handler was called with correct arguments
        mock_handler.assert_called_once_with(event, hook)

    def test_dispatch_event_handler_exception(self, mock_kube_config, mock_kube_client):
        """Test that handler exceptions are caught and logged."""
        monitor = K8sEventMonitor()

        # Register a handler that raises an exception
        def failing_handler(event, hook):
            raise ValueError("Handler failed")

        monitor.register_handler("failing_handler", failing_handler)

        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
        )
        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "handler": "failing_handler",
        }

        # Should not raise exception, just log it
        monitor._dispatch_event(event, hook)


class TestK8sEventMonitorFilterEvaluation:
    """Tests for filter evaluation logic."""

    def test_match_event_with_simple_filter(self, mock_kube_config, mock_kube_client):
        """Test matching with simple filter expression."""
        monitor = K8sEventMonitor()

        # Create a mock Pod object with status
        pod = Mock()
        pod.kind = "Pod"
        pod.metadata = Mock()
        pod.metadata.name = "test-pod"
        pod.metadata.namespace = "default"
        pod.status = Mock()
        pod.status.phase = "Failed"

        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "filters": {"status.phase": "Failed"},
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is True

    def test_match_event_with_filter_mismatch(self, mock_kube_config, mock_kube_client):
        """Test non-matching filter."""
        monitor = K8sEventMonitor()

        pod = Mock()
        pod.kind = "Pod"
        pod.metadata = Mock()
        pod.metadata.name = "test-pod"
        pod.metadata.namespace = "default"
        pod.status = Mock()
        pod.status.phase = "Running"

        event = {"type": "MODIFIED", "object": pod}

        hook = {
            "resource_type": "Pod",
            "namespace": "*",
            "event_types": ["MODIFIED"],
            "filters": {"status.phase": "Failed"},
            "handler": "handle_pod",
        }

        assert monitor._match_event(event, hook) is False

    def test_get_nested_value_simple_path(self, mock_kube_config, mock_kube_client):
        """Test getting nested value with simple path."""
        monitor = K8sEventMonitor()

        obj = Mock()
        obj.status = Mock()
        obj.status.phase = "Running"

        value = monitor._get_nested_value(obj, "status.phase")
        assert value == "Running"

    def test_get_nested_value_missing_path(self, mock_kube_config, mock_kube_client):
        """Test getting nested value with missing path."""
        monitor = K8sEventMonitor()

        # Use a real object instead of Mock to test missing attributes
        class TestObj:
            def __init__(self):
                self.status = type("obj", (object,), {})()

        obj = TestObj()

        value = monitor._get_nested_value(obj, "status.nonexistent")
        assert value is None

    def test_get_nested_value_with_array_wildcard(self, mock_kube_config, mock_kube_client):
        """Test getting nested value with array wildcard."""
        monitor = K8sEventMonitor()

        obj = Mock()
        obj.status = Mock()
        obj.status.containerStatuses = [
            Mock(name="container1"),
            Mock(name="container2"),
        ]

        value = monitor._get_nested_value(obj, "status.containerStatuses[*]")
        assert isinstance(value, list)
        assert len(value) == 2


class TestK8sEventMonitorHandlerRegistration:
    """Tests for handler registration."""

    def test_register_handler(self, mock_kube_config, mock_kube_client):
        """Test registering a handler."""
        monitor = K8sEventMonitor()

        def test_handler(event, hook):
            pass

        monitor.register_handler("test_handler", test_handler)

        assert "test_handler" in monitor._handlers
        assert monitor._handlers["test_handler"] == test_handler

    def test_register_multiple_handlers(self, mock_kube_config, mock_kube_client):
        """Test registering multiple handlers."""
        monitor = K8sEventMonitor()

        def handler1(event, hook):
            pass

        def handler2(event, hook):
            pass

        monitor.register_handler("handler1", handler1)
        monitor.register_handler("handler2", handler2)

        assert len(monitor._handlers) == 2
        assert "handler1" in monitor._handlers
        assert "handler2" in monitor._handlers


class TestK8sEventMonitorResourceTypes:
    """Tests for resource type extraction."""

    def test_get_resource_types_from_hooks(self, mock_kube_config, mock_kube_client):
        """Test extracting resource types from hooks."""
        monitor = K8sEventMonitor()

        hooks = [
            {"resource_type": "Pod", "handler": "handle_pod"},
            {"resource_type": "Service", "handler": "handle_service"},
            {"resource_type": "Pod", "handler": "handle_pod_2"},  # Duplicate
        ]

        monitor.register_hooks(hooks)
        resource_types = monitor._get_resource_types_from_hooks()

        assert len(resource_types) == 2
        assert "Pod" in resource_types
        assert "Service" in resource_types

    def test_get_resource_types_empty_hooks(self, mock_kube_config, mock_kube_client):
        """Test extracting resource types from empty hooks."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        resource_types = monitor._get_resource_types_from_hooks()
        assert resource_types == []


class TestK8sEventMonitorReconnection:
    """Tests for reconnection logic."""

    def test_exponential_backoff_timing(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test that reconnection uses exponential backoff timing."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        # Mock the watch stream to fail multiple times
        api_exception = Exception("Connection failed")
        mock_watch.Watch.return_value.stream.side_effect = [
            api_exception,
            api_exception,
            api_exception,
        ]

        # Track sleep calls to verify exponential backoff
        sleep_calls = []

        def mock_wait(timeout):
            sleep_calls.append(timeout)
            # Stop after 3 failures
            if len(sleep_calls) >= 3:
                monitor.running = False
            return False  # Don't actually sleep

        monitor._stop_event.wait = mock_wait

        # Start the monitor
        monitor.start()

        # Wait for thread to complete
        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=2.0)

        # Verify exponential backoff: 30s, 60s, 120s
        assert len(sleep_calls) >= 3
        assert sleep_calls[0] == 30  # First retry: base delay
        assert sleep_calls[1] == 60  # Second retry: 30 * 2^1
        assert sleep_calls[2] == 120  # Third retry: 30 * 2^2

    def test_max_reconnection_delay(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test that reconnection delay caps at maximum value."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        # Mock the watch stream to fail many times
        api_exception = Exception("Connection failed")
        mock_watch.Watch.return_value.stream.side_effect = [api_exception] * 10

        sleep_calls = []

        def mock_wait(timeout):
            sleep_calls.append(timeout)
            # Stop after 6 failures (should hit max delay)
            if len(sleep_calls) >= 6:
                monitor.running = False
            return False

        monitor._stop_event.wait = mock_wait

        monitor.start()

        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=2.0)

        # Verify that delay caps at 300 seconds (max_reconnect_delay)
        # Progression: 30, 60, 120, 240, 300, 300
        assert len(sleep_calls) >= 5
        assert sleep_calls[4] == 300  # Should be capped at max
        if len(sleep_calls) >= 6:
            assert sleep_calls[5] == 300  # Should remain capped

    def test_connection_recovery_after_failure(
        self, mock_kube_config, mock_kube_client, mock_watch
    ):
        """Test that connection recovers after temporary failure."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        # Mock the watch stream to fail once, then succeed
        api_exception = Exception("Temporary connection failure")

        # Create a mock event generator that yields one event
        def mock_event_generator():
            yield {
                "type": "ADDED",
                "object": V1Pod(
                    kind="Pod", metadata=V1ObjectMeta(name="test-pod", namespace="default")
                ),
            }
            # After yielding one event, stop the monitor
            monitor.running = False

        mock_watch.Watch.return_value.stream.side_effect = [
            api_exception,  # First attempt fails
            mock_event_generator(),  # Second attempt succeeds
        ]

        sleep_calls = []

        def mock_wait(timeout):
            sleep_calls.append(timeout)
            return False  # Don't actually sleep

        monitor._stop_event.wait = mock_wait

        monitor.start()

        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=2.0)

        # Verify that reconnection was attempted
        assert len(sleep_calls) >= 1
        assert sleep_calls[0] == 30  # First retry after failure

        # Verify that stream was called twice (initial + retry)
        assert mock_watch.Watch.return_value.stream.call_count == 2

    def test_reconnection_resets_delay_on_success(
        self, mock_kube_config, mock_kube_client, mock_watch
    ):
        """Test that reconnection delay resets after successful connection."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        api_exception = Exception("Connection failed")

        # Create event generators
        def success_generator_1():
            yield {
                "type": "ADDED",
                "object": V1Pod(
                    kind="Pod", metadata=V1ObjectMeta(name="pod-1", namespace="default")
                ),
            }

        def success_generator_2():
            yield {
                "type": "ADDED",
                "object": V1Pod(
                    kind="Pod", metadata=V1ObjectMeta(name="pod-2", namespace="default")
                ),
            }
            monitor.running = False

        # Fail twice, succeed, fail once more, succeed again
        mock_watch.Watch.return_value.stream.side_effect = [
            api_exception,  # Fail
            api_exception,  # Fail again
            success_generator_1(),  # Success - should reset delay
            api_exception,  # Fail after success
            success_generator_2(),  # Success again
        ]

        sleep_calls = []

        def mock_wait(timeout):
            sleep_calls.append(timeout)
            return False

        monitor._stop_event.wait = mock_wait

        monitor.start()

        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=2.0)

        # Verify exponential backoff for first two failures: 30s, 60s
        assert len(sleep_calls) >= 3
        assert sleep_calls[0] == 30  # First failure
        assert sleep_calls[1] == 60  # Second failure (exponential)
        # After success, delay should reset
        assert sleep_calls[2] == 30  # Third failure (reset to base delay)

    def test_api_exception_handling(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test handling of Kubernetes API exceptions during reconnection."""
        from kubernetes.client.rest import ApiException

        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        # Create an ApiException
        api_exception = ApiException(status=503, reason="Service Unavailable")
        mock_watch.Watch.return_value.stream.side_effect = [
            api_exception,
            api_exception,
        ]

        sleep_calls = []

        def mock_wait(timeout):
            sleep_calls.append(timeout)
            if len(sleep_calls) >= 2:
                monitor.running = False
            return False

        monitor._stop_event.wait = mock_wait

        monitor.start()

        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=2.0)

        # Verify that ApiException is handled and reconnection is attempted
        assert len(sleep_calls) >= 2
        assert sleep_calls[0] == 30
        assert sleep_calls[1] == 60

    def test_stop_during_reconnection_wait(self, mock_kube_config, mock_kube_client, mock_watch):
        """Test that stop() interrupts reconnection wait."""
        monitor = K8sEventMonitor()
        monitor.register_hooks([])

        api_exception = Exception("Connection failed")
        mock_watch.Watch.return_value.stream.side_effect = api_exception

        # Track if wait was called
        wait_called = threading.Event()
        original_wait = monitor._stop_event.wait

        def mock_wait(timeout):
            wait_called.set()
            # Call original wait which will return True when stop is called
            return original_wait(timeout)

        monitor._stop_event.wait = mock_wait

        monitor.start()

        # Wait for the watch loop to enter reconnection wait
        wait_called.wait(timeout=1.0)

        # Now stop the monitor
        monitor.stop()

        # Thread should exit quickly (not wait full reconnection delay)
        if monitor._watch_thread:
            monitor._watch_thread.join(timeout=1.0)
            assert not monitor._watch_thread.is_alive()
