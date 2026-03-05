# [UC-JRN-004] Analytics e KPIs de Journey

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-JRN-004 |
| **Domain** | journeys |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Sistema de KPIs hierarquico para journeys com auto-seed de metricas default. Suporta 3 niveis de hierarquia: platform, company e journey. KPI snapshots sao calculados periodicamente e exibidos em painel dedicado no Journey Builder.

### Data Models

- **Model**: KpiSnapshot (repo: platform-backend, path: `backend/src/domain/models/KpiSnapshot.js`)
  - Fields: `journey_id: ObjectId`, `company_id: ObjectId`, `metric_name: string`, `value: number`, `period: string`, `created_at: Date`
- **Model**: BaseMetric (repo: platform-backend, path: `backend/src/domain/models/BaseMetric.js`)
  - Fields: `name: string`, `type: enum[counter|gauge|rate]`, `formula: string`
- **Model**: SuccessMetric (repo: platform-backend, path: `backend/src/domain/models/SuccessMetric.js`)
  - Fields: `name: string`, `target: number`, `current: number`, `journey_id: ObjectId`

### Services

- **Service**: journeyAnalyticsService (repo: platform-backend, path: `backend/src/application/services/journeyAnalyticsService.js`)
  - Methods: `getKpis()`, `getSnapshots()`, `seedDefaultKpis()`, `calculateMetrics()`, `getHierarchy()`

### Routes/Endpoints

- `GET /api/journeys/:id/analytics` -> `journeyAnalyticsService.getKpis()`
- `GET /api/journeys/:id/analytics/snapshots` -> `journeyAnalyticsService.getSnapshots()`
- `POST /api/journeys/:id/analytics/kpis` -> custom KPI creation

### Frontend Components

- **Component**: KpiPanel (repo: engage-ai-flow, path: `client/src/components/journey-builder/analytics/KpiPanel.tsx`)
- **Component**: JourneyAnalyticsPanel (repo: engage-ai-flow, path: `client/src/components/journey-builder/JourneyAnalyticsPanel.tsx`)

## Acceptance Criteria

1. GIVEN uma nova journey criada
   WHEN a journey e ativada pela primeira vez
   THEN o sistema auto-seed KPIs default (completion_rate, avg_time, drop_off_rate, conversion_rate)

2. GIVEN uma journey ativa com execucoes
   WHEN o usuario abre o KPI panel
   THEN exibe metricas atuais com comparativo ao nivel da company e da platform (hierarquia 3 niveis)

3. GIVEN KPI snapshots acumulados ao longo do tempo
   WHEN o usuario seleciona periodo no analytics panel
   THEN exibe evolucao temporal dos KPIs com graficos de tendencia

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **KpiCalculation** - nova
   - Spec: docs/specs/skills/kpi_calculation.md
   - Calculo hierarquico de KPIs com snapshots temporais

## Required Agent Capabilities

- **Primary**: `crm_data_agent` - capabilities: [analytics, kpi, data_pipeline]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, charts]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/journeyAnalyticsService'`
- `category: crm_model` + `source_file CONTAINS 'models/KpiSnapshot'`
- `category: crm_frontend` + `source_file CONTAINS 'journey-builder/analytics'`
- `category: usecase` + `domain: journeys`

## Related Use Cases

- **Depends on**: UC-JRN-001 (Journey Builder - journey precisa existir), UC-JRN-003 (Motor de Execucao - execucao gera dados)
- **Enables**: UC-JRN-002 (Intelligence - KPIs alimentam sugestoes de IA)
- **Conflicts with**: nenhum

## Implementation Notes

- KPI hierarchy: platform > company > journey (metricas herdadas e overrideable)
- Auto-seed cria 4 KPIs default quando journey e ativada pela primeira vez
- Snapshots calculados via cron a cada hora e persistidos em MongoDB
- ClickHouse usado para queries de agregacao pesada (timeseries)
- Frontend usa Recharts para graficos de evolucao temporal
- BaseMetric suporta formulas customizadas (ex: "conversions / unique_entries * 100")
