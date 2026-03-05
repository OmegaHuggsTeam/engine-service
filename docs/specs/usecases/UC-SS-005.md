# [UC-SS-005] Message Delivery Service e Smartico Integration

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-005 |
| **Domain** | sms_delivery |
| **Repos** | sendspeed0/sendspeed-message-delivery (branch: main), sendspeed0/nodejs-api (branch: dev) |
| **Priority** | P1-High |
| **Complexity** | M |
| **Status** | Production |

## Domain Context

Servico de delivery de mensagens que consome do RabbitMQ, envia para suppliers via HTTP e integra com Smartico CRM para tracking. O sendspeed-message-delivery e o consumer principal que processa a queue de envio. O nodejs-api (legado) e o Producer/Consumer original com campaign replication.

### Data Models

- **Model**: DeliveryMessage (sendspeed-message-delivery: `src/`)
  - Fields: `id`, `phone`, `message`, `supplier`, `campaign_id`, `client_id`, `priority: enum(normal|high|urgent)`, `retry_count`, `max_retries`
- **Model**: DeliveryResult
  - Fields: `message_id`, `status: enum(sent|delivered|failed|timeout)`, `supplier_response: object`, `latency_ms`, `cost`
- **Model**: SmarticoEvent (sendspeed-message-delivery: `src/integrations/`)
  - Fields: `event_type`, `contact_id`, `message_id`, `status`, `metadata: object`

### Services

- **Service**: DeliveryConsumer (sendspeed-message-delivery: `src/consumers/`)
  - RabbitMQ consumer com prefetch configuravel
  - Methods: `consume(message)`, `processDelivery(message)`, `handleFailure(message, error)`
  - Batch buffering: acumula mensagens para envio em batch ao supplier
  - Supplier HTTP client com timeout e circuit breaker
- **Service**: StatusNormalizer (sendspeed-message-delivery: `src/normalizers/`)
  - Normaliza respostas de cada supplier para formato padrao
  - Mapping: supplier-specific status codes → DeliveryResult.status
- **Service**: SmarticoIntegration (sendspeed-message-delivery: `src/integrations/`)
  - Sync de eventos de delivery com Smartico CRM
  - Methods: `syncDeliveryEvent(event)`, `updateContactStatus(contact_id, status)`
  - Batch sync: acumula eventos e sincroniza a cada 5 segundos
- **Service**: CampaignReplicator (nodejs-api: `src/`)
  - Legado: replica campanhas do app-send-speed para processamento
  - Methods: `replicateCampaign(campaign_id)`, `produceMessages(campaign)`
  - RabbitMQ Producer com confirmation mode

### Routes/Endpoints

- RabbitMQ Queue: `sms_delivery` → DeliveryConsumer
- RabbitMQ Queue: `campaign_replication` → CampaignReplicator (legado)
- HTTP outbound: supplier APIs (Pushfy, Sona, Infobip, etc.)
- HTTP outbound: Smartico CRM API para sync de eventos

## Acceptance Criteria

1. GIVEN mensagem na queue sms_delivery com supplier=pushfy
   WHEN DeliveryConsumer.processDelivery() e executado
   THEN request HTTP e feito para API Pushfy, resposta e normalizada via StatusNormalizer, e DeliveryResult e publicado na queue de status

2. GIVEN batch de 100 mensagens acumuladas para mesmo supplier
   WHEN batch buffer timeout (2s) e atingido
   THEN todas 100 mensagens sao enviadas em batch request unico ao supplier, reduzindo overhead HTTP

3. GIVEN delivery com status 'delivered' confirmado
   WHEN SmarticoIntegration.syncDeliveryEvent() e chamado
   THEN evento e acumulado no buffer e sincronizado com Smartico CRM no proximo batch (cada 5s)

4. GIVEN supplier retorna erro HTTP 500
   WHEN DeliveryConsumer.handleFailure() processa o erro
   THEN mensagem e reenfileirada com retry_count incrementado, ate max_retries (default 3), apos o qual vai para DLQ

5. GIVEN circuit breaker aberto para supplier Sona (5 falhas consecutivas)
   WHEN nova mensagem com supplier=sona chega
   THEN mensagem e roteada para supplier alternativo ou reenfileirada com delay

6. GIVEN campanha legada via nodejs-api
   WHEN CampaignReplicator.replicateCampaign() processa
   THEN mensagens sao produzidas para queue sms_delivery no formato padrao do DeliveryConsumer

## Required Skills

1. **MessageDelivery** - existente
   - Spec: docs/specs/skills/message_delivery.md
   - Delivery com batch buffering, circuit breaker e retry patterns

2. **CrmSync** - existente
   - Spec: docs/specs/skills/crm_sync.md
   - Integracao com Smartico CRM para tracking de eventos

## Required Agent Capabilities

- **Primary**: `sendspeed_pipeline_agent` - capabilities: [message_delivery, rabbitmq, circuit_breaker, batch_processing]
- **Secondary**: `sendspeed_sms_agent` - capabilities: [supplier_routing, status_normalization]

## RAG Chunk References

- `category: sendspeed_delivery` + `source_file CONTAINS 'DeliveryConsumer'`
- `category: sendspeed_delivery` + `source_file CONTAINS 'SmarticoIntegration'`
- `category: sendspeed_delivery` + `source_file CONTAINS 'StatusNormalizer'`

## Related Use Cases

- **Depends on**: UC-SS-001 (Pipeline SMS - publica mensagens na queue), UC-SS-002 (Webhook - recebe status de volta)
- **Enables**: UC-SS-006 (Blacklist - alimenta dados de falha para maturation pipeline)
- **Conflicts with**: nenhum

## Implementation Notes

- DeliveryConsumer usa RabbitMQ prefetch=100 para throughput otimizado
- Batch buffering por supplier: acumula ate 100 msgs ou 2s timeout (o que vier primeiro)
- Circuit breaker: abre apos 5 falhas consecutivas, half-open apos 30s
- Smartico sync e fire-and-forget com retry interno — nao bloqueia delivery
- nodejs-api (legado) coexiste com nodejs-api-v02 — CampaignReplicator produz no mesmo formato
- Status normalization centralizada — cada supplier tem mapping table dedicado
