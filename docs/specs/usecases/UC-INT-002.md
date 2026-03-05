# [UC-INT-002] Entrega Email via Resend

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-INT-002 |
| **Domain** | integrations |
| **Repos** | userin-integrations |
| **Priority** | P0-Critical |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Entrega de emails transacionais e marketing via Resend API. Suporta templates HTML com personalizacao (merge tags), tracking de open/click, bounce handling, e compliance com CAN-SPAM/GDPR. Integrado ao Journey Builder e Campaign Manager como canal de entrega principal.

### Data Models

- **Model**: EmailMessage (repo: userin-integrations, path: `src/domain/models/EmailMessage.ts`)
  - Fields: `id: string`, `to: string`, `from: string`, `subject: string`, `html: string`, `text?: string`, `templateId?: string`, `mergeVars: object`, `status: enum[queued|sent|delivered|opened|clicked|bounced|complained]`, `campaignId?: string`
- **Model**: EmailTemplate (repo: userin-integrations, path: `src/domain/models/EmailTemplate.ts`)
  - Fields: `id: string`, `name: string`, `subject: string`, `html: string`, `mergeFields: string[]`, `companyId: string`
- **Model**: EmailEvent (repo: userin-integrations, path: `src/domain/models/EmailEvent.ts`)
  - Fields: `messageId: string`, `type: enum[delivered|opened|clicked|bounced|complained|unsubscribed]`, `timestamp: Date`, `metadata: object`

### Services

- **Service**: EmailService (repo: userin-integrations, path: `src/application/services/EmailService.ts`)
  - Methods: `send()`, `sendBulk()`, `renderTemplate()`, `getStatus()`, `getEvents()`
- **Service**: ResendAdapter (repo: userin-integrations, path: `src/application/services/ResendAdapter.ts`)
  - Methods: `sendEmail()`, `createBatch()`, `getDomainStatus()`, `getApiUsage()`
- **Service**: EmailQueueWorker (repo: userin-integrations, path: `src/workers/EmailQueueWorker.ts`)
  - Methods: `processQueue()`, `handleBounce()`, `handleComplaint()`, `updateSuppressionList()`

### Routes/Endpoints

- `POST /api/email/send` -> `EmailService.send()`
- `POST /api/email/bulk` -> `EmailService.sendBulk()`
- `GET /api/email/:id/status` -> `EmailService.getStatus()`
- `POST /api/email/webhook/events` -> callback de eventos do Resend
- `GET /api/email/templates` -> `EmailService.getTemplates()`

### Frontend Components

- Template editor integrado no Campaign Manager (engage-ai-flow)

## Acceptance Criteria

1. GIVEN um contato com email valido e opt-in ativo
   WHEN uma campanha ou journey dispara envio de email
   THEN o email e renderizado com merge tags resolvidos e enviado via Resend API

2. GIVEN um email enviado com sucesso
   WHEN o destinatario abre o email
   THEN evento "opened" e registrado via webhook e status atualizado

3. GIVEN um email que resulta em hard bounce
   WHEN o webhook de bounce e recebido
   THEN o email do contato e adicionado a suppression list e futuros envios sao bloqueados

4. GIVEN um template com merge fields (ex: {{first_name}}, {{company}})
   WHEN renderizado para envio
   THEN todos os merge fields sao substituidos pelos dados do contato

## Required Skills

1. **EmailDelivery** - nova
   - Spec: docs/specs/skills/email_delivery.md
   - Envio e tracking de email via Resend

2. **TemplateRendering** - nova
   - Spec: docs/specs/skills/template_rendering.md
   - Renderizacao de templates com merge tags

## Required Agent Capabilities

- **Primary**: `crm_integration_agent` - capabilities: [email, crm_integration]
- **Secondary**: `crm_backend_agent` - capabilities: [campaigns, journeys]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'userin-integrations/services/EmailService'`
- `category: crm_backend` + `source_file CONTAINS 'userin-integrations/services/ResendAdapter'`
- `category: crm_data_pipeline` + `source_file CONTAINS 'userin-integrations/workers/EmailQueueWorker'`
- `category: usecase` + `domain: integrations`

## Related Use Cases

- **Depends on**: UC-CON-001 (Contatos - precisa de email valido)
- **Enables**: UC-CAM-004 (Triggers de Campanha - email como canal), UC-JRN-003 (Motor de Journey - SendEmail e node de acao), UC-ANA-001 (Analytics - open/click rates)
- **Conflicts with**: nenhum

## Implementation Notes

- Resend API key por company (multi-tenant)
- Queue usa Kafka topic `email.outbound` com particao por domain
- Bounce handling: soft bounce -> retry 3x, hard bounce -> suppress permanently
- Complaint (spam report) -> auto-unsubscribe + flag no contato
- Templates renderizados server-side com Handlebars (nao client-side)
- Rate limit Resend: respect 429 com exponential backoff
- Unsubscribe link obrigatorio no footer (CAN-SPAM compliance)
- Tracking pixel injetado automaticamente para open tracking
