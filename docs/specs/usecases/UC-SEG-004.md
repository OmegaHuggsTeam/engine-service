# [UC-SEG-004] Widgets do Dashboard de Segmentos

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SEG-004 |
| **Domain** | segments |
| **Repos** | segment-engine, front |
| **Priority** | P2-Medium |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Dashboard React+Vite+Tailwind com 6 componentes visuais para analise semanal de segmentos, alimentado pelo WeeklyStatsWorker (cron Monday 00:01) que gera tabela ClickHouse com 80+ colunas de KPIs e pelo WeeklyAiAnalysisService que produz insights via GPT-4o-mini. O frontend consome endpoints REST `/api/weekly-stats/*` do segment-engine (port 3055) para renderizar metricas, funnels, distribuicoes e evolucao semanal com seletor de empresa e semana.

### Data Models

- **Model**: userin_weekly_companies_stats (repo: segment-engine, path: `src/clickhouse/schema.ts`)
  - Table type: ReplacingMergeTree in ClickHouse
  - 80+ columns: KPIs semanais por empresa (usuarios ativos, depositos, sessoes, engagement, retention, etc.)
  - Created/updated by WeeklyStatsWorker every Monday 00:01

### Services

- **Service**: WeeklyStatsWorker (repo: segment-engine, path: `src/workers/weekly-stats.worker.ts`)
  - Cron: Monday 00:01
  - Creates/updates `userin_weekly_companies_stats` table in ClickHouse (ReplacingMergeTree)
  - 80+ columns of weekly KPIs per company
- **Service**: WeeklyStatsService (repo: segment-engine, path: `src/services/weekly-stats.service.ts`)
  - Queries ClickHouse weekly stats for API consumption
  - Computes summaries, transitions, and current-week data
- **Service**: WeeklyAiAnalysisService (repo: segment-engine, path: `src/services/weekly-ai-analysis.service.ts`)
  - Uses GPT-4o-mini to generate weekly analysis insights from KPI data
  - Produces narrative summaries, trends, and recommendations

### Routes/Endpoints

- `GET /api/weekly-stats/companies` -> WeeklyStatsService (list companies with stats)
- `GET /api/weekly-stats/:companyId/summary` -> WeeklyStatsService (weekly KPI summary)
- `GET /api/weekly-stats/:companyId/analysis` -> WeeklyAiAnalysisService (GPT-4o-mini insights)
- `GET /api/weekly-stats/:companyId/transitions` -> WeeklyStatsService (stage transitions)
- `GET /api/weekly-stats/:companyId/current-week` -> WeeklyStatsService (current week live data)
- `GET /api/weekly-stats/:companyId/current-week-ai` -> WeeklyAiAnalysisService (current week AI analysis)

### Frontend Components

- **Component**: AiInsights (repo: front, path: `front/src/components/AiInsights`)
  - Renders GPT-4o-mini generated analysis with narrative summaries and recommendations
  - Consumes: `/api/weekly-stats/:companyId/analysis` and `/api/weekly-stats/:companyId/current-week-ai`
- **Component**: FunnelChart (repo: front, path: `front/src/components/FunnelChart`)
  - Stage funnel visualization: anonymous -> registered -> ftd -> depositor
  - Consumes: `/api/weekly-stats/:companyId/summary` (stage counts)
- **Component**: MetricCard (repo: front, path: `front/src/components/MetricCard`)
  - Individual KPI cards with value, trend indicator, and week-over-week comparison
  - Consumes: `/api/weekly-stats/:companyId/summary`
- **Component**: TierDistribution (repo: front, path: `front/src/components/TierDistribution`)
  - Distribution chart of deposit tiers: none/low/medium/high/whale
  - Consumes: `/api/weekly-stats/:companyId/summary` (tier breakdown)
- **Component**: TransitionsCard (repo: front, path: `front/src/components/TransitionsCard`)
  - Stage transition flows (ex: anonymous->registered, registered->ftd) with counts
  - Consumes: `/api/weekly-stats/:companyId/transitions`
- **Component**: WeeklyEvolutionChart (repo: front, path: `front/src/components/WeeklyEvolutionChart`)
  - Multi-week trend chart showing KPI evolution over time
  - Consumes: `/api/weekly-stats/:companyId/summary` (multiple weeks)
- **Component**: CompanySelector (repo: front, path: `front/src/components/CompanySelector`)
  - Dropdown to select company for dashboard context
  - Consumes: `/api/weekly-stats/companies`
- **Component**: WeekSelector (repo: front, path: `front/src/components/WeekSelector`)
  - Week picker for selecting which weekly snapshot to view

## Acceptance Criteria

