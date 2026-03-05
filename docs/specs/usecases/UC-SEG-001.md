# [UC-SEG-001] Pipeline de Segmentacao Comportamental

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SEG-001 |
| **Domain** | segments |
| **Repos** | segment-engine |
| **Priority** | P0-Critical |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Pipeline completo de segmentacao comportamental que processa eventos de usuario via Kafka em 3 fases (classify, fetch ClickHouse, compileProfile), produzindo perfis enriquecidos com 15 secoes em MongoDB. O ActiveUsersWorker detecta usuarios inativos a cada minuto via ClickHouse e publica no Kafka topic `users-segmentation`, onde o KafkaConsumer orquestra classificacao de estagio, 3 queries consolidadas ao ClickHouse, calculo de best-time e preferencias, e finalmente a compilacao do perfil em 10 etapas via ProfileService.compileProfile().

### Data Models

- **Model**: UserProfile (repo: segment-engine, path: `src/models/user-profile.model.ts`)
  - 15 sections:
  - Identification: `externalId: string`, `companyId: string`, `visitorId: string`, `allLocalstorageIds: string[]`
  - Stage: `stage: enum[anonymous|registered|ftd|mtd]`, `hookTypes: string[]`
  - BestTime: `bestHour: number`, `bestDayHour: object`, `dailyRanking: object`, `topHours: number[]`, `proposedContactTimestamp: Date`
  - Deposits: `count: number`, `total: number`, `average: number`, `ftd: {amount, date}`, `last: {amount, date, type}`, `weekly: object`, `trend: string`, `tier: enum[none|low|medium|high|whale]`
  - Preferences: `topGames: object[]`, `topCategories: object[]`, `totalPageViews: number`, `uniquePages: number`
  - FavoriteGame: `name: string`, `url: string`, `category: string`, `visits: number`
  - Navigation: `lastSession: object`, `allVisitedPages: string[]`, `topPages: object[]`
  - Behavior: `avgSessionDurationMinutes: number`, `sessionsPerWeek: number`, `totalSessions: number`, `lastActiveAt: Date`, `deviceCount: number`
  - Intention: `score: number (0-100)`, `level: enum[high|medium|low]`, `nextStep: string`, `signals: {positive[], negative[]}`, `breakdown: object`
  - Tags: `name: string`, `displayName: string`, `color: string`, `appliedAt: Date`, `ruleId: string`, `manual: boolean`, `journeyId: string`
  - DynamicFields: `Record<string, any>` (AGG, SIGNAL, OUTPUT, AI_SCORING results)
  - Objects: `Record<string, any>` (custom objects like Game Vendor, Payment Method)
  - BalanceRealtime: `variationCount: number`, `isLosingStreak: boolean`, `hitZeroThisSession: boolean`, `alert50Triggered: boolean`, `alert80Triggered: boolean`

### Services

- **Service**: ProfileService (repo: segment-engine, path: `src/services/profile.service.ts`)
  - Methods: `compileProfile()` - 10-step pipeline that orchestrates all sub-services into a single UserProfile document
- **Service**: BehaviorService (repo: segment-engine, path: `src/services/behavior.service.ts`)
  - Computes: `avgSessionDuration`, `sessionsPerWeek`, `totalSessions`, `lastActiveAt`, `deviceCount`
- **Service**: EngagementService (repo: segment-engine, path: `src/services/engagement.service.ts`)
  - Computes: `avgSessionDuration`, `avgPageViewsPerSession`, `avgGamesPerSession`, `daysSinceLastActive`
- **Service**: IntentionService (repo: segment-engine, path: `src/services/intention.service.ts`)
  - Computes: score 0-100, levels high/medium/low, breakdown by 7 factors
- **Service**: PreferencesService (repo: segment-engine, path: `src/services/preferences.service.ts`)
  - Computes: top 20 pages, top 10 games, category distribution via urlMatcherService
- **Service**: DepositService (repo: segment-engine, path: `src/services/deposit.service.ts`)
  - Computes: tiers (none/low/medium/high/whale), trend, weekly analysis
