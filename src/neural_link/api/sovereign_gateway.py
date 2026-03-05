"""Sovereign AI Command Center — API Gateway.

FastAPI router at /api/v1 providing REST + WebSocket endpoints for the
Next.js frontend. Wraps UnifiedInterface, TelemetryHub, and GraphManager
without replacing the existing webhook_listener (:8765).

Mount point: port 8766
CORS: localhost:3000 (Next.js dev server)

Usage standalone:
    python -m src.neural_link.api.sovereign_gateway

Usage as sub-app:
    from src.neural_link.api.sovereign_gateway import app
"""

import asyncio
import copy
import json
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.routing import APIRouter
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Pydantic response models
# ---------------------------------------------------------------------------


class AgentStatus(BaseModel):
    id: str
    name: str
    type: str
    status: str = "active"
    success_rate: float | None = None


class TaskSubmission(BaseModel):
    query: str
    context: dict[str, Any] | None = None


class RAGResult(BaseModel):
    content: str = ""
    source: str = ""
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class GraphNode(BaseModel):
    id: str
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSubset(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class ServiceInfo(BaseModel):
    service: str
    node_count: int = 0
    neighbors: list[str] = Field(default_factory=list)


class ClusterHealth(BaseModel):
    timestamp: str
    services: dict[str, Any]
    summary: dict[str, int]


class FlowComposeRequest(BaseModel):
    objective: str
    context: dict[str, Any] | None = None


class FlowComposeResult(BaseModel):
    objective: str
    workflow: dict[str, Any] = Field(default_factory=dict)
    nodes: list[str] = Field(default_factory=list)
    status: str = "composed"


class FlowDeployRequest(BaseModel):
    """Workflow JSON para injetar no n8n e ativar."""
    workflow: dict[str, Any]


class FlowDeployResult(BaseModel):
    success: bool = False
    message: str = ""
    workflow_id: str | None = None


# -- Jitbit Macro -----------------------------------------------------------

class JitbitErrorBody(BaseModel):
    """Payload do webhook POST /api/v1/jitbit/error (n8n / macro)."""
    macro: str = ""
    error: str = ""
    step: str = ""
    line: int | None = None


# -- CRM models -------------------------------------------------------------

class CrmLeadCreate(BaseModel):
    name: str
    email: str | None = None
    company: str | None = None
    source_channel: str = "manual"
    tags: list[str] = Field(default_factory=list)


class CrmLeadUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    company: str | None = None
    tags: list[str] | None = None
    trust: float | None = None


class CrmLeadResponse(BaseModel):
    id: str
    name: str
    email: str | None = None
    company: str | None = None
    trust: float = 0.5
    interaction_count: int = 0
    source_channel: str = "manual"
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class CrmLeadScoreResponse(BaseModel):
    lead_id: str
    trust: float
    interaction_count: int
    last_interaction: str | None
    flow_count: int
    interaction_score: float
    recency_score: float
    flow_score: float


class CrmFlowCreate(BaseModel):
    name: str
    objective: str = ""
    n8n_workflow_id: str | None = None


class CrmFlowUpdate(BaseModel):
    name: str | None = None
    objective: str | None = None
    status: str | None = None


class CrmFlowResponse(BaseModel):
    id: str
    name: str
    objective: str = ""
    n8n_workflow_id: str | None = None
    status: str = "draft"
    lead_count: int = 0
    created_at: str = ""


class CrmInteractionCreate(BaseModel):
    lead_id: str
    agent_id: str | None = None
    channel: str = "manual"
    action: str = ""
    detail: str = ""


class CrmGraphResponse(BaseModel):
    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


class CrmStatsResponse(BaseModel):
    total_leads: int = 0
    total_flows: int = 0
    total_interactions: int = 0
    avg_trust: float = 0.0


# -- KPI models -------------------------------------------------------------

class KpiToolReviewSubmit(BaseModel):
    tool_name: str
    sprint_date: str
    score_correto: float = Field(ge=0, le=100)
    score_completo: float = Field(ge=0, le=100)
    score_qualidade: float = Field(ge=0, le=100)
    deliverables_done: int = 0
    deliverables_total: int = 0
    issues_critical: int = 0
    issues_medium: int = 0
    issues_low: int = 0
    reviewer: str = "claude_code"
    notes: str = ""


class KpiRecommendResponse(BaseModel):
    model: str = ""
    avg_quality: float = 0.0
    total_cost: float = 0.0
    total_requests: int = 0
    cost_per_quality_point: float = 0.0
    reason: str = ""


# ---------------------------------------------------------------------------
# Service layer (lazy init, graceful fallback)
# ---------------------------------------------------------------------------


@dataclass
class _Services:
    """Lazy-initialized backend services."""
    _interface: Any = None
    _telemetry_hub: Any = None
    _graph: Any = None
    _model_benchmark: Any = None
    _tool_scorecard: Any = None
    _cost_quality_analyzer: Any = None
    _metrics_timeseries: Any = None
    _kpi_provider: Any = None
    _initialized: bool = False

    def ensure_initialized(self) -> None:
        if self._initialized:
            return
        self._initialized = True

        # UnifiedInterface
        try:
            from .interface import UnifiedInterface
            self._interface = UnifiedInterface.get_instance()
            logger.info("Sovereign gateway: UnifiedInterface connected")
        except Exception as exc:
            logger.warning("UnifiedInterface unavailable: %s", exc)

        # TelemetryHub
        try:
            from ..telemetry.provider import TelemetryHub
            self._telemetry_hub = TelemetryHub()
            logger.info("Sovereign gateway: TelemetryHub created")
        except Exception as exc:
            logger.warning("TelemetryHub unavailable: %s", exc)

        # GraphManager
        try:
            from ..graph.manager import GraphManager
            gm = GraphManager.from_env()
            if gm.verify_connectivity():
                self._graph = gm
                logger.info("Sovereign gateway: GraphManager connected")
            else:
                logger.warning("Neo4j connectivity check failed")
        except Exception as exc:
            logger.warning("GraphManager unavailable: %s", exc)

        # KPI subsystems
        try:
            from ..telemetry.model_benchmark import ModelBenchmark
            self._model_benchmark = ModelBenchmark(graph_manager=self._graph)
            from ..telemetry.tool_scorecard import ToolScorecard
            self._tool_scorecard = ToolScorecard(graph_manager=self._graph)
            from ..telemetry.cost_quality_analyzer import CostQualityAnalyzer
            self._cost_quality_analyzer = CostQualityAnalyzer(graph_manager=self._graph)
            from ..telemetry.metrics_timeseries import MetricsTimeSeries
            self._metrics_timeseries = MetricsTimeSeries(graph_manager=self._graph)
            from ..telemetry.kpi_provider import KpiProvider
            self._kpi_provider = KpiProvider()
            logger.info("Sovereign gateway: KPI subsystems initialized")
        except Exception as exc:
            logger.warning("KPI subsystems init failed: %s", exc)

    @property
    def interface(self):
        self.ensure_initialized()
        return self._interface

    @property
    def telemetry_hub(self):
        self.ensure_initialized()
        return self._telemetry_hub

    @property
    def graph(self):
        self.ensure_initialized()
        return self._graph

    @property
    def model_benchmark(self):
        self.ensure_initialized()
        return self._model_benchmark

    @property
    def tool_scorecard(self):
        self.ensure_initialized()
        return self._tool_scorecard

    @property
    def cost_quality_analyzer(self):
        self.ensure_initialized()
        return self._cost_quality_analyzer

    @property
    def metrics_timeseries(self):
        self.ensure_initialized()
        return self._metrics_timeseries

    @property
    def kpi_provider(self):
        self.ensure_initialized()
        return self._kpi_provider


_svc = _Services()

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------


class ConnectionManager:
    """Thread-safe WebSocket broadcast manager."""

    def __init__(self) -> None:
        self._channels: dict[str, set[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, channel: str, ws: WebSocket) -> None:
        await ws.accept()
        async with self._lock:
            self._channels.setdefault(channel, set()).add(ws)
        logger.debug("WS connect: %s (total: %d)", channel, len(self._channels.get(channel, [])))

    async def disconnect(self, channel: str, ws: WebSocket) -> None:
        async with self._lock:
            conns = self._channels.get(channel)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self._channels[channel]

    async def broadcast(self, channel: str, data: dict | list) -> None:
        async with self._lock:
            conns = list(self._channels.get(channel, []))
        payload = json.dumps(data, default=str)
        dead: list[WebSocket] = []
        for ws in conns:
            try:
                await ws.send_text(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.disconnect(channel, ws)

    def channel_count(self, channel: str) -> int:
        return len(self._channels.get(channel, set()))


_ws_manager = ConnectionManager()

# ---------------------------------------------------------------------------
# Background tasks
# ---------------------------------------------------------------------------

_bg_tasks: list[asyncio.Task] = []


async def _agent_health_loop() -> None:
    """Broadcast agent status every 5 seconds."""
    while True:
        try:
            if _ws_manager.channel_count("agent-health") > 0 and _svc.interface:
                statuses = _svc.interface.get_agent_status()
                await _ws_manager.broadcast("agent-health", statuses)
        except Exception as exc:
            logger.debug("Agent health broadcast error: %s", exc)
        await asyncio.sleep(5)


async def _telemetry_loop() -> None:
    """Poll TelemetryHub and broadcast events."""
    while True:
        try:
            if _ws_manager.channel_count("telemetry") > 0 and _svc.telemetry_hub:
                events = _svc.telemetry_hub.poll_all()
                if events:
                    payload = [
                        {
                            "event_type": e.event_type.value if hasattr(e.event_type, "value") else str(e.event_type),
                            "source": e.source,
                            "message": e.message,
                            "timestamp": e.timestamp,
                            "data": e.data,
                        }
                        for e in events
                    ]
                    await _ws_manager.broadcast("telemetry", payload)
        except Exception as exc:
            logger.debug("Telemetry broadcast error: %s", exc)
        await asyncio.sleep(2)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/v1", tags=["sovereign"])


# -- Agents ------------------------------------------------------------------

@router.get("/agents", response_model=list[AgentStatus])
async def list_agents():
    """List all 19 agents with status and performance metrics."""
    if not _svc.interface:
        return []
    rows = _svc.interface.get_agent_status()
    if not rows:
        # Graph has no Agent nodes yet — fall back to static registry
        try:
            from ..orchestrator.agent_selector import AGENT_REGISTRY
            rows = [
                {"id": aid, "name": info["name"], "type": info["type"],
                 "status": "active", "success_rate": None}
                for aid, info in AGENT_REGISTRY.items()
            ]
        except ImportError:
            pass
    return [AgentStatus(**r) for r in rows]


@router.get("/agents/{agent_id}/history")
async def agent_history(agent_id: str, limit: int = Query(default=20, le=100)):
    """Task history for a specific agent."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(
            "MATCH (t:Task)-[:ASSIGNED_TO]->(a:Agent {id: $agent_id}) "
            "RETURN t ORDER BY t.created_at DESC LIMIT $limit",
            {"agent_id": agent_id, "limit": limit},
        )
        return rows
    except Exception as exc:
        logger.warning("agent_history error: %s", exc)
        return []


# -- Tasks -------------------------------------------------------------------

@router.post("/tasks")
async def submit_task(body: TaskSubmission):
    """Submit a task to the Neural Link orchestrator."""
    if not _svc.interface:
        return {"answer": "Orchestrator not available", "error": True}
    result = _svc.interface.process(body.query, context=body.context)

    # Broadcast flow event if we have subscribers
    if _ws_manager.channel_count("flow-events") > 0:
        await _ws_manager.broadcast("flow-events", {
            "type": "task_submitted",
            "query": body.query,
            "result_preview": result.get("answer", "")[:200],
        })

    return result


@router.get("/tasks/recent")
async def recent_tasks(limit: int = Query(default=20, le=100)):
    """Get recent tasks from the graph."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        return _svc.graph.execute_read(q.GET_RECENT_TASKS, {"limit": limit})
    except Exception as exc:
        logger.warning("recent_tasks error: %s", exc)
        return []


# -- RAG ---------------------------------------------------------------------

@router.get("/rag/search")
async def rag_search(q: str = Query(..., min_length=1), top_k: int = Query(default=10, le=50)):
    """Hybrid RAG search across chunks and concepts."""
    if not _svc.interface:
        return []
    return _svc.interface.search(q, top_k=top_k)


# -- Graph -------------------------------------------------------------------

@router.get("/graph/explore", response_model=GraphSubset)
async def graph_explore(
    center: str = Query(..., description="Node ID to explore from"),
    depth: int = Query(default=2, ge=1, le=4),
):
    """Return a subgraph centered on a node, up to N hops deep."""
    if not _svc.graph:
        return GraphSubset()
    try:
        query = (
            "MATCH path = (start {id: $center})-[*1..$depth]-(connected) "
            "UNWIND nodes(path) AS n "
            "UNWIND relationships(path) AS r "
            "WITH collect(DISTINCT n) AS ns, collect(DISTINCT r) AS rs "
            "RETURN ns, rs"
        )
        rows = _svc.graph.execute_read(query, {"center": center, "depth": depth})
        if not rows:
            return GraphSubset()

        row = rows[0]
        nodes = []
        for n in row.get("ns", []):
            nodes.append(GraphNode(
                id=n.get("id", str(n.get("elementId", ""))),
                labels=list(n.get("labels", n.get("_labels", []))),
                properties={k: v for k, v in n.items() if k not in ("labels", "_labels", "elementId")},
            ))

        edges = []
        for r in row.get("rs", []):
            edges.append(GraphEdge(
                source=str(r.get("startNodeElementId", "")),
                target=str(r.get("endNodeElementId", "")),
                type=r.get("type", ""),
                properties=dict(r) if isinstance(r, dict) else {},
            ))

        return GraphSubset(nodes=nodes, edges=edges)
    except Exception as exc:
        logger.warning("graph_explore error: %s", exc)
        return GraphSubset()


@router.get("/graph/services", response_model=list[ServiceInfo])
async def graph_services():
    """All Service nodes from GraphSynergy with neighbor counts."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_ALL_SERVICES)
        services = []
        for row in rows:
            name = row.get("service", "")
            neighbors_rows = _svc.graph.execute_read(
                q.GET_SERVICE_NEIGHBORS, {"service_name": name}
            )
            neighbor_names = sorted({r.get("connected_service", "") for r in neighbors_rows if r.get("connected_service")})
            services.append(ServiceInfo(
                service=name,
                node_count=row.get("node_count", 0),
                neighbors=neighbor_names,
            ))
        return services
    except Exception as exc:
        logger.warning("graph_services error: %s", exc)
        return []


# -- Cluster -----------------------------------------------------------------

@router.get("/cluster/health", response_model=ClusterHealth)
async def cluster_health():
    """Cluster health check (ChromaDB, Neo4j, Evidence, n8n, Tailscale)."""
    try:
        import sys
        from pathlib import Path
        tools_dir = Path(__file__).resolve().parent.parent.parent.parent / "tools"
        sys.path.insert(0, str(tools_dir.parent))
        from tools.cluster_health import collect_cluster_health
        result = collect_cluster_health()
        return ClusterHealth(**result)
    except Exception as exc:
        logger.warning("cluster_health error: %s", exc)
        return ClusterHealth(
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
            services={},
            summary={"total": 0, "ok": 0, "fail": 0, "skip": 0},
        )


# -- Jitbit Macro -----------------------------------------------------------

# Estado in-memory para status do macro (last_error, last_activity)
_jitbit_state: dict[str, Any] = {
    "last_error": None,
    "last_activity": None,
    "stale_threshold_seconds": 300,
}


def _jitbit_log_path() -> "Path":
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent.parent
    return root / "logs" / "mission_zero.log"


@router.get("/jitbit/status")
async def jitbit_status():
    """
    Retorna se o macro está rodando ou travado (baseado no timestamp do último log).
    Se last_error estiver preenchido (via POST /jitbit/error), status = stuck.
    Caso contrário, usa mtime do logs/mission_zero.log: recente = running.
    """
    now = time.time()
    last_error = _jitbit_state.get("last_error")
    if last_error:
        return {
            "status": "stuck",
            "last_error": last_error,
            "last_activity": _jitbit_state.get("last_activity"),
        }

    log_path = _jitbit_log_path()
    threshold = _jitbit_state.get("stale_threshold_seconds", 300)
    if log_path.exists():
        mtime = log_path.stat().st_mtime
        age = now - mtime
        if age < threshold:
            return {
                "status": "running",
                "last_error": None,
                "last_activity": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(mtime)),
            }

    return {
        "status": "idle",
        "last_error": None,
        "last_activity": _jitbit_state.get("last_activity"),
    }


@router.post("/jitbit/error")
async def jitbit_error(body: JitbitErrorBody):
    """
    Webhook para quando o macro falha (n8n / SpecialistAgent).
    Payload: { macro, error, step, line }.
    Usado pelo JourneyCanvas para mostrar onde o macro parou.
    """
    _jitbit_state["last_error"] = {
        "macro": body.macro,
        "error": body.error,
        "step": body.step,
        "line": body.line,
    }
    _jitbit_state["last_activity"] = time.strftime("%Y-%m-%dT%H:%M:%S")  # noqa: DTZ005
    logger.info("Jitbit error received: %s @ %s (line %s)", body.step, body.error, body.line)

    # Broadcast para JourneyCanvas
    await _ws_manager.broadcast("journey-events", {
        "type": "jitbit_error",
        "payload": _jitbit_state["last_error"],
        "timestamp": _jitbit_state["last_activity"],
    })

    return {"ok": True}


@router.post("/jitbit/heal")
async def jitbit_heal():
    """
    Dispara tools/sanitize_macro_env.py via subprocess para resetar o ambiente.
    Após sucesso, broadcast em journey-events para atualizar o JourneyCanvas.
    """
    import subprocess
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent.parent.parent
    script = root / "tools" / "sanitize_macro_env.py"
    if not script.exists():
        return {"ok": False, "message": "sanitize_macro_env.py não encontrado"}

    try:
        proc = subprocess.run(
            [str(script.resolve())],
            cwd=str(root),
            capture_output=True,
            text=True,
            timeout=30,
        )
        if proc.returncode != 0:
            return {"ok": False, "message": proc.stderr or f"Exit code {proc.returncode}"}

        # Limpa last_error e atualiza última atividade
        _jitbit_state["last_error"] = None
        _jitbit_state["last_activity"] = time.strftime("%Y-%m-%dT%H:%M:%S")  # noqa: DTZ005

        # Broadcast para JourneyCanvas
        await _ws_manager.broadcast("journey-events", {
            "type": "heal_completed",
            "payload": {"status": "active"},
            "timestamp": _jitbit_state["last_activity"],
        })

        return {"ok": True, "message": "Sanitização concluída."}
    except subprocess.TimeoutExpired:
        return {"ok": False, "message": "Timeout ao executar sanitize_macro_env.py"}
    except Exception as exc:
        logger.exception("jitbit_heal error: %s", exc)
        return {"ok": False, "message": str(exc)}


# -- Flows -------------------------------------------------------------------

@router.post("/flows/compose", response_model=FlowComposeResult)
async def compose_flow(body: FlowComposeRequest):
    """Natural language → n8n workflow composition."""
    # Placeholder: ComposerAgent not yet implemented.
    # Returns structured stub for frontend development.
    result = FlowComposeResult(
        objective=body.objective,
        workflow={"nodes": [], "connections": {}},
        nodes=[],
        status="stub",
    )

    if _ws_manager.channel_count("flow-events") > 0:
        await _ws_manager.broadcast("flow-events", {
            "type": "flow_composed",
            "objective": body.objective,
            "status": result.status,
        })

    return result


@router.post("/flows/deploy", response_model=FlowDeployResult)
async def deploy_flow(body: FlowDeployRequest):
    """
    Injeta workflow JSON na API do n8n e ativa.
    Usado pelo bot Telegram ao clicar em 'Deploy no n8n'.
    """
    import os
    import httpx

    workflow = body.workflow
    if not workflow or "nodes" not in workflow:
        return FlowDeployResult(success=False, message="Workflow inválido: falta 'nodes'")

    api_url = os.environ.get("N8N_API_URL", "http://localhost:5678").rstrip("/")
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        api_url = api_url or "http://n8n:5678"
    api_url = api_url or "http://localhost:5678"
    url = f"{api_url}/api/v1/workflows"
    api_key = os.environ.get("N8N_API_KEY", "")

    if not api_key:
        return FlowDeployResult(success=False, message="N8N_API_KEY não configurado")

    # Remove credenciais do import (configurar no n8n)
    payload = {
        "name": workflow.get("name", "Imported Workflow"),
        "nodes": copy.deepcopy(workflow.get("nodes", [])),
        "connections": workflow.get("connections", {}),
        "settings": workflow.get("settings", {}),
    }
    for node in payload.get("nodes", []):
        node.pop("credentials", None)

    headers = {"Content-Type": "application/json", "X-N8N-API-KEY": api_key}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload, headers=headers)
        if r.status_code in (200, 201):
            data = r.json()
            wf_id = str(data.get("id", data.get("data", {}).get("id", "")))
            # Ativar workflow
            patch_url = f"{url}/{wf_id}"
            async with httpx.AsyncClient(timeout=15) as client:
                await client.patch(patch_url, json={"active": True}, headers=headers)
            # CRM: if workflow metadata contains crm_flow_id, activate the Flow
            crm_flow_id = workflow.get("crm_flow_id")
            if crm_flow_id and _svc.graph:
                try:
                    from ..graph import queries as q
                    _svc.graph.execute_write(q.UPDATE_FLOW_STATUS, {
                        "flow_id": crm_flow_id,
                        "status": "active",
                    })
                    _broadcast_crm_event("flow_status_changed", {
                        "id": crm_flow_id, "status": "active",
                    })
                except Exception:
                    pass
            return FlowDeployResult(success=True, message=f"Workflow importado e ativado", workflow_id=wf_id)
        return FlowDeployResult(success=False, message=f"n8n retornou {r.status_code}: {r.text[:150]}")
    except Exception as exc:
        logger.exception("Deploy n8n falhou: %s", exc)
        return FlowDeployResult(success=False, message=str(exc))


# -- CRM helpers --------------------------------------------------------------

def _broadcast_crm_event(event_type: str, payload: dict) -> None:
    """Schedule a CRM event broadcast (fire-and-forget)."""
    import time as _time
    event = {"type": event_type, "payload": payload, "timestamp": _time.strftime("%Y-%m-%dT%H:%M:%S")}
    asyncio.ensure_future(_ws_manager.broadcast("crm-events", event))


def _recency_decay(timestamp_str: str | None) -> float:
    """
    Calculate recency score with exponential decay (30-day halflife).
    Returns 1.0 for recent interactions, decays to 0.5 after 30 days.
    """
    if not timestamp_str:
        return 0.0
    try:
        from datetime import datetime
        import math
        
        # Parse timestamp
        ts = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
        now = datetime.now(ts.tzinfo) if ts.tzinfo else datetime.now()
        
        # Calculate days since last interaction
        days_ago = (now - ts).total_seconds() / 86400
        
        # Exponential decay with 30-day halflife
        halflife = 30.0
        decay_factor = math.exp(-0.693147 * days_ago / halflife)
        
        return max(0.0, min(1.0, decay_factor))
    except Exception:
        return 0.0


def _recalculate_trust(lead_id: str, graph) -> float:
    """
    Recalculate trust score for a lead based on:
    - interaction_count (weight 0.4, capped at 20)
    - recency of last interaction (weight 0.3, exponential decay)
    - flow membership count (weight 0.3, capped at 5)
    """
    try:
        from ..graph import queries as q
        
        # Get scoring data
        data = graph.execute_read(q.CALCULATE_LEAD_SCORE, {"id": lead_id})
        if not data:
            return 0.0
        
        row = data[0]
        
        # Calculate component scores
        interaction_score = min(row["interaction_count"] / 20.0, 1.0)
        recency_score = _recency_decay(row["last_interaction"])
        flow_score = min(row["flow_count"] / 5.0, 1.0)
        
        # Weighted average
        trust = (interaction_score * 0.4) + (recency_score * 0.3) + (flow_score * 0.3)
        
        # Update lead trust in graph
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        graph.execute_write(q.UPDATE_LEAD_TRUST, {
            "lead_id": lead_id,
            "trust": trust,
            "updated_at": now,
        })
        
        return trust
    except Exception as exc:
        logger.warning("_recalculate_trust error: %s", exc)
        return 0.0


# -- CRM endpoints ------------------------------------------------------------

@router.get("/crm/leads", response_model=list[CrmLeadResponse])
async def list_crm_leads(limit: int = Query(default=50, le=200)):
    """List all CRM leads, newest first."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_ALL_LEADS, {"limit": limit})
        return [CrmLeadResponse(**r) for r in rows]
    except Exception as exc:
        logger.warning("list_crm_leads error: %s", exc)
        return []


@router.get("/crm/leads/search", response_model=list[CrmLeadResponse])
async def search_crm_leads(q: str = Query(default="", description="Search term"), limit: int = Query(default=50, le=200)):
    """Fulltext search for leads by name, email, or company."""
    if not _svc.graph or not q:
        return []
    try:
        from ..graph import queries as qry
        rows = _svc.graph.execute_read(qry.FULLTEXT_SEARCH_LEADS, {"query": q, "limit": limit})
        # Remove score field from results
        return [CrmLeadResponse(**{k: v for k, v in r.items() if k != "score"}) for r in rows]
    except Exception as exc:
        logger.warning("search_crm_leads error: %s", exc)
        return []


@router.post("/crm/leads", response_model=CrmLeadResponse, status_code=201)
async def create_crm_lead(body: CrmLeadCreate):
    """Create a new CRM lead."""
    if not _svc.graph:
        return CrmLeadResponse(id="", name=body.name)
    try:
        from ..graph import queries as q
        import uuid
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        lead_id = f"lead_{uuid.uuid4().hex[:12]}"
        params = {
            "id": lead_id,
            "name": body.name,
            "email": body.email,
            "company": body.company,
            "trust": 0.5,
            "source_channel": body.source_channel,
            "tags": body.tags,
            "created_at": now,
            "updated_at": now,
        }
        _svc.graph.execute_write(q.UPSERT_LEAD, params)
        _broadcast_crm_event("lead_created", {"id": lead_id, "name": body.name})
        return CrmLeadResponse(**params, interaction_count=0)
    except Exception as exc:
        logger.warning("create_crm_lead error: %s", exc)
        return CrmLeadResponse(id="", name=body.name)


@router.get("/crm/leads/{lead_id}", response_model=CrmLeadResponse)
async def get_crm_lead(lead_id: str):
    """Get a single lead by ID."""
    if not _svc.graph:
        return CrmLeadResponse(id=lead_id, name="")
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_LEAD_BY_ID, {"lead_id": lead_id})
        if rows:
            return CrmLeadResponse(**rows[0])
        return CrmLeadResponse(id=lead_id, name="")
    except Exception as exc:
        logger.warning("get_crm_lead error: %s", exc)
        return CrmLeadResponse(id=lead_id, name="")


@router.put("/crm/leads/{lead_id}", response_model=CrmLeadResponse)
async def update_crm_lead(lead_id: str, body: CrmLeadUpdate):
    """Update a lead's fields."""
    if not _svc.graph:
        return CrmLeadResponse(id=lead_id, name="")
    try:
        from ..graph import queries as q
        
        # Build update params (only include non-None fields)
        params = {"id": lead_id}
        updated_fields = []
        
        if body.name is not None:
            params["name"] = body.name
            updated_fields.append("name")
        if body.email is not None:
            params["email"] = body.email
            updated_fields.append("email")
        if body.company is not None:
            params["company"] = body.company
            updated_fields.append("company")
        if body.tags is not None:
            params["tags"] = body.tags
            updated_fields.append("tags")
        if body.trust is not None:
            params["trust"] = body.trust
            updated_fields.append("trust")
        
        # Execute update
        result = _svc.graph.execute_write(q.UPDATE_LEAD, params)
        
        if result:
            _broadcast_crm_event("lead_updated", {
                "lead_id": lead_id,
                "fields": updated_fields,
            })
            
            # Fetch updated lead
            rows = _svc.graph.execute_read(q.GET_LEAD_BY_ID, {"lead_id": lead_id})
            if rows:
                return CrmLeadResponse(**rows[0])
        
        return CrmLeadResponse(id=lead_id, name="")
    except Exception as exc:
        logger.warning("update_crm_lead error: %s", exc)
        return CrmLeadResponse(id=lead_id, name="")


@router.delete("/crm/leads/{lead_id}", status_code=204)
async def delete_crm_lead(lead_id: str):
    """Soft-delete a lead."""
    if not _svc.graph:
        return
    try:
        from ..graph import queries as q
        
        _svc.graph.execute_write(q.SOFT_DELETE_LEAD, {"id": lead_id})
        _broadcast_crm_event("lead_deleted", {"lead_id": lead_id})
    except Exception as exc:
        logger.warning("delete_crm_lead error: %s", exc)


@router.get("/crm/leads/{lead_id}/score", response_model=CrmLeadScoreResponse)
async def get_lead_score(lead_id: str):
    """Get trust score breakdown for a lead."""
    if not _svc.graph:
        return CrmLeadScoreResponse(
            lead_id=lead_id,
            trust=0.0,
            interaction_count=0,
            last_interaction=None,
            flow_count=0,
            interaction_score=0.0,
            recency_score=0.0,
            flow_score=0.0,
        )
    try:
        from ..graph import queries as q
        
        # Get scoring data
        data = _svc.graph.execute_read(q.CALCULATE_LEAD_SCORE, {"id": lead_id})
        if not data:
            return CrmLeadScoreResponse(
                lead_id=lead_id,
                trust=0.0,
                interaction_count=0,
                last_interaction=None,
                flow_count=0,
                interaction_score=0.0,
                recency_score=0.0,
                flow_score=0.0,
            )
        
        row = data[0]
        
        # Calculate component scores
        interaction_count = row["interaction_count"]
        last_interaction = row["last_interaction"]
        flow_count = row["flow_count"]
        
        interaction_score = min(interaction_count / 20.0, 1.0)
        recency_score = _recency_decay(last_interaction)
        flow_score = min(flow_count / 5.0, 1.0)
        
        # Weighted average
        trust = (interaction_score * 0.4) + (recency_score * 0.3) + (flow_score * 0.3)
        
        return CrmLeadScoreResponse(
            lead_id=lead_id,
            trust=trust,
            interaction_count=interaction_count,
            last_interaction=last_interaction,
            flow_count=flow_count,
            interaction_score=interaction_score,
            recency_score=recency_score,
            flow_score=flow_score,
        )
    except Exception as exc:
        logger.warning("get_lead_score error: %s", exc)
        return CrmLeadScoreResponse(
            lead_id=lead_id,
            trust=0.0,
            interaction_count=0,
            last_interaction=None,
            flow_count=0,
            interaction_score=0.0,
            recency_score=0.0,
            flow_score=0.0,
        )


@router.get("/crm/leads/{lead_id}/interactions")
async def get_lead_interactions(lead_id: str, limit: int = Query(default=50, le=200)):
    """Get interaction history for a lead."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        return _svc.graph.execute_read(q.GET_LEAD_INTERACTIONS, {"lead_id": lead_id, "limit": limit})
    except Exception as exc:
        logger.warning("get_lead_interactions error: %s", exc)
        return []


@router.get("/crm/graph", response_model=CrmGraphResponse)
async def get_crm_graph(limit: int = Query(default=200, le=1000)):
    """Full CRM graph for LeadGraph visualization."""
    if not _svc.graph:
        return CrmGraphResponse()
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_LEAD_GRAPH, {"limit": limit})
        if not rows:
            return CrmGraphResponse()

        nodes_map: dict[str, GraphNode] = {}
        edges: list[GraphEdge] = []

        for row in rows:
            # Extract nodes from each relationship pattern
            for key, label in [("l", "Lead"), ("f", "Flow"), ("l2", "Lead"), ("a", "Agent")]:
                node = row.get(key)
                if node and isinstance(node, dict):
                    nid = node.get("id", "")
                    if nid and nid not in nodes_map:
                        nodes_map[nid] = GraphNode(
                            id=nid,
                            labels=[label],
                            properties={k: v for k, v in node.items() if k != "id"},
                        )

            # Extract interactions
            interaction = row.get("i")
            if interaction and isinstance(interaction, dict):
                iid = interaction.get("id", "")
                if iid and iid not in nodes_map:
                    nodes_map[iid] = GraphNode(
                        id=iid,
                        labels=["Interaction"],
                        properties={k: v for k, v in interaction.items() if k != "id"},
                    )

            # Build edges from relationships
            for rkey, rel_type, src_key, tgt_key in [
                ("r1", "PART_OF_FLOW", "l", "f"),
                ("r2", "INTERACTED_WITH", "l", "l2"),
                ("r3", "FOR_LEAD", "i", "l"),
                ("r4", "BY_AGENT", "i", "a"),
            ]:
                rel = row.get(rkey)
                src_node = row.get(src_key)
                tgt_node = row.get(tgt_key)
                if rel and src_node and tgt_node:
                    src_id = src_node.get("id", "") if isinstance(src_node, dict) else ""
                    tgt_id = tgt_node.get("id", "") if isinstance(tgt_node, dict) else ""
                    if src_id and tgt_id:
                        edges.append(GraphEdge(source=src_id, target=tgt_id, type=rel_type))

        return CrmGraphResponse(nodes=list(nodes_map.values()), edges=edges)
    except Exception as exc:
        logger.warning("get_crm_graph error: %s", exc)
        return CrmGraphResponse()


@router.get("/crm/flows", response_model=list[CrmFlowResponse])
async def list_crm_flows(limit: int = Query(default=50, le=200)):
    """List CRM flows with lead counts."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_ALL_FLOWS, {"limit": limit})
        return [CrmFlowResponse(**r) for r in rows]
    except Exception as exc:
        logger.warning("list_crm_flows error: %s", exc)
        return []


@router.post("/crm/flows", response_model=CrmFlowResponse, status_code=201)
async def create_crm_flow(body: CrmFlowCreate):
    """Create a new CRM flow."""
    if not _svc.graph:
        return CrmFlowResponse(id="", name=body.name)
    try:
        from ..graph import queries as q
        import uuid
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        flow_id = f"flow_{uuid.uuid4().hex[:12]}"
        params = {
            "id": flow_id,
            "name": body.name,
            "objective": body.objective,
            "n8n_workflow_id": body.n8n_workflow_id,
            "status": "draft",
            "created_at": now,
        }
        _svc.graph.execute_write(q.UPSERT_FLOW, params)
        _broadcast_crm_event("flow_status_changed", {"id": flow_id, "name": body.name, "status": "draft"})
        return CrmFlowResponse(**params, lead_count=0)
    except Exception as exc:
        logger.warning("create_crm_flow error: %s", exc)
        return CrmFlowResponse(id="", name=body.name)


@router.get("/crm/flows/{flow_id}", response_model=CrmFlowResponse)
async def get_crm_flow(flow_id: str):
    """Get a single flow by ID."""
    if not _svc.graph:
        return CrmFlowResponse(id=flow_id, name="")
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_FLOW_BY_ID, {"flow_id": flow_id})
        if rows:
            row = rows[0]
            lead_ids = row.pop("lead_ids", [])
            return CrmFlowResponse(**row, lead_count=len(lead_ids) if lead_ids else 0)
        return CrmFlowResponse(id=flow_id, name="")
    except Exception as exc:
        logger.warning("get_crm_flow error: %s", exc)
        return CrmFlowResponse(id=flow_id, name="")


@router.put("/crm/flows/{flow_id}", response_model=CrmFlowResponse)
async def update_crm_flow(flow_id: str, body: CrmFlowUpdate):
    """Update a flow's fields."""
    if not _svc.graph:
        return CrmFlowResponse(id=flow_id, name="")
    try:
        from ..graph import queries as q
        
        # Build update params (only include non-None fields)
        params = {"id": flow_id}
        updated_fields = []
        
        if body.name is not None:
            params["name"] = body.name
            updated_fields.append("name")
        if body.objective is not None:
            params["objective"] = body.objective
            updated_fields.append("objective")
        if body.status is not None:
            params["status"] = body.status
            updated_fields.append("status")
        
        # Execute update
        result = _svc.graph.execute_write(q.UPDATE_FLOW, params)
        
        if result:
            _broadcast_crm_event("flow_updated", {
                "flow_id": flow_id,
                "fields": updated_fields,
            })
            
            # Fetch updated flow
            rows = _svc.graph.execute_read(q.GET_FLOW_BY_ID, {"flow_id": flow_id})
            if rows:
                row = rows[0]
                lead_ids = row.pop("lead_ids", [])
                return CrmFlowResponse(**row, lead_count=len(lead_ids) if lead_ids else 0)
        
        return CrmFlowResponse(id=flow_id, name="")
    except Exception as exc:
        logger.warning("update_crm_flow error: %s", exc)
        return CrmFlowResponse(id=flow_id, name="")


@router.delete("/crm/flows/{flow_id}", status_code=204)
async def delete_crm_flow(flow_id: str):
    """Soft-delete a flow."""
    if not _svc.graph:
        return
    try:
        from ..graph import queries as q
        
        _svc.graph.execute_write(q.SOFT_DELETE_FLOW, {"id": flow_id})
        _broadcast_crm_event("flow_deleted", {"flow_id": flow_id})
    except Exception as exc:
        logger.warning("delete_crm_flow error: %s", exc)


@router.post("/crm/flows/{flow_id}/leads/{lead_id}", status_code=204)
async def add_lead_to_flow(flow_id: str, lead_id: str):
    """Add a lead to a flow."""
    if not _svc.graph:
        return
    try:
        from ..graph import queries as q
        _svc.graph.execute_write(q.CREATE_LEAD_PART_OF_FLOW, {
            "lead_id": lead_id,
            "flow_id": flow_id,
            "added_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        })
    except Exception as exc:
        logger.warning("add_lead_to_flow error: %s", exc)


@router.post("/crm/interactions", status_code=201)
async def record_crm_interaction(body: CrmInteractionCreate):
    """Record a CRM interaction (used by agents + n8n)."""
    if not _svc.graph:
        return {"id": ""}
    try:
        from ..graph import queries as q
        import uuid
        now = time.strftime("%Y-%m-%dT%H:%M:%S")
        interaction_id = f"interaction_{uuid.uuid4().hex[:12]}"
        params = {
            "id": interaction_id,
            "lead_id": body.lead_id,
            "agent_id": body.agent_id,
            "channel": body.channel,
            "action": body.action,
            "detail": body.detail,
            "timestamp": now,
        }
        _svc.graph.execute_write(q.UPSERT_INTERACTION, params)

        # Link interaction to lead
        _svc.graph.execute_write(q.CREATE_INTERACTION_FOR_LEAD, {
            "interaction_id": interaction_id,
            "lead_id": body.lead_id,
        })

        # Link interaction to agent if provided
        if body.agent_id:
            try:
                _svc.graph.execute_write(q.CREATE_INTERACTION_BY_AGENT, {
                    "interaction_id": interaction_id,
                    "agent_id": body.agent_id,
                })
            except Exception:
                pass  # Agent may not exist in graph yet

        # Increment lead interaction count
        _svc.graph.execute_write(q.INCREMENT_LEAD_INTERACTION_COUNT, {
            "lead_id": body.lead_id,
            "updated_at": now,
        })

        # Auto-recalculate trust score
        _recalculate_trust(body.lead_id, _svc.graph)

        _broadcast_crm_event("interaction_recorded", {
            "id": interaction_id,
            "lead_id": body.lead_id,
            "action": body.action,
        })
        return {"id": interaction_id}
    except Exception as exc:
        logger.warning("record_crm_interaction error: %s", exc)
        return {"id": ""}


@router.get("/crm/stats", response_model=CrmStatsResponse)
async def crm_stats():
    """Dashboard CRM stats (lead/flow/interaction counts)."""
    if not _svc.graph:
        return CrmStatsResponse()
    try:
        from ..graph import queries as q
        rows = _svc.graph.execute_read(q.GET_CRM_STATS)
        if rows:
            r = rows[0]
            return CrmStatsResponse(
                total_leads=r.get("total_leads", 0),
                total_flows=r.get("total_flows", 0),
                total_interactions=r.get("total_interactions", 0),
                avg_trust=round(r.get("avg_trust", 0.0), 3),
            )
        return CrmStatsResponse()
    except Exception as exc:
        logger.warning("crm_stats error: %s", exc)
        return CrmStatsResponse()


# -- Pipeline Stats (fix: missing endpoint frontend expects) ------------------

@router.get("/pipeline/stats")
async def pipeline_stats():
    """CostTracker aggregate statistics. Frontend PipelineStats expects this."""
    if _svc.interface:
        try:
            orch = _svc.interface._orchestrator
            if orch and hasattr(orch, "cost_stats"):
                return orch.cost_stats
        except Exception:
            pass
    return {"total_requests": 0}


# -- KPI Metrics Intelligence ------------------------------------------------

@router.get("/kpi/models")
async def kpi_models():
    """Model leaderboard ranked by cost-effectiveness."""
    if not _svc.model_benchmark:
        return []
    return _svc.model_benchmark.get_leaderboard()


@router.get("/kpi/models/{model_id}/history")
async def kpi_model_history(model_id: str, limit: int = Query(default=30, le=365)):
    """Daily time series for a specific model."""
    if not _svc.model_benchmark:
        return []
    return _svc.model_benchmark.get_model_history(model_id, limit=limit)


@router.get("/kpi/tools")
async def kpi_tools():
    """Tool comparison aggregates."""
    if not _svc.tool_scorecard:
        return []
    return _svc.tool_scorecard.get_comparison()


@router.get("/kpi/tools/{tool_name}/history")
async def kpi_tool_history(tool_name: str, limit: int = Query(default=20, le=100)):
    """Sprint-by-sprint reviews for a tool."""
    if not _svc.tool_scorecard:
        return []
    return _svc.tool_scorecard.get_tool_history(tool_name, limit=limit)


@router.post("/kpi/tools/review")
async def kpi_submit_review(body: KpiToolReviewSubmit):
    """Submit a tool review following REVIEW_TEMPLATE.md formula."""
    if not _svc.tool_scorecard:
        return {"error": "ToolScorecard not available"}
    try:
        result = _svc.tool_scorecard.submit_review(
            tool_name=body.tool_name,
            sprint_date=body.sprint_date,
            score_correto=body.score_correto,
            score_completo=body.score_completo,
            score_qualidade=body.score_qualidade,
            deliverables_done=body.deliverables_done,
            deliverables_total=body.deliverables_total,
            issues_critical=body.issues_critical,
            issues_medium=body.issues_medium,
            issues_low=body.issues_low,
            reviewer=body.reviewer,
            notes=body.notes,
        )
        if result:
            return result
        return {"error": "Review submission failed"}
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/kpi/cost-quality")
async def kpi_cost_quality():
    """$/quality-point analysis by model, agent, and task_type."""
    if not _svc.cost_quality_analyzer:
        return {"by_model": [], "by_agent": [], "by_task_type": []}
    return _svc.cost_quality_analyzer.get_combined()


@router.get("/kpi/trends")
async def kpi_trends(dimension: str = Query(default="model"), limit: int = Query(default=90, le=365)):
    """Daily aggregates by dimension (model|agent|task_type)."""
    if not _svc.metrics_timeseries:
        return []
    return _svc.metrics_timeseries.get_trends(dimension_type=dimension, limit=limit)


@router.get("/kpi/agents/heatmap")
async def kpi_agent_heatmap():
    """Agent x task_type quality matrix."""
    if not _svc.graph:
        return []
    try:
        from ..graph import queries as q
        return _svc.graph.execute_read(q.GET_AGENT_TASK_TYPE_HEATMAP)
    except Exception as exc:
        logger.warning("kpi_agent_heatmap error: %s", exc)
        return []


@router.get("/kpi/anomalies")
async def kpi_anomalies():
    """Regression alerts from MetricsTimeSeries."""
    if not _svc.metrics_timeseries:
        return []
    return _svc.metrics_timeseries.detect_anomalies()


@router.get("/kpi/recommend", response_model=KpiRecommendResponse)
async def kpi_recommend(
    task_type: str = Query(default=""),
    min_quality: float = Query(default=7.0, ge=0, le=10),
):
    """Recommend best model for task_type + quality threshold."""
    if not _svc.cost_quality_analyzer:
        return KpiRecommendResponse()
    result = _svc.cost_quality_analyzer.recommend_model(task_type=task_type, min_quality=min_quality)
    if result:
        return KpiRecommendResponse(**result)
    return KpiRecommendResponse(reason="No model meets the quality threshold")


# -- UseCase Registry endpoints -----------------------------------------------

@router.get("/usecases")
async def list_usecases(
    domain: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
):
    """List use cases with optional domain/status filters."""
    from .usecase_registry import UseCaseRegistry
    registry = UseCaseRegistry(_svc.graph)
    if domain:
        return registry.get_by_domain(domain)
    if status:
        return registry.get_by_status(status)
    return registry.get_all(limit=limit)


@router.get("/usecases/roadmap")
async def usecase_roadmap():
    """Full roadmap view with dependencies and agent assignments."""
    from .usecase_registry import UseCaseRegistry
    registry = UseCaseRegistry(_svc.graph)
    return registry.get_roadmap()


@router.get("/usecases/coverage")
async def usecase_coverage():
    """Agent coverage matrix: which agents cover which use cases."""
    from .usecase_registry import UseCaseRegistry
    registry = UseCaseRegistry(_svc.graph)
    return registry.get_agent_coverage()


@router.get("/usecases/gaps")
async def usecase_skill_gaps():
    """Skills required by use cases but not owned by any agent."""
    from .usecase_registry import UseCaseRegistry
    registry = UseCaseRegistry(_svc.graph)
    return registry.get_skill_gaps()


@router.get("/usecases/{usecase_id}")
async def get_usecase(usecase_id: str):
    """Get single use case with full context (agents, skills, modules, deps)."""
    from .usecase_registry import UseCaseRegistry
    registry = UseCaseRegistry(_svc.graph)
    result = registry.get_by_id(usecase_id)
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="UseCase not found")
    return result


# -- WebSocket channels -------------------------------------------------------

@router.websocket("/ws/telemetry")
async def ws_telemetry(ws: WebSocket):
    """Real-time telemetry event stream."""
    await _ws_manager.connect("telemetry", ws)
    try:
        while True:
            # Keep connection alive; client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _ws_manager.disconnect("telemetry", ws)


@router.websocket("/ws/agent-health")
async def ws_agent_health(ws: WebSocket):
    """Periodic agent status broadcast (every 5 seconds)."""
    await _ws_manager.connect("agent-health", ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _ws_manager.disconnect("agent-health", ws)


@router.websocket("/ws/flow-events")
async def ws_flow_events(ws: WebSocket):
    """Flow Canvas real-time updates."""
    await _ws_manager.connect("flow-events", ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _ws_manager.disconnect("flow-events", ws)


@router.websocket("/ws/crm-events")
async def ws_crm_events(ws: WebSocket):
    """CRM real-time updates (lead/flow/interaction changes)."""
    await _ws_manager.connect("crm-events", ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _ws_manager.disconnect("crm-events", ws)


@router.websocket("/ws/journey-events")
async def ws_journey_events(ws: WebSocket):
    """Jornadas: heal_completed, jitbit_error. JourneyCanvas subscreve para sincronia visual."""
    await _ws_manager.connect("journey-events", ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        await _ws_manager.disconnect("journey-events", ws)


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------

# Monitores (threads) - Telegram + K8s
_monitor_threads: list = []
_monitor_handles: dict = {}  # k8s_monitor, pod_monitor para shutdown


@asynccontextmanager
async def lifespan(application: FastAPI):
    """Start background loops on startup, cancel on shutdown."""
    import threading

    _svc.ensure_initialized()
    _bg_tasks.append(asyncio.create_task(_agent_health_loop()))
    _bg_tasks.append(asyncio.create_task(_telemetry_loop()))

    # K8sEventBufferProvider para broadcast de eventos via WebSocket
    try:
        from ..telemetry.provider import TelemetryHub, K8sEventBufferProvider
        k8s_provider = K8sEventBufferProvider()
        _svc.telemetry_hub.register(k8s_provider)
        logger.info("K8sEventBufferProvider registrado no TelemetryHub")
    except Exception as exc:
        logger.warning("K8sEventBufferProvider não disponível: %s", exc)
        k8s_provider = None

    # CrmEventProvider para broadcast de eventos CRM via TelemetryHub
    try:
        from ..telemetry.provider import CrmEventProvider
        crm_provider = CrmEventProvider()
        _svc.telemetry_hub.register(crm_provider)
        logger.info("CrmEventProvider registrado no TelemetryHub")
    except Exception as exc:
        logger.warning("CrmEventProvider não disponível: %s", exc)

    # KpiProvider para broadcast de anomalias KPI
    try:
        if _svc.kpi_provider and _svc.telemetry_hub:
            _svc.telemetry_hub.register(_svc.kpi_provider)
            logger.info("KpiProvider registrado no TelemetryHub")
    except Exception as exc:
        logger.warning("KpiProvider não disponível: %s", exc)

    # TelegramCommandHandler
    try:
        from ..telemetry.telegram_command_handler import TelegramCommandHandler
        tg_handler = TelegramCommandHandler()
        tg_handler.start()
        _monitor_threads.append(("telegram", tg_handler))
        logger.info("TelegramCommandHandler iniciado")
    except Exception as exc:
        logger.warning("TelegramCommandHandler não iniciado: %s", exc)

    # K8sEventMonitor + PodStatusMonitor (opcional - requer cluster)
    try:
        from ..k8s_monitoring.wire_monitoring import wire_and_start
        k8s_monitor, pod_monitor = wire_and_start()
        _monitor_handles["k8s"] = k8s_monitor
        _monitor_handles["pod"] = pod_monitor
        if k8s_provider:
            def _push_failure(event):
                k8s_provider.push_pod_failure(
                    event.pod_name, event.namespace, event.reason,
                    is_neo4j=event.is_neo4j, is_chromadb=event.is_chromadb,
                )
            pod_monitor.register_handler(_push_failure)
            logger.info("PodStatusMonitor conectado ao WebSocket broadcast")
    except Exception as exc:
        logger.info("K8sEventMonitor não iniciado (sem cluster): %s", exc)

    logger.info("Sovereign gateway background tasks started")
    yield

    # Shutdown monitores
    if _monitor_handles.get("k8s"):
        try:
            _monitor_handles["k8s"].stop()
        except Exception:
            pass
    for _name, handler in _monitor_threads:
        if hasattr(handler, "stop"):
            try:
                handler.stop()
            except Exception:
                pass

    for t in _bg_tasks:
        t.cancel()
    _bg_tasks.clear()
    logger.info("Sovereign gateway background tasks stopped")


app = FastAPI(
    title="Sovereign AI Command Center",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# ---------------------------------------------------------------------------
# Standalone entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    uvicorn.run(app, host="0.0.0.0", port=8766)
