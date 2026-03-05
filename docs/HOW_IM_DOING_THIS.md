# How I'm Doing This

A first-person narrative on building the Bunker Intelligence / Neural Link CRM system.

---

## The Problem

I have 924 passing tests, 29 specialized agents, 55+ REST/WebSocket endpoints, a 5-layer optimization pipeline, and a full KPI intelligence system. The system works. But here's what keeps me up at night: **60% of the project folders had no documentation**, 22 Kiro specs were unverified, docs were scattered across 78+ markdown files with no single entry point, and 26 out of 29 agents had no individual specification.

The system was growing faster than I could document it. Every sprint added features — CRM CRUD, SendSpeed integration, model benchmarking, cost tracking — but the documentation debt compounded. A new developer joining this project would need days just to understand the architecture, let alone contribute.

So I stopped building features and started building clarity.

---

## The Multi-Tool Approach

I don't use a single AI tool. I use four, each for what it does best:

| Tool | Strength | Phase 2 Score | Role |
|------|----------|---------------|------|
| **Kiro** | Spec-driven generation | 92/100 | Agent specs, UseCase definitions, structured templates |
| **Cursor** | Bulk code & infrastructure | 91/100 | Frontend AI infra, Postman collections, cost tracker |
| **Anti Gravity** | Frontend UX polish | 97/100 | Animations, responsive design, keyboard shortcuts |
| **Claude Code** | Review, integration, audit | — | Audit reports, GET_STARTED, narrative, schema mods |

The scoring formula is consistent across all tools: **Correto 40% + Completo 30% + Qualidade 30%**. This isn't arbitrary — it reflects what matters:

- **Correto (40%)**: Does it actually work? No bugs, no regressions. This gets the highest weight because broken code has negative value.
- **Completo (30%)**: Did it deliver everything promised? Partial implementations create technical debt.
- **Qualidade (30%)**: Is it well-structured, tested, maintainable? Quality prevents future bugs.

The cadence is: **Plan -> Execute (parallel) -> Review -> Fix -> Update MEMORY**. Each sprint produces scored deliverables. No sprint is "done" until it's reviewed and scored.

---

## The Cost Strategy

Here's the uncomfortable truth about AI-powered systems: **LLM tokens are expensive at scale**. A naive implementation that sends every query through a 70B parameter model will burn through credits in hours.

My solution is a 5-layer optimization pipeline, where each layer either answers the query for free or reduces the cost of the next layer:

### Layer 0 — Cache + Deterministic (Zero Cost)
- **SHA-256 exact cache**: Same query = same answer, instantly
- **Semantic similarity cache**: Similar queries (threshold 0.92) return cached results
- **Graph shortcuts**: Regex patterns bypass LLM entirely for status checks, agent listings, roadmap queries

### Layer 1 — Triage (Minimal Cost)
- **Simple request detection**: Single-intent queries skip LLM decomposition
- **Model tier routing**: 8B model for triage/eval/synthesis, 70B for generation/analysis/repair
- **Complexity override**: Score > 0.7 forces the bigger model

### Layer 2 — Context Precision (Controlled Cost)
- **Adaptive truncation**: Content length scales with relevance score (max_chars = 500 * score)
- **Relevance threshold**: Filters low-score noise from RAG results
- **High-confidence fast path**: Skips full evaluation when confidence is high

### Layer 3 — Quality Gate (Smart Evaluation)
- **Skip for proven agents**: Agents with success_rate >= 0.85 skip LLM evaluation
- **Sample for medium agents**: 30% sampling for agents between 0.7-0.85
- **Always evaluate**: Generation and repair tasks get full quality assessment

The result: every request has a `RequestCostProfile` tracking exactly how many tokens it consumed, which layers it hit, whether it used cache, and what it cost in USD. No guessing.

---

## Efficiency Goals

These are the targets I'm tracking via the KPI system:

| Metric | Target | Why |
|--------|--------|-----|
| Cache hit rate | >30% | Repeated questions should be free |
| Evaluation skip rate | >40% | Proven agents don't need re-evaluation |
| Layer 0/1 handling | >50% of queries | Most questions are simple |
| Cost per query | <$0.001 average | Sustainable at scale |

The `CostTracker` aggregates these metrics across all requests. The `MetricsTimeSeries` persists daily aggregates to Neo4j for trend analysis. The `CostQualityAnalyzer` computes $/quality-point per model, agent, and task type — so I know exactly where money is being wasted.

---

## KPI Intelligence

This is the system that watches the system. Five interconnected components:

1. **ModelBenchmark** — Per-model tracking: latency, tokens, cost, quality, failures. Buffer-based, flushes to Neo4j `:ModelMetric` daily buckets.

2. **ToolScorecard** — CRUD `:ToolReview` nodes using the review formula. Every tool sprint gets a score. Every score feeds into trend analysis.

3. **CostQualityAnalyzer** — Computes $/quality-point per model, per agent, per task type. Has a `recommend_model()` function that suggests the optimal model for any task based on historical data.

4. **MetricsTimeSeries** — Converts `CostTracker` profiles into `:RequestMetric` nodes, rolls up into `:DailyAggregate` nodes, and detects anomalies (cost spikes, quality drops).

5. **KpiProvider** — TelemetryProvider implementation that emits `KPI_ANOMALY_DETECTED` events when metrics go sideways.

These aren't theoretical. There are 112 tests proving they work, 12 API endpoints serving data, and a frontend dashboard with 5 tabs visualizing everything.

---

## Product Vision

The end goal is a **self-sovereign CRM** — a system that doesn't depend on any single SaaS vendor. The data lives in Neo4j (graph relationships), ChromaDB (vector search), and your own infrastructure (Kubernetes).

The architecture:

```
User Query
    |
    v
[5-Layer Pipeline]
    |
    v
[Agent Selection] --> [29 Agents]
    |                      |
    v                      v
[Neo4j Graph] <-----> [ChromaDB Vectors]
    |
    v
[SendSpeed Integration] --> SMS, Webhooks, Campaigns
    |
    v
[n8n Workflows] --> Automation, Notifications
```

SendSpeed integration covers 8 use cases (UC-SS-001 through UC-SS-008): SMS pipeline, webhooks, campaigns, billing, delivery, blacklist, backoffice, and portal API. Each has a dedicated domain agent with real code analysis from the actual repositories.

The CRM module handles leads, flows, interactions — all persisted as graph nodes with trust scoring that auto-recalculates on every interaction.

---

## What's Next

**UC-AUDIT-001** is the first KPI-tracked UseCase. Every audit result is persisted as an `:AuditResult` node in Neo4j, scored using the same formula as ToolScorecard. This means:

- Audit results show up in the KPI dashboard
- Anomalies trigger alerts (via KpiProvider)
- We can track documentation quality over time
- We can correlate doc quality with agent performance

The path to 100% efficiency:
1. Close the 9 not-started Kiro specs (sentinela-monitor, jitbit-macro first)
2. Generate remaining agent specs (26 files)
3. Increase test coverage for 4 folders with zero tests
4. Refactor web_extractor.py (2,700 LOC god file)
5. Add K8s resource limits and probes before production

The system is self-improving by design. Every sprint scores itself, every agent tracks its success rate, every query records its cost. The question isn't whether we'll get there — it's how fast.

---

*Written 2026-03-04 as part of UC-AUDIT-001 — the first KPI-tracked project audit.*