- **Service**: BestTimeService (repo: segment-engine, path: `src/services/best-time.service.ts`)
  - Computes: exponential decay weighted hours, saves to UserBestTime model
- **Service**: UserDataFetcherService (repo: segment-engine, path: `src/services/user-data-fetcher.service.ts`)
  - 3 consolidated ClickHouse queries replacing ~15 individual queries
- **Service**: EventProcessorService (repo: segment-engine, path: `src/services/event-processor.service.ts`)
  - Idempotent insert, feature update, segment evaluation pipeline
- **Service**: TagService (repo: segment-engine, path: `src/services/tag.service.ts`)
  - Evaluates tag rules against compiled profiles

### Workers

- **Worker**: ActiveUsersWorker (repo: segment-engine, path: `src/workers/active-users.worker.ts`)
  - Cron: `*/1 * * * *` (every minute), queries ClickHouse for users inactive 1-2min, publishes to Kafka topic `users-segmentation`
- **Worker**: ClassifierWorker (repo: segment-engine, path: `src/workers/classifier.worker.ts`)
  - Classifies stage: anonymous -> registered -> ftd -> depositor based on hooks
- **Worker**: ExpirationWorker (repo: segment-engine, path: `src/workers/expiration.worker.ts`)
  - FeatureBucket expiration for rolling features
- **Worker**: WeeklyStatsWorker (repo: segment-engine, path: `src/workers/weekly-stats.worker.ts`)
  - Cron: Monday 00:01, creates userin_weekly_companies_stats table (80+ columns)

### Kafka

- **Topic**: `users-segmentation` - main segmentation pipeline
- **Topics**: `ml.scoring.registration`, `ml.scoring.ftd`, `ml.scoring.deposit` - ML scoring events
- **Consumer**: eachBatch mode, 3-level dedup (in-batch Map, cross-batch MongoDB $in, TTL tracking)
- **Producer**: batch 500, `sendMLScoringEvent()` fire-and-forget

### ClickHouse Tables

- `userin_segments_events` (MergeTree) - Raw events
- `userin_segments_deposits_hourly` (SummingMergeTree) - Hourly deposit aggregates
- `userin_segments_deposits_daily` (SummingMergeTree) - Daily deposit aggregates
- `userin_segments_clicks_hourly` (SummingMergeTree) - Hourly click aggregates
- `userin_segments_purchases_daily` (SummingMergeTree) - Daily purchase aggregates
- PeerDB tables (read-only): `users_final`, `userinstaging_events_final`, `userin_hooks_final`, `companies_final`
- Materialized Views: `deposits_hourly_mv`, `deposits_daily_mv`, `clicks_hourly_mv`, `purchases_daily_mv`

### Routes/Endpoints

- `POST /events` -> EventProcessorService (idempotent insert)
- `GET /api/profiles` -> ProfileService
- `GET /api/user-profiles?reprocess=true` -> ProfileService.compileProfile() with forced reprocessing
- `GET /segments` -> SegmentEvaluator
- `GET /users` -> User listing with profile data
- `GET /api/diagnostic` -> System diagnostics

### Frontend Components

- Nenhum componente frontend direto (segment-engine e backend puro, port 3055)

## Acceptance Criteria

1. GIVEN um evento de usuario chegando via ClickHouse (PeerDB)
   WHEN o ActiveUsersWorker executa no cron de 1 minuto e detecta usuario inativo ha 1-2min
   THEN publica mensagem no Kafka topic `users-segmentation` com externalId e companyId

2. GIVEN uma mensagem no Kafka topic `users-segmentation`
   WHEN o KafkaConsumer processa o batch em eachBatch mode
   THEN executa 3 fases sequenciais: ClassifierWorker classifica stage, UserDataFetcherService executa 3 queries consolidadas no ClickHouse, e ProfileService.compileProfile() executa o pipeline de 10 etapas

