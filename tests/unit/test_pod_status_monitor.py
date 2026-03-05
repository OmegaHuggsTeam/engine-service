"""
Unit tests for PodStatusMonitor.

Tests CrashLoopBackOff detection, failure info extraction, and analysis workflow.
"""

import pytest
from unittest.mock import Mock, MagicMock
from collections import deque
from src.neural_link.k8s_monitoring.pod_status_monitor import (
    PodStatusMonitor,
    PodFailureEvent,
)


class TestPodStatusMonitor:
    """Unit tests for PodStatusMonitor class."""

    def test_initialization(self):
        """Test PodStatusMonitor initializes with correct dependencies."""
        log_analyzer = Mock()
        specialist_agent = Mock()
        notifier = Mock()

        monitor = PodStatusMonitor(
            log_analyzer=log_analyzer,
            specialist_agent=specialist_agent,
            notifier=notifier,
            max_queue_size=10,
        )

        assert monitor._log_analyzer is log_analyzer
        assert monitor._specialist_agent is specialist_agent
        assert monitor._notifier is notifier
        assert isinstance(monitor._failure_queue, deque)
        assert monitor._failure_queue.maxlen == 10

    def test_is_crash_loop_backoff_detects_failure(self):
        """Test _is_crash_loop_backoff correctly identifies CrashLoopBackOff state."""
        monitor = PodStatusMonitor()

        # Create mock Pod object with CrashLoopBackOff
        pod = Mock()
        pod.status = Mock()
        container_status = Mock()
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        pod.status.containerStatuses = [container_status]

        assert monitor._is_crash_loop_backoff(pod) is True

    def test_is_crash_loop_backoff_returns_false_for_running_pod(self):
        """Test _is_crash_loop_backoff returns False for running Pod."""
        monitor = PodStatusMonitor()

        # Create mock Pod object with Running state
        pod = Mock()
        pod.status = Mock()
        container_status = Mock()
        container_status.state = Mock()
        container_status.state.running = Mock()
        container_status.state.waiting = None
        pod.status.containerStatuses = [container_status]

        assert monitor._is_crash_loop_backoff(pod) is False

    def test_is_crash_loop_backoff_handles_no_status(self):
        """Test _is_crash_loop_backoff handles Pod with no status."""
        monitor = PodStatusMonitor()

        pod = Mock()
        pod.status = None

        assert monitor._is_crash_loop_backoff(pod) is False

    def test_is_crash_loop_backoff_handles_no_container_statuses(self):
        """Test _is_crash_loop_backoff handles Pod with no containerStatuses."""
        monitor = PodStatusMonitor()

        pod = Mock()
        pod.status = Mock()
        pod.status.containerStatuses = None

        assert monitor._is_crash_loop_backoff(pod) is False

    def test_extract_failure_info_creates_event(self):
        """Test _extract_failure_info extracts all required fields."""
        monitor = PodStatusMonitor()

        # Create mock Pod object
        pod = Mock()
        pod.metadata = Mock()
        pod.metadata.name = "neo4j-0"
        pod.metadata.namespace = "bunker"
        pod.metadata.creationTimestamp = "2024-01-01T00:00:00Z"

        pod.status = Mock()
        container_status = Mock()
        container_status.name = "neo4j"
        container_status.restartCount = 5
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        container_status.state.waiting.message = "Back-off restarting failed container"

        # Add last terminated state
        container_status.lastState = Mock()
        container_status.lastState.terminated = Mock()
        container_status.lastState.terminated.exitCode = 1
        container_status.lastState.terminated.reason = "Error"
        container_status.lastState.terminated.message = "Container failed"
        container_status.lastState.terminated.finishedAt = "2024-01-01T00:05:00Z"

        pod.status.containerStatuses = [container_status]

        failure = monitor._extract_failure_info(pod)

        assert failure is not None
        assert failure.pod_name == "neo4j-0"
        assert failure.namespace == "bunker"
        assert failure.container_name == "neo4j"
        assert failure.reason == "CrashLoopBackOff"
        assert failure.message == "Back-off restarting failed container"
        assert failure.restart_count == 5
        assert failure.last_state is not None
        assert failure.last_state["exit_code"] == 1
        assert failure.last_state["reason"] == "Error"
        assert failure.timestamp == "2024-01-01T00:00:00Z"
        assert failure.is_neo4j is True
        assert failure.is_chromadb is False

    def test_extract_failure_info_detects_chromadb(self):
        """Test _extract_failure_info correctly identifies ChromaDB pods."""
        monitor = PodStatusMonitor()

        pod = Mock()
        pod.metadata = Mock()
        pod.metadata.name = "chromadb-deployment-abc123"
        pod.metadata.namespace = "default"
        pod.metadata.creationTimestamp = "2024-01-01T00:00:00Z"

        pod.status = Mock()
        container_status = Mock()
        container_status.name = "chroma"
        container_status.restartCount = 3
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        container_status.state.waiting.message = None
        container_status.lastState = None

        pod.status.containerStatuses = [container_status]

        failure = monitor._extract_failure_info(pod)

        assert failure is not None
        assert failure.is_chromadb is True
        assert failure.is_neo4j is False

    def test_extract_failure_info_handles_no_metadata(self):
        """Test _extract_failure_info returns None for Pod without metadata."""
        monitor = PodStatusMonitor()

        pod = Mock()
        pod.metadata = None

        failure = monitor._extract_failure_info(pod)

        assert failure is None

    def test_extract_failure_info_handles_multi_container_pod(self):
        """Test _extract_failure_info handles multi-container Pods correctly."""
        monitor = PodStatusMonitor()

        pod = Mock()
        pod.metadata = Mock()
        pod.metadata.name = "multi-container-pod"
        pod.metadata.namespace = "default"
        pod.metadata.creationTimestamp = "2024-01-01T00:00:00Z"

        # First container is running
        container1 = Mock()
        container1.name = "sidecar"
        container1.state = Mock()
        container1.state.running = Mock()
        container1.state.waiting = None

        # Second container is in CrashLoopBackOff
        container2 = Mock()
        container2.name = "main"
        container2.restartCount = 2
        container2.state = Mock()
        container2.state.waiting = Mock()
        container2.state.waiting.reason = "CrashLoopBackOff"
        container2.state.waiting.message = "Container crashed"
        container2.lastState = None

        pod.status = Mock()
        pod.status.containerStatuses = [container1, container2]

        failure = monitor._extract_failure_info(pod)

        assert failure is not None
        assert failure.container_name == "main"
        assert failure.restart_count == 2

    def test_handle_pod_event_processes_crash_loop_backoff(self):
        """Test handle_pod_event processes CrashLoopBackOff events."""
        log_analyzer = Mock()
        log_analyzer.get_pod_logs = Mock(return_value="Error: Connection refused")

        specialist_agent = Mock()
        specialist_agent.analyze_pod_logs = Mock(return_value="Check database connection")

        notifier = Mock()
        notifier.send_pod_failure_alert = Mock()

        monitor = PodStatusMonitor(
            log_analyzer=log_analyzer,
            specialist_agent=specialist_agent,
            notifier=notifier,
        )

        # Create event with CrashLoopBackOff Pod
        pod = Mock()
        pod.metadata = Mock()
        pod.metadata.name = "test-pod"
        pod.metadata.namespace = "default"
        pod.metadata.creationTimestamp = "2024-01-01T00:00:00Z"

        pod.status = Mock()
        container_status = Mock()
        container_status.name = "test-container"
        container_status.restartCount = 1
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        container_status.state.waiting.message = "Container failed"
        container_status.lastState = None

        pod.status.containerStatuses = [container_status]

        event = {"type": "MODIFIED", "object": pod}
        hook = {}

        monitor.handle_pod_event(event, hook)

        # Verify failure was added to queue
        assert len(monitor._failure_queue) == 1
        failure = monitor._failure_queue[0]
        assert failure.pod_name == "test-pod"

        # Verify analysis pipeline was triggered
        log_analyzer.get_pod_logs.assert_called_once()
        specialist_agent.analyze_pod_logs.assert_called_once()
        notifier.send_pod_failure_alert.assert_called_once()

    def test_handle_pod_event_ignores_non_crash_loop_backoff(self):
        """Test handle_pod_event ignores events that are not CrashLoopBackOff."""
        monitor = PodStatusMonitor()

        # Create event with running Pod
        pod = Mock()
        pod.status = Mock()
        container_status = Mock()
        container_status.state = Mock()
        container_status.state.running = Mock()
        container_status.state.waiting = None
        pod.status.containerStatuses = [container_status]

        event = {"type": "MODIFIED", "object": pod}
        hook = {}

        monitor.handle_pod_event(event, hook)

        # Verify no failure was added to queue
        assert len(monitor._failure_queue) == 0

    def test_handle_pod_event_handles_missing_object(self):
        """Test handle_pod_event handles events with missing object."""
        monitor = PodStatusMonitor()

        event = {"type": "MODIFIED"}
        hook = {}

        # Should not raise exception
        monitor.handle_pod_event(event, hook)

        assert len(monitor._failure_queue) == 0

    def test_analyze_failure_handles_log_analyzer_error(self):
        """Test _analyze_failure continues when log analyzer fails."""
        log_analyzer = Mock()
        log_analyzer.get_pod_logs = Mock(side_effect=Exception("kubectl failed"))

        specialist_agent = Mock()
        notifier = Mock()

        monitor = PodStatusMonitor(
            log_analyzer=log_analyzer,
            specialist_agent=specialist_agent,
            notifier=notifier,
        )

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
            container_name="test",
        )

        # Should not raise exception
        monitor._analyze_failure(failure)

    def test_analyze_failure_handles_specialist_agent_error(self):
        """Test _analyze_failure continues when specialist agent fails."""
        log_analyzer = Mock()
        log_analyzer.get_pod_logs = Mock(return_value="logs")

        specialist_agent = Mock()
        specialist_agent.analyze_pod_logs = Mock(side_effect=Exception("Analysis failed"))

        notifier = Mock()

        monitor = PodStatusMonitor(
            log_analyzer=log_analyzer,
            specialist_agent=specialist_agent,
            notifier=notifier,
        )

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
            container_name="test",
        )

        # Should not raise exception
        monitor._analyze_failure(failure)

    def test_register_handler_adds_handler(self):
        """Test register_handler adds handler to list."""
        monitor = PodStatusMonitor()
        handler = Mock()

        monitor.register_handler(handler)

        assert handler in monitor._handlers

    def test_handle_pod_event_calls_registered_handlers(self):
        """Test handle_pod_event calls all registered handlers."""
        monitor = PodStatusMonitor()
        handler1 = Mock()
        handler2 = Mock()

        monitor.register_handler(handler1)
        monitor.register_handler(handler2)

        # Create CrashLoopBackOff event
        pod = Mock()
        pod.metadata = Mock()
        pod.metadata.name = "test-pod"
        pod.metadata.namespace = "default"
        pod.metadata.creationTimestamp = "2024-01-01T00:00:00Z"

        pod.status = Mock()
        container_status = Mock()
        container_status.name = "test"
        container_status.restartCount = 1
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        container_status.state.waiting.message = None
        container_status.lastState = None

        pod.status.containerStatuses = [container_status]

        event = {"type": "MODIFIED", "object": pod}
        hook = {}

        monitor.handle_pod_event(event, hook)

        # Verify both handlers were called
        handler1.assert_called_once()
        handler2.assert_called_once()

        # Verify they received the PodFailureEvent
        call_arg = handler1.call_args[0][0]
        assert isinstance(call_arg, PodFailureEvent)
        assert call_arg.pod_name == "test-pod"

    def test_failure_queue_respects_max_size(self):
        """Test failure queue respects max_queue_size limit."""
        monitor = PodStatusMonitor(max_queue_size=2)

        # Add 3 failures
        for i in range(3):
            failure = PodFailureEvent(
                pod_name=f"pod-{i}",
                namespace="default",
            )
            monitor._failure_queue.append(failure)

        # Queue should only contain last 2 failures
        assert len(monitor._failure_queue) == 2
        assert monitor._failure_queue[0].pod_name == "pod-1"
        assert monitor._failure_queue[1].pod_name == "pod-2"
