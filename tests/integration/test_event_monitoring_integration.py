"""
Integration test for event monitoring workflow.

This test verifies that ManifestLoader and K8sEventMonitor work together correctly.
"""

import pytest
from unittest.mock import Mock, patch
from kubernetes.client import V1Pod, V1ObjectMeta, V1PodStatus, V1ContainerStatus, V1ContainerState, V1ContainerStateWaiting

from src.neural_link.k8s_monitoring.manifest_loader import ManifestLoader
from src.neural_link.k8s_monitoring.k8s_event_monitor import K8sEventMonitor


class TestEventMonitoringIntegration:
    """Integration tests for the complete event monitoring workflow."""

    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config")
    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client")
    def test_load_manifest_and_register_hooks(self, mock_client, mock_config):
        """Test loading manifest and registering hooks with K8sEventMonitor."""
        # Load the actual manifest
        loader = ManifestLoader()
        manifest = loader.load_manifest("superpowers/n8n/manifest.json")
        
        # Validate it
        assert loader.validate_hooks(manifest) is True
        
        # Extract hooks
        hooks = loader.get_k8s_hooks(manifest)
        assert len(hooks) >= 2
        
        # Create monitor and register hooks
        monitor = K8sEventMonitor()
        monitor.register_hooks(hooks)
        
        # Verify hooks are registered
        assert len(monitor.hooks) == len(hooks)
        assert monitor.hooks == hooks

    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config")
    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client")
    def test_event_matching_with_real_manifest(self, mock_client, mock_config):
        """Test that events match correctly with real manifest configuration."""
        # Load manifest
        loader = ManifestLoader()
        manifest = loader.load_manifest("superpowers/n8n/manifest.json")
        hooks = loader.get_k8s_hooks(manifest)
        
        # Create monitor
        monitor = K8sEventMonitor()
        monitor.register_hooks(hooks)
        
        # Create a Pod in CrashLoopBackOff state (should match first hook)
        container_status = Mock()
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        
        pod = Mock()
        pod.kind = "Pod"
        pod.metadata = Mock()
        pod.metadata.name = "neo4j-pod"
        pod.metadata.namespace = "bunker"
        pod.status = Mock()
        pod.status.phase = "Failed"
        pod.status.containerStatuses = [container_status]
        
        event = {
            "type": "MODIFIED",
            "object": pod
        }
        
        # Find the CrashLoopBackOff hook
        crash_hook = next(
            h for h in hooks 
            if h.get("resource_type") == "Pod" and 
            "CrashLoopBackOff" in str(h.get("filters", {}))
        )
        
        # Should match
        assert monitor._match_event(event, crash_hook) is True

    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config")
    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client")
    def test_handler_dispatch_with_real_manifest(self, mock_client, mock_config):
        """Test that handlers are dispatched correctly with real manifest."""
        # Load manifest
        loader = ManifestLoader()
        manifest = loader.load_manifest("superpowers/n8n/manifest.json")
        hooks = loader.get_k8s_hooks(manifest)
        
        # Create monitor
        monitor = K8sEventMonitor()
        monitor.register_hooks(hooks)
        
        # Register mock handlers
        mock_pod_handler = Mock()
        mock_service_handler = Mock()
        monitor.register_handler("handle_pod_crash", mock_pod_handler)
        monitor.register_handler("handle_service_change", mock_service_handler)
        
        # Create a Pod event that should trigger handle_pod_crash
        container_status = Mock()
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        
        pod = Mock()
        pod.kind = "Pod"
        pod.metadata = Mock()
        pod.metadata.name = "test-pod"
        pod.metadata.namespace = "default"
        pod.status = Mock()
        pod.status.phase = "Failed"
        pod.status.containerStatuses = [container_status]
        
        pod_event = {
            "type": "MODIFIED",
            "object": pod
        }
        
        # Process the event
        monitor._process_event(pod_event)
        
        # Verify handler was called
        mock_pod_handler.assert_called_once()
        mock_service_handler.assert_not_called()

    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config")
    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client")
    def test_multiple_hooks_can_match_same_event(self, mock_client, mock_config):
        """Test that multiple hooks can match and dispatch for the same event."""
        # Create a custom manifest with overlapping hooks
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "namespace": "*",
                        "event_types": ["MODIFIED"],
                        "handler": "handler1"
                    },
                    {
                        "resource_type": "Pod",
                        "namespace": "default",
                        "event_types": ["MODIFIED"],
                        "handler": "handler2"
                    }
                ]
            }
        }
        
        loader = ManifestLoader()
        hooks = loader.get_k8s_hooks(manifest)
        
        # Create monitor
        monitor = K8sEventMonitor()
        monitor.register_hooks(hooks)
        
        # Register handlers
        mock_handler1 = Mock()
        mock_handler2 = Mock()
        monitor.register_handler("handler1", mock_handler1)
        monitor.register_handler("handler2", mock_handler2)
        
        # Create event
        pod = V1Pod(
            kind="Pod",
            metadata=V1ObjectMeta(name="test-pod", namespace="default"),
            status=V1PodStatus(phase="Running")
        )
        
        event = {
            "type": "MODIFIED",
            "object": pod
        }
        
        # Process event
        monitor._process_event(event)
        
        # Both handlers should be called
        mock_handler1.assert_called_once()
        mock_handler2.assert_called_once()

    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config")
    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client")
    def test_namespace_filtering_works_correctly(self, mock_client, mock_config):
        """Test that namespace filtering works as expected."""
        # Load manifest
        loader = ManifestLoader()
        manifest = loader.load_manifest("superpowers/n8n/manifest.json")
        hooks = loader.get_k8s_hooks(manifest)
        
        # Create monitor
        monitor = K8sEventMonitor()
        monitor.register_hooks(hooks)
        
        # Register handlers
        mock_handler = Mock()
        monitor.register_handler("handle_service_change", mock_handler)
        
        # Create a Service event in "bunker" namespace (should match)
        service_bunker = Mock()
        service_bunker.kind = "Service"
        service_bunker.metadata = Mock()
        service_bunker.metadata.name = "test-service"
        service_bunker.metadata.namespace = "bunker"
        
        event_bunker = {
            "type": "ADDED",
            "object": service_bunker
        }
        
        monitor._process_event(event_bunker)
        assert mock_handler.call_count == 1
        
        # Create a Service event in "default" namespace (should NOT match)
        service_default = Mock()
        service_default.kind = "Service"
        service_default.metadata = Mock()
        service_default.metadata.name = "test-service"
        service_default.metadata.namespace = "default"
        
        event_default = {
            "type": "ADDED",
            "object": service_default
        }
        
        monitor._process_event(event_default)
        # Should still be 1 (not called again)
        assert mock_handler.call_count == 1

    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config")
    @patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client")
    def test_filter_evaluation_with_nested_paths(self, mock_client, mock_config):
        """Test that complex filter paths work correctly."""
        # Load manifest
        loader = ManifestLoader()
        manifest = loader.load_manifest("superpowers/n8n/manifest.json")
        hooks = loader.get_k8s_hooks(manifest)
        
        # Create monitor
        monitor = K8sEventMonitor()
        monitor.register_hooks(hooks)
        
        # Find the CrashLoopBackOff hook
        crash_hook = next(
            h for h in hooks 
            if "CrashLoopBackOff" in str(h.get("filters", {}))
        )
        
        # Test with matching filters
        container_status = Mock()
        container_status.state = Mock()
        container_status.state.waiting = Mock()
        container_status.state.waiting.reason = "CrashLoopBackOff"
        
        pod_match = Mock()
        pod_match.kind = "Pod"
        pod_match.metadata = Mock()
        pod_match.metadata.name = "test-pod"
        pod_match.metadata.namespace = "default"
        pod_match.status = Mock()
        pod_match.status.phase = "Failed"
        pod_match.status.containerStatuses = [container_status]
        
        event_match = {
            "type": "MODIFIED",
            "object": pod_match
        }
        
        assert monitor._match_event(event_match, crash_hook) is True
        
        # Test with non-matching phase
        pod_no_match = Mock()
        pod_no_match.kind = "Pod"
        pod_no_match.metadata = Mock()
        pod_no_match.metadata.name = "test-pod"
        pod_no_match.metadata.namespace = "default"
        pod_no_match.status = Mock()
        pod_no_match.status.phase = "Running"  # Different phase
        pod_no_match.status.containerStatuses = [container_status]
        
        event_no_match = {
            "type": "MODIFIED",
            "object": pod_no_match
        }
        
        assert monitor._match_event(event_no_match, crash_hook) is False
