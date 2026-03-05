# [UC-SS-002] Webhook Processing e Status Delivery

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-002 |
| **Domain** | sms_delivery |
| **Repos** | sendspeed0/v01-webhook-api (branch: dev), sendspeed0/status-queue-consumer (branch: main) |
| **Priority** | P0-Critical |
| **Complexity** | L |
| **Status** | Production |

## Domain Context

Sistema de recebimento e processamento de webhooks de status de entrega SMS. O v01-webhook-api (Express.js) recebe callbacks de 4 fornecedores (Sona, Pushfy, Infobip, Yup) com 12 contas de provider, normaliza status e publica no RabbitMQ. O status-queue-consumer processa em batches de 30K, atualiza status no banco e faz callback de delivery para o CRM do cliente.

### Data Models

- **Model**: WebhookPayload (v01-webhook-api: `src/`)
  - Fields: `provider: string`, `account: string`, `message_id: string`, `status: string`, `raw_payload: object`, `received_at: datetime`
- **Model**: NormalizedStatus
  - Fields: `message_id: string`, `status: enum(delivered|failed|rejected|expired|unknown)`, `provider_status: string`, `timestamp: datetime`
- **Config**: ProviderAccounts (12 accounts across 4 providers)
  - Sona: 3 accounts (sona_main, sona_backup, sona_premium)
  - Pushfy: 4 accounts (pushfy_01 through pushfy_04)
  - Infobip: 3 accounts (infobip_br, infobip_intl, infobip_bulk)
  - Yup: 2 accounts (yup_standard, yup_priority)

### Services

- **Service**: WebhookReceiver (v01-webhook-api: `src/routes/`)
  - Routes: `POST /webhook/:provider/:account` - endpoint generico por provider/account
  - Normalization: cada provider tem parser dedicado (SonaParser, PushfyParser, etc.)
  - Output: publica NormalizedStatus no RabbitMQ queue `status_updates`
- **Service**: StatusBatchProcessor (status-queue-consumer: `src/`)
  - Batch size: 30,000 mensagens por ciclo
  - Methods: `processBatch(messages[])`, `updateDatabase(statuses[])`, `deliverCallbacks(statuses[])`
  - Database: batch UPDATE com prepared statements para performance
- **Service**: CrmCallbackDelivery (status-queue-consumer: `src/`)
  - Methods: `deliverToClient(client_webhook_url, status_data)`
  - Retry: 3 tentativas com exponential backoff
  - DLQ: Dead Letter Queue para callbacks falhados apos 3 retries
- **Service**: StatusNormalizer (v01-webhook-api: `src/normalizers/`)
  - Converte status provider-specific para enum padrao (delivered|failed|rejected|expired|unknown)
  - Mapping tables por provider (ex: Sona "DELIVRD" → delivered, "UNDELIV" → failed)

### Routes/Endpoints

- `POST /webhook/sona/:account` → SonaParser → RabbitMQ
- `POST /webhook/pushfy/:account` → PushfyParser → RabbitMQ
- `POST /webhook/infobip/:account` → InfobipParser → RabbitMQ
- `POST /webhook/yup/:account` → YupParser → RabbitMQ
- `GET /health` → health check com status do RabbitMQ connection

## Acceptance Criteria

1. GIVEN webhook recebido de Sona com status "DELIVRD" na conta sona_main
   WHEN WebhookReceiver processa o payload
   THEN status e normalizado para "delivered", NormalizedStatus e publicado no RabbitMQ queue status_updates

2. GIVEN 30K mensagens acumuladas na queue status_updates
   WHEN StatusBatchProcessor.processBatch() e executado
   THEN todos os 30K status sao atualizados no banco via batch UPDATE com prepared statements em < 10 segundos

3. GIVEN status atualizado para mensagem com client_webhook_url configurado
   WHEN CrmCallbackDelivery.deliverToClient() e chamado
   THEN POST e feito para webhook do cliente com status_data, com retry automatico (3x exponential backoff) em caso de falha

4. GIVEN callback falhou apos 3 tentativas de retry
   WHEN ultimo retry falha
   THEN mensagem e enviada para Dead Letter Queue (DLQ) para reprocessamento manual

5. GIVEN webhook recebido de provider desconhecido ou conta invalida
   WHEN request chega em /webhook/:provider/:account
   THEN resposta 400 e retornada e evento e logado para auditoria

6. GIVEN multiplos webhooks do mesmo message_id (duplicatas)
   WHEN StatusBatchProcessor processa o batch
   THEN apenas o status mais recente e mantido (idempotencia por message_id)

## Required Skills

1. **WebhookProcessing** - existente
   - Spec: docs/specs/skills/webhook_processing.md
   - Recebimento e normalizacao de webhooks multi-provider

2. **BatchProcessing** - existente
   - Spec: docs/specs/skills/batch_processing.md
   - Processamento de alto volume com batching e DLQ

## Required Agent Capabilities

- **Primary**: `sendspeed_sms_agent` - capabilities: [webhook_processing, status_normalization, batch_processing]
- **Secondary**: `sendspeed_pipeline_agent` - capabilities: [rabbitmq, dlq, retry_patterns]

## RAG Chunk References

- `category: sendspeed_webhook` + `source_file CONTAINS 'WebhookReceiver'`
- `category: sendspeed_pipeline` + `source_file CONTAINS 'StatusBatchProcessor'`
- `category: sendspeed_pipeline` + `source_file CONTAINS 'CrmCallbackDelivery'`

## Related Use Cases

- **Depends on**: UC-SS-001 (Pipeline SMS - gera as mensagens cujo status e recebido)
- **Enables**: UC-SS-005 (Status Processing - normaliza status para delivery service)
- **Conflicts with**: nenhum

## Implementation Notes

- v01-webhook-api e Express.js puro (sem framework), roda em porta dedicada
- 12 contas de provider permitem balanceamento de carga e isolamento de falhas
- StatusBatchProcessor otimizado para 30K msgs/batch - usa prepared statements MySQL
- CrmCallbackDelivery com exponential backoff: 1s, 4s, 16s entre retries
- DLQ permite reprocessamento manual via admin interface
- Idempotencia garantida por message_id - updates sao UPSERT
- Health check verifica RabbitMQ connection - critical para monitoring
