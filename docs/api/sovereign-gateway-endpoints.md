# Sovereign Gateway API Reference

**Base URL**: `http://localhost:8766/api/v1`
**CORS**: localhost:3000

## REST Endpoints (47)

### Orchestrator

| Method | Path | Description |
|--------|------|-------------|
| POST | `/tasks` | Submit task to Neural Link orchestrator |
| GET | `/tasks/recent` | Get recent tasks (limit: 20-100) |

### Agents

| Method | Path | Description |
|--------|------|-------------|
| GET | `/agents` | List all agents with status and performance |
| GET | `/agents/{agent_id}/history` | Task history for agent (limit: 20-100) |

### RAG & Graph

| Method | Path | Description |
|--------|------|-------------|
| GET | `/rag/search?q=&top_k=` | Hybrid RAG search (top_k: 10-50) |
| GET | `/graph/explore?center=&depth=` | Explore graph from node (depth: 1-4) |
| GET | `/graph/services` | All Service nodes with neighbors (GraphSynergy) |

### Cluster

| Method | Path | Description |
|--------|------|-------------|
| GET | `/cluster/health` | Health check: ChromaDB, Neo4j, Evidence, n8n, Tailscale |

### Jitbit

| Method | Path | Description |
|--------|------|-------------|
| GET | `/jitbit/status` | Macro status (running/stuck) |
| POST | `/jitbit/error` | Webhook for macro failures |
| POST | `/jitbit/heal` | Trigger environment reset |

### Flows

| Method | Path | Description |
|--------|------|-------------|
| POST | `/flows/compose` | Natural language to n8n workflow |
| POST | `/flows/deploy` | Inject workflow JSON to n8n |

### CRM - Leads

| Method | Path | Description |
|--------|------|-------------|
| GET | `/crm/leads` | List all leads (limit: 50-200) |
| GET | `/crm/leads/search?q=` | Fulltext search leads |
| POST | `/crm/leads` | Create lead (201) |
| GET | `/crm/leads/{lead_id}` | Get single lead |
| PUT | `/crm/leads/{lead_id}` | Update lead fields |
| DELETE | `/crm/leads/{lead_id}` | Soft-delete lead (204) |
| GET | `/crm/leads/{lead_id}/score` | Trust score breakdown |
| GET | `/crm/leads/{lead_id}/interactions` | Interaction history (limit: 50-200) |

### CRM - Flows

| Method | Path | Description |
|--------|------|-------------|
| GET | `/crm/flows` | List flows with lead counts (limit: 50-200) |
| POST | `/crm/flows` | Create flow (201) |
| GET | `/crm/flows/{flow_id}` | Get single flow |
| PUT | `/crm/flows/{flow_id}` | Update flow fields |
| DELETE | `/crm/flows/{flow_id}` | Soft-delete flow (204) |
| POST | `/crm/flows/{flow_id}/leads/{lead_id}` | Add lead to flow (204) |

### CRM - Other

| Method | Path | Description |
|--------|------|-------------|
| POST | `/crm/interactions` | Record interaction (201) |
| GET | `/crm/graph` | Full CRM graph for visualization (limit: 200-1000) |
| GET | `/crm/stats` | Dashboard stats (counts, avg_trust) |

### Pipeline & KPI

| Method | Path | Description |
|--------|------|-------------|
| GET | `/pipeline/stats` | CostTracker aggregate statistics |
| GET | `/kpi/models` | Model leaderboard by cost-effectiveness |
| GET | `/kpi/models/{model_id}/history` | Daily time series for model (limit: 30-365) |
| GET | `/kpi/tools` | Tool comparison aggregates |
| GET | `/kpi/tools/{tool_name}/history` | Sprint-by-sprint tool reviews (limit: 20-100) |
| POST | `/kpi/tools/review` | Submit tool review |
| GET | `/kpi/cost-quality` | $/quality-point analysis |
| GET | `/kpi/trends` | Daily aggregates by dimension (limit: 90-365) |
| GET | `/kpi/agents/heatmap` | Agent x task_type quality matrix |
| GET | `/kpi/anomalies` | Regression alerts |
| GET | `/kpi/recommend?task_type=&min_quality=` | Recommend model for task |

### UseCases

| Method | Path | Description |
|--------|------|-------------|
| GET | `/usecases` | List use cases (domain?, status?, limit?) |
| GET | `/usecases/roadmap` | Full roadmap with dependencies |
| GET | `/usecases/coverage` | Agent coverage matrix |
| GET | `/usecases/gaps` | Skill gaps |
| GET | `/usecases/{usecase_id}` | Get UC with full context |

## WebSocket Endpoints (5)

| Path | Description | Frequency |
|------|-------------|-----------|
| `/ws/telemetry` | Real-time telemetry events | On event |
| `/ws/agent-health` | Agent status broadcast | Every 5s |
| `/ws/flow-events` | Flow Canvas updates | On change |
| `/ws/crm-events` | CRM lead/flow/interaction changes | On change |
| `/ws/journey-events` | Journey events (heal, errors) | On event |

## Webhook Listener (Port 8765)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Health check |
| POST | `/webhook` | IFTTT webhook receiver (auth: X-Webhook-Key) |
| POST | `/{event:path}` | Legacy path-based webhook |

## Key Request/Response Models

### TaskSubmission (POST /tasks)
```json
{"query": "string", "context": {"key": "value"}}
```

### CrmLeadCreate (POST /crm/leads)
```json
{"name": "string", "email": "string?", "company": "string?", "source_channel": "string?", "tags": ["string"]}
```

### CrmFlowCreate (POST /crm/flows)
```json
{"name": "string", "objective": "string?", "n8n_workflow_id": "string?"}
```

### KpiToolReviewSubmit (POST /kpi/tools/review)
```json
{
  "tool_name": "string",
  "sprint_date": "YYYY-MM-DD",
  "score_correto": 0-100,
  "score_completo": 0-100,
  "score_qualidade": 0-100,
  "deliverables_done": 0,
  "deliverables_total": 0,
  "issues_critical": 0,
  "issues_medium": 0,
  "issues_low": 0,
  "reviewer": "string?",
  "notes": "string?"
}
```
