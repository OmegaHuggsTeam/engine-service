# [UC-SS-004] Billing, Credits e Client Management

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-004 |
| **Domain** | billing |
| **Repos** | sendspeed0/app-send-speed (branch: main), sendspeed0/backoffice (branch: main), sendspeed0/portal-cliente-api (branch: main) |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Production |

## Domain Context

Sistema de billing e gestao de creditos da plataforma SendSpeed. Tres camadas: app-send-speed (PHP portal do cliente), backoffice (Laravel 9 admin) e portal-cliente-api (Laravel 11 API REST). O modelo de negocio e pre-pago: clientes compram creditos que sao debitados a cada envio. Cada canal/supplier tem custo diferente. Multi-tenant via UUID api_keys.

### Data Models

- **Model**: Client (portal-cliente-api: `app/Domain/Models/`)
  - Fields: `id: uuid`, `name`, `email`, `api_key: uuid`, `plan: enum(free|starter|pro|enterprise)`, `credit_balance: decimal`, `status: enum(active|suspended|blocked)`, `created_at`
- **Model**: CreditTransaction (portal-cliente-api: `app/Domain/Models/`)
  - Fields: `id`, `client_id`, `type: enum(purchase|debit|refund|bonus)`, `amount: decimal`, `description`, `reference_id`, `balance_after`, `created_at`
- **Model**: Invoice (backoffice: `app/Models/`)
  - Fields: `id`, `client_id`, `amount`, `credits_purchased`, `payment_method`, `status: enum(pending|paid|cancelled)`, `due_date`
- **Model**: PricingTable (backoffice: `app/Models/`)
  - Fields: `id`, `channel`, `supplier_id`, `cost_per_unit: decimal`, `client_markup: decimal`, `effective_price: decimal`, `active`

### Services

- **Service**: CreditService (portal-cliente-api: `app/Domain/Services/`)
  - Clean Architecture/DDD - Domain layer
  - Methods: `purchaseCredits(client_id, amount, payment_ref)`, `debitCredits(client_id, amount, reference)`, `refundCredits(client_id, amount, reason)`, `getBalance(client_id)`, `getStatement(client_id, period)`
  - Atomic transactions with optimistic locking
- **Service**: ClientManagement (portal-cliente-api: `app/Domain/Services/`)
  - 32 CRUD endpoints for full client lifecycle
  - Methods: `register(data)`, `updatePlan(client_id, plan)`, `suspend(client_id, reason)`, `generateApiKey(client_id)`
  - Multi-tenant isolation via api_key header
- **Service**: BillingService (backoffice: `app/Services/`)
  - Invoice generation, payment reconciliation
  - Methods: `generateInvoice(client_id, period)`, `processPayment(invoice_id, payment_data)`, `applyBonus(client_id, amount, reason)`
  - Kafka integration for async payment processing
- **Service**: PricingEngine (backoffice: `app/Services/`)
  - Dynamic pricing based on volume, channel, supplier
  - Methods: `calculatePrice(channel, supplier, volume)`, `getClientPrice(client_id, channel)`
  - Tiered pricing: volume discounts at 10K, 50K, 100K thresholds

### Routes/Endpoints

- `GET /api/v1/credits/balance` → CreditService.getBalance (portal-cliente-api)
- `GET /api/v1/credits/statement` → CreditService.getStatement
- `POST /api/v1/credits/purchase` → CreditService.purchaseCredits
- `GET /api/v1/clients` → ClientManagement CRUD (portal-cliente-api, 32 endpoints)
- `POST /admin/invoices/generate` → BillingService.generateInvoice (backoffice)
- `POST /admin/pricing/update` → PricingEngine update (backoffice)
- `POST /admin/clients/{id}/bonus` → BillingService.applyBonus

## Acceptance Criteria

1. GIVEN cliente ativo com plano 'pro'
   WHEN purchaseCredits(client_id, 10000, payment_ref) e chamado
   THEN CreditTransaction tipo 'purchase' e criada, balance_after reflete novo saldo, e transacao e atomica com optimistic locking

2. GIVEN campanha executando com 5000 SMS
   WHEN debitCredits() e chamado para cada batch
   THEN creditos sao debitados atomicamente, e se saldo insuficiente no meio da campanha, execucao e pausada e alerta e gerado

3. GIVEN SMS falhou com status 'failed' confirmado pelo webhook
   WHEN refundCredits() e acionado automaticamente
   THEN creditos sao devolvidos com CreditTransaction tipo 'refund' e reference_id apontando para o envio original

4. GIVEN admin gerando invoice para cliente no periodo mensal
   WHEN BillingService.generateInvoice() e chamado
   THEN invoice inclui total de creditos consumidos, breakdown por canal/supplier, e preco calculado com volume discounts

5. GIVEN request API com header x-api-key invalido ou ausente
   WHEN qualquer endpoint do portal-cliente-api e acessado
   THEN resposta 401 Unauthorized, nenhum dado e exposto, e tentativa e logada para auditoria

6. GIVEN cliente com volume > 50K SMS/mes
   WHEN PricingEngine.getClientPrice() e calculado
   THEN preco reflete tier discount de 50K (ex: 15% off sobre preco base)

## Required Skills

1. **CreditManagement** - existente
   - Spec: docs/specs/skills/credit_management.md
   - Transacoes atomicas, optimistic locking, statement generation

2. **BillingEngine** - existente
   - Spec: docs/specs/skills/billing_engine.md
   - Invoice generation, pricing tiers, payment reconciliation

## Required Agent Capabilities

- **Primary**: `sendspeed_admin_agent` - capabilities: [billing, credit_management, client_management, pricing]
- **Secondary**: `sendspeed_api_agent` - capabilities: [rest_api, multi_tenant, authentication]

## RAG Chunk References

- `category: sendspeed_api` + `source_file CONTAINS 'CreditService'`
- `category: sendspeed_api` + `source_file CONTAINS 'ClientManagement'`
- `category: sendspeed_admin` + `source_file CONTAINS 'BillingService'`
- `category: sendspeed_admin` + `source_file CONTAINS 'PricingEngine'`

## Related Use Cases

- **Depends on**: UC-SS-001 (Pipeline SMS - gera debitos de credito)
- **Enables**: UC-SS-003 (Campaign Management - validacao de creditos antes do envio)
- **Conflicts with**: nenhum

## Implementation Notes

- portal-cliente-api usa Clean Architecture/DDD com Laravel 11 (Domain/Application/Infrastructure layers)
- PostgreSQL para dados transacionais (creditos, invoices) + MongoDB para logs e audit trail
- Multi-tenant strict: toda query filtra por client_id derivado do api_key no middleware
- Optimistic locking no credit_balance previne race conditions em debitos concorrentes
- PricingEngine com 3 tiers: base (0-10K), mid (10K-50K), high (50K+) com descontos progressivos
- Kafka consumer no backoffice para processar pagamentos de gateway externo
- Redis cache para balance queries (TTL 30s) - invalidado em qualquer transacao
