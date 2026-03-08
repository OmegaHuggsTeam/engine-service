# Journey Builder Ecosystem — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a container-first Journey Builder where each canvas node is a real Docker sandbox, with AI copilot, NL journey generation, and KPI dashboard.

**Architecture:** React Flow canvas in the engine-service Next.js frontend (`frontend/src/modules/journey/`). Backend extends Sovereign Gateway (:8766) with Docker SDK container management, journey execution engine, and AI generation endpoints. All real-time feedback via existing WebSocket infrastructure.

**Tech Stack:** Next.js 16 + @xyflow/react v12 + SWR + Framer Motion + D3 | Python FastAPI + Docker SDK + Pydantic v2 | Neo4j + ChromaDB

**Existing Patterns to Follow:**
- Frontend modules: `src/modules/<name>/` with `hooks/` subdirectory
- API client: functions in `src/lib/gateway.ts`, SWR wrappers in `hooks/use<Module>Api.ts`
- WebSocket: mirror `useCrmWebSocket.ts` pattern (exponential backoff reconnect)
- Pages: `src/app/dashboard/<name>/page.tsx` + entry in `TABS` array in `dashboard/layout.tsx`
- React Flow: `useNodesState`, `useEdgesState`, custom `nodeTypes`, `proOptions={{ hideAttribution: true }}`, `colorMode="dark"`
- Backend routes: Pydantic models at top of file, `@router.get/post` on `/api/v1/` prefix, `try/except` with `logger.warning`
- Backend broadcast: `_ws_manager.broadcast(channel, data)` with `channel_count` guard
- Styling: CSS custom properties from `globals.css` (no hardcoded hex except in canvas)
- Dynamic imports: `dynamic(() => import(...), { ssr: false })` for browser-only components

---

## Phase 1: Backend — Container Orchestrator (Docker SDK)

### Task 1.1: Install Docker SDK + Create ContainerOrchestrator Module

**Files:**
- Create: `src/neural_link/containers/__init__.py`
- Create: `src/neural_link/containers/orchestrator.py`
- Create: `src/neural_link/containers/models.py`
- Modify: `requirements.txt` (add `docker>=7.0.0`)
- Test: `src/neural_link/tests/test_container_orchestrator.py`

**Step 1: Write the failing test**

```python
# src/neural_link/tests/test_container_orchestrator.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from neural_link.containers.models import ContainerConfig, ContainerStatus, ContainerMetrics
from neural_link.containers.orchestrator import ContainerOrchestrator


class TestContainerOrchestrator:
    def setup_method(self):
        self.orch = ContainerOrchestrator()

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
            mock_container.id = "abc123"
            mock_container.status = "running"
            mock_docker.return_value.containers.run.return_value = mock_container
            result = self.orch.spawn(config)
        assert result.container_id == "abc123"
        assert result.status == "running"

    def test_get_status_returns_metrics(self):
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_container.status = "running"
            mock_container.stats.return_value = {
                "cpu_stats": {"cpu_usage": {"total_usage": 1000}},
                "precpu_stats": {"cpu_usage": {"total_usage": 500}},
                "memory_stats": {"usage": 67108864, "limit": 134217728},
            }
            mock_docker.return_value.containers.get.return_value = mock_container
            status = self.orch.get_status("abc123")
        assert status.status == "running"
        assert status.memory_mb > 0

    def test_stop_and_remove(self):
        with patch("docker.from_env") as mock_docker:
            mock_container = MagicMock()
            mock_docker.return_value.containers.get.return_value = mock_container
            self.orch.stop("abc123")
        mock_container.stop.assert_called_once()
        mock_container.remove.assert_called_once()

    def test_list_containers_by_tenant(self):
        with patch("docker.from_env") as mock_docker:
            mock_c1 = MagicMock()
            mock_c1.id = "c1"
            mock_c1.labels = {"huggsai.tenant_id": "t1", "huggsai.node_id": "n1"}
            mock_c1.status = "running"
            mock_c2 = MagicMock()
            mock_c2.id = "c2"
            mock_c2.labels = {"huggsai.tenant_id": "t1", "huggsai.node_id": "n2"}
            mock_c2.status = "exited"
            mock_docker.return_value.containers.list.return_value = [mock_c1, mock_c2]
            result = self.orch.list_by_tenant("t1")
        assert len(result) == 2
```

**Step 2: Run test to verify it fails**

Run: `cd C:/labs/inteligence/chunk-generator && python -m pytest src/neural_link/tests/test_container_orchestrator.py -v`
Expected: FAIL — modules not found

**Step 3: Write the Pydantic models**

```python
# src/neural_link/containers/models.py
from pydantic import BaseModel, Field
from typing import Any
from datetime import datetime


class ContainerConfig(BaseModel):
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
    container_id: str
    node_id: str
    tenant_id: str
    image: str
    status: str  # created | running | exited | paused | dead
    started_at: str | None = None


class ContainerMetrics(BaseModel):
    container_id: str
    status: str
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    logs: str = ""


class ContainerExecResult(BaseModel):
    container_id: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
```

**Step 4: Write the orchestrator**

```python
# src/neural_link/containers/orchestrator.py
import docker
import time
import logging
from .models import ContainerConfig, ContainerInfo, ContainerMetrics, ContainerExecResult

logger = logging.getLogger(__name__)

LABEL_PREFIX = "huggsai"


class ContainerOrchestrator:
    def __init__(self):
        self._client = None

    @property
    def client(self):
        if self._client is None:
            self._client = docker.from_env()
        return self._client

    def spawn(self, config: ContainerConfig) -> ContainerInfo:
        labels = {
            f"{LABEL_PREFIX}.tenant_id": config.tenant_id,
            f"{LABEL_PREFIX}.node_id": config.node_id,
            f"{LABEL_PREFIX}.journey_id": config.journey_id or "",
        }
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
        return ContainerInfo(
            container_id=container.id,
            node_id=config.node_id,
            tenant_id=config.tenant_id,
            image=config.image,
            status=container.status,
        )

    def get_status(self, container_id: str) -> ContainerMetrics:
        container = self.client.containers.get(container_id)
        stats = container.stats(stream=False)
        mem_usage = stats.get("memory_stats", {}).get("usage", 0)
        mem_mb = mem_usage / (1024 * 1024)
        cpu_delta = stats.get("cpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        pre_cpu = stats.get("precpu_stats", {}).get("cpu_usage", {}).get("total_usage", 0)
        cpu_pct = ((cpu_delta - pre_cpu) / 1e9) * 100 if cpu_delta > pre_cpu else 0.0
        return ContainerMetrics(
            container_id=container_id,
            status=container.status,
            memory_mb=round(mem_mb, 2),
            cpu_percent=round(cpu_pct, 2),
        )

    def stop(self, container_id: str) -> None:
        container = self.client.containers.get(container_id)
        container.stop(timeout=5)
        container.remove(force=True)

    def exec_in_container(self, container_id: str, cmd: str) -> ContainerExecResult:
        container = self.client.containers.get(container_id)
        start = time.monotonic()
        exit_code, output = container.exec_run(cmd, demux=True)
        duration = (time.monotonic() - start) * 1000
        stdout = (output[0] or b"").decode("utf-8", errors="replace") if isinstance(output, tuple) else ""
        stderr = (output[1] or b"").decode("utf-8", errors="replace") if isinstance(output, tuple) else ""
        return ContainerExecResult(
            container_id=container_id,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_ms=round(duration, 2),
        )

    def get_logs(self, container_id: str, tail: int = 100) -> str:
        container = self.client.containers.get(container_id)
        return container.logs(tail=tail).decode("utf-8", errors="replace")

    def list_by_tenant(self, tenant_id: str) -> list[ContainerInfo]:
        containers = self.client.containers.list(
            all=True,
            filters={"label": f"{LABEL_PREFIX}.tenant_id={tenant_id}"},
        )
        return [
            ContainerInfo(
                container_id=c.id,
                node_id=c.labels.get(f"{LABEL_PREFIX}.node_id", ""),
                tenant_id=tenant_id,
                image=str(c.image),
                status=c.status,
            )
            for c in containers
        ]

    def cleanup_journey(self, journey_id: str) -> int:
        containers = self.client.containers.list(
            all=True,
            filters={"label": f"{LABEL_PREFIX}.journey_id={journey_id}"},
        )
        count = 0
        for c in containers:
            try:
                c.stop(timeout=2)
                c.remove(force=True)
                count += 1
            except Exception as e:
                logger.warning("cleanup container %s: %s", c.id[:12], e)
        return count
```

**Step 5: Create __init__.py**

```python
# src/neural_link/containers/__init__.py
from .orchestrator import ContainerOrchestrator
from .models import ContainerConfig, ContainerInfo, ContainerMetrics, ContainerExecResult

__all__ = ["ContainerOrchestrator", "ContainerConfig", "ContainerInfo", "ContainerMetrics", "ContainerExecResult"]
```

**Step 6: Run tests to verify they pass**

Run: `cd C:/labs/inteligence/chunk-generator && python -m pytest src/neural_link/tests/test_container_orchestrator.py -v`
Expected: 4 PASSED

**Step 7: Commit**

```bash
git add src/neural_link/containers/ src/neural_link/tests/test_container_orchestrator.py
git commit -m "feat(containers): add ContainerOrchestrator with Docker SDK"
```

---

### Task 1.2: Add Container API Endpoints to Sovereign Gateway

**Files:**
- Modify: `src/neural_link/api/sovereign_gateway.py` (add ~80 lines of endpoints + models)
- Test: `src/neural_link/tests/test_container_endpoints.py`

**Step 1: Write the failing test**