3. GIVEN o KafkaConsumer processando um batch de usuarios
   WHEN mensagens duplicadas aparecem no mesmo batch ou entre batches
   THEN a deduplicacao em 3 niveis (in-batch Map, cross-batch MongoDB $in, TTL tracking) elimina processamento redundante

4. GIVEN o ProfileService.compileProfile() executando
   WHEN todos os 10 passos completam (behavior, engagement, intention, preferences, deposits, bestTime, tags, dynamicFields, objects, balanceRealtime)
   THEN o UserProfile e salvo em MongoDB com todas as 15 secoes populadas corretamente

5. GIVEN um usuario com hookTypes indicando primeiro deposito
   WHEN o ClassifierWorker processa o hook
   THEN o stage avanca de `registered` para `ftd` e o ProfileService e trigado para recompilacao

6. GIVEN o WeeklyStatsWorker executando na segunda-feira 00:01
   WHEN o cron dispara
   THEN cria/atualiza tabela `userin_weekly_companies_stats` no ClickHouse com 80+ colunas de KPIs semanais

## Required Skills

1. **SegmentPipeline** - nova
   - Spec: docs/specs/skills/segment_pipeline.md
   - Pipeline de classificacao comportamental via Kafka workers com 3-phase processing

2. **UserProfiling** - nova
   - Spec: docs/specs/skills/user_profiling.md
   - Compilacao de perfis de usuario com 15 secoes via ProfileService 10-step pipeline

3. **ClickHouseQuerying** - nova
   - Spec: docs/specs/skills/clickhouse_querying.md
   - Queries consolidadas em ClickHouse com MergeTree/SummingMergeTree/ReplacingMergeTree

## Required Agent Capabilities

- **Primary**: `crm_data_agent` - capabilities: [segmentation, kafka, data_pipeline, profiling, clickhouse]
- **Secondary**: `crm_backend_agent` - capabilities: [crm_backend, segments, mongodb]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/profile.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/behavior.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/engagement.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/intention.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/user-data-fetcher.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/event-processor.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/workers/active-users.worker'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/workers/classifier.worker'`
- `category: crm_model` + `source_file CONTAINS 'user-profile.model'`
- `category: crm_infra` + `source_file CONTAINS 'segment-engine/src/clickhouse/schema'`
- `category: usecase` + `domain: segments`

## Related Use Cases

- **Depends on**: UC-TRK-001 (Coleta de Eventos - eventos alimentam ClickHouse via PeerDB)
- **Enables**: UC-SEG-002 (Sinais Dinamicos - perfis base para computacao dinamica), UC-SEG-003 (Best-Time-to-Send - BestTimeService integrado no pipeline), UC-SEG-004 (Dashboard Widgets - WeeklyStatsWorker alimenta visualizacoes), UC-JRN-001 (Journey Builder - SegmentTrigger usa segmentos)
- **Conflicts with**: nenhum

## Implementation Notes

- Segment-engine e um microservico TypeScript/Node separado rodando na porta 3055
- Infraestrutura: MongoDB (perfis) + ClickHouse (analytics, database `userin-analytics-v2`) + Redis (cache) + Kafka (Confluent Cloud)
- KafkaConsumer usa eachBatch mode com 3-level dedup para idempotencia
- UserDataFetcherService consolida ~15 queries individuais em 3 queries ClickHouse otimizadas
- ProfileService.compileProfile() orquestra 10 sub-services em pipeline sequencial
- UserProfile em MongoDB tem 15 secoes distintas incluindo BalanceRealtime para iGaming
- ActiveUsersWorker roda a cada 1 minuto, detecta usuarios inativos via ClickHouse query
- ClassifierWorker avanca stages (anonymous -> registered -> ftd -> mtd) baseado em hookTypes
- ML scoring events publicados via Kafka fire-and-forget (batch 500) para topics ml.scoring.*
- ClickHouse usa MergeTree para eventos raw, SummingMergeTree para agregacoes temporais, ReplacingMergeTree para snapshots
- PeerDB sincroniza tabelas read-only (users_final, userinstaging_events_final, userin_hooks_final, companies_final)
