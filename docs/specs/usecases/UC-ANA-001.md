# [UC-ANA-001] Pipeline de Analytics Cross-Repo

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-ANA-001 |
| **Domain** | analytics |
| **Repos** | sendspeed0/analytics, segment-engine, engage-ai-flow |
| **Priority** | P0-Critical |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Pipeline completo de analytics que abrange 3 repositorios: analytics service (port 3007) para metricas real-time, card analytics e acquisition analytics com recomendacoes AI; segment-engine para KPIs semanais (80+ colunas ClickHouse), cohort retention e AI analysis vertical-specific; e engage-ai-flow para dashboards frontend com D3, Recharts e componentes interativos. O fluxo de dados inicia no TrackerJS, passa por ingestion-service (Kafka), workers (MongoDB + forward), PeerDB CDC (MongoDB para ClickHouse), e culmina em visualizacoes real-time e weekly reports com AI insights.

### Data Models

- **Model**: Visitor (repo: analytics, store: MongoDB collection `visitors`)
  - Fields: `visitorId: string`, `sessionId: string`, `deviceInfo: object`, `location: object`, `firstSeen: Date`, `lastSeen: Date`
- **Model**: Event (repo: analytics, store: MongoDB collection `events`)
  - Fields: `visitorId: string`, `type: string`, `page: string`, `timestamp: Date`, `metadata: object`
- **Model**: Session (repo: analytics, store: MongoDB collection `sessions`)
  - Fields: `sessionId: string`, `visitorId: string`, `startTime: Date`, `endTime: Date`, `pageViews: number`, `actions: number`
- **Model**: Card (repo: analytics, store: MongoDB collection `cards`)
  - Fields: `cardId: string`, `companyId: string`, `type: string`, `events: CardEvent[]`, `createdAt: Date`
- **Model**: userin_weekly_companies_stats (repo: segment-engine, store: ClickHouse ReplacingMergeTree)
  - 80+ columns: funnel KPIs, tier distribution, deposits, churn, reactivation, sessions, intention, top games, cohort retention W1-W4, week-over-week deltas
- **Model**: userin_segments_events (repo: segment-engine, store: ClickHouse MergeTree)
  - Raw event stream for aggregation via Materialized Views
- **Model**: campaign_metrics (repo: segment-engine, store: ClickHouse View)
  - Aggregated campaign performance from campaign_site_entries + campaign_user_journey

### Services

- **Service**: AnalyticsService (repo: analytics, path: `src/services/analyticsService.ts`)
  - Methods: `getActiveUsers(companyId, windows=[1,5,30]min)`, `getEventChart(companyId, 12min lookback)`, `getTopPages(companyId)`, `getLiveEventFeed(companyId)`, `getLocationStats(companyId)`, `getDeviceStats(companyId)`, `getEngagementScore(visitorId)` - formula: (timeOnSite/10)*25 + (pagesViewed/5)*25 + (sessionCount/3)*25 + (actionsPerSession/10)*25
- **Service**: CardAnalyticsService (repo: analytics, path: `src/services/cardAnalyticsService.ts`)
  - Methods: `getCardEvents(cardId)`, `getConversionFunnel(companyId)` (previews->opens->clicks->CTA clicks), `getUserJourney(visitorId, cardId)`, `compareCards(cardIds[])`, `getCardRanking(companyId)`, `getTimingMetrics(cardId)`
- **Service**: AcquisitionAnalyticsService (repo: analytics, path: `src/services/acquisitionAnalyticsService.ts`)
  - Methods: `getUniqueAccesses(companyId)`, `getTimeToFirstClick(companyId)`, `getScrollDepth(companyId)`, `getBounceRate(companyId)` (<3 clicks = bounce), `getClicksPerSession(companyId)`, `getPageTimeAnalysis(companyId)`, `getPageRankings(companyId)`
- **Service**: AIRecommendationService (repo: analytics, path: `src/services/aiRecommendationService.ts`)
  - Methods: `getMetricHealth(value, thresholds)` -> boa/aceitavel/ruim, `getCardSuggestions(companyId)` with risk types: exitRisk/doubtRisk/conversionRisk
  - LLM: GPT-4o-mini via OpenAI API
