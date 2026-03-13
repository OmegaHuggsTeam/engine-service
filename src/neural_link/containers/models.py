"""Pydantic v2 models for the Container Orchestrator module.

Defines configuration, info, metrics, and execution result models
used by ContainerOrchestrator and the Sovereign Gateway API endpoints.
"""

from pydantic import BaseModel, Field


class ContainerConfig(BaseModel):
    """Configuration for spawning a new container."""

    image: str
    tenant_id: str
    node_id: str
    journey_id: str | None = None
    memory_limit_mb: int = 128
    cpu_period: int = 100000
    cpu_quota: int = 50000  # 50% of one core
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30


class ContainerInfo(BaseModel):
    """Basic container information returned after spawn or list."""

    container_id: str
    node_id: str
    tenant_id: str
    image: str
    status: str  # created | running | exited | paused | dead
    started_at: str | None = None


class ContainerMetrics(BaseModel):
    """Runtime metrics for a container (status, memory, CPU, logs)."""

    container_id: str
    status: str
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    logs: str = ""


class ContainerExecResult(BaseModel):
    """Result of executing a command inside a container."""

    container_id: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
