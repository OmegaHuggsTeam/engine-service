# Journey Builder Ecosystem — Design Document

**Date:** 2026-03-07
**Author:** Hugo Fernandes (@HuggsF) + Claude (Architect)
**Status:** Approved
**Repo:** `OmegaHuggsTeam/engine-service`
**Location:** `frontend/src/modules/journey/`

---

## 1. Vision

HuggsAI is a **business orchestration platform where each client-company is a universe of sandbox containers**. The Journey Builder is the visual interface that:

1. **Models** — users draw flows (journeys) by dragging nodes onto a canvas
2. **Provisions** — each node spawns an isolated Docker container with tenant configuration
3. **Executes** — the journey runs, containers process in sequence/parallel, real-time feedback via WebSocket
4. **Learns** — AI (29 agents + HybridRAG) analyzes results, suggests optimizations, generates entire journeys via NL
5. **Measures** — KPI dashboard consumes telemetry, visual SLA on edges, cost/quality analysis

### Business Model: Metamodels via Generic Transactions

Each client-company receives a **tenant namespace** with:
- **Sandbox containers** pre-configured for their domain (e-commerce, SaaS, consulting)
- **Generic transactions** — abstractions mapping business operations: `LeadCapture`, `Qualify`, `Nurture`, `Convert`, `Retain`
- These metamodels are **journey templates** that AI adapts to client context
- The Builder is the **reader and translator** of these metamodels — translating business logic into executable containers

### Architectural Approach: Container-First Canvas

Each node in the React Flow canvas maps 1:1 to a real Docker container. The canvas is literally a visual docker-compose. Real execution via Engine API -> Docker SDK.

---

## 2. Ecosystem Layers

```
PRESENTATION LAYER
  Journey Canvas  |  KPI Dashboard  |  AI Copilot Sidebar
  (React Flow)    |  (Recharts)     |  (Chat + Suggestions)

ORCHESTRATION LAYER
  Sovereign Gateway (:8766)
  - ContainerOrchestrator (Docker SDK)
  - JourneyExecutor (DAG walker + container spawn)
  - NLJourneyGenerator (LLM -> DAG via /flows/compose)
  - TenantConfigManager (JSON rules per company)
  - TelemetryHub (metrics -> WebSocket -> frontend)

INTELLIGENCE LAYER
  29 Specialized Agents
  - marketing_agent (campaigns, copy, A/B)
  - analytics_agent (metrics, trends, anomalies)
  - crm_*_agents (backend, frontend, data, integration)
  - HybridRAG (ChromaDB + Neo4j 2-hop + TF-IDF)

INFRASTRUCTURE LAYER
  Docker Containers (sandbox per node)
  - Neo4j (knowledge graph + leads + flows)
  - ChromaDB (vectors for RAG)
  - n8n (automated workflow execution)
  - Redis (Layer 0 cache + pub/sub)
  - Dynamic containers (spawned by JourneyExecutor)
```

---

## 3. Canvas Architecture

### Component Tree

```
JourneyCanvas
  ToolbarPanel (top)
    JourneyName (editable inline)
    TenantSelector (multi-tenant dropdown)
    RunButton (execute journey)
    GenerateButton (AI generates DAG via NL)
    StatusBadge (draft/running/success/failure)

  NodePalette (left sidebar)
    Triggers: Manual, Event, Segment, Scheduled
    Conditions: Conditional, Split A/B
    Actions: SMS, Email, WhatsApp, Webhook, Tag, Score
    Control: Wait, End, Loop
    Integrations: SendSpeed, Meta, GA, Smartico
    Tracking: PageView, ClickTrack, Conversion

  Canvas (center area, React Flow)
    NodeSandbox[] (generic rendered nodes)
    AnimatedEdge[] (connections with visual SLA)

  CopilotSidebar (right sidebar, toggle)
    AIChat (contextual conversation with agents)
    Suggestions (recommended next node)
    JourneyGenerator (NL input -> complete DAG)

  DebugPanel (bottom panel, collapse/expand)
    ContainerLogs (stdout/stderr of active container)
    Metrics (latency, memory, CPU of sandbox)
    TestRunner (inline test code, syntax highlight)
```