- **Service**: WeeklyStatsService (repo: segment-engine, path: `src/services/weekly-stats.service.ts`)
  - Methods: `getFunnelKpis(companyId, week)`, `getTierDistribution(companyId)`, `getChurnReactivation(companyId)`, `getCohortRetention(companyId, W1-W4)`, `getWeekOverWeekDelta(companyId)`
- **Service**: WeeklyAiAnalysisService (repo: segment-engine, path: `src/services/weekly-ai-analysis.service.ts`)
  - Methods: `analyzeWeeklyStats(companyId, vertical)` - GPT-4o-mini with vertical-specific prompts (gambling/ecommerce/saas/fintech)
- **Service**: AudienceQueries (repo: segment-engine, path: `src/services/audience-queries.service.ts`)
  - Methods: `getDepositSum24hAudience(companyId, page)`, `getDepositSumNDaysAudience(companyId, days, page)`, `getActiveUsersAudience(companyId, page)`, `getSegmentSnapshot(companyId, segmentId, page)` - all paginated

### Workers

- **Worker**: WeeklyStatsWorker (repo: segment-engine, path: `src/workers/weekly-stats.worker.ts`)
  - Cron: Monday 00:01, queries ClickHouse, builds userin_weekly_companies_stats (80+ columns ReplacingMergeTree), triggers AI analysis

### ClickHouse Tables

- `userin_weekly_companies_stats` (ReplacingMergeTree) - Weekly KPI snapshots
- `userin_segments_events` (MergeTree) - Raw events
- `userin_segments_deposits_hourly` (SummingMergeTree) - Hourly deposit aggregates
- `userin_segments_deposits_daily` (SummingMergeTree) - Daily deposit aggregates
- `userin_segments_clicks_hourly` (SummingMergeTree) - Hourly click aggregates
- `userin_segments_purchases_daily` (SummingMergeTree) - Daily purchase aggregates
- `game_similarities` (ReplacingMergeTree) - Game similarity matrix
- `campaign_site_entries` (MergeTree) - Campaign entry tracking
- `campaign_user_journey` (MergeTree) - Campaign user journey events
- `campaign_metrics` (View) - Aggregated campaign metrics
- Materialized Views: `deposits_hourly_mv`, `deposits_daily_mv`, `clicks_hourly_mv`, `purchases_daily_mv`

### Routes/Endpoints

- `GET /api/analytics/active-users` -> AnalyticsService.getActiveUsers()
- `GET /api/analytics/event-chart` -> AnalyticsService.getEventChart()
- `GET /api/analytics/top-pages` -> AnalyticsService.getTopPages()
- `GET /api/analytics/live-feed` -> AnalyticsService.getLiveEventFeed()
- `GET /api/analytics/location` -> AnalyticsService.getLocationStats()
- `GET /api/analytics/devices` -> AnalyticsService.getDeviceStats()
- `GET /api/analytics/engagement/:visitorId` -> AnalyticsService.getEngagementScore()
- `GET /api/analytics/cards/:cardId/events` -> CardAnalyticsService.getCardEvents()
- `GET /api/analytics/cards/funnel` -> CardAnalyticsService.getConversionFunnel()
- `GET /api/analytics/cards/compare` -> CardAnalyticsService.compareCards()
- `GET /api/analytics/cards/ranking` -> CardAnalyticsService.getCardRanking()
- `GET /api/analytics/acquisition/accesses` -> AcquisitionAnalyticsService.getUniqueAccesses()
- `GET /api/analytics/acquisition/bounce-rate` -> AcquisitionAnalyticsService.getBounceRate()
- `GET /api/analytics/acquisition/scroll-depth` -> AcquisitionAnalyticsService.getScrollDepth()
- `GET /api/analytics/ai/recommendations` -> AIRecommendationService.getCardSuggestions()
- `GET /api/weekly-stats/:companyId` -> WeeklyStatsService.getFunnelKpis()
- `GET /api/weekly-stats/:companyId/cohort` -> WeeklyStatsService.getCohortRetention()
- `GET /api/weekly-stats/:companyId/ai-analysis` -> WeeklyAiAnalysisService.analyzeWeeklyStats()
- `GET /api/audience/:companyId/deposits-24h` -> AudienceQueries.getDepositSum24hAudience()
- `GET /api/audience/:companyId/active-users` -> AudienceQueries.getActiveUsersAudience()
- `GET /api/audience/:companyId/snapshot` -> AudienceQueries.getSegmentSnapshot()

