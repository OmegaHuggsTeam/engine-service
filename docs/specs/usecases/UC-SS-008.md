# [UC-SS-008] Portal Cliente API (Multi-Tenant REST)

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-008 |
| **Domain** | api_platform |
| **Repos** | sendspeed0/portal-cliente-api (branch: main) |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Production |

## Domain Context

API REST multi-tenant da SendSpeed construida com Laravel 11 seguindo Clean Architecture/DDD. Fornece 32 endpoints CRUD para clientes consumirem programaticamente: envio de SMS, gestao de contatos, listas, templates e consulta de creditos/extratos. Isolamento multi-tenant via UUID api_keys no header. PostgreSQL para dados transacionais, MongoDB para logs.

### Data Models

- **Model**: ApiClient (portal-cliente-api: `app/Domain/Models/`)
  - Fields: `id: uuid`, `company_name`, `api_key: uuid`, `secret_key: uuid`, `plan`, `rate_limit: integer`, `daily_limit: integer`, `status: enum(active|suspended|revoked)`, `webhook_url: string`, `ip_whitelist: json`
- **Model**: Contact (portal-cliente-api: `app/Domain/Models/`)
  - Fields: `id`, `client_id`, `phone`, `name`, `email`, `tags: json`, `custom_fields: json`, `opt_in: boolean`, `created_at`
- **Model**: ContactList (portal-cliente-api: `app/Domain/Models/`)
  - Fields: `id`, `client_id`, `name`, `description`, `contact_count`, `status`, `last_synced_at`
- **Model**: MessageTemplate (portal-cliente-api: `app/Domain/Models/`)
  - Fields: `id`, `client_id`, `name`, `content`, `variables: json`, `channel`, `max_length`, `status`
- **Model**: ApiLog (portal-cliente-api: `app/Infrastructure/Models/`)
  - Fields: `id`, `client_id`, `endpoint`, `method`, `status_code`, `request_body: json`, `response_body: json`, `ip`, `latency_ms`, `created_at`
  - Stored in MongoDB for high-volume logging

### Services

- **Service**: AuthMiddleware (portal-cliente-api: `app/Infrastructure/Middleware/`)
  - Validates x-api-key + x-secret-key headers
  - IP whitelist check if configured
  - Rate limiting per api_key (token bucket algorithm)
  - Sets tenant context for all downstream queries
- **Service**: MessageService (portal-cliente-api: `app/Domain/Services/`)
  - Methods: `sendSingle(phone, message, options)`, `sendBulk(phones[], message)`, `sendToList(list_id, message)`, `getStatus(message_id)`
  - Validates credits before send, delegates to nodejs-api-v02
- **Service**: ContactService (portal-cliente-api: `app/Domain/Services/`)
  - Full CRUD: `create`, `update`, `delete`, `getById`, `search`, `importCsv`, `exportCsv`
  - Tag management: `addTags`, `removeTags`, `filterByTags`
  - Dedup: phone-based deduplication within client scope
- **Service**: ListService (portal-cliente-api: `app/Domain/Services/`)
  - Methods: `create`, `addContacts`, `removeContacts`, `sync`, `getContactCount`
  - Lazy contact count: updated via background job
- **Service**: TemplateService (portal-cliente-api: `app/Domain/Services/`)
  - Methods: `create`, `update`, `preview(template_id, variables)`, `validate`
  - Variable interpolation: `{{name}}`, `{{phone}}`, `{{custom.field}}`
  - Max length validation per channel (SMS: 160 chars, WhatsApp: 4096, etc.)
- **Service**: ApiLogger (portal-cliente-api: `app/Infrastructure/Services/`)
  - Logs every API request to MongoDB
  - Methods: `log(request, response, latency)`, `getClientLogs(client_id, period)`, `getMetrics(client_id)`
  - Retention: 90 days, auto-purge via TTL index

### Routes/Endpoints (32 total)

