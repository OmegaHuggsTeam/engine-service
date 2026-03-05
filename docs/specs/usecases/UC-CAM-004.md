# [UC-CAM-004] Agendamento e Triggers de Campanha

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CAM-004 |
| **Domain** | campaigns |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P2-Medium |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Gerencia o agendamento de campanhas para envio futuro e a execucao via Kafka workers. Campanhas podem ser agendadas para data/hora especifica ou disparadas por triggers de evento. O CampaignWorker consome mensagens do Kafka e orquestra o envio em lotes.

### Data Models

- **Model**: Campaign (repo: platform-backend, path: `backend/src/domain/models/Campaign.js`)
  - Fields: `schedule: { scheduled_at: Date, timezone: string, recurring: boolean }`, `trigger: { type: enum[manual|scheduled|event], event_name: string }`

### Services

- **Service**: campaignService (repo: platform-backend, path: `backend/src/application/services/campaignService.js`)
  - Methods: `schedule()`, `cancelSchedule()`, `getScheduled()`, `triggerNow()`
- **Kafka Worker**: CampaignWorker (repo: platform-backend, path: `backend/src/infrastructure/kafka/CampaignWorker.js`)
  - Consumes: `campaigns.scheduled`, `campaigns.triggered`
- **Kafka Producer**: CampaignProducer (repo: platform-backend, path: `backend/src/infrastructure/kafka/CampaignProducer.js`)
  - Produces: `campaigns.scheduled`, `campaigns.triggered`, `campaigns.batch.send`

### Routes/Endpoints

- `POST /api/campaigns/:id/schedule` -> `campaignService.schedule()`
- `DELETE /api/campaigns/:id/schedule` -> `campaignService.cancelSchedule()`
- `POST /api/campaigns/:id/trigger` -> `campaignService.triggerNow()`

### Frontend Components

- **Component**: CampaignScheduler (repo: engage-ai-flow, path: `client/src/components/campaigns/CampaignScheduler.tsx`)
- **Component**: TriggerConfig (repo: engage-ai-flow, path: `client/src/components/campaigns/TriggerConfig.tsx`)

## Acceptance Criteria

1. GIVEN uma campanha em status 'draft' com audiencia definida
   WHEN o usuario agenda para data futura via POST /api/campaigns/:id/schedule
   THEN o status muda para 'scheduled' e Kafka recebe mensagem em `campaigns.scheduled`

2. GIVEN uma campanha agendada
   WHEN a data/hora agendada e atingida
   THEN o CampaignWorker consome a mensagem e inicia envio em lotes via CampaignProducer

3. GIVEN uma campanha agendada
   WHEN o usuario cancela o agendamento via DELETE /api/campaigns/:id/schedule
   THEN o status volta para 'draft' e a mensagem Kafka e invalidada

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **KafkaOrchestration** - nova
   - Spec: docs/specs/skills/kafka_orchestration.md
   - Producao e consumo de mensagens Kafka para campanhas

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, campaigns, kafka]
- **Secondary**: `crm_integration_agent` - capabilities: [kafka, scheduling, workers]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/campaignService'`
- `category: crm_backend` + `source_file CONTAINS 'kafka/CampaignWorker'`
- `category: crm_backend` + `source_file CONTAINS 'kafka/CampaignProducer'`
- `category: usecase` + `domain: campaigns`

## Related Use Cases

- **Depends on**: UC-CAM-001 (Criar Campanha - necessario ter campanha criada)
- **Enables**: UC-CAM-003 (Analytics - envios geram dados de analytics)
- **Conflicts with**: nenhum

## Implementation Notes

- Kafka e usado para desacoplamento entre agendamento e envio
- CampaignWorker processa em lotes de 1000 contatos para evitar sobrecarga
- Timezone handling usa moment-timezone para conversao
- Campanhas recorrentes usam cron expression no campo schedule
- Retry policy: 3 tentativas com backoff exponencial no CampaignWorker
