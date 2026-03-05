# [UC-XXX] Nome do Use Case

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-XXX |
| **Domain** | campaigns / journeys / segments / contacts / integrations / analytics / tracker |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P0-Critical / P1-High / P2-Medium / P3-Low |
| **Complexity** | S / M / L / XL |
| **Status** | Spec / Ready / InProgress / Done |

## Domain Context

Descricao concisa do que este use case faz no dominio CRM (2-3 frases).

### Data Models

- **Model**: NomeDoModel (repo: platform-backend, path: `backend/src/domain/models/NomeDoModel.js`)
  - Fields: `name: string`, `status: enum[draft|active|paused]`, `template_id: ObjectId`

### Services

- **Service**: nomeService (repo: platform-backend, path: `backend/src/application/services/nomeService.js`)
  - Methods: `create()`, `findById()`, `update()`, `delete()`, `listForCompany()`

### Routes/Endpoints

- `POST /api/v1/resource` -> `nomeService.create()`
- `GET /api/v1/resource/:id` -> `nomeService.findById()`

### Frontend Components

- **Page**: NomePage (repo: engage-ai-flow, path: `client/src/pages/NomePage.tsx`)
- **Component**: NomeComponent (repo: engage-ai-flow, path: `client/src/components/nome/NomeComponent.tsx`)

## Acceptance Criteria

1. GIVEN um usuario autenticado com companyId
   WHEN cria um novo recurso via POST /api/v1/resource
   THEN o recurso e salvo com status 'draft' e retorna 201

2. GIVEN um recurso existente
   WHEN o usuario acessa GET /api/v1/resource/:id
   THEN retorna o recurso com todos os campos populados

3. GIVEN dados invalidos
   WHEN tenta criar via POST
   THEN retorna 400 com mensagem de validacao

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **JourneyOrchestration** - nova
   - Spec: docs/specs/skills/journey_orchestration.md
   - Execucao de nodes no Journey Builder engine

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, campaigns, mongodb]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'platform-backend/services/nomeService'`
- `category: crm_model` + `domain: campaigns`
- `category: crm_frontend` + `source_file CONTAINS 'pages/NomePage'`
- `category: usecase` + `domain: campaigns`

## Related Use Cases

- **Depends on**: UC-CON-001 (Import de Contatos - necessario ter contatos para alvo)
- **Enables**: UC-ANA-001 (Analytics - gera dados para pipeline de analytics)
- **Conflicts with**: nenhum

## Implementation Notes

- O backend usa MongoDB com Mongoose, nao SQL
- Kafka topic `campaigns.created` e emitido apos criacao
- Frontend usa React Router v6, nao Next.js
- Autenticacao via JWT com `x-company-id` header
- ClickHouse usado para analytics (nao para CRUD)
