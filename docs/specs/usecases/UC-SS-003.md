# [UC-SS-003] Campaign Management e Scheduling

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-003 |
| **Domain** | campaign_management |
| **Repos** | sendspeed0/app-send-speed (branch: main), sendspeed0/backoffice (branch: main) |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Production |

## Domain Context

Sistema de gestao de campanhas SMS da plataforma SendSpeed. O app-send-speed (PHP 7.4 + Vue.js 2) oferece wizard multi-step para criacao de campanhas com selecao de lista de telefones, mensagem, supplier, agendamento e execucao. O backoffice (Laravel 9) gerencia campanhas do lado admin com aprovacao, limites e monitoramento. Suporta 5 canais: SMS, VoIP, WhatsApp, RCS, Email.

### Data Models

- **Model**: Campaign (app-send-speed: `app/Models/Campaign.php`)
  - Fields: `id`, `client_id`, `name`, `message`, `channel: enum(sms|voip|whatsapp|rcs|email)`, `supplier_id`, `phone_list_id`, `status: enum(draft|scheduled|running|paused|completed|failed)`, `scheduled_at`, `total_numbers`, `total_sent`, `total_delivered`, `total_failed`, `cost_per_unit`, `total_cost`
- **Model**: PhoneList (app-send-speed: `app/Models/PhoneList.php`)
  - Fields: `id`, `client_id`, `name`, `total_numbers`, `file_path`, `status`, `deduplicated_count`
- **Model**: CampaignTemplate (app-send-speed: `app/Models/`)
  - Fields: `id`, `name`, `message_template`, `variables: json`, `channel`, `max_chars`
- **Model**: CampaignSchedule (backoffice: `app/Models/`)
  - Fields: `campaign_id`, `send_at`, `timezone`, `repeat: enum(once|daily|weekly)`, `active_hours_start`, `active_hours_end`

### Services

- **Service**: CampaignWizard (app-send-speed: `resources/js/components/`)
  - Vue.js 2 multi-step wizard: Step1(Nome+Canal) → Step2(Lista) → Step3(Mensagem) → Step4(Supplier) → Step5(Agendamento) → Step6(Confirmacao)
  - Validacao client-side + server-side em cada step
- **Service**: CampaignExecutor (app-send-speed: `app/Jobs/`)
  - Laravel Queue Job para execucao assincrona
  - Chunking: divide phone_list em batches de 1000
  - Rate limiting per supplier
  - Progress tracking via Redis pub/sub
- **Service**: CampaignApproval (backoffice: `app/Services/`)
  - Admin review e aprovacao de campanhas acima de threshold
  - Auto-approve para campanhas < 1000 numeros
  - Block list check antes de aprovacao
- **Service**: CampaignAnalytics (backoffice: `app/Services/`)
  - Dashboard com metricas: delivery rate, cost analysis, supplier performance
  - Export CSV/PDF de resultados

### Routes/Endpoints

- `POST /api/campaigns` → CampaignWizard.create (app-send-speed)
- `PUT /api/campaigns/{id}` → update campaign
- `POST /api/campaigns/{id}/schedule` → CampaignSchedule
- `POST /api/campaigns/{id}/execute` → CampaignExecutor dispatch
- `POST /api/campaigns/{id}/pause` → pause running campaign
- `GET /api/campaigns/{id}/progress` → real-time progress via Redis
- `POST /admin/campaigns/{id}/approve` → CampaignApproval (backoffice)
- `GET /admin/campaigns/analytics` → CampaignAnalytics dashboard

## Acceptance Criteria

1. GIVEN usuario no wizard de campanha com canal SMS selecionado
   WHEN completa todos os 6 steps e confirma
   THEN campanha e criada com status 'draft', creditos sao reservados, e phone_list e validada e deduplicada

2. GIVEN campanha agendada para datetime futuro
   WHEN CampaignSchedule.send_at e atingido
   THEN CampaignExecutor e disparado automaticamente, phone_list e dividida em batches de 1000, e envio comeca com rate limiting por supplier

3. GIVEN campanha com 50K numeros em execucao
   WHEN progresso e consultado via GET /api/campaigns/{id}/progress
   THEN resposta inclui total_sent, total_delivered, total_failed, percentage_complete em real-time via Redis pub/sub

4. GIVEN campanha com mais de 1000 numeros submetida
   WHEN CampaignApproval verifica
   THEN campanha fica com status 'pending_approval' ate admin aprovar no backoffice

5. GIVEN campanha em execucao
   WHEN admin clica pause
   THEN envio e interrompido gracefully (batch atual completa), status muda para 'paused', creditos nao utilizados sao mantidos reservados

6. GIVEN campanha completada
   WHEN CampaignAnalytics processa resultados
   THEN dashboard mostra delivery_rate, cost_per_delivered, supplier_performance_breakdown com opcao de export CSV/PDF

## Required Skills

1. **CampaignOrchestration** - existente
   - Spec: docs/specs/skills/campaign_orchestration.md
   - Wizard multi-step, scheduling, execucao assincrona com progress tracking

2. **SupplierManagement** - existente
   - Spec: docs/specs/skills/supplier_management.md
   - Selecao, rate limiting e monitoring de 15+ suppliers

## Required Agent Capabilities

- **Primary**: `sendspeed_admin_agent` - capabilities: [campaign_management, scheduling, approval_workflow]
- **Secondary**: `sendspeed_sms_agent` - capabilities: [campaign_execution, supplier_routing]

## RAG Chunk References

- `category: sendspeed_app` + `source_file CONTAINS 'Campaign'`
- `category: sendspeed_app` + `source_file CONTAINS 'CampaignWizard'`
- `category: sendspeed_admin` + `source_file CONTAINS 'CampaignApproval'`
- `category: sendspeed_admin` + `source_file CONTAINS 'CampaignAnalytics'`

## Related Use Cases

- **Depends on**: UC-SS-001 (Pipeline SMS - executa os envios)
- **Enables**: UC-SS-004 (Billing - calculo de custos por campanha)
- **Conflicts with**: nenhum

## Implementation Notes

- Vue.js 2 wizard com 6 steps - state gerenciado via Vuex store
- Phone list upload suporta CSV e TXT com deduplicacao automatica
- CampaignExecutor usa Laravel Queue (Redis driver) para procesamento assincrono
- Batching de 1000 numeros por job para evitar memory overflow
- Rate limiting configuravel por supplier (ex: Pushfy max 100 req/s, Sona max 50 req/s)
- Progress tracking via Redis PUBLISH/SUBSCRIBE para real-time updates
- Campanhas multi-canal: mesmo wizard, suppliers diferentes por canal
- Backoffice auto-approve threshold configuravel por cliente (default 1000)
