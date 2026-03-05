# [UC-CON-003] Perfil de Contato com Historico de Interacoes

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CON-003 |
| **Domain** | contacts |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Exibe perfil completo de um contato incluindo dados basicos, tags, custom fields, listas, segmentos e historico cronologico de todas as interacoes (emails enviados, SMS, eventos trackados, journeys percorridas). Serve como hub central de informacoes do contato.

### Data Models

- **Model**: Contact (repo: platform-backend, path: `backend/src/domain/models/Contact.js`)
  - Fields: `email: string`, `phone: string`, `name: string`, `company_id: ObjectId`, `tags: string[]`, `custom_fields: object`
- **Model**: Interaction (repo: platform-backend, path: `backend/src/domain/models/Interaction.js`)
  - Fields: `contact_id: ObjectId`, `type: enum[email|sms|event|journey|tag]`, `action: string`, `metadata: object`, `created_at: Date`

### Services

- **Service**: contactService (repo: platform-backend, path: `backend/src/application/services/contactService.js`)
  - Methods: `findById()`, `getWithInteractions()`, `getTimeline()`, `updateTags()`, `updateCustomFields()`

### Routes/Endpoints

- `GET /api/contacts/:id` -> `contactService.findById()`
- `GET /api/contacts/:id/interactions` -> `contactService.getWithInteractions()`
- `GET /api/contacts/:id/timeline` -> `contactService.getTimeline()`

### Frontend Components

- **Page**: CRMContactDetailPage (repo: engage-ai-flow, path: `client/src/pages/CRMContactDetailPage.tsx`)
- **Page**: PersonDetailPage (repo: engage-ai-flow, path: `client/src/pages/PersonDetailPage.tsx`)

## Acceptance Criteria

1. GIVEN um contato existente com interacoes
   WHEN o usuario acessa CRMContactDetailPage
   THEN exibe dados basicos, tags, custom fields, segmentos atribuidos e listas associadas

2. GIVEN contato com historico de interacoes
   WHEN a timeline e carregada
   THEN exibe lista cronologica reversa de todas as interacoes (emails, SMS, eventos, journeys) com paginacao infinita

3. GIVEN contato com dados de segmentacao
   WHEN perfil e exibido
   THEN mostra engagement score, intention score e segmentos ativos do contato

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

## Required Agent Capabilities

- **Primary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, contact_profile]
- **Secondary**: `crm_backend_agent` - capabilities: [crm_backend, contacts]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/contactService'`
- `category: crm_frontend` + `source_file CONTAINS 'CRMContactDetailPage'`
- `category: crm_frontend` + `source_file CONTAINS 'PersonDetailPage'`
- `category: crm_model` + `domain: contacts`
- `category: usecase` + `domain: contacts`

## Related Use Cases

- **Depends on**: UC-CON-001 (Import de Contatos - contatos precisam existir), UC-SEG-001 (Segmentacao - scores e segmentos do contato)
- **Enables**: UC-CON-004 (Ontologia - perfil e base para atributos customizados)
- **Conflicts with**: nenhum

## Implementation Notes

- Timeline usa paginacao cursor-based para performance com milhares de interacoes
- Interacoes sao armazenadas em colecao separada com indice em (contact_id, created_at)
- PersonDetailPage e CRMContactDetailPage compartilham componentes mas diferem no layout
- Tags podem ser adicionadas/removidas inline no perfil
- Custom fields sao renderizados dinamicamente baseado no schema da empresa
- Segmentos e scores vem do segment-engine via API call separada
