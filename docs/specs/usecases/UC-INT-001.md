# [UC-INT-001] Entrega SMS via SendSpeed

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-INT-001 |
| **Domain** | integrations |
| **Repos** | userin-integrations |
| **Priority** | P0-Critical |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Entrega de mensagens SMS atraves da infraestrutura propria SendSpeed. Suporta envio individual e em massa (bulk), com tracking de delivery status, retry automatico, e rate limiting por operator. Integrado ao Journey Builder como node de acao e ao Campaign Manager para disparos em massa.

### Data Models

- **Model**: SmsMessage (repo: userin-integrations, path: `src/domain/models/SmsMessage.ts`)
  - Fields: `id: string`, `to: string`, `from: string`, `body: string`, `status: enum[queued|sent|delivered|failed|rejected]`, `campaignId?: string`, `journeyId?: string`, `metadata: object`
- **Model**: SmsProvider (repo: userin-integrations, path: `src/domain/models/SmsProvider.ts`)
  - Fields: `id: string`, `name: string`, `apiKey: string`, `region: string`, `rateLimit: number`, `enabled: boolean`
- **Model**: DeliveryReport (repo: userin-integrations, path: `src/domain/models/DeliveryReport.ts`)
  - Fields: `messageId: string`, `status: string`, `errorCode?: string`, `deliveredAt?: Date`, `operator: string`

### Services

- **Service**: SmsService (repo: userin-integrations, path: `src/application/services/SmsService.ts`)
  - Methods: `send()`, `sendBulk()`, `getStatus()`, `retry()`, `getDeliveryReport()`
- **Service**: SmsProviderAdapter (repo: userin-integrations, path: `src/application/services/SmsProviderAdapter.ts`)
  - Methods: `connect()`, `sendViaProvider()`, `checkBalance()`, `getProviderStatus()`
- **Service**: SmsQueueWorker (repo: userin-integrations, path: `src/workers/SmsQueueWorker.ts`)
  - Methods: `processQueue()`, `handleRetry()`, `reportDelivery()`

### Routes/Endpoints

- `POST /api/sms/send` -> `SmsService.send()`
- `POST /api/sms/bulk` -> `SmsService.sendBulk()`
- `GET /api/sms/:id/status` -> `SmsService.getStatus()`
- `POST /api/sms/webhook/delivery` -> callback de delivery report do provider

### Frontend Components

- Nao possui UI propria (acionado via Journey Builder ou Campaign Manager)

## Acceptance Criteria

1. GIVEN um contato com numero de telefone valido e consentimento opt-in
   WHEN uma campanha ou journey dispara envio SMS
   THEN a mensagem e enfileirada, enviada via provider, e status atualizado para "sent"

2. GIVEN uma mensagem enviada com status "sent"
   WHEN o provider retorna delivery report via webhook
   THEN o status e atualizado para "delivered" ou "failed" com errorCode

3. GIVEN uma mensagem com status "failed" e errorCode retryable
   WHEN o retry automatico executa (max 3 tentativas, backoff exponencial)
   THEN a mensagem e reenviada com incremento do retry counter

4. GIVEN um bulk send de 10.000 mensagens
   WHEN processadas pelo SmsQueueWorker
   THEN respeita rate limit do provider (ex: 100/s) e completa sem throttling errors

## Required Skills

1. **SmsDelivery** - nova
   - Spec: docs/specs/skills/sms_delivery.md
   - Envio e tracking de SMS via providers

2. **QueueProcessing** - existente
   - Spec: docs/specs/skills/queue_processing.md
   - Processamento de filas com retry e rate limiting

## Required Agent Capabilities

- **Primary**: `crm_integration_agent` - capabilities: [sms, crm_integration]
- **Secondary**: `crm_backend_agent` - capabilities: [campaigns, journeys]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'userin-integrations/services/SmsService'`
- `category: crm_data_pipeline` + `source_file CONTAINS 'userin-integrations/workers/SmsQueueWorker'`
- `category: crm_model` + `source_file CONTAINS 'userin-integrations/models/SmsMessage'`
- `category: usecase` + `domain: integrations`

## Related Use Cases

- **Depends on**: UC-CON-001 (Contatos - precisa de numero de telefone valido)
- **Enables**: UC-CAM-004 (Triggers de Campanha - SMS como canal de entrega), UC-JRN-003 (Motor de Journey - SendSMS e node de acao)
- **Conflicts with**: nenhum

## Implementation Notes

- Queue usa Kafka topic `sms.outbound` com particao por operator region
- Retry com backoff exponencial: 1min, 5min, 30min (max 3 tentativas)
- Rate limiting implementado via token bucket per-provider
- Delivery webhooks sao idempotentes (dedup por messageId)
- Phone number normalization: E.164 format obrigatorio
- Opt-out handling: verifica lista de unsubscribe antes de enviar
