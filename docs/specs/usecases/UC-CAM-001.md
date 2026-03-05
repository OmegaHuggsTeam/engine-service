# [UC-CAM-001] Criar Campanha com Selecao de Template

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CAM-001 |
| **Domain** | campaigns |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Permite ao usuario criar uma nova campanha selecionando um template pre-definido, configurando audiencia e parametros de envio. A campanha e criada em status 'draft' e pode ser editada antes de ativacao. Este e o ponto de entrada principal do modulo de campanhas.

### Data Models

- **Model**: Campaign (repo: platform-backend, path: `backend/src/domain/models/Campaign.js`)
  - Fields: `name: string`, `status: enum[draft|active|paused|completed]`, `template_id: ObjectId`, `company_id: ObjectId`, `audience: object`, `schedule: object`
- **Model**: Template (repo: platform-backend, path: `backend/src/domain/models/Template.js`)
  - Fields: `name: string`, `type: enum[email|sms|push]`, `content: object`, `company_id: ObjectId`

### Services

- **Service**: campaignService (repo: platform-backend, path: `backend/src/application/services/campaignService.js`)
  - Methods: `create()`, `findById()`, `update()`, `delete()`, `listForCompany()`, `activate()`, `pause()`

### Routes/Endpoints

- `POST /api/campaigns` -> `campaignService.create()`
- `GET /api/campaigns` -> `campaignService.listForCompany()`
- `GET /api/campaigns/:id` -> `campaignService.findById()`
- `PUT /api/campaigns/:id` -> `campaignService.update()`
- `DELETE /api/campaigns/:id` -> `campaignService.delete()`

### Frontend Components

- **Page**: CampaignsPage (repo: engage-ai-flow, path: `client/src/pages/CampaignsPage.tsx`)
- **Page**: CreateCampaignPage (repo: engage-ai-flow, path: `client/src/pages/CreateCampaignPage.tsx`)
- **Page**: CampaignDetailPage (repo: engage-ai-flow, path: `client/src/pages/CampaignDetailPage.tsx`)

## Acceptance Criteria

1. GIVEN um usuario autenticado com companyId
   WHEN cria uma campanha via POST /api/campaigns com template_id valido
   THEN a campanha e salva com status 'draft', template vinculado, e retorna 201

2. GIVEN uma campanha existente em status 'draft'
   WHEN o usuario acessa GET /api/campaigns/:id
   THEN retorna a campanha com template populado e configuracoes de audiencia

3. GIVEN template_id invalido ou ausente
   WHEN tenta criar campanha via POST /api/campaigns
   THEN retorna 400 com mensagem de validacao indicando template obrigatorio

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **TemplateSelection** - nova
   - Spec: docs/specs/skills/template_selection.md
   - Selecao e vinculacao de templates a campanhas

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, campaigns, mongodb]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, campaign_ui]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'platform-backend/services/campaignService'`
- `category: crm_model` + `domain: campaigns`
- `category: crm_frontend` + `source_file CONTAINS 'pages/CampaignsPage'`
- `category: crm_frontend` + `source_file CONTAINS 'pages/CreateCampaignPage'`
- `category: usecase` + `domain: campaigns`

## Related Use Cases

- **Depends on**: nenhum (ponto de entrada)
- **Enables**: UC-CAM-002 (A/B Testing - requer campanha criada), UC-CAM-003 (Analytics - gera dados), UC-CAM-004 (Agendamento - campanha precisa existir)
- **Conflicts with**: nenhum

## Implementation Notes

- O backend usa MongoDB com Mongoose, nao SQL
- Kafka topic `campaigns.created` e emitido apos criacao
- Frontend usa React Router v6, nao Next.js
- Autenticacao via JWT com `x-company-id` header
- Templates sao listados via endpoint separado GET /api/templates
