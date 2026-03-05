# [UC-SS-007] Backoffice Administration e Supplier Management

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-007 |
| **Domain** | administration |
| **Repos** | sendspeed0/backoffice (branch: main) |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Production |

## Domain Context

Painel administrativo da plataforma SendSpeed construido em Laravel 9 (MySQL + Redis + Kafka). Gerencia todos os aspectos operacionais: clientes, suppliers, campanhas, billing, phone blocking (Lost List) e monitoramento. Interface web com Blade templates + jQuery para interatividade.

### Data Models

- **Model**: SupplierConfig (backoffice: `app/Models/`)
  - Fields: `id`, `name`, `type`, `api_url`, `api_key`, `status: enum(active|inactive|maintenance)`, `priority: integer`, `rate_limit: integer`, `cost_per_sms: decimal`, `supported_channels: json`, `health_status: enum(healthy|degraded|down)`, `last_health_check: datetime`
- **Model**: LostList (backoffice: `app/Models/`)
  - Fields: `id`, `phone`, `reason: enum(complaint|opt_out|invalid|carrier_block)`, `source`, `added_at`, `client_id`
  - Historicamente chamado "Lost List" — equivalente ao blacklist de producao
- **Model**: ClientAccount (backoffice: `app/Models/`)
  - Fields: `id`, `company_name`, `contact_email`, `plan`, `credit_balance`, `monthly_limit`, `status`, `api_keys: json`, `notes`
- **Model**: SystemAlert (backoffice: `app/Models/`)
  - Fields: `id`, `type: enum(supplier_down|low_credits|high_failure_rate|fraud_detected)`, `severity: enum(info|warning|critical)`, `message`, `acknowledged`, `created_at`

### Services

- **Service**: SupplierManager (backoffice: `app/Services/`)
  - CRUD completo para suppliers com health monitoring
  - Methods: `addSupplier(config)`, `updateSupplier(id, config)`, `toggleStatus(id)`, `healthCheck(id)`, `healthCheckAll()`
  - Auto health check: cron a cada 5 minutos, marca supplier como degraded/down
  - Priority-based routing: suppliers com priority mais alto sao preferidos
- **Service**: LostListManager (backoffice: `app/Services/`)
  - Gestao da Lost List (blacklist de producao)
  - Methods: `addToLostList(phone, reason)`, `removeFromLostList(phone)`, `importBulk(csv_file)`, `exportAll(format)`
  - Integra com blacklist-sendspeed para sync bidirecional
- **Service**: ClientAdminService (backoffice: `app/Services/`)
  - Gestao completa de contas de clientes
  - Methods: `createClient(data)`, `suspendClient(id, reason)`, `adjustCredits(id, amount, reason)`, `setMonthlyLimit(id, limit)`
  - Audit trail para todas as operacoes admin
- **Service**: AlertService (backoffice: `app/Services/`)
  - Monitoring e alertas do sistema
  - Methods: `createAlert(type, severity, message)`, `acknowledgeAlert(id)`, `getActiveAlerts()`
  - Thresholds: supplier failure_rate > 20% → warning, > 50% → critical
  - Low credits: alerta quando cliente tem < 100 creditos
- **Service**: KafkaCallbackProcessor (backoffice: `app/Services/`)
  - Consome callbacks Kafka de pagamentos e status updates
  - Methods: `processPaymentCallback(event)`, `processStatusCallback(event)`
  - Redis caching para dedup de callbacks

### Routes/Endpoints

- `GET /admin/suppliers` → SupplierManager dashboard
- `POST /admin/suppliers` → SupplierManager.addSupplier
- `PUT /admin/suppliers/{id}` → SupplierManager.updateSupplier
- `POST /admin/suppliers/{id}/health-check` → SupplierManager.healthCheck
- `GET /admin/lost-list` → LostListManager dashboard
- `POST /admin/lost-list/import` → LostListManager.importBulk (CSV upload)
- `GET /admin/clients` → ClientAdminService dashboard
- `POST /admin/clients/{id}/adjust-credits` → ClientAdminService.adjustCredits
- `GET /admin/alerts` → AlertService.getActiveAlerts
- `POST /admin/alerts/{id}/acknowledge` → AlertService.acknowledgeAlert

## Acceptance Criteria

1. GIVEN admin adicionando novo supplier Twillio
   WHEN SupplierManager.addSupplier() e chamado com config valida
   THEN supplier e criado com status 'active', health check e executado imediatamente, e supplier aparece na lista com prioridade configurada

2. GIVEN supplier Sona com failure_rate > 50% nas ultimas 2h
   WHEN AlertService detecta threshold
   THEN SystemAlert critical e criado, supplier status muda para 'degraded', e routing automaticamente reduz trafego para esse supplier

3. GIVEN admin importando CSV de 5K phones para Lost List
   WHEN LostListManager.importBulk() processa o arquivo
   THEN phones sao adicionados com dedup, sync e disparado para blacklist-sendspeed, e report mostra total adicionados/duplicados/invalidos

4. GIVEN admin ajustando creditos de cliente (bonus ou correcao)
   WHEN ClientAdminService.adjustCredits() e chamado
   THEN CreditTransaction e criada com tipo adequado (bonus/adjustment), balance e atualizado, e operacao e registrada no audit trail com admin_id

5. GIVEN health check cron rodando a cada 5 minutos
   WHEN SupplierManager.healthCheckAll() executa
   THEN cada supplier e testado, status atualizado (healthy/degraded/down), e suppliers down geram SystemAlert automaticamente

6. GIVEN callback Kafka de pagamento recebido
   WHEN KafkaCallbackProcessor.processPaymentCallback() processa
   THEN invoice e atualizada para 'paid', creditos sao adicionados ao cliente, e dedup via Redis previne processamento duplicado

## Required Skills

1. **AdminPanel** - existente
   - Spec: docs/specs/skills/admin_panel.md
   - Gestao de suppliers, clientes, billing e alertas via interface web

2. **SupplierMonitoring** - existente
   - Spec: docs/specs/skills/supplier_monitoring.md
   - Health checks, alertas, priority routing

## Required Agent Capabilities

- **Primary**: `sendspeed_admin_agent` - capabilities: [supplier_management, client_management, lost_list, alerting, admin_panel]
- **Secondary**: `sendspeed_pipeline_agent` - capabilities: [kafka_processing, redis_caching]

## RAG Chunk References

- `category: sendspeed_admin` + `source_file CONTAINS 'SupplierManager'`
- `category: sendspeed_admin` + `source_file CONTAINS 'LostListManager'`
- `category: sendspeed_admin` + `source_file CONTAINS 'ClientAdminService'`
- `category: sendspeed_admin` + `source_file CONTAINS 'AlertService'`

## Related Use Cases

- **Depends on**: nenhum (admin e independente)
- **Enables**: UC-SS-001 (Pipeline SMS - supplier config), UC-SS-004 (Billing - credit adjustments), UC-SS-006 (Blacklist - Lost List sync)
- **Conflicts with**: nenhum

## Implementation Notes

- Laravel 9 com Blade templates + jQuery — nao e SPA
- MySQL como banco principal, Redis para cache e session
- Kafka consumer para callbacks assincronos (pagamentos, status)
- Audit trail em tabela dedicada — todas operacoes admin sao logadas
- Health check usa HEAD request para API de cada supplier — timeout 5s
- Priority routing: supplier com priority 1 recebe 60% do trafego, priority 2 recebe 30%, etc.
- Lost List e historicamente separada do blacklist-sendspeed — sync bidirecional via cron