### Frontend Components

- **Page**: RealTimeDashboard (repo: engage-ai-flow, path: `client/src/pages/analytics/RealTimeDashboard.tsx`)
- **Page**: SegmentsDashboard (repo: engage-ai-flow, path: `client/src/pages/segments/SegmentsDashboard.tsx`)
- **Page**: CardResultsAnalytics (repo: engage-ai-flow, path: `client/src/pages/analytics/CardResultsAnalytics.tsx`)
- **Page**: CampaignStatsPage (repo: engage-ai-flow, path: `client/src/pages/campaigns/CampaignStatsPage.tsx`)
- **Page**: EnhancedCampaignStatsPage (repo: engage-ai-flow, path: `client/src/pages/campaigns/EnhancedCampaignStatsPage.tsx`)
- **Component**: ActiveUsersList (repo: engage-ai-flow, path: `client/src/components/analytics/ActiveUsersList.tsx`)
- **Component**: AnalyticsMetrics (repo: engage-ai-flow, path: `client/src/components/analytics/AnalyticsMetrics.tsx`)
- **Component**: DeviceStats (repo: engage-ai-flow, path: `client/src/components/analytics/DeviceStats.tsx`)
- **Component**: LiveEventsFeed (repo: engage-ai-flow, path: `client/src/components/analytics/LiveEventsFeed.tsx`)
- **Component**: RealTimeActivityChart (repo: engage-ai-flow, path: `client/src/components/analytics/RealTimeActivityChart.tsx`)
- **Component**: UserCard (repo: engage-ai-flow, path: `client/src/components/analytics/UserCard.tsx`)
- **Component**: UserLocationMap (repo: engage-ai-flow, path: `client/src/components/analytics/UserLocationMap.tsx`)
- **Component**: KpiCards (repo: engage-ai-flow, path: `client/src/components/segments/KpiCards.tsx`)
- **Component**: StageFunnel (repo: engage-ai-flow, path: `client/src/components/segments/StageFunnel.tsx`)
- **Component**: WeeklyEvolutionChart (repo: engage-ai-flow, path: `client/src/components/segments/WeeklyEvolutionChart.tsx`)
- **Component**: CohortRetentionChart (repo: engage-ai-flow, path: `client/src/components/segments/CohortRetentionChart.tsx`)
- **Component**: CohortHeatmap (repo: engage-ai-flow, path: `client/src/components/segments/CohortHeatmap.tsx`)
- **Component**: TierDistribution (repo: engage-ai-flow, path: `client/src/components/segments/TierDistribution.tsx`)
- **Component**: TransitionsCard (repo: engage-ai-flow, path: `client/src/components/segments/TransitionsCard.tsx`)
- **Component**: UtmStatsChart (repo: engage-ai-flow, path: `client/src/components/segments/UtmStatsChart.tsx`)
- **Component**: TopTagsCard (repo: engage-ai-flow, path: `client/src/components/segments/TopTagsCard.tsx`)
- **Component**: CardFunnelChart (repo: engage-ai-flow, path: `client/src/components/analytics/CardFunnelChart.tsx`)
- **Component**: CombinedFunnelChart (repo: engage-ai-flow, path: `client/src/components/analytics/CombinedFunnelChart.tsx`)
- **Component**: DetailedFunnelChart (repo: engage-ai-flow, path: `client/src/components/analytics/DetailedFunnelChart.tsx`)
- **Component**: DropoffAnalysisChart (repo: engage-ai-flow, path: `client/src/components/analytics/DropoffAnalysisChart.tsx`)
- **Component**: AIRecommendations (repo: engage-ai-flow, path: `client/src/components/analytics/AIRecommendations.tsx`)
- **Component**: ClickableKpiCard (repo: engage-ai-flow, path: `client/src/components/analytics/ClickableKpiCard.tsx`)
- **Component**: MetricAnalysisCard (repo: engage-ai-flow, path: `client/src/components/analytics/MetricAnalysisCard.tsx`)
- **Component**: HealthRecommendations (repo: engage-ai-flow, path: `client/src/components/analytics/HealthRecommendations.tsx`)
- **Component**: SuggestedCardDisplay (repo: engage-ai-flow, path: `client/src/components/analytics/SuggestedCardDisplay.tsx`)
- **Component**: CampaignStats (repo: engage-ai-flow, path: `client/src/components/campaigns/CampaignStats.tsx`)

