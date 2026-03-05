"""
Pydantic models para o Orchestrator.
Task, TaskResult, TaskType, TaskStatus, OrchestratorResponse.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


class TaskType(str, Enum):
    QUERY = "query"
    AUTOMATION = "automation"
    REPAIR = "repair"
    GENERATION = "generation"
    ANALYSIS = "analysis"


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class Task(BaseModel):
    """Tarefa decomposta pelo TaskDecomposer."""
    id: str = ""
    description: str
    type: TaskType = TaskType.QUERY
    priority: int = Field(default=5, ge=1, le=10)
    required_capabilities: list[str] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    input_data: dict[str, Any] = Field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    assigned_agent: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class TaskResult(BaseModel):
    """Resultado da execucao de uma Task."""
    task_id: str
    success: bool
    output: Any = None
    error: Optional[str] = None
    agent_used: Optional[str] = None
    execution_time_ms: float = 0
    chunks_used: list[str] = Field(default_factory=list)


class OrchestratorResponse(BaseModel):
    """Resposta final do NeuralLinkOrchestrator."""
    answer: str
    tasks: list[Task] = Field(default_factory=list)
    results: list[TaskResult] = Field(default_factory=list)
    rag_results: list[dict[str, Any]] = Field(default_factory=list)
    knowledge_enrichment: dict[str, Any] = Field(default_factory=dict)
    session_id: str = ""
    processing_time_ms: float = 0


# ============================================================
# CRM Models
# ============================================================


class LeadSource(str, Enum):
    TELEGRAM = "telegram"
    EMAIL = "email"
    N8N = "n8n"
    MANUAL = "manual"
    WEBHOOK = "webhook"


class FlowStatus(str, Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class CrmLead(BaseModel):
    """A CRM lead node in the knowledge graph."""
    id: str = Field(default_factory=lambda: f"lead_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    name: str
    email: Optional[str] = None
    company: Optional[str] = None
    trust: float = Field(default=0.5, ge=0.0, le=1.0)
    interaction_count: int = 0
    source_channel: LeadSource = LeadSource.MANUAL
    rag_context_id: Optional[str] = None
    tags: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CrmFlow(BaseModel):
    """A CRM flow (campaign / funnel) node."""
    id: str = Field(default_factory=lambda: f"flow_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    name: str
    objective: str = ""
    n8n_workflow_id: Optional[str] = None
    status: FlowStatus = FlowStatus.DRAFT
    created_at: str = Field(default_factory=lambda: datetime.now().isoformat())


class CrmInteraction(BaseModel):
    """An interaction event between an agent/user and a lead."""
    id: str = Field(default_factory=lambda: f"interaction_{datetime.now().strftime('%Y%m%d%H%M%S')}")
    lead_id: str
    agent_id: Optional[str] = None
    channel: str = "manual"
    action: str = ""
    detail: str = ""
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
