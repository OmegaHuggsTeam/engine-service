"""
Unit tests for wire_monitoring main entry point.

Tests the initialization and wiring of all k8s monitoring components.
"""

import os
import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from src.neural_link.k8s_monitoring.wire_monitoring import (
    wire_and_start,
    validate_configuration,
    shutdown,
)


class TestWireMonitoring:
    """Test suite for wire_monitoring module."""

    def test_validate_configuration_missing_token(self):
        """Test configuration validation fails when TELEGRAM_BOT_TOKEN is missing."""
        with patch.dict(os.environ, {}, clear=True):
            is_valid, errors = validate_configuration()
            assert not is_valid
            assert any("TELEGRAM_BOT_TOKEN" in error for error in errors)

    def test_validate_configuration_invalid_kubeconfig(self):
        """Test configuration validation fails when KUBECONFIG path doesn't exist."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "test_token",
                "KUBECONFIG": "/nonexistent/path/kubeconfig",
            },
        ):
            is_valid, errors = validate_configuration()
            assert not is_valid
            assert any("KUBECONFIG" in error for error in errors)

    def test_validate_configuration_missing_manifest(self):
        """Test configuration validation fails when manifest file doesn't exist."""
        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "test_token",
                "K8S_MANIFEST_PATH": "/nonexistent/manifest.json",
            },
        ):
            is_valid, errors = validate_configuration()
            assert not is_valid
            assert any("Manifest" in error for error in errors)

    def test_validate_configuration_success(self, tmp_path):
        """Test configuration validation succeeds with valid settings."""
        # Create temporary manifest file
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text('{"hooks": {"on_k8s_event": []}}')

        with patch.dict(
            os.environ,
            {
                "TELEGRAM_BOT_TOKEN": "test_token",
                "K8S_MANIFEST_PATH": str(manifest_path),
            },
        ):
            is_valid, errors = validate_configuration()
            assert is_valid
            assert len(errors) == 0

    @patch("src.neural_link.k8s_monitoring.wire_monitoring.K8sEventMonitor")
    @patch("src.neural_link.k8s_monitoring.wire_monitoring.PodStatusMonitor")
    @patch("src.neural_link.k8s_monitoring.wire_monitoring.KubectlLogAnalyzer")
    @patch("src.neural_link.k8s_monitoring.wire_monitoring.ManifestLoader")
    def test_wire_and_start_basic(
        self,
        mock_manifest_loader,
        mock_log_analyzer,
        mock_pod_monitor,
        mock_k8s_monitor,
        tmp_path,
    ):
        """Test basic wiring of components without optional dependencies."""
        # Setup manifest loader mock
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            '{"hooks": {"on_k8s_event": [{"resource_type": "Pod", "event_types": ["MODIFIED"], "handler": "handle_pod_crash"}]}}'
        )

        mock_loader_instance = Mock()
        mock_loader_instance.load_manifest.return_value = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"],
                        "handler": "handle_pod_crash",
                    }
                ]
            }
        }
        mock_loader_instance.validate_hooks.return_value = True
        mock_loader_instance.get_k8s_hooks.return_value = [
            {
                "resource_type": "Pod",
                "event_types": ["MODIFIED"],
                "handler": "handle_pod_crash",
            }
        ]
        mock_manifest_loader.return_value = mock_loader_instance

        # Setup other mocks
        mock_log_analyzer_instance = Mock()
        mock_log_analyzer.return_value = mock_log_analyzer_instance

        mock_pod_monitor_instance = Mock()
        mock_pod_monitor.return_value = mock_pod_monitor_instance

        mock_k8s_monitor_instance = Mock()
        mock_k8s_monitor.return_value = mock_k8s_monitor_instance

        # Mock SpecialistAgent import to fail
        with patch.dict("sys.modules", {"src.neural_link.agents.specialist_agent": None}):
            # Call wire_and_start
            k8s_monitor, pod_monitor = wire_and_start(
                manifest_path=str(manifest_path),
                kubeconfig_path=None,
                bot_token="test_token",
            )

            # Verify components were initialized
            assert k8s_monitor == mock_k8s_monitor_instance
            assert pod_monitor == mock_pod_monitor_instance

            # Verify manifest was loaded
            mock_loader_instance.load_manifest.assert_called_once_with(
                str(manifest_path)
            )
            mock_loader_instance.validate_hooks.assert_called_once()
            mock_loader_instance.get_k8s_hooks.assert_called_once()

            # Verify K8sEventMonitor was configured
            mock_k8s_monitor_instance.register_hooks.assert_called_once()
            mock_k8s_monitor_instance.register_handler.assert_called_once()
            mock_k8s_monitor_instance.start.assert_called_once()

    @patch("src.neural_link.k8s_monitoring.wire_monitoring._k8s_monitor")
    @patch("src.neural_link.k8s_monitoring.wire_monitoring._notifier")
    def test_shutdown(self, mock_notifier, mock_k8s_monitor):
        """Test graceful shutdown stops all components."""
        # Setup mocks
        mock_k8s_monitor_instance = Mock()
        mock_notifier_instance = Mock()
        mock_notifier_instance.process_queue.return_value = 5

        with patch(
            "src.neural_link.k8s_monitoring.wire_monitoring._k8s_monitor",
            mock_k8s_monitor_instance,
        ):
            with patch(
                "src.neural_link.k8s_monitoring.wire_monitoring._notifier",
                mock_notifier_instance,
            ):
                # Call shutdown
                shutdown()

                # Verify K8sEventMonitor was stopped
                mock_k8s_monitor_instance.stop.assert_called_once()

                # Verify message queue was processed
                mock_notifier_instance.process_queue.assert_called_once()

    def test_wire_and_start_with_telegram_notifier(self, tmp_path):
        """Test wiring includes TelegramNotifier when bot_token is provided."""
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(
            '{"hooks": {"on_k8s_event": [{"resource_type": "Pod", "event_types": ["MODIFIED"], "handler": "handle_pod_crash"}]}}'
        )

        with patch(
            "src.neural_link.k8s_monitoring.wire_monitoring.ManifestLoader"
        ) as mock_loader:
            with patch(
                "src.neural_link.k8s_monitoring.wire_monitoring.K8sEventMonitor"
            ) as mock_k8s:
                with patch(
                    "src.neural_link.k8s_monitoring.wire_monitoring.PodStatusMonitor"
                ) as mock_pod:
                    with patch(
                        "src.neural_link.k8s_monitoring.wire_monitoring.KubectlLogAnalyzer"
                    ):
                        with patch(
                            "src.neural_link.k8s_monitoring.telegram_notifier.TelegramNotifier"
                        ) as mock_notifier:
                            # Setup manifest loader
                            mock_loader_instance = Mock()
                            mock_loader_instance.load_manifest.return_value = {
                                "hooks": {"on_k8s_event": []}
                            }
                            mock_loader_instance.validate_hooks.return_value = True
                            mock_loader_instance.get_k8s_hooks.return_value = []
                            mock_loader.return_value = mock_loader_instance

                            # Call with bot_token
                            wire_and_start(
                                manifest_path=str(manifest_path),
                                bot_token="test_token_123",
                                default_chat_id=12345,
                            )

                            # Verify TelegramNotifier was initialized with correct params
                            mock_notifier.assert_called_once_with(
                                bot_token="test_token_123",
                                default_chat_id=12345,
                            )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
