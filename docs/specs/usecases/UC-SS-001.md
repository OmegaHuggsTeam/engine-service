# [UC-SS-001] Pipeline de Envio SMS Multi-Supplier

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-001 |
| **Domain** | sms_delivery |
| **Repos** | sendspeed0/nodejs-api-v02 (branch: dev), sendspeed0/app-send-speed (branch: main) |
| **Priority** | P0-Critical |
| **Complexity** | XL |
| **Status** | Production |

## Domain Context

Pipeline de envio SMS multi-supplier da SendSpeed com 15+ fornecedores e 2 paths de ingestao. O nodejs-api-v02 (TypeScript, Hexagonal Architecture) recebe mensagens via REST, valida, roteia para supplier correto e publica no RabbitMQ. O app-send-speed (PHP 7.4) gerencia campanhas, creditos e selecao de supplier via Strategy pattern.

### Data Models

- **Model**: Message (nodejs-api-v02: `src/domain/entities/`)
  - Fields: `id: string`, `phone: string`, `message: string`, `supplier: string`, `status: enum(pending|sent|delivered|failed)`, `campaign_id: string`, `client_id: string`, `credits: number`
- **Model**: Campaign (app-send-speed: `app/Models/`)
  - Fields: `id`, `name`, `message`, `phone_list`, `supplier_id`, `status`, `scheduled_at`, `total_sent`, `total_delivered`, `total_failed`
- **Model**: Supplier (app-send-speed: `app/Models/`)
  - Fields: `id`, `name`, `type: enum(pushfy|sona|infobip|mex10|plugni|yup|...)`, `api_url`, `api_key`, `status`, `priority`, `cost_per_sms`
- **Enum**: SupplierType
  - Values: `pushfy`, `sona`, `infobip`, `mex10`, `plugni`, `yup`, `facilitamovel`, `mobizon`, `smsdev`, `aws_sns`, `zenvia`, `iagente`, `comtele`, `twilio`

### Services

- **Service**: MessageIngestionV2 (nodejs-api-v02: `src/application/usecases/`)
  - Methods: `ingestV2(payload)` - novo path com validacao robusta
  - Flow: REST → Validation → Supplier Routing → RabbitMQ publish
  - Partitioning: consistent hash por phone number para ordering garantido
- **Service**: MessageIngestionV1 (nodejs-api-v02: `src/application/usecases/`)
  - Methods: `ingestV1(payload)` - path legado compativel
  - Flow: REST → basic validation → RabbitMQ publish (formato antigo)
- **Service**: SupplierStrategy (app-send-speed: `app/Services/Suppliers/`)
  - Pattern: Strategy com factory - cada supplier implementa interface comum
  - Methods: `send(phone, message, options)`, `getBalance()`, `getStatus()`
  - 15+ implementacoes concretas (PushfySupplier, SonaSupplier, InfobipSupplier, etc.)
- **Service**: CampaignService (app-send-speed: `app/Services/`)
  - Methods: `create(data)`, `schedule(campaign_id, datetime)`, `execute(campaign_id)`, `pause(campaign_id)`
  - Credit deduction before send, rollback on failure
- **Service**: CreditService (app-send-speed: `app/Services/`)
  - Methods: `deduct(client_id, amount)`, `refund(client_id, amount)`, `getBalance(client_id)`
  - Pre-validation: blocks send if insufficient credits
- **Service**: DeduplicationService (app-send-speed: `app/Services/`)
  - Methods: `deduplicate(phone_list)`, `checkRecent(phone, hours=24)`
  - Anti-fraud: blocks duplicate sends within configurable window

### Routes/Endpoints

- `POST /api/v2/messages` → MessageIngestionV2 (nodejs-api-v02)
- `POST /api/v1/messages` → MessageIngestionV1 (nodejs-api-v02, legado)
- `POST /api/campaigns` → CampaignService.create (app-send-speed)
- `POST /api/campaigns/{id}/execute` → CampaignService.execute
- `GET /api/suppliers` → lista suppliers disponíveis
- `GET /api/credits/{client_id}` → CreditService.getBalance

## Acceptance Criteria

1. GIVEN mensagem recebida via POST /api/v2/messages com phone e message validos
   WHEN MessageIngestionV2.ingestV2() e chamado
   THEN mensagem e validada, supplier selecionado via routing rules, e publicada no RabbitMQ com consistent hash partitioning por phone number

2. GIVEN campanha criada com phone_list de 10K numeros
   WHEN CampaignService.execute() e chamado
   THEN creditos sao deduzidos via CreditService.deduct(), mensagens sao publicadas no RabbitMQ em batches, e progresso e atualizado em real-time

3. GIVEN supplier Pushfy selecionado para envio
   WHEN PushfySupplier.send() e chamado
   THEN request HTTP e feito para API do Pushfy com api_key correta, resposta e normalizada para status padrao (sent|delivered|failed)

4. GIVEN phone number que recebeu SMS nas ultimas 24h
   WHEN DeduplicationService.checkRecent() retorna true
   THEN envio e bloqueado com erro DUPLICATE_WITHIN_WINDOW

5. GIVEN cliente com saldo insuficiente de creditos
   WHEN tentativa de envio e feita
   THEN CreditService.deduct() lanca excecao INSUFFICIENT_CREDITS e nenhuma mensagem e publicada

6. GIVEN path V1 legado ativo
   WHEN POST /api/v1/messages recebe payload no formato antigo
   THEN MessageIngestionV1.ingestV1() converte para formato interno e processa normalmente

## Required Skills

1. **SmsDelivery** - existente
   - Spec: docs/specs/skills/sms_delivery.md
   - Envio multi-supplier com Strategy pattern e routing inteligente

2. **CreditManagement** - existente
   - Spec: docs/specs/skills/credit_management.md
   - Gestao de creditos com pre-validacao e rollback

## Required Agent Capabilities

- **Primary**: `sendspeed_sms_agent` - capabilities: [sms_delivery, supplier_routing, campaign_execution, credit_management, rabbitmq]
- **Secondary**: `sendspeed_admin_agent` - capabilities: [supplier_management, campaign_management]

## RAG Chunk References

- `category: sendspeed_sms` + `source_file CONTAINS 'MessageIngestion'`
- `category: sendspeed_sms` + `source_file CONTAINS 'SupplierStrategy'`
- `category: sendspeed_app` + `source_file CONTAINS 'CampaignService'`
- `category: sendspeed_app` + `source_file CONTAINS 'CreditService'`

## Related Use Cases

- **Depends on**: nenhum (core pipeline)
- **Enables**: UC-SS-002 (Webhook Processing), UC-SS-003 (Campaign Management), UC-SS-005 (Status Processing)
- **Conflicts with**: nenhum

## Implementation Notes

- nodejs-api-v02 usa Hexagonal Architecture (ports/adapters) com TypeScript
- 2 paths de ingestao coexistem: V1 (legado) e V2 (novo com validacao robusta)
- RabbitMQ com consistent hash exchange para garantir ordering por phone
- app-send-speed PHP 7.4 com Vue.js 2 - migração para Laravel 11 em andamento
- Strategy pattern permite adicionar novos suppliers sem alterar código core
- Cada supplier tem custos diferentes - routing considera custo + disponibilidade + historico
- Anti-fraud: dedup por phone + cooldown window configuravel por cliente
- Creditos pre-debitados antes do envio, refund automatico em caso de falha confirmada
