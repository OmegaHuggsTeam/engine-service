# [UC-AUDIT-001] Project Documentation Audit & KPI Tracking

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-AUDIT-001 |
| **Domain** | audit |
| **Repos** | mcp-engine-service (self) |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Active |

## Domain Context

Systematic audit of the entire Bunker Intelligence / Neural Link CRM project. Covers folder-by-folder code quality analysis, Kiro spec verification, agent documentation coverage, and documentation consolidation. This is the first KPI-tracked UseCase — all audit results are persisted as `:AuditResult` nodes in Neo4j and scored using the ToolScorecard formula (Correto 40% + Completo 30% + Qualidade 30%).

### Data Models

- **Model**: AuditResult (repo: mcp-engine-service, path: `src/neural_link/graph/queries.py`)
  - Fields: `id: string`, `target: string`, `target_type: enum[folder|spec|agent|doc]`, `score_correto: float`, `score_completo: float`, `score_qualidade: float`, `nota_geral: float`, `file_count: int`, `test_count: int`, `issues: list[string]`, `recommendations: list[string]`, `audited_at: datetime`

### Services

- **Service**: UseCase Indexer (repo: mcp-engine-service, path: `src/neural_link/rag/usecase_indexer.py`)
  - Methods: `index_usecase()` — parses this spec into ChromaDB chunks + Neo4j :UseCase node
- **Service**: ToolScorecard (repo: mcp-engine-service, path: `src/neural_link/telemetry/tool_scorecard.py`)
  - Methods: `submit_review()`, `get_reviews()` — persists scoring using the review formula
- **Service**: CostQualityAnalyzer (repo: mcp-engine-service, path: `src/neural_link/telemetry/cost_quality_analyzer.py`)
  - Methods: `recommend_model()` — suggests optimal model for audit classification tasks

### Routes/Endpoints

- `GET /api/v1/pipeline/stats` -> Aggregated pipeline metrics (cache rate, cost, layers)
- `GET /api/v1/kpi/tools` -> ToolReview history (audit scores tracked here)
- `POST /api/v1/kpi/tools` -> Submit new ToolReview (audit result)
- `GET /api/v1/usecases` -> All UseCases including UC-AUDIT-001
- `GET /api/v1/usecases/roadmap` -> Roadmap with audit status

## Acceptance Criteria

1. GIVEN the project root directory
   WHEN the audit system scans all folders in src/, automation_hub/, rpg_cortex/, tools/, scripts/, infra/
   THEN it MUST produce a structured audit report per folder with score (0-100)

2. GIVEN 22 Kiro spec suites in .kiro/specs/
   WHEN the audit system parses each spec directory
   THEN it MUST report: files present, completion %, stale data flags, and recommendations

3. GIVEN 29 agents in AGENT_REGISTRY
   WHEN the audit system checks docs/specs/agents/
   THEN it MUST identify which agents have specs (3) and which need specs (26)

4. GIVEN an AuditResult for any target
   WHEN the result is persisted to Neo4j
   THEN the :AuditResult node MUST have scores (correto, completo, qualidade, nota_geral) and link to the audited :UseCase or :Agent via AUDIT_OF relationship

5. GIVEN all audit reports are generated
   WHEN the summary is compiled
   THEN docs/audit/SUMMARY.md MUST contain: aggregated scores, top 5 critical gaps, priority ranking, and total file/test counts

## Required Skills

1. **DocumentationAudit** - new
   - Spec: (this UseCase defines it)
   - Folder scanning, file counting, quality scoring (Correto 40% + Completo 30% + Qualidade 30%)

2. **KpiTracking** - existing
   - Spec: docs/specs/skills/kpi_tracking.md
   - ToolScorecard integration for audit result persistence

3. **GraphPersistence** - existing
   - Spec: implicit via queries.py
   - UPSERT_AUDIT_RESULT / GET_AUDIT_RESULTS Cypher queries

## Required Agent Capabilities

- **Primary**: `documentation_agent` - capabilities: [documentation, audit, analysis]
- **Secondary**: `analytics_agent` - capabilities: [analytics, kpi, metrics]

## RAG Chunk References

- `category: audit` + `domain: documentation`
- `category: usecase` + `domain: audit`
- `category: kpi` + `source_file CONTAINS 'tool_scorecard'`
- `category: telemetry` + `source_file CONTAINS 'cost_quality_analyzer'`

## Related Use Cases

- **Depends on**: none (first audit UseCase — bootstraps the system)
- **Enables**: All future UC-* specs (establishes audit methodology and scoring baseline)
- **Conflicts with**: none

## Implementation Notes

- Scoring formula: `nota_geral = score_correto * 0.4 + score_completo * 0.3 + score_qualidade * 0.3`
- Same formula used in ToolScorecard (REVIEW_TEMPLATE) for consistency
- AuditResult nodes use MERGE (idempotent) — re-running the audit updates scores
- target_type enum: folder, spec, agent, doc
- Issues and recommendations stored as string arrays in Neo4j
- The audit is a point-in-time snapshot; audited_at tracks when
- First KPI-tracked UseCase: proves the metrics pipeline works end-to-end