```python
# src/neural_link/tests/test_container_endpoints.py
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
        mock_svc.container_orch = MagicMock()
        from neural_link.api.sovereign_gateway import app
        yield TestClient(app)


class TestContainerEndpoints:
    def test_spawn_container(self, client):
        with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
            mock_svc.container_orch.spawn.return_value = MagicMock(
                container_id="abc123", node_id="n1", tenant_id="t1",
                image="huggsai/trigger:latest", status="running"
            )
            resp = client.post("/api/v1/containers/spawn", json={
                "image": "huggsai/trigger:latest",
                "tenant_id": "t1",
                "node_id": "n1",
            })
        assert resp.status_code == 200
        assert resp.json()["container_id"] == "abc123"

    def test_get_container_status(self, client):
        with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
            mock_svc.container_orch.get_status.return_value = MagicMock(
                container_id="abc123", status="running",
                memory_mb=64.5, cpu_percent=12.3,
            )
            resp = client.get("/api/v1/containers/abc123/status")
        assert resp.status_code == 200
        assert resp.json()["status"] == "running"

    def test_list_containers(self, client):
        with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
            mock_svc.container_orch.list_by_tenant.return_value = []
            resp = client.get("/api/v1/containers?tenant_id=t1")
        assert resp.status_code == 200

    def test_stop_container(self, client):
        with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
            mock_svc.container_orch.stop.return_value = None
            resp = client.delete("/api/v1/containers/abc123")
        assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest src/neural_link/tests/test_container_endpoints.py -v`
Expected: FAIL — no container endpoints exist

**Step 3: Add Pydantic models and endpoints to sovereign_gateway.py**

Add these models near other Pydantic models in sovereign_gateway.py:

```python
# --- Container Management Models ---
class ContainerSpawnRequest(BaseModel):
    image: str
    tenant_id: str
    node_id: str
    journey_id: str | None = None
    memory_limit_mb: int = 128
    env: dict[str, str] = Field(default_factory=dict)
    timeout_seconds: int = 30

class ContainerSpawnResponse(BaseModel):
    container_id: str
    node_id: str
    tenant_id: str
    image: str
    status: str

class ContainerStatusResponse(BaseModel):
    container_id: str
    status: str
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    logs: str = ""

class ContainerListResponse(BaseModel):
    containers: list[dict] = Field(default_factory=list)
    count: int = 0
```

Add these endpoints after existing routes:

```python
# --- Container Management Endpoints ---

@router.post("/containers/spawn", response_model=ContainerSpawnResponse)
async def spawn_container(req: ContainerSpawnRequest):
    try:
        from neural_link.containers import ContainerOrchestrator, ContainerConfig
        orch = _svc.container_orch
        if not orch:
            orch = ContainerOrchestrator()
            _svc.container_orch = orch
        config = ContainerConfig(
            image=req.image, tenant_id=req.tenant_id, node_id=req.node_id,
            journey_id=req.journey_id, memory_limit_mb=req.memory_limit_mb,
            env=req.env, timeout_seconds=req.timeout_seconds,
        )
        info = orch.spawn(config)
        if _ws_manager.channel_count("journey-events") > 0:
            await _ws_manager.broadcast("journey-events", {
                "type": "container_spawned",
                "container_id": info.container_id,
                "node_id": info.node_id,
                "tenant_id": info.tenant_id,
            })
        return ContainerSpawnResponse(**info.model_dump())
    except Exception as exc:
        logger.warning("spawn_container error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/containers/{container_id}/status", response_model=ContainerStatusResponse)
async def get_container_status(container_id: str):
    try:
        orch = _svc.container_orch
        if not orch:
            raise HTTPException(status_code=503, detail="Container orchestrator not initialized")
        metrics = orch.get_status(container_id)
        logs = orch.get_logs(container_id, tail=50)
        return ContainerStatusResponse(
            container_id=metrics.container_id, status=metrics.status,
            memory_mb=metrics.memory_mb, cpu_percent=metrics.cpu_percent,
            logs=logs,
        )
    except Exception as exc:
        logger.warning("get_container_status error: %s", exc)
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/containers")
async def list_containers(tenant_id: str | None = None):
    try:
        orch = _svc.container_orch
        if not orch:
            return {"containers": [], "count": 0}
        containers = orch.list_by_tenant(tenant_id) if tenant_id else []
        return {"containers": [c.model_dump() for c in containers], "count": len(containers)}
    except Exception as exc:
        logger.warning("list_containers error: %s", exc)
        return {"containers": [], "count": 0}


@router.delete("/containers/{container_id}")
async def stop_container(container_id: str):
    try:
        orch = _svc.container_orch
        if not orch:
            raise HTTPException(status_code=503, detail="Container orchestrator not initialized")
        orch.stop(container_id)
        if _ws_manager.channel_count("journey-events") > 0:
            await _ws_manager.broadcast("journey-events", {
                "type": "container_stopped",
                "container_id": container_id,
            })
        return {"success": True, "container_id": container_id}
    except Exception as exc:
        logger.warning("stop_container error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))
```

**Step 4: Run tests**

Run: `python -m pytest src/neural_link/tests/test_container_endpoints.py -v`
Expected: 4 PASSED

**Step 5: Commit**

```bash
git add src/neural_link/api/sovereign_gateway.py src/neural_link/tests/test_container_endpoints.py
git commit -m "feat(api): add container management endpoints (spawn, status, list, stop)"
```

---

## Phase 2: Backend — Journey Executor

### Task 2.1: JourneyExecutor (DAG Walker)

**Files:**
- Create: `src/neural_link/containers/journey_executor.py`
- Create: `src/neural_link/containers/journey_models.py`
- Test: `src/neural_link/tests/test_journey_executor.py`

**Step 1: Write the failing test**

```python
# src/neural_link/tests/test_journey_executor.py
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from neural_link.containers.journey_models import JourneyDAG, DAGNode, DAGEdge
from neural_link.containers.journey_executor import JourneyExecutor


class TestJourneyExecutor:
    def setup_method(self):
        self.mock_orch = MagicMock()
        self.mock_broadcast = AsyncMock()
        self.executor = JourneyExecutor(self.mock_orch, self.mock_broadcast)

    def test_parse_dag_nodes(self):
        dag = JourneyDAG(
            journey_id="j1",
            tenant_id="t1",
            nodes=[
                DAGNode(id="n1", type="trigger", subtype="trigger_manual", config={}),
                DAGNode(id="n2", type="condition", subtype="condition_if", config={"field": "tag", "value": "vip"}),
                DAGNode(id="n3", type="action", subtype="action_tag", config={"tag": "premium"}),
                DAGNode(id="n4", type="control", subtype="control_end", config={}),
            ],
            edges=[
                DAGEdge(source="n1", target="n2"),
                DAGEdge(source="n2", target="n3", label="true"),
                DAGEdge(source="n2", target="n4", label="false"),
            ],
        )
        order = self.executor.topological_sort(dag)
        assert order[0] == "n1"  # trigger first
        assert "n2" in order  # condition after trigger

    def test_execute_node_spawns_container(self):
        self.mock_orch.spawn.return_value = MagicMock(
            container_id="c1", status="running"
        )
        self.mock_orch.exec_in_container.return_value = MagicMock(
            exit_code=0, stdout='{"result": true}', stderr="", duration_ms=45.0
        )
        self.mock_orch.stop.return_value = None
        node = DAGNode(id="n1", type="trigger", subtype="trigger_manual", config={})
        result = asyncio.get_event_loop().run_until_complete(
            self.executor.execute_node(node, "j1", "t1", {})
        )
        assert result["status"] == "success"
        assert result["latency_ms"] > 0

    def test_control_end_skips_container(self):
        node = DAGNode(id="n4", type="control", subtype="control_end", config={})
        result = asyncio.get_event_loop().run_until_complete(
            self.executor.execute_node(node, "j1", "t1", {})
        )
        assert result["status"] == "success"
        assert result.get("container_id") is None  # no container for control_end

    def test_control_wait_delays(self):
        node = DAGNode(id="nw", type="control", subtype="control_wait", config={"seconds": 0.01})
        result = asyncio.get_event_loop().run_until_complete(
            self.executor.execute_node(node, "j1", "t1", {})
        )
        assert result["status"] == "success"
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest src/neural_link/tests/test_journey_executor.py -v`
Expected: FAIL — modules not found

**Step 3: Write journey models**

```python
# src/neural_link/containers/journey_models.py
from pydantic import BaseModel, Field
from typing import Any


class DAGNode(BaseModel):
    id: str
    type: str  # trigger | condition | action | control | integration | tracking
    subtype: str  # trigger_manual | condition_if | action_sms | etc.
    config: dict[str, Any] = Field(default_factory=dict)
    label: str = ""


class DAGEdge(BaseModel):
    source: str
    target: str
    label: str = ""  # "true" | "false" | "" for unconditional


class JourneyDAG(BaseModel):
    journey_id: str
    tenant_id: str
    nodes: list[DAGNode]
    edges: list[DAGEdge]


class NodeResult(BaseModel):
    node_id: str
    status: str  # success | failure | timeout | skipped
    container_id: str | None = None
    latency_ms: float = 0.0
    output: dict[str, Any] = Field(default_factory=dict)
    error: str = ""


class JourneyExecutionResult(BaseModel):
    journey_id: str
    tenant_id: str
    status: str  # running | completed | failed
    node_results: list[NodeResult] = Field(default_factory=list)
    total_latency_ms: float = 0.0
    total_cost: float = 0.0
    containers_spawned: int = 0
```

**Step 4: Write the executor**