- **Messages**: `POST /api/v1/messages/send`, `POST /api/v1/messages/bulk`, `POST /api/v1/messages/list/{id}`, `GET /api/v1/messages/{id}/status`
- **Contacts**: `GET /api/v1/contacts`, `POST /api/v1/contacts`, `PUT /api/v1/contacts/{id}`, `DELETE /api/v1/contacts/{id}`, `POST /api/v1/contacts/import`, `GET /api/v1/contacts/export`
- **Lists**: `GET /api/v1/lists`, `POST /api/v1/lists`, `PUT /api/v1/lists/{id}`, `DELETE /api/v1/lists/{id}`, `POST /api/v1/lists/{id}/contacts`, `DELETE /api/v1/lists/{id}/contacts`
- **Templates**: `GET /api/v1/templates`, `POST /api/v1/templates`, `PUT /api/v1/templates/{id}`, `DELETE /api/v1/templates/{id}`, `POST /api/v1/templates/{id}/preview`
- **Credits**: `GET /api/v1/credits/balance`, `GET /api/v1/credits/statement`, `GET /api/v1/credits/usage`
- **Account**: `GET /api/v1/account`, `PUT /api/v1/account`, `POST /api/v1/account/webhook`, `GET /api/v1/account/logs`, `GET /api/v1/account/metrics`

## Acceptance Criteria

1. GIVEN request com x-api-key e x-secret-key validos no header
   WHEN AuthMiddleware processa
   THEN tenant context e setado, rate limit e verificado, e request prossegue para controller

2. GIVEN request sem api_key ou com api_key invalida
   WHEN AuthMiddleware processa
   THEN resposta 401 retornada, ApiLog registrado em MongoDB com tentativa falhada

3. GIVEN POST /api/v1/messages/send com phone e message validos
   WHEN MessageService.sendSingle() e chamado
   THEN creditos sao verificados, mensagem e delegada para nodejs-api-v02, message_id e retornado, e credito e debitado

4. GIVEN POST /api/v1/contacts/import com CSV de 10K contatos
   WHEN ContactService.importCsv() processa
   THEN contatos sao importados com dedup por phone dentro do client scope, tags sao aplicadas, e response inclui total_imported/duplicated/errors

5. GIVEN template com variaveis {{name}} e {{custom.loyalty_level}}
   WHEN TemplateService.preview(template_id, {name: "João", custom: {loyalty_level: "gold"}}) e chamado
   THEN mensagem renderizada e retornada com variaveis interpoladas e validacao de max_length

6. GIVEN cliente com rate_limit de 100 req/min
   WHEN 101o request chega no mesmo minuto
   THEN resposta 429 Too Many Requests com header Retry-After e retornada

7. GIVEN GET /api/v1/account/metrics para periodo de 30 dias
   WHEN ApiLogger.getMetrics() e consultado
   THEN metricas retornam: total_requests, success_rate, avg_latency_ms, messages_sent, credits_used

## Required Skills

1. **RestApiDesign** - existente
   - Spec: docs/specs/skills/rest_api_design.md
   - Clean Architecture/DDD, multi-tenant, rate limiting, API logging

2. **ContactManagement** - existente
   - Spec: docs/specs/skills/contact_management.md
   - CRUD, import/export, tagging, deduplication

## Required Agent Capabilities

- **Primary**: `sendspeed_api_agent` - capabilities: [rest_api, multi_tenant, authentication, rate_limiting, contact_management, template_engine]
- **Secondary**: `sendspeed_sms_agent` - capabilities: [sms_delivery, credit_management]

## RAG Chunk References

- `category: sendspeed_api` + `source_file CONTAINS 'AuthMiddleware'`
- `category: sendspeed_api` + `source_file CONTAINS 'MessageService'`
- `category: sendspeed_api` + `source_file CONTAINS 'ContactService'`
- `category: sendspeed_api` + `source_file CONTAINS 'TemplateService'`

## Related Use Cases

- **Depends on**: UC-SS-001 (Pipeline SMS - delegate de envio), UC-SS-004 (Billing - creditos)
- **Enables**: UC-SS-003 (Campaign Management - clientes criam campanhas via API)
- **Conflicts with**: nenhum

## Implementation Notes

- Laravel 11 com Clean Architecture: Domain → Application → Infrastructure layers
- PostgreSQL para dados transacionais (contatos, templates, creditos)
- MongoDB para logs de API (alto volume, TTL 90 dias)
- Multi-tenant strict: middleware injeta client_id em todo request, queries sempre filtram
- Rate limiting via token bucket no Redis — configuravel por cliente e por endpoint
- IP whitelist opcional — se configurado, rejeita requests de IPs nao listados
- Variable interpolation suporta nested objects: {{custom.field.subfield}}
- API versioning via URL prefix (/api/v1/) — preparado para v2
