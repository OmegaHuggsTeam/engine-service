"""Engine SDK — Python client for the Engine Service Sovereign Gateway.

Usage (async)::

    from engine_sdk import EngineClient

    async with EngineClient(base_url="http://localhost:8766") as client:
        results = await client.rag.search("revenue Q4")
        agents = await client.agents.list()
        stats = await client.telemetry.pipeline_stats()

Usage (sync)::

    from engine_sdk import EngineSyncClient

    client = EngineSyncClient()
    results = client.rag.search("revenue Q4")
    client.close()
"""

from .client import EngineClient
from .sync_client import EngineSyncClient
from .exceptions import (
    AuthenticationError,
    ConnectionError,
    EngineError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)
from .models import (
    AgentInfo,
    AgentResponse,
    ClusterHealth,
    ContainerExecResult,
    ContainerInfo,
    ContainerStatus,
    CrmFlow,
    CrmLead,
    CrmLeadScore,
    CrmStats,
    ErrorResolution,
    FlowComposeResult,
    FlowDeployResult,
    GraphEdge,
    GraphNode,
    GraphSubset,
    IngestResult,
    KpiRecommendation,
    PipelineStats,
    RAGResult,
)

__all__ = [
    # Clients
    "EngineClient",
    "EngineSyncClient",
    # Exceptions
    "EngineError",
    "AuthenticationError",
    "ConnectionError",
    "NotFoundError",
    "ServerError",
    "TimeoutError",
    "ValidationError",
    # Models
    "AgentInfo",
    "AgentResponse",
    "ClusterHealth",
    "ContainerExecResult",
    "ContainerInfo",
    "ContainerStatus",
    "CrmFlow",
    "CrmLead",
    "CrmLeadScore",
    "CrmStats",
    "ErrorResolution",
    "FlowComposeResult",
    "FlowDeployResult",
    "GraphEdge",
    "GraphNode",
    "GraphSubset",
    "IngestResult",
    "KpiRecommendation",
    "PipelineStats",
    "RAGResult",
]

__version__ = "0.1.0"