### NodeSandbox Component (Generic, Injectable)

```typescript
interface NodeSandboxProps {
  id: string;
  type: NodeType; // 'trigger' | 'condition' | 'action' | 'control' | 'integration' | 'tracking'
  subtype: string; // 'manual' | 'sms' | 'conditional' | 'webhook' | etc.
  config: Record<string, unknown>; // type-specific configuration
  tenantId: string;
  containerId?: string; // Docker container ID when spawned
  status: 'idle' | 'provisioning' | 'running' | 'success' | 'failure' | 'timeout';
  metrics?: {
    latencyMs: number;
    memoryMb: number;
    cpuPercent: number;
    startedAt: string;
    completedAt?: string;
  };
  testCode?: string; // inline sandbox test code
}
```

Each NodeSandbox renders:
- **Icon** (Lucide) based on subtype
- **Label** with editable name
- **Status indicator** (pulsating dot: gray=idle, blue=provisioning, green=running, solid-green=success, red=failure)
- **Mini-metrics** (latency in ms, inline below label)
- **Handles** (input/output ports for connections)
- **On click**: opens DebugPanel with container logs, metrics, and test code

---

## 4. Builder Component Table

| Category | Subtype | Icon | Container Image | Description |
|----------|---------|------|-----------------|-------------|
| **Trigger** | `trigger_manual` | Play | `huggsai/trigger:latest` | Manual start, fires via button |
| **Trigger** | `trigger_event` | Zap | `huggsai/trigger:latest` | Fires when event occurs |
| **Trigger** | `trigger_segment` | Users | `huggsai/trigger:latest` | Fires when lead enters segment |
| **Trigger** | `trigger_schedule` | Clock | `huggsai/trigger:latest` | Cron-based trigger |
| **Condition** | `condition_if` | GitBranch | `huggsai/condition:latest` | Evaluates boolean expression (tag, score, field) |
| **Condition** | `condition_split` | Split | `huggsai/condition:latest` | A/B percentage split |
| **Action** | `action_sms` | MessageSquare | `huggsai/action-sms:latest` | Sends SMS via SendSpeed |
| **Action** | `action_email` | Mail | `huggsai/action-email:latest` | Sends email (template) |
| **Action** | `action_whatsapp` | MessageCircle | `huggsai/action-wa:latest` | Sends WhatsApp |
| **Action** | `action_webhook` | Globe | `huggsai/action-webhook:latest` | Generic HTTP call |
| **Action** | `action_tag` | Tag | `huggsai/action-crm:latest` | Adds/removes tag on lead |
| **Action** | `action_score` | TrendingUp | `huggsai/action-crm:latest` | Changes lead score |
| **Control** | `control_wait` | Timer | — (native, no container) | Configurable delay |
| **Control** | `control_end` | Square | — (native) | Finalizes branch |
| **Control** | `control_loop` | RefreshCw | `huggsai/control:latest` | Loop with exit condition |
| **Integration** | `int_sendspeed` | Send | `huggsai/int-sendspeed:latest` | SendSpeed SMS API |
| **Integration** | `int_meta` | Facebook | `huggsai/int-meta:latest` | Meta Ads/Pixel |
| **Integration** | `int_ga` | BarChart | `huggsai/int-ga:latest` | Google Analytics |
| **Tracking** | `track_pageview` | Eye | `huggsai/tracker:latest` | Records pageview |
| **Tracking** | `track_click` | MousePointer | `huggsai/tracker:latest` | Records click |
| **Tracking** | `track_conversion` | Target | `huggsai/tracker:latest` | Records conversion |

---

## 5. Animated Edges (SLA Visual)

Each AnimatedEdge between nodes shows:
- **Progress animation** 0->100% (particles moving in flow direction)
- **Color by SLA**: Green (`< 500ms`), Yellow (`500-1000ms`), Red (`> 1000ms`)
- **State**: dashed (idle) -> animated (running) -> solid (success) -> pulsating red (failure)
- Real latency displayed at edge center

---

## 6. Multi-Tenant Configuration

