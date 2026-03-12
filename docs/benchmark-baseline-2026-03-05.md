# Benchmark Baseline — 2026-03-05

## Stack
- ChromaDB: latest (Rust-based)
- Neo4j: 5.26.21 Community
- Gateway: FastAPI on port 8766
- Evidence: FastAPI on port 5000
- Docker Compose: 5 containers, all healthy

## API Latencies (cold start, local Docker)

| Endpoint | Latency |
|----------|---------|
| `/api/v1/agents` | 10ms |
| `/api/v1/kpi/models` | 10ms |
| `/api/v1/kpi/anomalies` | 8ms |
| `/api/v1/kpi/cost-quality` | 24ms |
| `/api/v1/kpi/tools` | 59ms |
| `/api/v1/crm/stats` | 11ms |
| `/api/v1/crm/leads` | 94ms |
| `/api/v1/graph/services` | 12ms |
| `/api/v1/tasks/recent` | 10ms |
| `/api/v1/rag/search` | 20ms |
| `/api/v1/cluster/health` | 8s (checks 5 services) |

## Pipeline Query (Layer 3 — LLM)
- Query: "What marketing agents are available?"
- Total time: 32s (timeout on groq module — not installed in Docker)
- Agent selected: ai_engineer_agent
- Execution time: 202ms (excluding LLM call)
- Status: Failed (groq not in requirements-docker.txt)

## Database State
- Agents: 27 registered (from AGENT_REGISTRY fallback)
- Leads: 0
- Flows: 0
- Interactions: 0
- RAG chunks: 0 (needs initialization via run_init.py)
- KPI models: 0 (no LLM calls yet)

## Notes
- Layer 0 (cache): Not yet populated — first run
- Layer 1 (triage): Working — agent selection in <10ms
- Layer 2 (RAG): Empty — needs chunk ingestion
- Layer 3 (LLM): Blocked — `groq` SDK missing in Docker image
- Fix needed: Add `groq` to `requirements-docker.txt`

## Target (Month 5)
- Pipeline: <200ms latency
- Cost: <$0.001/request
- Accuracy: >95%
