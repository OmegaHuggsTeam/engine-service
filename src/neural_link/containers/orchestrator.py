"""ContainerOrchestrator — Docker SDK wrapper for sandbox containers.

Manages lifecycle of Docker containers used as Journey Builder node sandboxes.
Lazy-initializes docker.from_env() on first use. All containers are labelled
with huggsai.tenant_id, huggsai.node_id, and huggsai.journey_id for filtering.

Usage:
    orch = ContainerOrchestrator()
    info = orch.spawn(ContainerConfig(image="ghcr.io/omegahuggsteam/sandbox-trigger:latest", ...))
    metrics = orch.get_status(info.container_id)
    orch.stop(info.container_id)
"""

import logging
import time

import docker

from .models import (
    ContainerConfig,
    ContainerExecResult,
    ContainerInfo,
    ContainerMetrics,
)

logger = logging.getLogger(__name__)

LABEL_PREFIX = "huggsai"


class ContainerOrchestrator:
    """Manages Docker container lifecycle for Journey Builder nodes."""

    def __init__(self) -> None:
        self._client = None

    @property
    def client(self):
        """Lazy Docker client — only connects on first use."""
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    # ------------------------------------------------------------------
    # spawn
    # ------------------------------------------------------------------
    def spawn(self, config: ContainerConfig) -> ContainerInfo:
        """Create and start a detached container with huggsai labels.

        Args:
            config: Container configuration (image, tenant, node, resources).

        Returns:
            ContainerInfo with the new container's ID and status.
        """
        labels = {
            f"{LABEL_PREFIX}.tenant_id": config.tenant_id,
            f"{LABEL_PREFIX}.node_id": config.node_id,
            f"{LABEL_PREFIX}.journey_id": config.journey_id or "",
        }
        try:
            container = self.client.containers.run(
                image=config.image,
                detach=True,
                labels=labels,
                environment=config.env,
                mem_limit=f"{config.memory_limit_mb}m",
                cpu_period=config.cpu_period,
                cpu_quota=config.cpu_quota,
                network_mode="bridge",
                remove=False,
            )
            logger.info(
                "Container spawned: %s (image=%s, tenant=%s, node=%s)",
                container.id[:12],
                config.image,
                config.tenant_id,
                config.node_id,
            )
            return ContainerInfo(
                container_id=container.id,
                node_id=config.node_id,
                tenant_id=config.tenant_id,
                image=config.image,
                status=container.status,
            )
        except Exception as exc:
            logger.warning("spawn error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # get_status
    # ------------------------------------------------------------------
    def get_status(self, container_id: str) -> ContainerMetrics:
        """Get runtime metrics for a container (memory, CPU, logs).

        Args:
            container_id: Docker container ID.

        Returns:
            ContainerMetrics with current stats.
        """
        try:
            container = self.client.containers.get(container_id)
            stats = container.stats(stream=False)

            # Memory
            mem_stats = stats.get("memory_stats", {})
            mem_usage = mem_stats.get("usage", 0)
            memory_mb = mem_usage / (1024 * 1024)

            # CPU percentage
            cpu_stats = stats.get("cpu_stats", {})
            precpu_stats = stats.get("precpu_stats", {})
            cpu_delta = cpu_stats.get("cpu_usage", {}).get("total_usage", 0) - precpu_stats.get(
                "cpu_usage", {}
            ).get("total_usage", 0)
            system_delta = cpu_stats.get("system_cpu_usage", 0) - precpu_stats.get(
                "system_cpu_usage", 0
            )
            online_cpus = cpu_stats.get("online_cpus", 1)
            cpu_percent = 0.0
            if system_delta > 0 and cpu_delta > 0:
                cpu_percent = (cpu_delta / system_delta) * online_cpus * 100.0

            # State info
            state = container.attrs.get("State", {})
            started_at = state.get("StartedAt")
            finished_at = state.get("FinishedAt")
            exit_code = state.get("ExitCode")

            # Logs (last 100 lines)
            logs = container.logs(tail=100)
            if isinstance(logs, bytes):
                logs = logs.decode("utf-8", errors="replace")

            return ContainerMetrics(
                container_id=container_id,
                status=container.status,
                memory_mb=round(memory_mb, 2),
                cpu_percent=round(cpu_percent, 2),
                started_at=started_at,
                finished_at=finished_at,
                exit_code=exit_code,
                logs=logs,
            )
        except Exception as exc:
            logger.warning("get_status error for %s: %s", container_id, exc)
            raise

    # ------------------------------------------------------------------
    # stop
    # ------------------------------------------------------------------
    def stop(self, container_id: str) -> None:
        """Stop and remove a container.

        Args:
            container_id: Docker container ID to stop and remove.
        """
        try:
            container = self.client.containers.get(container_id)
            container.stop(timeout=5)
            container.remove(force=True)
            logger.info("Container stopped and removed: %s", container_id[:12])
        except Exception as exc:
            logger.warning("stop error for %s: %s", container_id, exc)
            raise

    # ------------------------------------------------------------------
    # exec_in_container
    # ------------------------------------------------------------------
    def exec_in_container(self, container_id: str, cmd: str) -> ContainerExecResult:
        """Execute a command inside a running container.

        Args:
            container_id: Docker container ID.
            cmd: Shell command to execute.

        Returns:
            ContainerExecResult with exit code, stdout, stderr, and duration.
        """
        try:
            container = self.client.containers.get(container_id)
            t0 = time.perf_counter()
            exit_code, output = container.exec_run(cmd, demux=True)
            duration_ms = (time.perf_counter() - t0) * 1000

            stdout = ""
            stderr = ""
            if output:
                if isinstance(output, tuple):
                    stdout = (output[0] or b"").decode("utf-8", errors="replace")
                    stderr = (output[1] or b"").decode("utf-8", errors="replace")
                elif isinstance(output, bytes):
                    stdout = output.decode("utf-8", errors="replace")

            return ContainerExecResult(
                container_id=container_id,
                exit_code=exit_code,
                stdout=stdout,
                stderr=stderr,
                duration_ms=round(duration_ms, 2),
            )
        except Exception as exc:
            logger.warning("exec_in_container error for %s: %s", container_id, exc)
            raise

    # ------------------------------------------------------------------
    # get_logs
    # ------------------------------------------------------------------
    def get_logs(self, container_id: str, tail: int = 100) -> str:
        """Get recent logs from a container.

        Args:
            container_id: Docker container ID.
            tail: Number of log lines to retrieve.

        Returns:
            Log output as a string.
        """
        try:
            container = self.client.containers.get(container_id)
            logs = container.logs(tail=tail)
            if isinstance(logs, bytes):
                logs = logs.decode("utf-8", errors="replace")
            return logs
        except Exception as exc:
            logger.warning("get_logs error for %s: %s", container_id, exc)
            raise

    # ------------------------------------------------------------------
    # list_by_tenant
    # ------------------------------------------------------------------
    def list_by_tenant(self, tenant_id: str) -> list[ContainerInfo]:
        """List all containers for a given tenant.

        Args:
            tenant_id: Tenant identifier to filter by.

        Returns:
            List of ContainerInfo for matching containers.
        """
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": [f"{LABEL_PREFIX}.tenant_id={tenant_id}"]},
            )
            results = []
            for c in containers:
                labels = c.labels or {}
                image_name = ""
                if c.image and c.image.tags:
                    image_name = c.image.tags[0]
                results.append(
                    ContainerInfo(
                        container_id=c.id,
                        node_id=labels.get(f"{LABEL_PREFIX}.node_id", ""),
                        tenant_id=labels.get(f"{LABEL_PREFIX}.tenant_id", ""),
                        image=image_name,
                        status=c.status,
                    )
                )
            return results
        except Exception as exc:
            logger.warning("list_by_tenant error: %s", exc)
            raise

    # ------------------------------------------------------------------
    # cleanup_journey
    # ------------------------------------------------------------------
    def cleanup_journey(self, journey_id: str) -> int:
        """Stop and remove all containers for a journey.

        Args:
            journey_id: Journey identifier to filter by.

        Returns:
            Number of containers cleaned up.
        """
        try:
            containers = self.client.containers.list(
                all=True,
                filters={"label": [f"{LABEL_PREFIX}.journey_id={journey_id}"]},
            )
            count = 0
            for c in containers:
                try:
                    c.stop(timeout=5)
                    c.remove(force=True)
                    count += 1
                    logger.info(
                        "Cleaned up container %s for journey %s",
                        c.id[:12],
                        journey_id,
                    )
                except Exception as exc:
                    logger.warning("cleanup_journey: failed to remove %s: %s", c.id[:12], exc)
            return count
        except Exception as exc:
            logger.warning("cleanup_journey error: %s", exc)
            raise