```python
# src/neural_link/containers/journey_executor.py
import asyncio
import time
import logging
from collections import defaultdict, deque
from typing import Any, Callable, Awaitable
from .orchestrator import ContainerOrchestrator
from .models import ContainerConfig
from .journey_models import JourneyDAG, DAGNode, DAGEdge, NodeResult, JourneyExecutionResult

logger = logging.getLogger(__name__)

# Subtype -> container image mapping
NODE_IMAGES: dict[str, str] = {
    "trigger_manual": "huggsai/trigger:latest",
    "trigger_event": "huggsai/trigger:latest",
    "trigger_segment": "huggsai/trigger:latest",
    "trigger_schedule": "huggsai/trigger:latest",
    "condition_if": "huggsai/condition:latest",
    "condition_split": "huggsai/condition:latest",
    "action_sms": "huggsai/action-sms:latest",
    "action_email": "huggsai/action-email:latest",
    "action_whatsapp": "huggsai/action-wa:latest",
    "action_webhook": "huggsai/action-webhook:latest",
    "action_tag": "huggsai/action-crm:latest",
    "action_score": "huggsai/action-crm:latest",
    "control_loop": "huggsai/control:latest",
    "int_sendspeed": "huggsai/int-sendspeed:latest",
    "int_meta": "huggsai/int-meta:latest",
    "int_ga": "huggsai/int-ga:latest",
    "track_pageview": "huggsai/tracker:latest",
    "track_click": "huggsai/tracker:latest",
    "track_conversion": "huggsai/tracker:latest",
}

NATIVE_NODES = {"control_end", "control_wait"}


class JourneyExecutor:
    def __init__(
        self,
        orchestrator: ContainerOrchestrator,
        broadcast: Callable[[str, dict], Awaitable[None]],
    ):
        self.orch = orchestrator
        self.broadcast = broadcast

    def topological_sort(self, dag: JourneyDAG) -> list[str]:
        graph: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {n.id: 0 for n in dag.nodes}
        for edge in dag.edges:
            graph[edge.source].append(edge.target)
            in_degree[edge.target] = in_degree.get(edge.target, 0) + 1
        queue = deque([nid for nid, deg in in_degree.items() if deg == 0])
        order = []
        while queue:
            nid = queue.popleft()
            order.append(nid)
            for neighbor in graph[nid]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        return order

    async def execute_node(
        self,
        node: DAGNode,
        journey_id: str,
        tenant_id: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        start = time.monotonic()

        # Native nodes (no container)
        if node.subtype in NATIVE_NODES:
            if node.subtype == "control_wait":
                seconds = node.config.get("seconds", 1)
                await asyncio.sleep(seconds)
            latency = (time.monotonic() - start) * 1000
            return {"node_id": node.id, "status": "success", "latency_ms": round(latency, 2)}

        # Container-backed nodes
        image = NODE_IMAGES.get(node.subtype)
        if not image:
            return {"node_id": node.id, "status": "failure", "error": f"Unknown subtype: {node.subtype}"}

        try:
            config = ContainerConfig(
                image=image,
                tenant_id=tenant_id,
                node_id=node.id,
                journey_id=journey_id,
                env={
                    "NODE_TYPE": node.type,
                    "NODE_SUBTYPE": node.subtype,
                    "NODE_CONFIG": str(node.config),
                    "JOURNEY_ID": journey_id,
                    "TENANT_ID": tenant_id,
                },
            )
            info = self.orch.spawn(config)
            await self.broadcast("journey-events", {
                "type": "node_started",
                "journey_id": journey_id,
                "node_id": node.id,
                "container_id": info.container_id,
            })

            # Wait for container to finish (poll status)
            for _ in range(config.timeout_seconds * 2):
                metrics = self.orch.get_status(info.container_id)
                if metrics.status in ("exited", "dead"):
                    break
                await asyncio.sleep(0.5)

            exec_result = self.orch.exec_in_container(info.container_id, "cat /tmp/result.json")
            latency = (time.monotonic() - start) * 1000

            self.orch.stop(info.container_id)

            result = {
                "node_id": node.id,
                "status": "success" if exec_result.exit_code == 0 else "failure",
                "container_id": info.container_id,
                "latency_ms": round(latency, 2),
                "output": exec_result.stdout,
                "error": exec_result.stderr if exec_result.exit_code != 0 else "",
            }
            await self.broadcast("journey-events", {
                "type": "node_completed",
                "journey_id": journey_id,
                **result,
            })
            return result

        except Exception as exc:
            latency = (time.monotonic() - start) * 1000
            logger.warning("execute_node %s error: %s", node.id, exc)
            return {
                "node_id": node.id,
                "status": "failure",
                "latency_ms": round(latency, 2),
                "error": str(exc),
            }

    async def execute_journey(self, dag: JourneyDAG) -> JourneyExecutionResult:
        order = self.topological_sort(dag)
        node_map = {n.id: n for n in dag.nodes}
        edge_map: dict[str, list[DAGEdge]] = defaultdict(list)
        for e in dag.edges:
            edge_map[e.source].append(e)

        results: list[NodeResult] = []
        context: dict[str, Any] = {}
        containers_spawned = 0
        total_start = time.monotonic()

        await self.broadcast("journey-events", {
            "type": "journey_started",
            "journey_id": dag.journey_id,
            "tenant_id": dag.tenant_id,
        })

        for nid in order:
            node = node_map.get(nid)
            if not node:
                continue
            result = await self.execute_node(node, dag.journey_id, dag.tenant_id, context)
            nr = NodeResult(
                node_id=result["node_id"],
                status=result["status"],
                container_id=result.get("container_id"),
                latency_ms=result.get("latency_ms", 0),
                output={"raw": result.get("output", "")},
                error=result.get("error", ""),
            )
            results.append(nr)
            if nr.container_id:
                containers_spawned += 1
            context[nid] = result
            if nr.status == "failure":
                break  # stop on first failure

        total_latency = (time.monotonic() - total_start) * 1000
        overall_status = "completed" if all(r.status == "success" for r in results) else "failed"

        await self.broadcast("journey-events", {
            "type": "journey_completed",
            "journey_id": dag.journey_id,
            "status": overall_status,
            "total_latency_ms": round(total_latency, 2),
        })

        return JourneyExecutionResult(
            journey_id=dag.journey_id,
            tenant_id=dag.tenant_id,
            status=overall_status,
            node_results=results,
            total_latency_ms=round(total_latency, 2),
            containers_spawned=containers_spawned,
        )
```

**Step 5: Update containers/__init__.py**

```python
# src/neural_link/containers/__init__.py
from .orchestrator import ContainerOrchestrator
from .models import ContainerConfig, ContainerInfo, ContainerMetrics, ContainerExecResult
from .journey_models import JourneyDAG, DAGNode, DAGEdge, NodeResult, JourneyExecutionResult
from .journey_executor import JourneyExecutor

__all__ = [
    "ContainerOrchestrator", "ContainerConfig", "ContainerInfo", "ContainerMetrics", "ContainerExecResult",
    "JourneyDAG", "DAGNode", "DAGEdge", "NodeResult", "JourneyExecutionResult", "JourneyExecutor",
]
```

**Step 6: Run tests**

Run: `python -m pytest src/neural_link/tests/test_journey_executor.py -v`
Expected: 4 PASSED

**Step 7: Commit**

```bash
git add src/neural_link/containers/ src/neural_link/tests/test_journey_executor.py
git commit -m "feat(journey): add JourneyExecutor DAG walker with container orchestration"
```

---

### Task 2.2: Journey Execution + Generation API Endpoints

**Files:**
- Modify: `src/neural_link/api/sovereign_gateway.py` (add journey endpoints)
- Test: `src/neural_link/tests/test_journey_endpoints.py`

**Step 1: Write the failing test**

```python
# src/neural_link/tests/test_journey_endpoints.py
import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
        mock_svc.container_orch = MagicMock()
        mock_svc.journey_executor = MagicMock()
        from neural_link.api.sovereign_gateway import app
        yield TestClient(app)


class TestJourneyEndpoints:
    def test_execute_journey(self, client):
        with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
            mock_svc.journey_executor.execute_journey = AsyncMock(
                return_value=MagicMock(
                    journey_id="j1", tenant_id="t1", status="completed",
                    node_results=[], total_latency_ms=420.0,
                    containers_spawned=3, total_cost=0.0,
                    model_dump=lambda: {
                        "journey_id": "j1", "tenant_id": "t1",
                        "status": "completed", "node_results": [],
                        "total_latency_ms": 420.0, "containers_spawned": 3,
                        "total_cost": 0.0,
                    }
                )
            )
            resp = client.post("/api/v1/journeys/execute", json={
                "journey_id": "j1",
                "tenant_id": "t1",
                "nodes": [
                    {"id": "n1", "type": "trigger", "subtype": "trigger_manual", "config": {}},
                ],
                "edges": [],
            })
        assert resp.status_code == 200

    def test_generate_journey(self, client):
        with patch("neural_link.api.sovereign_gateway._svc") as mock_svc:
            mock_svc.interface = MagicMock()
            mock_svc.interface.process_query = AsyncMock(return_value={
                "response": '{"nodes": [], "edges": []}',
            })
            resp = client.post("/api/v1/journeys/generate", json={
                "prompt": "Create a reactivation journey for inactive leads",
                "tenant_id": "t1",
            })
        assert resp.status_code == 200
```

**Step 2: Run test to verify it fails**

Run: `python -m pytest src/neural_link/tests/test_journey_endpoints.py -v`
Expected: FAIL — endpoints don't exist

**Step 3: Add journey endpoints to sovereign_gateway.py**

Add Pydantic models:
```python
# --- Journey Execution Models ---
class JourneyExecuteRequest(BaseModel):
    journey_id: str
    tenant_id: str
    nodes: list[dict[str, Any]]
    edges: list[dict[str, Any]]

class JourneyGenerateRequest(BaseModel):
    prompt: str
    tenant_id: str
    constraints: dict[str, Any] = Field(default_factory=dict)

class JourneySuggestRequest(BaseModel):
    current_dag: dict[str, Any]
    selected_node_id: str
    tenant_id: str
```

