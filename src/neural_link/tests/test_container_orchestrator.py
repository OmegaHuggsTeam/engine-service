"""Unit tests for ContainerOrchestrator — Docker SDK integration.

Uses unittest.mock to patch docker.from_env so no real Docker daemon is needed.
Run: python -m pytest src/neural_link/tests/test_container_orchestrator.py -v
"""

import time
import pytest
from unittest.mock import MagicMock, patch

from src.neural_link.containers.models import (
    ContainerConfig,
    ContainerInfo,
    ContainerMetrics,
    ContainerExecResult,
)
from src.neural_link.containers.orchestrator import ContainerOrchestrator


class TestContainerOrchestrator:
    """Tests for ContainerOrchestrator with mocked Docker SDK."""

    def setup_method(self):
        self.orch = ContainerOrchestrator()

    # ------------------------------------------------------------------
    # test_spawn_container_returns_id
    # ------------------------------------------------------------------
    def test_spawn_container_returns_id(self):
        config = ContainerConfig(
            image="huggsai/trigger:latest",
            tenant_id="tenant-001",
            node_id="node-abc",
            memory_limit_mb=128,
            env={"ACTION": "manual_trigger"},
        )
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.id = "abc123def456"
            mock_container.status = "running"
            mock_container.image.tags = ["huggsai/trigger:latest"]
            mock_docker.return_value.containers.run.return_value = mock_container

            result = self.orch.spawn(config)

        assert isinstance(result, ContainerInfo)
        assert result.container_id == "abc123def456"
        assert result.status == "running"
        assert result.node_id == "node-abc"
        assert result.tenant_id == "tenant-001"
        assert result.image == "huggsai/trigger:latest"

        # Verify Docker SDK was called with correct labels
        call_kwargs = mock_docker.return_value.containers.run.call_args
        labels = call_kwargs.kwargs.get("labels", {})
        assert labels["huggsai.tenant_id"] == "tenant-001"
        assert labels["huggsai.node_id"] == "node-abc"

    # ------------------------------------------------------------------
    # test_get_status_returns_metrics
    # ------------------------------------------------------------------
    def test_get_status_returns_metrics(self):
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.id = "abc123def456"
            mock_container.status = "running"
            mock_container.attrs = {
                "State": {
                    "StartedAt": "2026-03-12T10:00:00Z",
                    "FinishedAt": "0001-01-01T00:00:00Z",
                }
            }
            mock_container.logs.return_value = b"container started\nprocessing..."
            mock_container.stats.return_value = {
                "cpu_stats": {
                    "cpu_usage": {"total_usage": 2000000},
                    "system_cpu_usage": 10000000000,
                    "online_cpus": 4,
                },
                "precpu_stats": {
                    "cpu_usage": {"total_usage": 1000000},
                    "system_cpu_usage": 9000000000,
                },
                "memory_stats": {
                    "usage": 67108864,  # 64 MB
                    "limit": 134217728,  # 128 MB
                },
            }
            mock_docker.return_value.containers.get.return_value = mock_container

            metrics = self.orch.get_status("abc123def456")

        assert isinstance(metrics, ContainerMetrics)
        assert metrics.container_id == "abc123def456"
        assert metrics.status == "running"
        assert metrics.memory_mb > 0  # 64 MB
        assert metrics.memory_mb == pytest.approx(64.0, abs=1.0)
        assert metrics.cpu_percent >= 0
        assert "container started" in metrics.logs

    # ------------------------------------------------------------------
    # test_stop_and_remove
    # ------------------------------------------------------------------
    def test_stop_and_remove(self):
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_docker.return_value.containers.get.return_value = mock_container

            self.orch.stop("abc123def456")

        mock_container.stop.assert_called_once_with(timeout=5)
        mock_container.remove.assert_called_once_with(force=True)

    # ------------------------------------------------------------------
    # test_list_containers_by_tenant
    # ------------------------------------------------------------------
    def test_list_containers_by_tenant(self):
        with patch("docker.from_env") as mock_docker:
            mock_c1 = MagicMock()
            mock_c1.id = "container-001"
            mock_c1.labels = {
                "huggsai.tenant_id": "tenant-001",
                "huggsai.node_id": "node-a",
                "huggsai.journey_id": "journey-x",
            }
            mock_c1.status = "running"
            mock_c1.image.tags = ["huggsai/trigger:latest"]

            mock_c2 = MagicMock()
            mock_c2.id = "container-002"
            mock_c2.labels = {
                "huggsai.tenant_id": "tenant-001",
                "huggsai.node_id": "node-b",
                "huggsai.journey_id": "",
            }
            mock_c2.status = "exited"
            mock_c2.image.tags = ["huggsai/action-crm:latest"]

            mock_docker.return_value.containers.list.return_value = [mock_c1, mock_c2]

            result = self.orch.list_by_tenant("tenant-001")

        assert len(result) == 2
        assert all(isinstance(r, ContainerInfo) for r in result)
        assert result[0].container_id == "container-001"
        assert result[0].status == "running"
        assert result[1].container_id == "container-002"
        assert result[1].status == "exited"

        # Verify filter was passed
        call_kwargs = mock_docker.return_value.containers.list.call_args
        assert call_kwargs.kwargs.get("filters", {}).get("label") == [
            "huggsai.tenant_id=tenant-001"
        ]

    # ------------------------------------------------------------------
    # test_exec_in_container
    # ------------------------------------------------------------------
    def test_exec_in_container(self):
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.exec_run.return_value = (
                0,  # exit_code
                (b"stdout output", b"stderr output"),  # demux=True
            )
            mock_docker.return_value.containers.get.return_value = mock_container

            result = self.orch.exec_in_container("abc123", "cat /tmp/result.json")

        assert isinstance(result, ContainerExecResult)
        assert result.container_id == "abc123"
        assert result.exit_code == 0
        assert result.stdout == "stdout output"
        assert result.stderr == "stderr output"
        assert result.duration_ms >= 0

    # ------------------------------------------------------------------
    # test_get_logs
    # ------------------------------------------------------------------
    def test_get_logs(self):
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.logs.return_value = b"line1\nline2\nline3"
            mock_docker.return_value.containers.get.return_value = mock_container

            logs = self.orch.get_logs("abc123", tail=50)

        assert "line1" in logs
        assert "line3" in logs
        mock_container.logs.assert_called_once_with(tail=50)

    # ------------------------------------------------------------------
    # test_cleanup_journey
    # ------------------------------------------------------------------
    def test_cleanup_journey(self):
        with patch("docker.from_env") as mock_docker:
            mock_c1 = MagicMock()
            mock_c1.id = "c1"
            mock_c2 = MagicMock()
            mock_c2.id = "c2"
            mock_docker.return_value.containers.list.return_value = [mock_c1, mock_c2]

            count = self.orch.cleanup_journey("journey-abc")

        assert count == 2
        mock_c1.stop.assert_called_once_with(timeout=5)
        mock_c1.remove.assert_called_once_with(force=True)
        mock_c2.stop.assert_called_once_with(timeout=5)
        mock_c2.remove.assert_called_once_with(force=True)

        call_kwargs = mock_docker.return_value.containers.list.call_args
        assert call_kwargs.kwargs.get("filters", {}).get("label") == [
            "huggsai.journey_id=journey-abc"
        ]

    # ------------------------------------------------------------------
    # test_spawn_with_journey_id
    # ------------------------------------------------------------------
    def test_spawn_with_journey_id(self):
        config = ContainerConfig(
            image="huggsai/condition:latest",
            tenant_id="tenant-002",
            node_id="node-cond",
            journey_id="journey-xyz",
            memory_limit_mb=256,
            cpu_period=100000,
            cpu_quota=25000,
            env={"NODE_TYPE": "condition"},
            timeout_seconds=60,
        )
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.id = "cond-container-id"
            mock_container.status = "running"
            mock_container.image.tags = ["huggsai/condition:latest"]
            mock_docker.return_value.containers.run.return_value = mock_container

            result = self.orch.spawn(config)

        assert result.container_id == "cond-container-id"
        call_kwargs = mock_docker.return_value.containers.run.call_args
        labels = call_kwargs.kwargs.get("labels", {})
        assert labels["huggsai.journey_id"] == "journey-xyz"
        assert call_kwargs.kwargs.get("mem_limit") == "256m"
