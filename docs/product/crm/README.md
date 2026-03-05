# Self-Sovereign CRM - Product Documentation

## Overview

The Self-Sovereign CRM is a graph-native customer relationship management system built on top of the Neural Link knowledge graph (Neo4j). It manages leads, flows (campaigns/funnels), and interactions — all stored as first-class graph nodes with typed relationships.

Unlike traditional CRMs, this system is:
- **Graph-native**: Leads, flows, and interactions are Neo4j nodes with traversable relationships
- **Agent-integrated**: The 19-agent orchestration system automatically records CRM interactions during task execution
- **Real-time**: WebSocket channel (`/ws/crm-events`) pushes events to the frontend
- **n8n-connected**: Flows can reference n8n workflows, with auto-activation on deploy

---

## Architecture

```
Frontend (Next.js :3000)           Gateway (FastAPI :8766)           Neo4j
+-----------------------+          +------------------------+        +------------------+
| CrmDashboard          |  REST    | /api/v1/crm/leads      |  Cypher| :Lead nodes      |
|   LeadGraph (D3)      |--------->| /api/v1/crm/flows      |------->| :Flow nodes      |
|   FlowCanvas (xyflow) |  WS     | /api/v1/crm/interactions|       | :Interaction     |
|   LeadTable           |<--------| /ws/crm-events          |       | relationships    |
+-----------------------+          +------------------------+        +------------------+
                                          |                                   ^
                                          v                                   |
                                   +-------------+                    +----------------+
                                   | TelemetryHub|                    | TaskExecutor   |
                                   | CrmEvent    |                    | (auto-records  |
                                   | Provider    |                    |  interactions) |
                                   +-------------+                    +----------------+
```

---

## Data Model

### Nodes

| Label | Key Properties | Description |
|-------|---------------|-------------|
| `Lead` | id, name, email, company, trust (0-1), interaction_count, source_channel, tags[] | A contact/prospect |
| `Flow` | id, name, objective, n8n_workflow_id, status (draft/active/paused/completed) | A campaign or funnel |
| `Interaction` | id, lead_id, agent_id, channel, action, detail, timestamp | An event between agent/user and lead |

### Relationships

| Pattern | Description |
|---------|-------------|
| `(Lead)-[:PART_OF_FLOW]->(Flow)` | Lead is enrolled in a flow |
| `(Lead)-[:INTERACTED_WITH]->(Lead)` | Two leads have interacted |
| `(Interaction)-[:FOR_LEAD]->(Lead)` | Interaction targets a lead |
| `(Interaction)-[:BY_AGENT]->(Agent)` | Interaction was performed by an agent |
| `(Flow)-[:USES_WORKFLOW]->(N8nNode)` | Flow is backed by an n8n workflow |
| `(Flow)-[:MENTIONED_IN]->(Chunk)` | Flow referenced in a knowledge chunk |

### Trust Score

Trust is a float 0.0-1.0 representing lead quality/engagement:
- **0.7-1.0** (green): High-trust, qualified lead
- **0.4-0.7** (amber): Medium engagement, needs nurturing
- **0.0-0.4** (red): Cold or unqualified

---

## API Endpoints

All endpoints are under `/api/v1/crm/` on the Sovereign Gateway (:8766).

| Method | Path | Description |
|--------|------|-------------|
| GET | `/crm/leads` | List leads (limit, newest first) |
| POST | `/crm/leads` | Create lead |
| GET | `/crm/leads/{id}` | Get single lead |
| GET | `/crm/leads/{id}/interactions` | Lead interaction history |
| GET | `/crm/graph` | Full CRM graph for visualization |
| GET | `/crm/flows` | List flows with lead counts |
| POST | `/crm/flows` | Create flow |
| GET | `/crm/flows/{id}` | Get flow with associated leads |
| POST | `/crm/flows/{id}/leads/{lead_id}` | Add lead to flow |
| POST | `/crm/interactions` | Record interaction |
| GET | `/crm/stats` | Dashboard stats |
| WS | `/ws/crm-events` | Real-time CRM event stream |

---

## Frontend Modules

Located in `frontend/src/modules/crm/`:

| File | Description |
|------|-------------|
| `CrmDashboard.tsx` | Tab container: Graph / Canvas / Table |
| `LeadGraph.tsx` | D3 force-directed graph of leads + flows |
| `FlowCanvas.tsx` | @xyflow/react DAG editor for CRM flows |
| `LeadTable.tsx` | Sortable lead list with inline create/edit |
| `hooks/useCrmApi.ts` | REST API hooks |
| `hooks/useCrmWebSocket.ts` | WS hook for real-time updates |

---

## Agent Integration

### Automatic Interaction Recording

When a task has `lead_id` in its `input_data`, the `TaskExecutor` automatically:
1. Creates an `Interaction` node
2. Links it to the Lead via `FOR_LEAD`
3. Links it to the Agent via `BY_AGENT`
4. Increments the Lead's `interaction_count`

### n8n Flow Activation

When deploying a workflow via `/flows/deploy` with `crm_flow_id` in the workflow metadata, the gateway automatically updates the Flow status to "active".

---

## Related Specifications

- [CRM Agent Spec](../../specs/agents/crm_agent.md)
- [Lead Scoring Skill](../../specs/skills/lead_scoring.md)
- [Social Analysis Skill](../../specs/skills/social_analysis.md)
- [Sovereign Command Center Spec](../../../vault/Specs/SovereignCommandCenter.md)

---

## Source Files

| Layer | File |
|-------|------|
| Pydantic models | `src/neural_link/orchestrator/models.py` |
| Cypher queries | `src/neural_link/graph/queries.py` (CRM section) |
| Schema | `src/neural_link/graph/schema.py` |
| Gateway endpoints | `src/neural_link/api/sovereign_gateway.py` |
| Telemetry provider | `src/neural_link/telemetry/provider.py` (CrmEventProvider) |
| Agent hook | `src/neural_link/orchestrator/task_executor.py` |
| TypeScript types | `frontend/src/types/crm.ts` |
| Gateway client | `frontend/src/lib/gateway.ts` |
| Tests | `src/neural_link/tests/test_crm.py` (34 tests) |