Add endpoints:
```python
# --- Journey Execution Endpoints ---

@router.post("/journeys/execute")
async def execute_journey(req: JourneyExecuteRequest):
    try:
        from neural_link.containers import JourneyDAG, DAGNode, DAGEdge, JourneyExecutor
        orch = _svc.container_orch
        if not orch:
            from neural_link.containers import ContainerOrchestrator
            orch = ContainerOrchestrator()
            _svc.container_orch = orch

        async def broadcast(channel, data):
            if _ws_manager.channel_count(channel) > 0:
                await _ws_manager.broadcast(channel, data)

        executor = JourneyExecutor(orch, broadcast)
        dag = JourneyDAG(
            journey_id=req.journey_id,
            tenant_id=req.tenant_id,
            nodes=[DAGNode(**n) for n in req.nodes],
            edges=[DAGEdge(**e) for e in req.edges],
        )
        result = await executor.execute_journey(dag)
        return result.model_dump()
    except Exception as exc:
        logger.warning("execute_journey error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/journeys/generate")
async def generate_journey(req: JourneyGenerateRequest):
    try:
        if not _svc.interface:
            raise HTTPException(status_code=503, detail="AI interface not initialized")
        enhanced_prompt = (
            f"Generate a journey DAG as JSON for tenant {req.tenant_id}. "
            f"User request: {req.prompt}. "
            f"Return JSON with 'nodes' (array of {{id, type, subtype, config, label}}) "
            f"and 'edges' (array of {{source, target, label}}). "
            f"Valid types: trigger, condition, action, control, integration, tracking. "
            f"Constraints: {req.constraints}"
        )
        response = await _svc.interface.process_query(enhanced_prompt)
        return {"prompt": req.prompt, "tenant_id": req.tenant_id, "dag": response}
    except Exception as exc:
        logger.warning("generate_journey error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/journeys/suggest")
async def suggest_next_node(req: JourneySuggestRequest):
    try:
        if not _svc.interface:
            return {"suggestions": []}
        prompt = (
            f"Given this journey DAG: {req.current_dag}, "
            f"the user selected node {req.selected_node_id}. "
            f"Suggest 3 next nodes that would improve this journey. "
            f"Return JSON array of {{type, subtype, label, reason}}."
        )
        response = await _svc.interface.process_query(prompt)
        return {"selected_node_id": req.selected_node_id, "suggestions": response}
    except Exception as exc:
        logger.warning("suggest_next_node error: %s", exc)
        return {"suggestions": []}
```

**Step 4: Run tests**

Run: `python -m pytest src/neural_link/tests/test_journey_endpoints.py -v`
Expected: 2 PASSED

**Step 5: Commit**

```bash
git add src/neural_link/api/sovereign_gateway.py src/neural_link/tests/test_journey_endpoints.py
git commit -m "feat(api): add journey execution, generation, and suggestion endpoints"
```

---

## Phase 3: Frontend — Journey Canvas Core

### Task 3.1: Types + API Client + SWR Hooks

**Files:**
- Create: `frontend/src/types/journey.ts`
- Modify: `frontend/src/lib/gateway.ts` (add journey API functions)
- Create: `frontend/src/modules/journey/hooks/useJourneyApi.ts`
- Create: `frontend/src/modules/journey/hooks/useJourneyWebSocket.ts`

**Step 1: Create journey types**

```typescript
// frontend/src/types/journey.ts
export type NodeType = 'trigger' | 'condition' | 'action' | 'control' | 'integration' | 'tracking';

export type NodeSubtype =
  | 'trigger_manual' | 'trigger_event' | 'trigger_segment' | 'trigger_schedule'
  | 'condition_if' | 'condition_split'
  | 'action_sms' | 'action_email' | 'action_whatsapp' | 'action_webhook' | 'action_tag' | 'action_score'
  | 'control_wait' | 'control_end' | 'control_loop'
  | 'int_sendspeed' | 'int_meta' | 'int_ga'
  | 'track_pageview' | 'track_click' | 'track_conversion';

export type NodeStatus = 'idle' | 'provisioning' | 'running' | 'success' | 'failure' | 'timeout';

export interface NodeSandboxData {
  type: NodeType;
  subtype: NodeSubtype;
  label: string;
  config: Record<string, unknown>;
  tenantId: string;
  containerId?: string;
  status: NodeStatus;
  metrics?: {
    latencyMs: number;
    memoryMb: number;
    cpuPercent: number;
    startedAt?: string;
    completedAt?: string;
  };
  testCode?: string;
}

export interface JourneyDAG {
  journeyId: string;
  tenantId: string;
  nodes: Array<{ id: string; type: NodeType; subtype: NodeSubtype; config: Record<string, unknown>; label?: string }>;
  edges: Array<{ source: string; target: string; label?: string }>;
}

export interface NodeResult {
  nodeId: string;
  status: 'success' | 'failure' | 'timeout' | 'skipped';
  containerId?: string;
  latencyMs: number;
  output?: Record<string, unknown>;
  error?: string;
}

export interface JourneyExecutionResult {
  journeyId: string;
  tenantId: string;
  status: 'running' | 'completed' | 'failed';
  nodeResults: NodeResult[];
  totalLatencyMs: number;
  totalCost: number;
  containersSpawned: number;
}

export interface JourneyEvent {
  type: 'journey_started' | 'node_started' | 'node_completed' | 'journey_completed'
    | 'container_spawned' | 'container_stopped';
  journeyId?: string;
  nodeId?: string;
  containerId?: string;
  status?: string;
  latencyMs?: number;
  timestamp?: string;
}

export interface TenantConfig {
  tenantId: string;
  name: string;
  plan: 'starter' | 'pro' | 'enterprise';
  sla: {
    maxLatencyMs: number;
    maxContainers: number;
    containerMemoryMb: number;
  };
  branding: {
    primaryColor: string;
    logo: string;
  };
  allowedNodeTypes: NodeType[];
  integrations: string[];
}

export interface ContainerStatus {
  containerId: string;
  status: string;
  memoryMb: number;
  cpuPercent: number;
  logs: string;
}

// Icon mapping for NodePalette
export const NODE_ICONS: Record<NodeSubtype, string> = {
  trigger_manual: 'Play',
  trigger_event: 'Zap',
  trigger_segment: 'Users',
  trigger_schedule: 'Clock',
  condition_if: 'GitBranch',
  condition_split: 'Split',
  action_sms: 'MessageSquare',
  action_email: 'Mail',
  action_whatsapp: 'MessageCircle',
  action_webhook: 'Globe',
  action_tag: 'Tag',
  action_score: 'TrendingUp',
  control_wait: 'Timer',
  control_end: 'Square',
  control_loop: 'RefreshCw',
  int_sendspeed: 'Send',
  int_meta: 'Facebook',
  int_ga: 'BarChart3',
  track_pageview: 'Eye',
  track_click: 'MousePointer',
  track_conversion: 'Target',
};

export const NODE_CATEGORIES: Record<string, { label: string; subtypes: NodeSubtype[] }> = {
  trigger: { label: 'Gatilhos', subtypes: ['trigger_manual', 'trigger_event', 'trigger_segment', 'trigger_schedule'] },
  condition: { label: 'Condições', subtypes: ['condition_if', 'condition_split'] },
  action: { label: 'Ações', subtypes: ['action_sms', 'action_email', 'action_whatsapp', 'action_webhook', 'action_tag', 'action_score'] },
  control: { label: 'Controle', subtypes: ['control_wait', 'control_end', 'control_loop'] },
  integration: { label: 'Integrações', subtypes: ['int_sendspeed', 'int_meta', 'int_ga'] },
  tracking: { label: 'Rastreamento', subtypes: ['track_pageview', 'track_click', 'track_conversion'] },
};

export const SUBTYPE_LABELS: Record<NodeSubtype, string> = {
  trigger_manual: 'Manual', trigger_event: 'Evento', trigger_segment: 'Segmento', trigger_schedule: 'Agendado',
  condition_if: 'Condicional', condition_split: 'Split A/B',
  action_sms: 'SMS', action_email: 'Email', action_whatsapp: 'WhatsApp', action_webhook: 'Webhook', action_tag: 'Tag', action_score: 'Score',
  control_wait: 'Esperar', control_end: 'Finalizar', control_loop: 'Loop',
  int_sendspeed: 'SendSpeed', int_meta: 'Meta', int_ga: 'Analytics',
  track_pageview: 'PageView', track_click: 'Click', track_conversion: 'Conversão',
};
```

**Step 2: Add API functions to gateway.ts**

Append to `frontend/src/lib/gateway.ts`:

```typescript
// --- Journey Builder API ---
export async function executeJourney(dag: {
  journeyId: string; tenantId: string;
  nodes: Array<{ id: string; type: string; subtype: string; config: Record<string, unknown> }>;
  edges: Array<{ source: string; target: string; label?: string }>;
}) {
  const res = await fetch(`${BASE}/api/v1/journeys/execute`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      journey_id: dag.journeyId, tenant_id: dag.tenantId,
      nodes: dag.nodes, edges: dag.edges,
    }),
  });
  if (!res.ok) throw new Error(`Execute journey failed: ${res.status}`);
  return res.json();
}

export async function generateJourney(prompt: string, tenantId: string, constraints?: Record<string, unknown>) {
  const res = await fetch(`${BASE}/api/v1/journeys/generate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt, tenant_id: tenantId, constraints: constraints || {} }),
  });
  if (!res.ok) throw new Error(`Generate journey failed: ${res.status}`);
  return res.json();
}

export async function suggestNextNode(currentDag: Record<string, unknown>, selectedNodeId: string, tenantId: string) {
  const res = await fetch(`${BASE}/api/v1/journeys/suggest`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ current_dag: currentDag, selected_node_id: selectedNodeId, tenant_id: tenantId }),
  });
  if (!res.ok) throw new Error(`Suggest failed: ${res.status}`);
  return res.json();
}

export async function fetchContainerStatus(containerId: string) {
  const res = await fetch(`${BASE}/api/v1/containers/${containerId}/status`);
  if (!res.ok) throw new Error(`Container status failed: ${res.status}`);
  return res.json();
}

export async function fetchContainers(tenantId: string) {
  const res = await fetch(`${BASE}/api/v1/containers?tenant_id=${tenantId}`);
  if (!res.ok) throw new Error(`List containers failed: ${res.status}`);
  return res.json();
}
```

**Step 3: Create SWR hooks**

```typescript
// frontend/src/modules/journey/hooks/useJourneyApi.ts
import useSWR from "swr";
import { swrFetcher } from "@/lib/gateway";

export function useContainers(tenantId: string) {
  return useSWR(
    tenantId ? `/api/v1/containers?tenant_id=${tenantId}` : null,
    swrFetcher,
    { refreshInterval: 5000 }
  );
}

export function useContainerStatus(containerId: string | null) {
  return useSWR(
    containerId ? `/api/v1/containers/${containerId}/status` : null,
    swrFetcher,
    { refreshInterval: 2000 }
  );
}

export function usePipelineStats() {
  return useSWR("/api/v1/pipeline/stats", swrFetcher, { refreshInterval: 15000 });
}

