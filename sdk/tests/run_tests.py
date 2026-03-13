"""Manual test runner for Engine SDK.

Runs all tests without pytest (workaround for pytest hanging on
Python 3.14 + Windows). Execute with:
    cd sdk && PYTHONPATH=. python tests/run_tests.py
"""

from __future__ import annotations

import asyncio
import json
import sys

import httpx

from engine_sdk import EngineClient, EngineSyncClient, __version__
from engine_sdk.models import (
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
from engine_sdk.exceptions import (
    AuthenticationError,
    ConnectionError,
    EngineError,
    NotFoundError,
    ServerError,
    TimeoutError,
    ValidationError,
)


errors: list[str] = []
passed = 0


def check(name: str, condition: bool) -> None:
    global passed
    if condition:
        passed += 1
    else:
        errors.append(name)
        print(f"  FAIL: {name}")


class MockTransport(httpx.AsyncBaseTransport):
    def __init__(self, status: int = 200, body=None):
        self.status = status
        self.body = body or {}
        self.requests: list[httpx.Request] = []

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if isinstance(self.body, (dict, list)):
            content = json.dumps(self.body).encode()
        else:
            content = str(self.body).encode()
        return httpx.Response(
            self.status,
            headers={"content-type": "application/json"},
            content=content,
            request=request,
        )


def make_client(status: int = 200, body=None) -> tuple[EngineClient, MockTransport]:
    t = MockTransport(status, body)
    hc = httpx.AsyncClient(base_url="http://test:8766", transport=t)
    return EngineClient(httpx_client=hc), t


def test_models() -> None:
    print("--- Models ---")

    # RAGResult
    check("RAGResult defaults", RAGResult().content == "" and RAGResult().score == 0.0)
    r = RAGResult(content="x", source="f.pdf", score=0.9)
    check("RAGResult full", r.source_file == "f.pdf" and r.content == "x")
    check("RAGResult alias", RAGResult.model_validate({"source": "y.pdf"}).source_file == "y.pdf")
    check("RAGResult populate_by_name", RAGResult(source_file="d.pdf").source_file == "d.pdf")

    # AgentInfo
    check("AgentInfo defaults", AgentInfo(id="a", name="A", type="t").status == "active")
    a = AgentInfo(id="a", name="A", type="t", capabilities=["x"], success_rate=0.95)
    check("AgentInfo full", a.capabilities == ["x"] and a.success_rate == 0.95)

    # AgentResponse
    check("AgentResponse defaults", AgentResponse().cost == 0.0 and AgentResponse().agent_id == "")
    ar = AgentResponse(agent_id="a", task="t", result={"k": "v"}, processing_time_ms=500, cost=0.01)
    check("AgentResponse full", ar.cost == 0.01 and ar.processing_time_ms == 500)

    # IngestResult
    check("IngestResult defaults", IngestResult().chunks_created == 0 and IngestResult().models_embedded == [])
    ir = IngestResult(chunks_created=42, source_file="r.pdf", models_embedded=["emb-3"])
    check("IngestResult full", ir.chunks_created == 42 and ir.models_embedded == ["emb-3"])

    # PipelineStats
    check("PipelineStats defaults", PipelineStats().total_requests == 0)
    ps = PipelineStats(cache_hit_rate=0.75, total_requests=5000, cost_today=1.5)
    check("PipelineStats full", ps.cache_hit_rate == 0.75 and ps.cost_today == 1.5)

    # Graph
    check("GraphNode", GraphNode(id="n", labels=["X"]).labels == ["X"])
    check("GraphEdge", GraphEdge(source="a", target="b", type="R").type == "R")
    check("GraphSubset empty", GraphSubset().nodes == [] and GraphSubset().edges == [])
    gs = GraphSubset(
        nodes=[GraphNode(id="a", labels=["X"])],
        edges=[GraphEdge(source="a", target="b", type="R")],
    )
    check("GraphSubset populated", len(gs.nodes) == 1 and len(gs.edges) == 1)

    # CRM
    check("CrmLead defaults", CrmLead(id="l", name="L").trust == 0.5 and CrmLead(id="l", name="L").tags == [])
    check("CrmFlow defaults", CrmFlow(id="f", name="F").status == "draft")
    check("CrmStats", CrmStats(total_leads=100, avg_trust=0.6).total_leads == 100)
    check("CrmLeadScore", CrmLeadScore(lead_id="l", trust=0.75, interaction_count=10).trust == 0.75)

    # Misc
    check("ClusterHealth", ClusterHealth(timestamp="t", summary={"ok": 1}).summary["ok"] == 1)
    check("KpiRecommendation", KpiRecommendation(model="haiku", reason="best").reason == "best")
    check("FlowComposeResult", FlowComposeResult(objective="x").status == "composed")
    check("FlowDeployResult", FlowDeployResult(success=True, workflow_id="w1").success is True)
    check("ContainerInfo", ContainerInfo(container_id="c", node_id="n", tenant_id="t", image="i", status="r").status == "r")
    check("ContainerStatus", ContainerStatus(container_id="c", status="running", memory_mb=64.5).memory_mb == 64.5)
    check("ContainerExecResult", ContainerExecResult(container_id="c", exit_code=0, stdout="hi").exit_code == 0)
    check("ErrorResolution", ErrorResolution(error_type="timeout", frequency=5).frequency == 5)


def test_client_init() -> None:
    print("--- Client Init ---")

    check("default url", EngineClient().base_url == "http://localhost:8766")
    check("custom url", EngineClient(base_url="https://x.com").base_url == "https://x.com")
    check("trailing slash", EngineClient(base_url="http://x:8766/").base_url == "http://x:8766")
    check("repr", "localhost:8766" in repr(EngineClient()))
    check("not closed", not EngineClient().is_closed)

    c = EngineClient()
    check("rag type", c.rag is not None)
    check("agents type", c.agents is not None)
    check("graph type", c.graph is not None)
    check("ingest type", c.ingest is not None)
    check("telemetry type", c.telemetry is not None)
    check("resource cached", c.rag is c.rag)


def test_sync_client() -> None:
    print("--- Sync Client ---")

    check("sync default url", EngineSyncClient().base_url == "http://localhost:8766")
    check("sync repr", "localhost:8766" in repr(EngineSyncClient()))

    sc = EngineSyncClient()
    check("sync rag", sc.rag is not None)
    check("sync agents", sc.agents is not None)
    check("sync graph", sc.graph is not None)
    check("sync ingest", sc.ingest is not None)
    check("sync telemetry", sc.telemetry is not None)

    with EngineSyncClient() as sc2:
        check("sync context manager", sc2.base_url == "http://localhost:8766")


def test_exceptions() -> None:
    print("--- Exceptions ---")

    try:
        raise EngineError("test", status_code=500, body={"err": True})
    except EngineError as e:
        check("EngineError fields", e.status_code == 500 and e.message == "test")

    check("EngineError repr", "500" in repr(EngineError("x", status_code=500)))

    check("hierarchy", all([
        issubclass(ConnectionError, EngineError),
        issubclass(AuthenticationError, EngineError),
        issubclass(NotFoundError, EngineError),
        issubclass(ValidationError, EngineError),
        issubclass(ServerError, EngineError),
        issubclass(TimeoutError, EngineError),
    ]))


async def test_rag_resource() -> None:
    print("--- RAG Resource ---")

    # search
    c, t = make_client(body=[
        {"content": "Q4 revenue", "source": "report.pdf", "score": 0.95, "metadata": {"page": 3}},
        {"content": "Growth 15%", "source": "analysis.md", "score": 0.87, "metadata": {}},
    ])
    results = await c.rag.search("revenue Q4")
    check("rag search count", len(results) == 2)
    check("rag search type", isinstance(results[0], RAGResult))
    check("rag search content", results[0].content == "Q4 revenue")
    check("rag search source", results[0].source_file == "report.pdf")
    check("rag search score", results[0].score == 0.95)
    check("rag search metadata", results[0].metadata == {"page": 3})

    # empty
    c2, _ = make_client(body=[])
    check("rag empty", await c2.rag.search("nothing") == [])

    # params
    c3, t3 = make_client(body=[])
    await c3.rag.search("test query", top_k=3)
    url = str(t3.requests[-1].url)
    check("rag params q", "q=test" in url)
    check("rag params top_k", "top_k=3" in url)

    # default top_k
    c4, t4 = make_client(body=[])
    await c4.rag.search("test")
    check("rag default top_k", "top_k=5" in str(t4.requests[-1].url))

    # search_by_category
    c5, t5 = make_client(body={"answer": "...", "results": [{"content": "cat result", "source": "f.pdf", "score": 0.8, "metadata": {}}]})
    results5 = await c5.rag.search_by_category("query", "reports", top_k=3)
    check("rag category count", len(results5) == 1)
    check("rag category content", results5[0].content == "cat result")
    body5 = json.loads(t5.requests[-1].content)
    check("rag category method", t5.requests[-1].method == "POST")
    check("rag category payload", body5["context"]["category"] == "reports")

    for client in [c, c2, c3, c4, c5]:
        await client._client.aclose()


async def test_agents_resource() -> None:
    print("--- Agents Resource ---")

    # list
    c, t = make_client(body=[
        {"id": "analyst", "name": "Analyst", "type": "domain", "status": "active", "success_rate": 0.95},
        {"id": "writer", "name": "Writer", "type": "specialist", "status": "active"},
    ])
    agents = await c.agents.list()
    check("agents list count", len(agents) == 2)
    check("agents list type", isinstance(agents[0], AgentInfo))
    check("agents list id", agents[0].id == "analyst")
    check("agents list method", t.requests[-1].method == "GET")

    # execute
    c2, t2 = make_client(body={
        "answer": "Q4 summary", "agent_id": "analyst",
        "processing_time_ms": 1250, "model_used": "haiku", "cost": 0.003,
    })
    resp = await c2.agents.execute("analyst", "summarize Q4")
    check("agents execute type", isinstance(resp, AgentResponse))
    check("agents execute agent_id", resp.agent_id == "analyst")
    check("agents execute task", resp.task == "summarize Q4")
    check("agents execute time", resp.processing_time_ms == 1250)
    check("agents execute cost", resp.cost == 0.003)
    body2 = json.loads(t2.requests[-1].content)
    check("agents execute method", t2.requests[-1].method == "POST")
    check("agents execute payload", body2["query"] == "summarize Q4")
    check("agents execute context", body2["context"]["preferred_agent"] == "analyst")

    # execute with custom context
    c2b, t2b = make_client(body={"answer": "ok"})
    await c2b.agents.execute("a", "t", context={"dept": "finance"})
    body2b = json.loads(t2b.requests[-1].content)
    check("agents execute custom ctx", body2b["context"]["dept"] == "finance")

    # create
    c3, t3 = make_client(body={"id": "custom-1", "name": "Custom", "type": "custom", "status": "active"})
    agent3 = await c3.agents.create(id="custom-1", name="Custom", capabilities=["analysis"])
    check("agents create id", agent3.id == "custom-1")
    check("agents create method", t3.requests[-1].method == "POST")
    body3 = json.loads(t3.requests[-1].content)
    check("agents create payload", body3["capabilities"] == ["analysis"])

    # update
    c4, t4 = make_client(body={"id": "a", "name": "Updated", "type": "t", "status": "inactive"})
    agent4 = await c4.agents.update("a", status="inactive")
    check("agents update status", agent4.status == "inactive")
    check("agents update method", t4.requests[-1].method == "PUT")
    check("agents update url", "/api/v1/agents/a" in str(t4.requests[-1].url))

    # delete
    c5, t5 = make_client(body={"success": True, "agent_id": "custom-1"})
    result5 = await c5.agents.delete("custom-1")
    check("agents delete result", result5["success"] is True)
    check("agents delete method", t5.requests[-1].method == "DELETE")

    # health (alias for list)
    c6, _ = make_client(body=[{"id": "a", "name": "A", "type": "t", "status": "active"}])
    agents6 = await c6.agents.health()
    check("agents health", len(agents6) == 1 and agents6[0].id == "a")

    for client in [c, c2, c2b, c3, c4, c5, c6]:
        await client._client.aclose()


async def test_error_handling() -> None:
    print("--- Error Handling ---")

    # 401
    c, _ = make_client(401, {"error": "unauthorized"})
    try:
        await c.rag.search("test")
        check("401 raises", False)
    except AuthenticationError as e:
        check("401 raises", e.status_code == 401)
    await c._client.aclose()

    # 404
    c, _ = make_client(404, {"error": "not found"})
    try:
        await c.agents.get_history("x")
        check("404 raises", False)
    except NotFoundError as e:
        check("404 raises", e.status_code == 404)
    await c._client.aclose()

    # 422
    c, _ = make_client(422, {"detail": "invalid"})
    try:
        await c.agents.create(id="", name="")
        check("422 raises", False)
    except ValidationError as e:
        check("422 raises", e.status_code == 422)
    await c._client.aclose()

    # 500
    c, _ = make_client(500, {"error": "internal"})
    try:
        await c.telemetry.pipeline_stats()
        check("500 raises", False)
    except ServerError as e:
        check("500 raises", e.status_code == 500)
    await c._client.aclose()


async def test_context_manager() -> None:
    print("--- Context Manager ---")

    async with EngineClient() as c:
        check("cm not closed inside", not c.is_closed)
    check("cm closed after exit", c.is_closed)

    hc = httpx.AsyncClient()
    async with EngineClient(httpx_client=hc) as c:
        pass
    check("cm custom not closed", not hc.is_closed)
    await hc.aclose()


async def test_telemetry_resource() -> None:
    print("--- Telemetry Resource ---")

    # pipeline_stats
    c, _ = make_client(body={"total_requests": 500, "cache_hit_rate": 0.8, "avg_latency_ms": 120})
    stats = await c.telemetry.pipeline_stats()
    check("pipeline_stats type", isinstance(stats, PipelineStats))
    check("pipeline_stats requests", stats.total_requests == 500)
    check("pipeline_stats cache", stats.cache_hit_rate == 0.8)
    await c._client.aclose()

    # cost_report
    c, _ = make_client(body={"by_model": [], "by_agent": []})
    report = await c.telemetry.cost_report()
    check("cost_report", isinstance(report, dict) and "by_model" in report)
    await c._client.aclose()

    # model_leaderboard
    c, _ = make_client(body=[{"model": "haiku", "score": 0.9}])
    lb = await c.telemetry.model_leaderboard()
    check("model_leaderboard", len(lb) == 1)
    await c._client.aclose()

    # cluster_health
    c, _ = make_client(body={"timestamp": "t", "services": {}, "summary": {"ok": 3}})
    health = await c.telemetry.cluster_health()
    check("cluster_health type", isinstance(health, ClusterHealth))
    check("cluster_health ok", health.summary.get("ok") == 3)
    await c._client.aclose()

    # recommend_model
    c, _ = make_client(body={"model": "haiku", "reason": "best"})
    rec = await c.telemetry.recommend_model()
    check("recommend_model", isinstance(rec, KpiRecommendation) and rec.model == "haiku")
    await c._client.aclose()


async def test_graph_resource() -> None:
    print("--- Graph Resource ---")

    # explore
    c, _ = make_client(body={"nodes": [{"id": "n1", "labels": ["Agent"], "properties": {}}], "edges": []})
    subset = await c.graph.explore("n1")
    check("graph explore type", isinstance(subset, GraphSubset))
    check("graph explore nodes", len(subset.nodes) == 1 and subset.nodes[0].id == "n1")
    await c._client.aclose()

    # services
    c, _ = make_client(body=[{"service": "neo4j", "node_count": 5, "neighbors": ["chroma"]}])
    svcs = await c.graph.services()
    check("graph services", len(svcs) == 1 and svcs[0]["service"] == "neo4j")
    await c._client.aclose()

    # schema
    c, _ = make_client(body=[{"service": "neo4j", "node_count": 5, "neighbors": ["chroma"]}])
    schema = await c.graph.schema()
    check("graph schema labels", "neo4j" in schema["labels"])
    check("graph schema count", schema["service_count"] == 1)
    await c._client.aclose()


async def run_all_async() -> None:
    await test_rag_resource()
    await test_agents_resource()
    await test_error_handling()
    await test_context_manager()
    await test_telemetry_resource()
    await test_graph_resource()


def main() -> None:
    test_models()
    test_client_init()
    test_sync_client()
    test_exceptions()
    asyncio.run(run_all_async())

    # Version
    check("version", __version__ == "0.1.0")

    total = passed + len(errors)
    print(f"\n{'='*50}")
    print(f"{passed}/{total} tests passed")
    if errors:
        print(f"FAILED ({len(errors)}): {errors}")
        sys.exit(1)
    else:
        print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