```typescript
interface TenantConfig {
  tenantId: string;
  name: string;
  plan: 'starter' | 'pro' | 'enterprise';
  sla: {
    maxLatencyMs: number; // 500 starter, 200 enterprise
    maxContainers: number; // 5 starter, 50 enterprise
    containerMemoryMb: number; // 128 starter, 512 enterprise
  };
  branding: {
    primaryColor: string;
    logo: string;
  };
  allowedNodeTypes: NodeType[];
  integrations: string[];
}
```

---

## 7. AI Copilot + Journey Generation

### Copilot Sidebar

- **Chat Tab**: Free conversation with specialized agents. Auto-routing: SMS question -> marketing_agent, metrics -> analytics_agent, code -> crm_backend_agent. Uses existing /tasks endpoint.
- **Suggestions Tab**: Given selected node + tenant context, suggests next best action based on HybridRAG patterns from Neo4j.
- **Generate Tab**: NL input -> complete DAG rendered on canvas in draft mode.

### Generation Flow

1. User describes in NL
2. `POST /journeys/generate { prompt, tenantId, constraints }`
3. Gateway -> NLJourneyGenerator -> marketing_agent + analytics_agent
4. Returns `{ nodes[], edges[], metadata }`
5. Frontend renders on canvas in draft mode (dashed border)
6. User adjusts, approves, clicks "Activate"

### Marketing + Identity Intelligence

- **Lead Profile Enrichment**: Neo4j trust score, interaction history, tags, segments, LTV
- **Behavioral Patterns via RAG**: ChromaDB chunks + Neo4j graph patterns
- **Identity Graph**: `(Lead)-[:PART_OF]->(Segment)-[:TARGETED_BY]->(Campaign)-[:USES]->(Journey)` — copilot navigates graph for context

---

## 8. KPI Dashboard

Consumes existing endpoints:

| Metric | Endpoint | Visualization |
|--------|----------|---------------|
| Cost per journey | `GET /kpi/cost-quality` | Gauge chart |
| Latency per node | `WS /ws/journey-events` | Sparkline per node |
| Model performance | `GET /kpi/models` | Bar chart |
| Anomalies | `GET /kpi/anomalies` | Alert badges |
| Daily trends | `GET /kpi/trends` | Line chart (7 days) |
| Agent heatmap | `GET /kpi/agents/heatmap` | Matrix heatmap |
| Container health | `GET /cluster/health` | Status cards |
| Pipeline stats | `GET /pipeline/stats` | Funnel chart (L0->L3) |

---

## 9. API Changes (Sovereign Gateway)

### New Endpoints Required

```python
# Container Management (Docker SDK)
POST   /api/v1/containers/spawn       # { image, config, tenantId } -> containerId
GET    /api/v1/containers/{id}/status  # status, metrics, logs
POST   /api/v1/containers/{id}/exec   # execute command in container
DELETE /api/v1/containers/{id}         # stop and remove container
GET    /api/v1/containers              # list active containers (filter: tenantId, journeyId)

# Journey Execution (orchestrates containers)
POST   /api/v1/journeys/execute        # { journeyId, dagJson, tenantId } -> executionId
GET    /api/v1/journeys/{id}/status    # per-node status + metrics
POST   /api/v1/journeys/{id}/stop     # stop execution, cleanup containers

# Tenant Config
GET    /api/v1/tenants/{id}/config     # returns TenantConfig
PUT    /api/v1/tenants/{id}/config     # updates config
GET    /api/v1/tenants/{id}/templates  # journey templates for tenant

# AI Generation (evolves existing /flows/compose)
POST   /api/v1/journeys/generate       # { prompt, tenantId, constraints } -> { nodes[], edges[] }
POST   /api/v1/journeys/suggest        # { currentDag, selectedNodeId } -> suggestions[]
```

### Existing Endpoints Reused (No Changes)

- `GET /kpi/*` — all metrics
- `WS /ws/journey-events` — execution event broadcast
- `WS /ws/crm-events` — lead/flow changes
- `POST /tasks` — task submission to agents
- `GET /crm/*` — leads, flows, interactions
- `GET /cluster/health` — infra container health

---

## 10. E2E Smoke Test Scenario