### Data Pipeline

- **Ingestion**: TrackerJS -> ingestion-service (Kafka topics: `userin_ingest_event`, `userin_ingest_profile`, `userin_ingest_object`) -> workers (eventWorker -> MongoDB + forward to `users-segmentation`)
- **CDC**: PeerDB: MongoDB -> ClickHouse (_flattened tables)
- **Weekly**: WeeklyStatsWorker: ClickHouse queries -> userin_weekly_companies_stats + AI analysis
- **Real-time**: analytics service reads MongoDB (visitors, events, sessions, cards) for sub-minute dashboards
- **Vectors**: Pinecone + OpenAI embeddings for AI recommendation context

## Acceptance Criteria

1. GIVEN um usuario acessando o dashboard de real-time analytics
   WHEN a pagina carrega
   THEN exibe active users (windows 1/5/30min), event chart (12min lookback), top pages, live event feed, location map e device stats, todos atualizando automaticamente

2. GIVEN eventos de card (preview, open, click, CTA click) sendo coletados
   WHEN o usuario acessa a pagina de Card Analytics
   THEN exibe conversion funnel (previews->opens->clicks->CTA clicks), card ranking por performance, timing metrics e dropoff analysis chart

3. GIVEN metricas de acquisition disponíveis
   WHEN o usuario acessa Acquisition Analytics
   THEN calcula e exibe unique accesses, time to first click, scroll depth, bounce rate (<3 clicks), clicks per session, page time analysis e page rankings

4. GIVEN metricas de health disponíveis para cards
   WHEN o AIRecommendationService processa via GPT-4o-mini
   THEN classifica cada metrica como boa/aceitavel/ruim e gera sugestoes de cards com risk types (exitRisk, doubtRisk, conversionRisk)

5. GIVEN o engagement score de um visitor
   WHEN calculado pelo AnalyticsService
   THEN aplica formula: (timeOnSite/10)*25 + (pagesViewed/5)*25 + (sessionCount/3)*25 + (actionsPerSession/10)*25, retornando valor 0-100

6. GIVEN o WeeklyStatsWorker executando na segunda-feira 00:01
   WHEN cron dispara
   THEN gera userin_weekly_companies_stats com 80+ colunas incluindo funnel KPIs, tier distribution, deposits, churn, reactivation, sessions, intention, top games, cohort retention W1-W4 e week-over-week deltas

7. GIVEN stats semanais geradas para uma company
   WHEN WeeklyAiAnalysisService processa via GPT-4o-mini
   THEN gera analise AI com prompts vertical-specific (gambling/ecommerce/saas/fintech)

8. GIVEN audience queries paginadas
   WHEN o usuario filtra por deposits-24h, deposits-N-days, active-users ou segment-snapshot
   THEN retorna resultados paginados do ClickHouse com totais e metadata de paginacao

9. GIVEN o Segments Dashboard carregado no frontend
   WHEN dados semanais estao disponiveis
   THEN renderiza KpiCards, StageFunnel, WeeklyEvolutionChart, CohortRetentionChart, CohortHeatmap, TierDistribution, TransitionsCard, UtmStatsChart e TopTagsCard

10. GIVEN campaign tracking ativo
    WHEN usuario acessa CampaignStatsPage
    THEN exibe metricas agregadas de campaign_site_entries + campaign_user_journey via campaign_metrics View do ClickHouse

## Required Skills

1. **RealTimeAnalytics** - nova
   - Spec: docs/specs/skills/real_time_analytics.md
   - Coleta e visualizacao de metricas em tempo real (active users, event charts, live feeds)

2. **CardAnalytics** - nova
   - Spec: docs/specs/skills/card_analytics.md
   - Funnel de conversao de cards, comparacao, ranking e timing metrics

