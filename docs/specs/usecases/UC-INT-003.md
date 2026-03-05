# [UC-INT-003] Adapter Smartico + SevenX/Databricks Ingestion

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-INT-003 |
| **Domain** | integrations |
| **Repos** | userin-integrations, ingestion-service |
| **Priority** | P1-High |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Duas integracoes combinadas: (1) Adapter Smartico para gamificacao e loyalty programs - sincroniza pontos, niveis e badges com o CRM; (2) Pipeline de ingestao SevenX/Databricks para importar dados de plataformas externas (casinos, sportsbooks) via batch e streaming, com deduplicacao Redis e transformacao para o schema interno.

### Data Models

- **Model**: SmaticoPlayer (repo: userin-integrations, path: `src/domain/models/SmaticoPlayer.ts`)
  - Fields: `externalId: string`, `points: number`, `level: number`, `badges: string[]`, `lastSync: Date`, `contactId: string`
- **Model**: SmaticoEvent (repo: userin-integrations, path: `src/domain/models/SmaticoEvent.ts`)
  - Fields: `type: enum[points_earned|level_up|badge_awarded|mission_completed]`, `playerId: string`, `data: object`, `timestamp: Date`
- **Model**: IngestionJob (repo: ingestion-service, path: `src/domain/models/IngestionJob.ts`)
  - Fields: `id: string`, `source: enum[sevenx|databricks|csv|api]`, `status: enum[pending|running|completed|failed]`, `recordsProcessed: number`, `recordsSkipped: number`, `errors: string[]`
- **Model**: IngestionRecord (repo: ingestion-service, path: `src/domain/models/IngestionRecord.ts`)
  - Fields: `externalId: string`, `source: string`, `data: object`, `deduplicationKey: string`, `processedAt?: Date`

### Services

- **Service**: SmaticoAdapter (repo: userin-integrations, path: `src/application/services/SmaticoAdapter.ts`)
  - Methods: `syncPlayer()`, `getPlayerData()`, `processEvent()`, `batchSync()`
- **Service**: SmaticoWebhookHandler (repo: userin-integrations, path: `src/application/services/SmaticoWebhookHandler.ts`)
  - Methods: `handleEvent()`, `validateSignature()`, `mapToContact()`
- **Service**: IngestionPipeline (repo: ingestion-service, path: `src/application/services/IngestionPipeline.ts`)
  - Methods: `ingest()`, `transform()`, `deduplicate()`, `load()`
- **Service**: SevenXConnector (repo: ingestion-service, path: `src/connectors/SevenXConnector.ts`)
  - Methods: `fetchPlayers()`, `fetchTransactions()`, `fetchEvents()`
- **Service**: DatabricksConnector (repo: ingestion-service, path: `src/connectors/DatabricksConnector.ts`)
  - Methods: `runQuery()`, `fetchResults()`, `streamResults()`
- **Service**: RedisDeduplicator (repo: ingestion-service, path: `src/application/services/RedisDeduplicator.ts`)
  - Methods: `isDuplicate()`, `markProcessed()`, `getStats()`, `cleanup()`

### Routes/Endpoints

- `POST /api/smartico/webhook` -> `SmaticoWebhookHandler.handleEvent()`
- `POST /api/smartico/sync/:contactId` -> `SmaticoAdapter.syncPlayer()`
- `POST /api/ingestion/jobs` -> `IngestionPipeline.ingest()`
- `GET /api/ingestion/jobs/:id` -> `IngestionPipeline.getJobStatus()`
- `POST /api/ingestion/sevenx/sync` -> `SevenXConnector.fetchPlayers()`

### Frontend Components

- **Page**: IngestionDashboard (repo: engage-ai-flow, path: `client/src/pages/integrations/IngestionDashboard.tsx`)
- **Component**: JobStatusTable (repo: engage-ai-flow, path: `client/src/components/integrations/JobStatusTable.tsx`)

## Acceptance Criteria

1. GIVEN um evento Smartico de points_earned via webhook
   WHEN recebido com assinatura valida
   THEN pontos sao atualizados no contato CRM e evento registrado na timeline

2. GIVEN um job de ingestao SevenX com 50.000 registros
   WHEN processado pela pipeline
   THEN registros duplicados sao filtrados via Redis (dedup key), novos registros sao transformados para schema interno e carregados no MongoDB

3. GIVEN registros ja processados anteriormente (mesmo deduplicationKey)
   WHEN aparecem em um novo batch
   THEN sao skipped sem erro e contados em recordsSkipped

4. GIVEN uma conexao Databricks configurada
   WHEN um job de ingestao streaming e iniciado
   THEN dados fluem em near-real-time com latencia <30s do source ao CRM

5. GIVEN um job de ingestao que falha parcialmente
   WHEN 10% dos registros tem erro de transformacao
   THEN os 90% validos sao carregados, erros sao logados no job com detalhes, e status final e "completed" com warnings

## Required Skills

1. **ExternalIntegration** - nova
   - Spec: docs/specs/skills/external_integration.md
   - Conexao com APIs externas (Smartico, SevenX, Databricks)

2. **DataIngestion** - nova
   - Spec: docs/specs/skills/data_ingestion.md
   - Pipeline ETL com deduplicacao e transformacao

3. **QueueProcessing** - existente
   - Spec: docs/specs/skills/queue_processing.md
   - Processamento de filas batch e streaming

## Required Agent Capabilities

- **Primary**: `crm_integration_agent` - capabilities: [crm_integration, smartico, event_collection]
- **Secondary**: `crm_data_agent` - capabilities: [ingestion, kafka_workers, behavioral_analysis]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'userin-integrations/services/SmaticoAdapter'`
- `category: crm_backend` + `source_file CONTAINS 'ingestion-service/services/IngestionPipeline'`
- `category: crm_backend` + `source_file CONTAINS 'ingestion-service/connectors'`
- `category: crm_data_pipeline` + `source_file CONTAINS 'ingestion-service/services/RedisDeduplicator'`
- `category: usecase` + `domain: integrations`

## Related Use Cases

- **Depends on**: UC-CON-001 (Contatos - ingestao cria/atualiza contatos)
- **Enables**: UC-SEG-001 (Segmentacao - dados ingeridos alimentam segmentos), UC-CON-003 (Perfil de Contato - Smartico data enriquece perfil), UC-ANA-001 (Analytics - dados de plataformas externas)
- **Conflicts with**: nenhum

## Implementation Notes

- Smartico webhook usa HMAC-SHA256 para validacao de assinatura
- Redis dedup usa SET com TTL de 7 dias (evita reprocessamento em re-runs)
- SevenX connector usa pagination (1000 records/page) com cursor-based
- Databricks connector usa SQL warehouse (nao cluster) para cost optimization
- Transformacao usa mapping configuravel por source (JSON schema)
- Ingestion jobs sao idempotentes (re-run seguro do mesmo batch)
- Kafka topic `ingestion.records` para streaming, batch usa direct API calls
- Error records salvos em `ingestion.dead_letter` topic para reprocessamento manual