export function useKpiCostQuality() {
  return useSWR("/api/v1/kpi/cost-quality", swrFetcher, { refreshInterval: 30000 });
}

export function useKpiTrends() {
  return useSWR("/api/v1/kpi/trends", swrFetcher, { refreshInterval: 60000 });
}

export function useKpiAnomalies() {
  return useSWR("/api/v1/kpi/anomalies", swrFetcher, { refreshInterval: 30000 });
}

export function useKpiHeatmap() {
  return useSWR("/api/v1/kpi/agents/heatmap", swrFetcher, { refreshInterval: 60000 });
}

export function useClusterHealth() {
  return useSWR("/api/v1/cluster/health", swrFetcher, { refreshInterval: 10000 });
}
```

**Step 4: Create WebSocket hook**

```typescript
// frontend/src/modules/journey/hooks/useJourneyWebSocket.ts
import { useState, useEffect, useRef, useCallback } from "react";
import type { JourneyEvent } from "@/types/journey";

const WS_BASE = process.env.NEXT_PUBLIC_GATEWAY_WS_URL || "ws://localhost:8766";

export function useJourneyWebSocket() {
  const [events, setEvents] = useState<JourneyEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const maxRetry = 30000;

  const connect = useCallback(() => {
    const ws = new WebSocket(`${WS_BASE}/api/v1/ws/journey-events`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      retryRef.current = 0;
    };

    ws.onmessage = (evt) => {
      try {
        const data: JourneyEvent = JSON.parse(evt.data);
        setEvents((prev) => [...prev.slice(-200), data]);
      } catch { /* ignore parse errors */ }
    };

    ws.onclose = () => {
      setConnected(false);
      const delay = Math.min(1000 * Math.pow(2, retryRef.current), maxRetry);
      retryRef.current++;
      setTimeout(connect, delay);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    connect();
    return () => {
      wsRef.current?.close();
    };
  }, [connect]);

  const clearEvents = useCallback(() => setEvents([]), []);

  return { events, connected, clearEvents };
}
```

**Step 5: Commit**

```bash
cd frontend && git add src/types/journey.ts src/lib/gateway.ts src/modules/journey/
git commit -m "feat(journey-ui): add types, API client, SWR hooks, and WebSocket hook"
```

---

### Task 3.2: NodeSandbox Component

**Files:**
- Create: `frontend/src/modules/journey/NodeSandbox.tsx`

**Step 1: Write the component**

```tsx
// frontend/src/modules/journey/NodeSandbox.tsx
"use client";
import { memo } from "react";
import { Handle, Position, type NodeProps } from "@xyflow/react";
import { motion } from "framer-motion";
import type { NodeSandboxData, NodeStatus } from "@/types/journey";
import { SUBTYPE_LABELS } from "@/types/journey";

const STATUS_COLORS: Record<NodeStatus, string> = {
  idle: "#606070",
  provisioning: "#448aff",
  running: "#448aff",
  success: "#00e676",
  failure: "#ff1744",
  timeout: "#ffab00",
};

const STATUS_PULSE: Record<NodeStatus, boolean> = {
  idle: false,
  provisioning: true,
  running: true,
  success: false,
  failure: true,
  timeout: false,
};

function NodeSandbox({ data, selected }: NodeProps & { data: NodeSandboxData }) {
  const color = STATUS_COLORS[data.status];
  const pulse = STATUS_PULSE[data.status];
  const label = data.label || SUBTYPE_LABELS[data.subtype] || data.subtype;

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className="relative"
      style={{
        background: "var(--color-surface)",
        border: `2px solid ${selected ? "var(--color-accent)" : color}`,
        borderRadius: 12,
        padding: "12px 16px",
        minWidth: 160,
        boxShadow: selected ? `0 0 20px ${color}40` : `0 2px 8px #00000040`,
      }}
    >
      <Handle type="target" position={Position.Top} style={{ background: color }} />

      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {/* Status dot */}
        <motion.div
          animate={pulse ? { scale: [1, 1.3, 1], opacity: [1, 0.6, 1] } : {}}
          transition={pulse ? { repeat: Infinity, duration: 1.5 } : {}}
          style={{
            width: 10, height: 10, borderRadius: "50%",
            background: color, flexShrink: 0,
          }}
        />
        <div>
          <div style={{ color: "var(--color-text)", fontSize: 13, fontWeight: 600 }}>
            {label}
          </div>
          <div style={{ color: "var(--color-text-muted)", fontSize: 11 }}>
            {data.type}
          </div>
        </div>
      </div>

      {/* Metrics line */}
      {data.metrics && (
        <div style={{
          marginTop: 6, fontSize: 11,
          color: data.metrics.latencyMs > 1000 ? "var(--color-error)" :
                 data.metrics.latencyMs > 500 ? "var(--color-warning)" : "var(--color-success)",
          fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        }}>
          {data.metrics.latencyMs.toFixed(0)}ms
          {data.metrics.memoryMb > 0 && ` · ${data.metrics.memoryMb.toFixed(0)}MB`}
        </div>
      )}

      {/* Container ID badge */}
      {data.containerId && (
        <div style={{
          marginTop: 4, fontSize: 10,
          color: "var(--color-text-muted)",
          fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        }}>
          {data.containerId.slice(0, 12)}
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={{ background: color }} />

      {/* Conditional: two outputs for condition nodes */}
      {data.type === "condition" && (
        <>
          <Handle
            type="source"
            position={Position.Right}
            id="false"
            style={{ background: "var(--color-error)", top: "50%" }}
          />
        </>
      )}
    </motion.div>
  );
}

export default memo(NodeSandbox);
```

**Step 2: Commit**

```bash
git add src/modules/journey/NodeSandbox.tsx
git commit -m "feat(journey-ui): add NodeSandbox React Flow custom node with status/metrics"
```

---

### Task 3.3: AnimatedEdge Component

**Files:**
- Create: `frontend/src/modules/journey/AnimatedEdge.tsx`

**Step 1: Write the component**

```tsx
// frontend/src/modules/journey/AnimatedEdge.tsx
"use client";
import { memo } from "react";
import { BaseEdge, getBezierPath, type EdgeProps } from "@xyflow/react";

interface AnimatedEdgeData {
  status: 'idle' | 'running' | 'success' | 'failure';
  latencyMs?: number;
  slaMaxMs?: number;
}

function getEdgeColor(data?: AnimatedEdgeData): string {
  if (!data || data.status === "idle") return "#606070";
  if (data.status === "failure") return "#ff1744";
  if (data.status === "running") return "#448aff";
  // success — color by SLA
  const ms = data.latencyMs ?? 0;
  if (ms < 500) return "#00e676";
  if (ms < 1000) return "#ffab00";
  return "#ff1744";
}

function AnimatedEdge(props: EdgeProps & { data?: AnimatedEdgeData }) {
  const { sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data, markerEnd } = props;
  const [edgePath, labelX, labelY] = getBezierPath({ sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition });
  const color = getEdgeColor(data);
  const isAnimated = data?.status === "running";
  const isDashed = data?.status === "idle";

  return (
    <>
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: 2,
          strokeDasharray: isDashed ? "8 4" : "none",
          filter: isAnimated ? `drop-shadow(0 0 4px ${color})` : "none",
          transition: "stroke 0.3s, stroke-dasharray 0.3s",
        }}
      />

      {/* Animated particle for running state */}
      {isAnimated && (
        <circle r={4} fill={color}>
          <animateMotion dur="1.5s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}

      {/* Latency label for completed edges */}
      {data?.status === "success" && data.latencyMs != null && (
        <foreignObject
          x={labelX - 25} y={labelY - 10}
          width={50} height={20}
          style={{ overflow: "visible" }}
        >
          <div style={{
            background: "#0e1117e0",
            color,
            fontSize: 10,
            fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
            padding: "1px 6px",
            borderRadius: 4,
            textAlign: "center",
            whiteSpace: "nowrap",
          }}>
            {data.latencyMs.toFixed(0)}ms
          </div>
        </foreignObject>
      )}
    </>
  );
}

export default memo(AnimatedEdge);
```

**Step 2: Commit**

```bash
git add src/modules/journey/AnimatedEdge.tsx
git commit -m "feat(journey-ui): add AnimatedEdge with SLA colors and particle animation"
```

---

### Task 3.4: NodePalette Sidebar

**Files:**
- Create: `frontend/src/modules/journey/NodePalette.tsx`

**Step 1: Write the component**

```tsx
// frontend/src/modules/journey/NodePalette.tsx
"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { NodeSubtype, NodeType } from "@/types/journey";
import { NODE_CATEGORIES, SUBTYPE_LABELS } from "@/types/journey";

interface NodePaletteProps {
  onDragStart: (subtype: NodeSubtype, type: NodeType) => void;
}

export default function NodePalette({ onDragStart }: NodePaletteProps) {
  const [expanded, setExpanded] = useState<string | null>("trigger");

  return (
    <div style={{
      width: 220, background: "var(--color-surface)", borderRight: "1px solid var(--color-border)",
      height: "100%", overflowY: "auto", padding: "8px 0",
    }}>
      <div style={{ padding: "8px 12px", color: "var(--color-text-secondary)", fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: 1 }}>
        Componentes
      </div>

      {Object.entries(NODE_CATEGORIES).map(([key, cat]) => (
        <div key={key}>
          <button
            onClick={() => setExpanded(expanded === key ? null : key)}
            style={{
              width: "100%", padding: "8px 12px", display: "flex", justifyContent: "space-between",
              alignItems: "center", background: "none", border: "none", cursor: "pointer",
              color: "var(--color-text)", fontSize: 13, fontWeight: 600,
            }}
          >
            {cat.label}
            <span style={{ fontSize: 10, color: "var(--color-text-muted)" }}>
              {expanded === key ? "▼" : "▶"}
            </span>
          </button>

          <AnimatePresence>
            {expanded === key && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                style={{ overflow: "hidden" }}
              >
                {cat.subtypes.map((subtype) => (
                  <div
                    key={subtype}
                    draggable
                    onDragStart={(e) => {
                      e.dataTransfer.setData("application/reactflow-subtype", subtype);
                      e.dataTransfer.setData("application/reactflow-type", key);
                      e.dataTransfer.effectAllowed = "move";
                      onDragStart(subtype, key as NodeType);
                    }}
                    style={{
                      padding: "6px 12px 6px 24px", cursor: "grab",
                      color: "var(--color-text-secondary)", fontSize: 12,
                      transition: "background 0.15s",
                    }}
                    onMouseEnter={(e) => (e.currentTarget.style.background = "var(--color-surface-alt)")}
                    onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
                  >
                    {SUBTYPE_LABELS[subtype]}
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      ))}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add src/modules/journey/NodePalette.tsx
git commit -m "feat(journey-ui): add NodePalette drag-and-drop sidebar"
```

---

### Task 3.5: DebugPanel Component

**Files:**
- Create: `frontend/src/modules/journey/DebugPanel.tsx`

**Step 1: Write the component**

```tsx
// frontend/src/modules/journey/DebugPanel.tsx
"use client";
import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useContainerStatus } from "./hooks/useJourneyApi";

interface DebugPanelProps {
  containerId: string | null;
  nodeId: string | null;
  testCode?: string;
}

export default function DebugPanel({ containerId, nodeId, testCode }: DebugPanelProps) {
  const [collapsed, setCollapsed] = useState(true);
  const [tab, setTab] = useState<"logs" | "metrics" | "test">("logs");
  const { data: status } = useContainerStatus(containerId);

  if (!nodeId) return null;

  return (
    <motion.div
      style={{
        position: "absolute", bottom: 0, left: 0, right: 0,
        background: "var(--color-surface)", borderTop: "1px solid var(--color-border)",
        zIndex: 50,
      }}
    >
      <button
        onClick={() => setCollapsed(!collapsed)}
        style={{
          width: "100%", padding: "6px 12px", display: "flex", justifyContent: "space-between",
          background: "var(--color-surface-alt)", border: "none", cursor: "pointer",
          color: "var(--color-text)", fontSize: 12, fontWeight: 600,
        }}
      >
        <span>Debug: {nodeId} {containerId ? `(${containerId.slice(0, 12)})` : ""}</span>
        <span>{collapsed ? "▲" : "▼"}</span>
      </button>

      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 200 }}
            exit={{ height: 0 }}
            style={{ overflow: "hidden" }}
          >
            {/* Tabs */}
            <div style={{ display: "flex", gap: 0, borderBottom: "1px solid var(--color-border)" }}>
              {(["logs", "metrics", "test"] as const).map((t) => (
                <button
                  key={t}
                  onClick={() => setTab(t)}
                  style={{
                    padding: "6px 16px", background: tab === t ? "var(--color-surface-alt)" : "transparent",
                    border: "none", color: tab === t ? "var(--color-accent)" : "var(--color-text-muted)",
                    cursor: "pointer", fontSize: 12, fontWeight: 500, textTransform: "capitalize",
                  }}
                >
                  {t}
                </button>
              ))}
            </div>

            {/* Content */}
            <div style={{ padding: 12, height: 154, overflowY: "auto" }}>
              {tab === "logs" && (
                <pre style={{
                  fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
                  fontSize: 11, color: "var(--color-text-secondary)",
                  whiteSpace: "pre-wrap", margin: 0,
                }}>
                  {status?.logs || "No logs available. Run the journey to see container output."}
                </pre>
              )}

              {tab === "metrics" && status && (
                <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                  <div>Status: <span style={{ color: status.status === "running" ? "var(--color-accent)" : "var(--color-text)" }}>{status.status}</span></div>
                  <div>Memory: {status.memoryMb?.toFixed(1)} MB</div>
                  <div>CPU: {status.cpuPercent?.toFixed(1)}%</div>
                </div>
              )}

              {tab === "test" && (
                <pre style={{
                  fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
                  fontSize: 11, color: "var(--color-text-secondary)",
                  whiteSpace: "pre-wrap", margin: 0,
                }}>
                  {testCode || "// No test code defined for this node"}
                </pre>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
```

**Step 2: Commit**

```bash
git add src/modules/journey/DebugPanel.tsx
git commit -m "feat(journey-ui): add DebugPanel with logs, metrics, and test tabs"
```

---

### Task 3.6: JourneyBuilder Main Component + Page Route

**Files:**
- Create: `frontend/src/modules/journey/JourneyBuilder.tsx`
- Modify: `frontend/src/app/dashboard/jornadas/page.tsx` (replace old JourneyCanvas with new JourneyBuilder)
- Modify: `frontend/src/app/dashboard/layout.tsx` (update TABS label if needed)

**Step 1: Write the JourneyBuilder**

```tsx
// frontend/src/modules/journey/JourneyBuilder.tsx
"use client";
import { useCallback, useRef, useState } from "react";
import {
  ReactFlow, Background, Controls, MiniMap,
  useNodesState, useEdgesState, addEdge,
  type Connection, type Node, type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { motion } from "framer-motion";
import NodeSandbox from "./NodeSandbox";
import AnimatedEdge from "./AnimatedEdge";
import NodePalette from "./NodePalette";
import DebugPanel from "./DebugPanel";
import { useJourneyWebSocket } from "./hooks/useJourneyWebSocket";
import { executeJourney } from "@/lib/gateway";
import type { NodeSandboxData, NodeSubtype, NodeType, NodeStatus } from "@/types/journey";

const nodeTypes = { sandbox: NodeSandbox };
const edgeTypes = { animated: AnimatedEdge };

let nodeIdCounter = 0;
function nextId() {
  return `node-${++nodeIdCounter}`;
}

export default function JourneyBuilder() {
  const reactFlowWrapper = useRef<HTMLDivElement>(null);
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [journeyStatus, setJourneyStatus] = useState<"idle" | "running" | "completed" | "failed">("idle");
  const [journeyName, setJourneyName] = useState("Nova Jornada");
  const tenantId = "default-tenant";

  const { events } = useJourneyWebSocket();

  // Update node statuses from WS events
  const lastProcessedRef = useRef(0);
  if (events.length > lastProcessedRef.current) {
    const newEvents = events.slice(lastProcessedRef.current);
    lastProcessedRef.current = events.length;
    for (const evt of newEvents) {
      if (evt.type === "node_started" && evt.nodeId) {
        setNodes((nds) => nds.map((n) =>
          n.id === evt.nodeId ? { ...n, data: { ...n.data, status: "running" as NodeStatus, containerId: evt.containerId } } : n
        ));
        if (evt.nodeId) {
          setEdges((eds) => eds.map((e) =>
            e.target === evt.nodeId ? { ...e, data: { ...e.data, status: "running" } } : e
          ));
        }
      }
      if (evt.type === "node_completed" && evt.nodeId) {
        const status: NodeStatus = evt.status === "success" ? "success" : "failure";
        setNodes((nds) => nds.map((n) =>
          n.id === evt.nodeId ? {
            ...n, data: {
              ...n.data, status,
              metrics: { latencyMs: evt.latencyMs || 0, memoryMb: 0, cpuPercent: 0 },
            },
          } : n
        ));
        setEdges((eds) => eds.map((e) =>
          e.target === evt.nodeId ? { ...e, data: { ...e.data, status: status === "success" ? "success" : "failure", latencyMs: evt.latencyMs } } : e
        ));
      }
      if (evt.type === "journey_completed") {
        setJourneyStatus(evt.status === "completed" ? "completed" : "failed");
      }
    }
  }

  const onConnect = useCallback((connection: Connection) => {
    setEdges((eds) => addEdge({
      ...connection, type: "animated",
      data: { status: "idle" },
    }, eds));
  }, [setEdges]);

  const onDrop = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    const subtype = event.dataTransfer.getData("application/reactflow-subtype") as NodeSubtype;
    const type = event.dataTransfer.getData("application/reactflow-type") as NodeType;
    if (!subtype || !type) return;

    const bounds = reactFlowWrapper.current?.getBoundingClientRect();
    if (!bounds) return;

    const id = nextId();
    const newNode: Node = {
      id,
      type: "sandbox",
      position: { x: event.clientX - bounds.left - 80, y: event.clientY - bounds.top - 20 },
      data: {
        type, subtype, label: "", config: {},
        tenantId, status: "idle" as NodeStatus,
      } satisfies NodeSandboxData,
    };
    setNodes((nds) => [...nds, newNode]);
  }, [setNodes, tenantId]);

  const onDragOver = useCallback((event: React.DragEvent) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "move";
  }, []);

  const onNodeClick = useCallback((_: React.MouseEvent, node: Node) => {
    setSelectedNode(node.id);
  }, []);

  const handleRun = async () => {
    if (nodes.length === 0) return;
    setJourneyStatus("running");

    // Reset all nodes to idle
    setNodes((nds) => nds.map((n) => ({ ...n, data: { ...n.data, status: "idle" as NodeStatus, metrics: undefined, containerId: undefined } })));
    setEdges((eds) => eds.map((e) => ({ ...e, data: { ...e.data, status: "idle" } })));

    const dag = {
      journeyId: `journey-${Date.now()}`,
      tenantId,
      nodes: nodes.map((n) => ({
        id: n.id,
        type: (n.data as NodeSandboxData).type,
        subtype: (n.data as NodeSandboxData).subtype,
        config: (n.data as NodeSandboxData).config,
      })),
      edges: edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: "",
      })),
    };

    try {
      await executeJourney(dag);
    } catch (err) {
      setJourneyStatus("failed");
      console.error("Journey execution failed:", err);
    }
  };

  const selectedNodeData = nodes.find((n) => n.id === selectedNode);

  return (
    <div style={{ display: "flex", height: "100%", position: "relative" }}>
      <NodePalette onDragStart={() => {}} />

      <div ref={reactFlowWrapper} style={{ flex: 1, position: "relative" }}>
        {/* Toolbar */}
        <div style={{
          position: "absolute", top: 0, left: 0, right: 0, zIndex: 10,
          display: "flex", alignItems: "center", gap: 12, padding: "10px 16px",
          background: "var(--color-bg)cc", backdropFilter: "blur(8px)",
          borderBottom: "1px solid var(--color-border)",
        }}>
          <input
            value={journeyName}
            onChange={(e) => setJourneyName(e.target.value)}
            style={{
              background: "transparent", border: "none", color: "var(--color-text)",
              fontSize: 16, fontWeight: 700, outline: "none", width: 200,
            }}
          />
          <div style={{
            padding: "2px 10px", borderRadius: 12, fontSize: 11, fontWeight: 600,
            background: journeyStatus === "running" ? "var(--color-accent)20" :
                        journeyStatus === "completed" ? "var(--color-success)20" :
                        journeyStatus === "failed" ? "var(--color-error)20" : "var(--color-border)40",
            color: journeyStatus === "running" ? "var(--color-accent)" :
                   journeyStatus === "completed" ? "var(--color-success)" :
                   journeyStatus === "failed" ? "var(--color-error)" : "var(--color-text-muted)",
          }}>
            {journeyStatus}
          </div>
          <div style={{ flex: 1 }} />
          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            onClick={handleRun}
            disabled={journeyStatus === "running" || nodes.length === 0}
            style={{
              padding: "6px 20px", borderRadius: 8, border: "none", cursor: "pointer",
              background: journeyStatus === "running" ? "var(--color-border)" : "var(--color-success)",
              color: "#fff", fontSize: 13, fontWeight: 600,
              opacity: journeyStatus === "running" || nodes.length === 0 ? 0.5 : 1,
            }}
          >
            {journeyStatus === "running" ? "Running..." : "Run"}
          </motion.button>
        </div>

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onDrop={onDrop}
          onDragOver={onDragOver}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          proOptions={{ hideAttribution: true }}
          colorMode="dark"
          fitView
          style={{ paddingTop: 52 }}
        >
          <Background gap={20} size={1} color="#ffffff08" />
          <Controls position="bottom-right" />
          <MiniMap
            nodeColor={(n) => {
              const d = n.data as NodeSandboxData;
              if (d.status === "success") return "#00e676";
              if (d.status === "failure") return "#ff1744";
              if (d.status === "running") return "#448aff";
              return "#606070";
            }}
            style={{ background: "var(--color-surface)" }}
          />
        </ReactFlow>

        <DebugPanel
          containerId={(selectedNodeData?.data as NodeSandboxData)?.containerId || null}
          nodeId={selectedNode}
          testCode={(selectedNodeData?.data as NodeSandboxData)?.testCode}
        />
      </div>
    </div>
  );
}
```

**Step 2: Update the jornadas page**

Replace `frontend/src/app/dashboard/jornadas/page.tsx`:

```tsx
// frontend/src/app/dashboard/jornadas/page.tsx
import dynamic from "next/dynamic";

const JourneyBuilder = dynamic(
  () => import("@/modules/journey/JourneyBuilder"),
  { ssr: false }
);

export default function JornadasPage() {
  return (
    <div style={{ height: "calc(100vh - 120px)" }}>
      <JourneyBuilder />
    </div>
  );
}
```

**Step 3: Commit**

```bash
git add src/modules/journey/JourneyBuilder.tsx src/app/dashboard/jornadas/page.tsx
git commit -m "feat(journey-ui): add JourneyBuilder with canvas, toolbar, palette, debug panel"
```

---

## Phase 4: Frontend — CopilotSidebar + KPI Integration

### Task 4.1: CopilotSidebar

**Files:**
- Create: `frontend/src/modules/journey/CopilotSidebar.tsx`
- Modify: `frontend/src/modules/journey/JourneyBuilder.tsx` (add sidebar toggle)

**Step 1: Write CopilotSidebar**

```tsx
// frontend/src/modules/journey/CopilotSidebar.tsx
"use client";
import { useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { generateJourney, suggestNextNode } from "@/lib/gateway";

interface CopilotSidebarProps {
  open: boolean;
  onClose: () => void;
  tenantId: string;
  currentDag: Record<string, unknown>;
  selectedNodeId: string | null;
  onDAGGenerated: (dag: { nodes: unknown[]; edges: unknown[] }) => void;
}

export default function CopilotSidebar({
  open, onClose, tenantId, currentDag, selectedNodeId, onDAGGenerated,
}: CopilotSidebarProps) {
  const [tab, setTab] = useState<"chat" | "suggest" | "generate">("generate");
  const [prompt, setPrompt] = useState("");
  const [messages, setMessages] = useState<Array<{ role: string; content: string }>>([]);
  const [suggestions, setSuggestions] = useState<unknown[]>([]);
  const [loading, setLoading] = useState(false);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const handleGenerate = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    try {
      const result = await generateJourney(prompt, tenantId);
      setMessages((prev) => [...prev,
        { role: "user", content: prompt },
        { role: "assistant", content: `Generated journey with ${result.dag?.response ? "AI response" : "error"}` },
      ]);
      if (result.dag) onDAGGenerated(result.dag);
      setPrompt("");
    } catch (err) {
      setMessages((prev) => [...prev, { role: "assistant", content: `Error: ${err}` }]);
    } finally {
      setLoading(false);
    }
  };

  const handleSuggest = async () => {
    if (!selectedNodeId) return;
    setLoading(true);
    try {
      const result = await suggestNextNode(currentDag, selectedNodeId, tenantId);
      setSuggestions(result.suggestions || []);
    } catch { setSuggestions([]); }
    finally { setLoading(false); }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          style={{
            background: "var(--color-surface)", borderLeft: "1px solid var(--color-border)",
            height: "100%", overflow: "hidden", display: "flex", flexDirection: "column",
          }}
        >
          {/* Header */}
          <div style={{
            padding: "12px 16px", display: "flex", justifyContent: "space-between",
            alignItems: "center", borderBottom: "1px solid var(--color-border)",
          }}>
            <span style={{ color: "var(--color-text)", fontWeight: 700, fontSize: 14 }}>AI Copilot</span>
            <button onClick={onClose} style={{ background: "none", border: "none", color: "var(--color-text-muted)", cursor: "pointer", fontSize: 18 }}>×</button>
          </div>

          {/* Tabs */}
          <div style={{ display: "flex", borderBottom: "1px solid var(--color-border)" }}>
            {(["generate", "suggest", "chat"] as const).map((t) => (
              <button
                key={t}
                onClick={() => { setTab(t); if (t === "suggest") handleSuggest(); }}
                style={{
                  flex: 1, padding: "8px 0", background: tab === t ? "var(--color-surface-alt)" : "transparent",
                  border: "none", color: tab === t ? "var(--color-accent)" : "var(--color-text-muted)",
                  cursor: "pointer", fontSize: 12, fontWeight: 500, textTransform: "capitalize",
                }}
              >
                {t === "generate" ? "Gerar" : t === "suggest" ? "Sugerir" : "Chat"}
              </button>
            ))}
          </div>

          {/* Content */}
          <div style={{ flex: 1, padding: 12, overflowY: "auto" }}>
            {tab === "generate" && (
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div style={{ color: "var(--color-text-secondary)", fontSize: 12 }}>
                  Descreva a jornada que deseja criar em linguagem natural.
                </div>
                <textarea
                  ref={inputRef}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Ex: Crie uma jornada de reativação para leads inativos há 30 dias..."
                  style={{
                    width: "100%", minHeight: 80, padding: 10, borderRadius: 8,
                    background: "var(--color-bg)", border: "1px solid var(--color-border)",
                    color: "var(--color-text)", fontSize: 12, resize: "vertical",
                    fontFamily: "inherit",
                  }}
                />
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleGenerate}
                  disabled={loading || !prompt.trim()}
                  style={{
                    padding: "8px 16px", borderRadius: 8, border: "none", cursor: "pointer",
                    background: "var(--color-accent)", color: "#fff", fontSize: 13, fontWeight: 600,
                    opacity: loading || !prompt.trim() ? 0.5 : 1,
                  }}
                >
                  {loading ? "Gerando..." : "Gerar Jornada"}
                </motion.button>
              </div>
            )}

            {tab === "suggest" && (
              <div style={{ fontSize: 12, color: "var(--color-text-secondary)" }}>
                {!selectedNodeId && "Selecione um nó no canvas para ver sugestões."}
                {selectedNodeId && suggestions.length === 0 && !loading && "Nenhuma sugestão disponível."}
                {loading && "Buscando sugestões..."}
                {(suggestions as Array<Record<string, string>>).map((s, i) => (
                  <div key={i} style={{ padding: 8, marginBottom: 6, background: "var(--color-surface-alt)", borderRadius: 8 }}>
                    <div style={{ fontWeight: 600, color: "var(--color-text)" }}>{s.label || s.subtype}</div>
                    <div style={{ fontSize: 11, color: "var(--color-text-muted)" }}>{s.reason}</div>
                  </div>
                ))}
              </div>
            )}

            {tab === "chat" && (
              <div style={{ fontSize: 12 }}>
                {messages.map((m, i) => (
                  <div key={i} style={{
                    padding: 8, marginBottom: 6, borderRadius: 8,
                    background: m.role === "user" ? "var(--color-accent)15" : "var(--color-surface-alt)",
                    color: "var(--color-text-secondary)",
                  }}>
                    {m.content}
                  </div>
                ))}
              </div>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
```

**Step 2: Update JourneyBuilder to include CopilotSidebar toggle**

In `JourneyBuilder.tsx`, add a state `const [copilotOpen, setCopilotOpen] = useState(false)` and add a toggle button in the toolbar and render `<CopilotSidebar>` after the canvas div.

**Step 3: Commit**

```bash
git add src/modules/journey/CopilotSidebar.tsx src/modules/journey/JourneyBuilder.tsx
git commit -m "feat(journey-ui): add CopilotSidebar with generate, suggest, and chat tabs"
```

---

### Task 4.2: JourneyKPI Dashboard Tab

**Files:**
- Create: `frontend/src/modules/journey/JourneyKPI.tsx`

**Step 1: Write KPI component using existing hooks**

```tsx
// frontend/src/modules/journey/JourneyKPI.tsx
"use client";
import { usePipelineStats, useKpiCostQuality, useKpiTrends, useKpiAnomalies, useKpiHeatmap, useClusterHealth } from "./hooks/useJourneyApi";

export default function JourneyKPI() {
  const { data: pipeline } = usePipelineStats();
  const { data: costQuality } = useKpiCostQuality();
  const { data: trends } = useKpiTrends();
  const { data: anomalies } = useKpiAnomalies();
  const { data: heatmap } = useKpiHeatmap();
  const { data: health } = useClusterHealth();

  const cards = [
    { label: "Cost/Exec", value: costQuality?.avg_cost ? `$${costQuality.avg_cost.toFixed(4)}` : "—", color: "var(--color-accent)" },
    { label: "Avg SLA", value: pipeline?.avg_latency ? `${pipeline.avg_latency.toFixed(0)}ms` : "—", color: "var(--color-success)" },
    { label: "Success Rate", value: pipeline?.success_rate ? `${(pipeline.success_rate * 100).toFixed(1)}%` : "—", color: "var(--color-success)" },
    { label: "Active Containers", value: health?.services?.length?.toString() || "0", color: "var(--color-warning)" },
  ];

  return (
    <div style={{ padding: 16, overflowY: "auto", height: "100%" }}>
      {/* KPI Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 16 }}>
        {cards.map((c) => (
          <div key={c.label} style={{
            background: "var(--color-surface)", borderRadius: 12, padding: 16,
            border: "1px solid var(--color-border)",
          }}>
            <div style={{ fontSize: 11, color: "var(--color-text-muted)", marginBottom: 4 }}>{c.label}</div>
            <div style={{ fontSize: 24, fontWeight: 700, color: c.color }}>{c.value}</div>
          </div>
        ))}
      </div>

      {/* Pipeline Funnel */}
      {pipeline && (
        <div style={{ background: "var(--color-surface)", borderRadius: 12, padding: 16, marginBottom: 12, border: "1px solid var(--color-border)" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-text)", marginBottom: 8 }}>Pipeline Funnel</div>
          {["L0: Cache", "L1: Triage", "L2: RAG", "L3: LLM"].map((layer, i) => {
            const pct = [45, 30, 20, 5][i]; // placeholder percentages
            return (
              <div key={layer} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                <span style={{ fontSize: 11, color: "var(--color-text-muted)", width: 80 }}>{layer}</span>
                <div style={{ flex: 1, height: 8, background: "var(--color-bg)", borderRadius: 4 }}>
                  <div style={{ width: `${pct}%`, height: "100%", background: "var(--color-accent)", borderRadius: 4 }} />
                </div>
                <span style={{ fontSize: 11, color: "var(--color-text-secondary)", width: 30 }}>{pct}%</span>
              </div>
            );
          })}
        </div>
      )}

      {/* Anomalies */}
      {anomalies && Array.isArray(anomalies) && anomalies.length > 0 && (
        <div style={{ background: "var(--color-surface)", borderRadius: 12, padding: 16, border: "1px solid var(--color-error)40" }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: "var(--color-error)", marginBottom: 8 }}>Anomalies</div>
          {anomalies.slice(0, 5).map((a: Record<string, string>, i: number) => (
            <div key={i} style={{ fontSize: 11, color: "var(--color-text-secondary)", marginBottom: 4 }}>
              {a.message || JSON.stringify(a)}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
```

**Step 2: Commit**

```bash
git add src/modules/journey/JourneyKPI.tsx
git commit -m "feat(journey-ui): add JourneyKPI dashboard with pipeline funnel and anomaly alerts"
```

---

## Phase 5: Integration + E2E Wiring

### Task 5.1: Wire Everything in JourneyBuilder + Add KPI Tab

**Files:**
- Modify: `frontend/src/modules/journey/JourneyBuilder.tsx` (add KPI tab, Copilot toggle, final wiring)

**Step 1: Add tab switching between Canvas and KPI**

Add to JourneyBuilder's toolbar a tab toggle: `[Canvas] [KPI] [Containers]`. Import and render JourneyKPI when KPI tab is active.

**Step 2: Ensure Copilot sidebar toggle button is in toolbar**

Add brain/sparkle icon button in toolbar that toggles `copilotOpen` state.

**Step 3: Commit**

```bash
git add src/modules/journey/JourneyBuilder.tsx
git commit -m "feat(journey-ui): wire KPI tab and Copilot toggle into JourneyBuilder"
```

---

### Task 5.2: Create Minimal Sandbox Container Images

**Files:**
- Create: `infra/containers/trigger/Dockerfile`
- Create: `infra/containers/trigger/run.sh`
- Create: `infra/containers/condition/Dockerfile`
- Create: `infra/containers/condition/run.sh`
- Create: `infra/containers/action-crm/Dockerfile`
- Create: `infra/containers/action-crm/run.sh`

**Step 1: Create minimal trigger container**

```dockerfile
# infra/containers/trigger/Dockerfile
FROM alpine:3.19
RUN apk add --no-cache jq
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
```

```bash
# infra/containers/trigger/run.sh
#!/bin/sh
echo '{"result": true, "type": "trigger", "subtype": "'$NODE_SUBTYPE'", "timestamp": "'$(date -Iseconds)'"}' > /tmp/result.json
sleep 0.1
```

**Step 2: Create condition container**

```dockerfile
# infra/containers/condition/Dockerfile
FROM alpine:3.19
RUN apk add --no-cache jq
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
```

```bash
# infra/containers/condition/run.sh
#!/bin/sh
# Simple condition evaluator — reads NODE_CONFIG env var
RESULT=$(echo "$NODE_CONFIG" | grep -q "true" && echo "true" || echo "false")
echo '{"result": '$RESULT', "type": "condition", "evaluated": "'$NODE_CONFIG'"}' > /tmp/result.json
sleep 0.05
```

**Step 3: Create action-crm container**

```dockerfile
# infra/containers/action-crm/Dockerfile
FROM alpine:3.19
RUN apk add --no-cache jq curl
COPY run.sh /run.sh
RUN chmod +x /run.sh
CMD ["/run.sh"]
```

```bash
# infra/containers/action-crm/run.sh
#!/bin/sh
echo '{"result": true, "type": "action", "subtype": "'$NODE_SUBTYPE'", "action": "completed"}' > /tmp/result.json
sleep 0.2
```

**Step 4: Build images**

```bash
cd infra/containers
docker build -t huggsai/trigger:latest trigger/
docker build -t huggsai/condition:latest condition/
docker build -t huggsai/action-crm:latest action-crm/
```

**Step 5: Commit**

```bash
git add infra/containers/
git commit -m "feat(infra): add minimal sandbox container images (trigger, condition, action-crm)"
```

---

### Task 5.3: E2E Smoke Test Script

**Files:**
- Create: `tools/e2e_journey_test.py`

**Step 1: Write E2E test**

```python
# tools/e2e_journey_test.py
"""
E2E Smoke Test: Validates the Journey Builder pipeline.
Trigger Manual -> Conditional -> Add Tag -> End

Run: python tools/e2e_journey_test.py
Requires: Gateway running on :8766, Docker available
"""
import httpx
import asyncio
import json
import sys


BASE = "http://localhost:8766/api/v1"

DAG = {
    "journey_id": "e2e-smoke-test",
    "tenant_id": "default-tenant",
    "nodes": [
        {"id": "n1", "type": "trigger", "subtype": "trigger_manual", "config": {}},
        {"id": "n2", "type": "condition", "subtype": "condition_if", "config": {"field": "tag", "value": "vip"}},
        {"id": "n3", "type": "action", "subtype": "action_tag", "config": {"tag": "premium"}},
        {"id": "n4", "type": "control", "subtype": "control_end", "config": {}},
    ],
    "edges": [
        {"source": "n1", "target": "n2"},
        {"source": "n2", "target": "n3", "label": "true"},
        {"source": "n2", "target": "n4", "label": "false"},
    ],
}


async def main():
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 1. Health check
        print("[1/3] Checking gateway health...")
        r = await client.get(f"{BASE}/cluster/health")
        assert r.status_code == 200, f"Health check failed: {r.status_code}"
        print(f"  OK — {r.json().get('summary', 'healthy')}")

        # 2. Execute journey
        print("[2/3] Executing journey DAG...")
        r = await client.post(f"{BASE}/journeys/execute", json=DAG)
        assert r.status_code == 200, f"Execute failed: {r.status_code} — {r.text}"
        result = r.json()
        print(f"  Status: {result['status']}")
        print(f"  Total latency: {result['total_latency_ms']:.0f}ms")
        print(f"  Containers spawned: {result['containers_spawned']}")
        for nr in result.get("node_results", []):
            emoji = "+" if nr["status"] == "success" else "x"
            print(f"  [{emoji}] {nr['node_id']}: {nr['status']} ({nr.get('latency_ms', 0):.0f}ms)")

        # 3. Verify
        print("[3/3] Verification...")
        all_success = all(nr["status"] == "success" for nr in result.get("node_results", []))
        if all_success and result["status"] == "completed":
            print("\n  E2E SMOKE TEST PASSED")
            return 0
        else:
            print("\n  E2E SMOKE TEST FAILED")
            return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
```

**Step 2: Commit**

```bash
git add tools/e2e_journey_test.py
git commit -m "test(e2e): add journey builder smoke test script"
```

---

## Summary — Implementation Order

| Phase | Tasks | Est. Files | Dependencies |
|-------|-------|-----------|-------------|
| **Phase 1** | ContainerOrchestrator + API endpoints | 6 new, 1 modified | Docker SDK |
| **Phase 2** | JourneyExecutor + Journey API endpoints | 4 new, 1 modified | Phase 1 |
| **Phase 3** | Types, API client, hooks, NodeSandbox, AnimatedEdge, NodePalette, DebugPanel, JourneyBuilder page | 9 new, 2 modified | Phase 2 (backend ready) |
| **Phase 4** | CopilotSidebar, JourneyKPI | 2 new, 1 modified | Phase 3 |
| **Phase 5** | Final wiring, container images, E2E test | 8 new, 1 modified | Phases 1-4 |

**Total:** ~29 new files, ~5 modified files, ~18 commits

**Critical path:** Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5 (sequential, each depends on prior)

**Parallelizable:** Within Phase 3, Tasks 3.2-3.5 (NodeSandbox, AnimatedEdge, NodePalette, DebugPanel) can be built in parallel before Task 3.6 wires them together.