3. **AcquisitionAnalytics** - nova
   - Spec: docs/specs/skills/acquisition_analytics.md
   - Metricas de aquisicao: bounce rate, scroll depth, time to first click, page rankings

4. **AIRecommendations** - nova
   - Spec: docs/specs/skills/ai_recommendations.md
   - Health classification e sugestoes de cards via GPT-4o-mini com risk types

5. **WeeklyKPIs** - nova
   - Spec: docs/specs/skills/weekly_kpis.md
   - Geracao e consulta de KPIs semanais (80+ colunas ClickHouse) com AI analysis vertical-specific

6. **CohortAnalysis** - nova
   - Spec: docs/specs/skills/cohort_analysis.md
   - Retention W1-W4, heatmap, tier transitions, week-over-week deltas

7. **ClickHouseQuerying** - existente
   - Spec: docs/specs/skills/clickhouse_querying.md
   - Queries em ClickHouse com MergeTree/SummingMergeTree/ReplacingMergeTree/Views

## Required Agent Capabilities

- **Primary**: `analytics_agent` - capabilities: [analytics, clickhouse, weekly_kpis, real_time_analytics, card_analytics, acquisition_analytics, ai_recommendations, cohort_analysis, campaign_analytics]
- **Secondary**: `crm_data_agent` - capabilities: [crm_data, segmentation, clickhouse, weekly_stats, profiling]
- **Tertiary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, segment_dashboard, campaign_dashboard]

## RAG Chunk References

- `category: analytics` + `source_file CONTAINS 'analytics/src/services/analyticsService'`
- `category: analytics` + `source_file CONTAINS 'analytics/src/services/cardAnalyticsService'`
- `category: analytics` + `source_file CONTAINS 'analytics/src/services/acquisitionAnalyticsService'`
- `category: analytics` + `source_file CONTAINS 'analytics/src/services/aiRecommendationService'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/weekly-stats.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/weekly-ai-analysis.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/audience-queries.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/workers/weekly-stats.worker'`
- `category: crm_infra` + `source_file CONTAINS 'segment-engine/src/clickhouse'`
- `category: crm_frontend` + `source_file CONTAINS 'engage-ai-flow/client/src/components/analytics'`
- `category: crm_frontend` + `source_file CONTAINS 'engage-ai-flow/client/src/components/segments'`
- `category: crm_frontend` + `source_file CONTAINS 'engage-ai-flow/client/src/components/campaigns'`
- `category: usecase` + `domain: analytics`

## Related Use Cases

- **Depends on**: UC-TRK-001 (Coleta de Eventos - TrackerJS alimenta o pipeline de ingestao), UC-SEG-001 (Pipeline de Segmentacao - perfis e ClickHouse tables como fonte de dados)
- **Enables**: UC-CAM-001 (Campanhas - analytics informa performance de campanhas), UC-JRN-001 (Journey Builder - metricas de engagement informam decisoes de jornada)
- **Conflicts with**: nenhum

## Implementation Notes

- Analytics service e um microservico TypeScript/Node separado rodando na porta 3007
- Dados real-time vem de MongoDB (visitors, events, sessions, cards) com queries sub-minuto
- Dados historicos/agregados vem de ClickHouse via segment-engine
- AI Recommendations usam GPT-4o-mini (OpenAI) + Pinecone vectors + OpenAI embeddings
- Weekly AI Analysis tambem usa GPT-4o-mini com prompts vertical-specific (gambling/ecommerce/saas/fintech)
- ClickHouse tables usam engines otimizados: MergeTree (raw), SummingMergeTree (agregacoes), ReplacingMergeTree (snapshots), Views (metricas derivadas)
- Materialized Views auto-agregam deposits_hourly, deposits_daily, clicks_hourly, purchases_daily
- PeerDB CDC sincroniza MongoDB -> ClickHouse em near-real-time
- Frontend usa Recharts para charts, D3 para visualizacoes complexas (heatmaps, force graphs)
- Engagement score formula: (timeOnSite/10)*25 + (pagesViewed/5)*25 + (sessionCount/3)*25 + (actionsPerSession/10)*25
- Bounce rate definido como sessoes com <3 clicks
- Audience queries sao todas paginadas para performance em datasets grandes
