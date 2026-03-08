"""Workflow Registry — CRUD API for WorkflowProduct management.

FastAPI APIRouter providing REST endpoints for creating, listing, updating,
deleting, deploying, and running WorkflowProduct entities.

Uses an in-memory dict store (will be swapped for Redis/Postgres later).

Mount:
    app.include_router(router, prefix="/api/v1")
"""

import importlib
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from src.neural_link.agents.content.models import Execution, WorkflowProduct

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# In-memory store (module-level, reset via _workflow_store.clear() in tests)
# ---------------------------------------------------------------------------

_workflow_store: dict[str, dict[str, Any]] = {}

# ---------------------------------------------------------------------------
# Agent registry — maps slug to module path for dynamic import
# ---------------------------------------------------------------------------

AGENT_REGISTRY: dict[str, str] = {
    # Example: "researcher": "src.neural_link.agents.content.researcher",
    # Agents will be registered here as they are implemented.
}

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------


class WorkflowCreateRequest(BaseModel):
    """Request body for creating a new WorkflowProduct."""

    id: str
    name: str
    description: str
    category: str
    n8n_workflow_json: dict[str, Any] = Field(default_factory=dict)
    config: dict[str, Any] = Field(default_factory=dict)
    schedule: Optional[str] = None
    agents_used: list[str] = Field(default_factory=list)
    webhook_urls: list[str] = Field(default_factory=list)
    brand_voice_file: Optional[str] = None
    cost_per_run: float = 0.0


class WorkflowUpdateRequest(BaseModel):
    """Request body for partial update of a WorkflowProduct.

    All fields are optional — only non-None fields are applied.
    """

    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    n8n_workflow_json: Optional[dict[str, Any]] = None
    config: Optional[dict[str, Any]] = None
    schedule: Optional[str] = None
    agents_used: Optional[list[str]] = None
    webhook_urls: Optional[list[str]] = None
    brand_voice_file: Optional[str] = None
    cost_per_run: Optional[float] = None
    status: Optional[str] = None


class DeployResponse(BaseModel):
    """Response from the deploy endpoint (stub)."""

    workflow_id: str
    n8n_workflow_id: str
    status: str
    deployed_at: str


class AgentExecuteRequest(BaseModel):
    """Request body for executing an agent by slug."""

    input: Any = None
    context: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    """Timezone-aware UTC now."""
    return datetime.now(timezone.utc)


def _get_workflow_or_404(workflow_id: str) -> dict[str, Any]:
    """Retrieve a workflow from the store or raise 404."""
    if workflow_id not in _workflow_store:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found")
    return _workflow_store[workflow_id]


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(tags=["workflows"])


# --- Create ---


@router.post("/workflows", status_code=201)
def create_workflow(payload: WorkflowCreateRequest) -> dict[str, Any]:
    """Create a new WorkflowProduct."""
    if payload.id in _workflow_store:
        raise HTTPException(status_code=409, detail=f"Workflow '{payload.id}' already exists")

    now = _utcnow()
    workflow = WorkflowProduct(
        id=payload.id,
        name=payload.name,
        description=payload.description,
        category=payload.category,
        n8n_workflow_json=payload.n8n_workflow_json,
        config=payload.config,
        schedule=payload.schedule,
        agents_used=payload.agents_used,
        webhook_urls=payload.webhook_urls,
        brand_voice_file=payload.brand_voice_file,
        cost_per_run=payload.cost_per_run,
        created_at=now,
        updated_at=now,
    )
    _workflow_store[payload.id] = workflow.model_dump(mode="json")
    return _workflow_store[payload.id]


# --- List ---


@router.get("/workflows")
def list_workflows(category: Optional[str] = Query(None)) -> list[dict[str, Any]]:
    """List all workflow products, optionally filtered by category."""
    workflows = list(_workflow_store.values())
    if category is not None:
        workflows = [w for w in workflows if w.get("category") == category]
    return workflows


# --- Search n8n templates ---


@router.get("/workflows/templates")
def search_templates(q: Optional[str] = Query(None)) -> list[dict[str, Any]]:
    """Search 4700 n8n templates via RAG.

    Returns empty list if RAG service is unavailable.
    """
    try:
        # Future: integrate with ChromaDB RAG for n8n template search
        # from src.neural_link.rag.search import search_n8n_templates
        # return search_n8n_templates(q, limit=20)
        return []
    except Exception:
        logger.warning("RAG template search failed, returning empty list")
        return []


# --- Get by ID ---


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> dict[str, Any]:
    """Get a single workflow product by ID."""
    return _get_workflow_or_404(workflow_id)


# --- Update (partial) ---


@router.put("/workflows/{workflow_id}")
def update_workflow(workflow_id: str, payload: WorkflowUpdateRequest) -> dict[str, Any]:
    """Partial update — only non-None fields are applied."""
    existing = _get_workflow_or_404(workflow_id)

    updates = payload.model_dump(exclude_none=True)
    existing.update(updates)
    existing["updated_at"] = _utcnow().isoformat()

    _workflow_store[workflow_id] = existing
    return existing


# --- Delete (soft) ---


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str) -> dict[str, Any]:
    """Soft delete — sets status to 'paused'."""
    existing = _get_workflow_or_404(workflow_id)
    existing["status"] = "paused"
    existing["updated_at"] = _utcnow().isoformat()
    _workflow_store[workflow_id] = existing
    return existing


# --- Deploy (stub) ---


@router.post("/workflows/{workflow_id}/deploy")
def deploy_workflow(workflow_id: str) -> dict[str, Any]:
    """Deploy workflow to n8n (stub — returns mock response)."""
    existing = _get_workflow_or_404(workflow_id)

    existing["status"] = "active"
    existing["updated_at"] = _utcnow().isoformat()
    _workflow_store[workflow_id] = existing

    return {
        "workflow_id": workflow_id,
        "n8n_workflow_id": f"n8n-{uuid.uuid4().hex[:8]}",
        "status": "deployed",
        "deployed_at": _utcnow().isoformat(),
    }


# --- Run (manual trigger) ---


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str) -> dict[str, Any]:
    """Manual trigger — creates an Execution record."""
    _get_workflow_or_404(workflow_id)

    execution = Execution(
        id=f"exec-{uuid.uuid4().hex[:8]}",
        workflow_product_id=workflow_id,
        status="running",
        cost_actual=0.0,
    )
    return execution.model_dump(mode="json")


# --- Execute agent by slug ---


@router.post("/agents/{agent_slug}/execute")
def execute_agent(agent_slug: str, payload: AgentExecuteRequest = None) -> dict[str, Any]:
    """Execute a specific agent by slug via dynamic import from AGENT_REGISTRY."""
    if agent_slug not in AGENT_REGISTRY:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{agent_slug}' not found in registry",
        )

    module_path = AGENT_REGISTRY[agent_slug]
    try:
        module = importlib.import_module(module_path)
        agent_fn = getattr(module, "execute", None)
        if agent_fn is None:
            raise HTTPException(
                status_code=500,
                detail=f"Agent module '{module_path}' has no 'execute' function",
            )

        result = agent_fn(
            input_data=payload.input if payload else None,
            context=payload.context if payload else {},
        )
        return {"agent": agent_slug, "status": "completed", "result": result}
    except ImportError as exc:
        logger.error("Failed to import agent '%s' from '%s': %s", agent_slug, module_path, exc)
        raise HTTPException(
            status_code=500,
            detail=f"Failed to load agent '{agent_slug}': {exc}",
        ) from exc
