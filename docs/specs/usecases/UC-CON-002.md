# [UC-CON-002] Gestao de Listas

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CON-002 |
| **Domain** | contacts |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Gerenciamento de listas de contatos para segmentacao manual e targeting de campanhas. Listas podem ser estaticas (membros adicionados manualmente) ou dinamicas (baseadas em filtros que atualizam automaticamente). Cada lista pertence a uma empresa e pode ser usada como audiencia em campanhas e journeys.

### Data Models

- **Model**: List (repo: platform-backend, path: `backend/src/domain/models/List.js`)
  - Fields: `name: string`, `description: string`, `company_id: ObjectId`, `type: enum[static|dynamic]`, `filter: object`, `member_count: number`, `created_at: Date`
- **Model**: ListMember (repo: platform-backend, path: `backend/src/domain/models/ListMember.js`)
  - Fields: `list_id: ObjectId`, `contact_id: ObjectId`, `added_at: Date`, `source: enum[manual|import|dynamic]`

### Services

- **Service**: listService (repo: platform-backend, path: `backend/src/application/services/listService.js`)
  - Methods: `create()`, `findById()`, `listForCompany()`, `addMembers()`, `removeMembers()`, `refreshDynamic()`, `getMemberCount()`

### Routes/Endpoints

- `POST /api/lists` -> `listService.create()`
- `GET /api/lists` -> `listService.listForCompany()`
- `GET /api/lists/:id` -> `listService.findById()`
- `POST /api/lists/:id/members` -> `listService.addMembers()`
- `DELETE /api/lists/:id/members` -> `listService.removeMembers()`

### Frontend Components

- **Page**: ListsPage (repo: engage-ai-flow, path: `client/src/pages/ListsPage.tsx`)
- **Page**: ListDetailPage (repo: engage-ai-flow, path: `client/src/pages/ListDetailPage.tsx`)

## Acceptance Criteria

1. GIVEN usuario autenticado com companyId
   WHEN cria uma lista estatica via POST /api/lists com type 'static'
   THEN a lista e criada vazia e pronta para adicao manual de membros

2. GIVEN uma lista dinamica com filtro definido (ex: tag = "vip" AND engagement > 80)
   WHEN refreshDynamic() executa
   THEN a lista atualiza automaticamente seus membros baseado nos filtros sem duplicatas

3. GIVEN uma lista com membros
   WHEN o usuario acessa ListDetailPage
   THEN exibe membros paginados com opcoes de adicionar, remover e exportar

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, contacts, lists]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/listService'`
- `category: crm_model` + `source_file CONTAINS 'models/List'`
- `category: crm_model` + `source_file CONTAINS 'models/ListMember'`
- `category: crm_frontend` + `source_file CONTAINS 'pages/ListsPage'`
- `category: usecase` + `domain: contacts`

## Related Use Cases

- **Depends on**: UC-CON-001 (Import de Contatos - contatos precisam existir para serem adicionados a listas)
- **Enables**: UC-CAM-001 (Criar Campanha - listas como audiencia), UC-JRN-001 (Journey Builder - listas como trigger de segmento)
- **Conflicts with**: nenhum

## Implementation Notes

- Listas dinamicas usam MongoDB aggregation pipeline para filtros complexos
- RefreshDynamic roda em background via Bull queue (nao bloqueia request)
- Member count e cacheado e atualizado a cada adicao/remocao
- Paginacao de membros usa cursor-based pagination para performance
- Listas dinamicas sao refreshed a cada 1 hora ou on-demand
- Limite de 100k membros por lista por questoes de performance