1. GIVEN o WeeklyStatsWorker executando na segunda-feira 00:01
   WHEN o cron dispara
   THEN cria/atualiza tabela `userin_weekly_companies_stats` no ClickHouse com 80+ colunas de KPIs incluindo usuarios ativos, depositos, sessoes, engagement e retention por empresa

2. GIVEN dados semanais disponiveis no ClickHouse
   WHEN o WeeklyAiAnalysisService processa os KPIs
   THEN envia os dados para GPT-4o-mini e retorna analise narrativa com sumario, tendencias e recomendacoes

3. GIVEN usuario autenticado acessando o dashboard
   WHEN seleciona uma empresa via CompanySelector e uma semana via WeekSelector
   THEN todos os 6 componentes visuais (AiInsights, FunnelChart, MetricCard, TierDistribution, TransitionsCard, WeeklyEvolutionChart) renderizam com dados da empresa e semana selecionadas

4. GIVEN o FunnelChart renderizando
   WHEN dados de stage estao disponiveis
   THEN exibe funil com 4 estagios (anonymous -> registered -> ftd -> depositor) com contagem e percentual de conversao entre estagios

5. GIVEN o TransitionsCard renderizando
   WHEN dados de transicoes estao disponiveis
   THEN exibe fluxos de transicao entre stages com contagem de usuarios que mudaram de estagio na semana

6. GIVEN o endpoint `/api/weekly-stats/:companyId/current-week`
   WHEN acessado durante a semana corrente
   THEN retorna dados parciais da semana em andamento para visualizacao em tempo real

## Required Skills

1. **CrmFrontendDashboard** - nova
   - Spec: docs/specs/skills/crm_frontend_dashboard.md
   - Dashboard React+Vite+Tailwind com componentes de visualizacao de KPIs semanais

2. **WeeklyStatsComputation** - nova
   - Spec: docs/specs/skills/weekly_stats_computation.md
   - Agregacao semanal de 80+ KPIs em ClickHouse com analise AI via GPT-4o-mini

## Required Agent Capabilities

- **Primary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, vite, tailwind, charts, dashboard]
- **Secondary**: `crm_data_agent` - capabilities: [analytics, clickhouse, segmentation, ai_analysis]

## RAG Chunk References

- `category: crm_frontend` + `source_file CONTAINS 'front/src/components/AiInsights'`
- `category: crm_frontend` + `source_file CONTAINS 'front/src/components/FunnelChart'`
- `category: crm_frontend` + `source_file CONTAINS 'front/src/components/MetricCard'`
- `category: crm_frontend` + `source_file CONTAINS 'front/src/components/TierDistribution'`
- `category: crm_frontend` + `source_file CONTAINS 'front/src/components/TransitionsCard'`
- `category: crm_frontend` + `source_file CONTAINS 'front/src/components/WeeklyEvolutionChart'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/workers/weekly-stats.worker'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/weekly-stats.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/weekly-ai-analysis.service'`
- `category: crm_infra` + `source_file CONTAINS 'segment-engine/src/clickhouse/schema'`
- `category: usecase` + `domain: segments`

## Related Use Cases

- **Depends on**: UC-SEG-001 (Pipeline de Segmentacao - perfis e stages alimentam KPIs semanais), UC-SEG-002 (Sinais Dinamicos - campos dinamicos contribuem para metricas), UC-SEG-003 (Best-Time-to-Send - dados de best-time disponiveis nos perfis)
- **Enables**: nenhum (consumidor final de dados, camada de visualizacao)
- **Conflicts with**: nenhum

## Implementation Notes

- Frontend usa React + Vite + Tailwind (nao Next.js ou CSS-in-JS)
- Segment-engine roda na porta 3055, frontend consome via API REST
- WeeklyStatsWorker usa cron Monday 00:01 para gerar snapshot semanal completo
- ClickHouse tabela userin_weekly_companies_stats usa ReplacingMergeTree para dedup de snapshots
- 80+ colunas incluem: total_users, active_users, new_registrations, ftd_count, deposit_total, avg_session_duration, retention_rate, etc.
- WeeklyAiAnalysisService usa GPT-4o-mini (nao GPT-4) para gerar analises narrativas
- Endpoint current-week retorna dados parciais da semana em andamento (live)
- CompanySelector e WeekSelector sao componentes de controle que filtram todos os widgets
- 8 componentes no total: 6 visuais (AiInsights, FunnelChart, MetricCard, TierDistribution, TransitionsCard, WeeklyEvolutionChart) + 2 seletores (CompanySelector, WeekSelector)
- API endpoints seguem padrao REST: /api/weekly-stats/companies e /api/weekly-stats/:companyId/*
- Deposit tiers no TierDistribution correspondem aos tiers do DepositService: none/low/medium/high/whale
- Stage funnel no FunnelChart corresponde aos stages do ClassifierWorker: anonymous/registered/ftd/depositor (mtd)