The single flow that proves everything works:

```
1. User opens JourneyCanvas -> empty canvas, NodePalette on left
2. Drags "Trigger Manual" -> NodeSandbox appears (status: idle)
3. Drags "Conditional (Has Tag?)" -> connects to trigger with dashed edge
4. Drags "Add Tag" -> connects to "true" output
5. Drags "Send SMS" -> connects to "false" output
6. Drags "End" -> connects both branches

   [Trigger Manual]
         |
   [Conditional: Has Tag "vip"?]
     true/     \false
[Add Tag "premium"] [SMS "Special offer"]
         \         /
        [End]

7. Clicks "Run" -> Gateway receives DAG -> JourneyExecutor:
   a. Spawns container "huggsai/trigger:latest" -> executes -> success (50ms)
   b. Animated edge green (50ms < 500ms SLA)
   c. Spawns container "huggsai/condition:latest" -> evaluates tag -> result: false
   d. Animated edge green
   e. Spawns container "huggsai/action-sms:latest" -> sends via SendSpeed -> success (320ms)
   f. Animated edge green
   g. End node -> cleanup containers -> journey: success

8. DebugPanel shows: container logs, total latency (420ms), cost ($0.0002)
9. KPI Dashboard updates: +1 execution, avg SLA 420ms, success rate 100%
10. Copilot suggests: "This journey can be optimized - 'Wait 1h' before SMS increases CTR by 23%"
```

---

## 11. Frontend State (Zustand)

```typescript
interface JourneyStore {
  // Canvas state
  nodes: NodeSandbox[];
  edges: AnimatedEdge[];
  selectedNodeId: string | null;

  // Execution state
  executionId: string | null;
  executionStatus: 'idle' | 'running' | 'completed' | 'failed';
  nodeStatuses: Record<string, NodeStatus>;

  // Tenant
  tenantId: string;
  tenantConfig: TenantConfig;

  // AI
  copilotMessages: CopilotMessage[];
  suggestions: Suggestion[];

  // KPI
  kpiData: KPISnapshot;

  // Actions
  addNode: (type, subtype, position) => void;
  connectNodes: (sourceId, targetId) => void;
  executeJourney: () => Promise<void>;
  generateJourney: (prompt: string) => Promise<void>;
}
```

---

## 12. Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Where to build | Engine-service Next.js frontend | Already has React Flow, WebSockets, Neo4j/ChromaDB connection |
| Node model | Node = real Docker container | Validates core thesis: each company is a container sandbox |
| Analytics | Custom dashboard in Next.js | Reuses existing KPI endpoints, zero overhead vs Metabase |
| AI in Builder | Copilot + generation (both) | Maximizes 29 existing agents via existing /tasks endpoint |
| Architecture | Container-First Canvas | Maximum realism, proves the metamodel concept |
| Scope | Full PRD + full functional screen | Complete ecosystem validation |

---

## 13. Gap Analysis

### What Exists
- React Flow (`@xyflow/react`) in engine-service frontend
- 54 API endpoints including CRM, KPI, flows, agents
- 5 WebSocket channels for real-time events
- 29 specialized agents + HybridRAG
- Docker Compose infrastructure (Neo4j, ChromaDB, Evidence)
- n8n workflow extraction/deployment pipeline

### What's Missing for MVP
1. **Docker SDK integration** in sovereign_gateway.py (`docker` Python lib)
2. **Container sandbox images** (`huggsai/trigger`, `huggsai/condition`, etc.)
3. **JourneyExecutor** class (DAG walker that spawns containers in order)
4. **JourneyCanvas React component** with NodeSandbox, AnimatedEdge
5. **NodePalette** sidebar with drag-and-drop
6. **CopilotSidebar** with AI chat + suggestions + generation
7. **DebugPanel** with container logs, metrics, test runner
8. **KPI Dashboard** tab with charts consuming existing endpoints
9. **TenantConfig** management (CRUD + Neo4j storage)
10. **Container lifecycle management** (spawn, monitor, cleanup, garbage collection)
11. **New API endpoints** (containers/*, journeys/execute, tenants/*, journeys/generate)
