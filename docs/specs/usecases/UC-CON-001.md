# [UC-CON-001] Import e Deduplicacao de Contatos

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CON-001 |
| **Domain** | contacts |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Permite importacao em massa de contatos via upload CSV com mapeamento de campos, preview de dados e deduplicacao automatica. O processamento e assincrono via Kafka para suportar arquivos grandes sem bloquear a UI.

### Data Models

- **Model**: Contact (repo: platform-backend, path: `backend/src/domain/models/Contact.js`)
  - Fields: `email: string`, `phone: string`, `name: string`, `company_id: ObjectId`, `tags: string[]`, `custom_fields: object`, `created_at: Date`
- **Model**: ImportJob (repo: platform-backend, path: `backend/src/domain/models/ImportJob.js`)
  - Fields: `company_id: ObjectId`, `status: enum[pending|processing|completed|failed]`, `total_rows: number`, `imported: number`, `duplicates: number`, `errors: number`

### Services

- **Service**: contactService (repo: platform-backend, path: `backend/src/application/services/contactService.js`)
  - Methods: `create()`, `findById()`, `findByEmail()`, `bulkCreate()`, `deduplicate()`, `importFromCsv()`

### Kafka Workers

- **Worker**: ImportWorker (repo: platform-backend, path: `backend/src/infrastructure/kafka/ImportWorker.js`)
  - Consumes: `contacts.import.batch`
- **Producer**: ImportProducer (repo: platform-backend, path: `backend/src/infrastructure/kafka/ImportProducer.js`)
  - Produces: `contacts.import.batch`, `contacts.import.complete`

### Routes/Endpoints

- `POST /api/contacts/import` -> `contactService.importFromCsv()`
- `GET /api/contacts/import/:jobId` -> status do ImportJob
- `POST /api/contacts` -> `contactService.create()`

### Frontend Components

- **Page**: CRMContactsImportPage (repo: engage-ai-flow, path: `client/src/pages/CRMContactsImportPage.tsx`)
- **Component**: CSVUploader (repo: engage-ai-flow, path: `client/src/components/contacts/CSVUploader.tsx`)
- **Component**: CSVFieldMapper (repo: engage-ai-flow, path: `client/src/components/contacts/CSVFieldMapper.tsx`)
- **Component**: CSVPreviewTable (repo: engage-ai-flow, path: `client/src/components/contacts/CSVPreviewTable.tsx`)

## Acceptance Criteria

1. GIVEN um arquivo CSV valido com headers
   WHEN o usuario faz upload e mapeia campos no CSVFieldMapper
   THEN o CSVPreviewTable exibe primeiras 10 linhas com mapeamento aplicado para validacao visual

2. GIVEN mapeamento confirmado e importacao iniciada
   WHEN o ImportProducer envia batches de 1000 registros para Kafka
   THEN o ImportWorker processa com deduplicacao por email/phone e retorna contagem de importados, duplicatas e erros

3. GIVEN importacao em andamento
   WHEN o usuario consulta GET /api/contacts/import/:jobId
   THEN retorna progresso em tempo real (imported/total_rows) com status atualizado

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **BulkImport** - nova
   - Spec: docs/specs/skills/bulk_import.md
   - Importacao em massa com deduplicacao via Kafka

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, contacts, kafka, import]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, file_upload]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/contactService'`
- `category: crm_backend` + `source_file CONTAINS 'kafka/ImportWorker'`
- `category: crm_frontend` + `source_file CONTAINS 'CRMContactsImportPage'`
- `category: crm_frontend` + `source_file CONTAINS 'CSVFieldMapper'`
- `category: usecase` + `domain: contacts`

## Related Use Cases

- **Depends on**: nenhum (ponto de entrada do modulo contacts)
- **Enables**: UC-CON-002 (Gestao de Listas - contatos importados podem ser adicionados a listas), UC-CON-003 (Perfil de Contato - contatos precisam existir), UC-SEG-001 (Segmentacao - contatos alimentam pipeline)
- **Conflicts with**: nenhum

## Implementation Notes

- Deduplicacao usa email como chave primaria, phone como secundaria
- Batches de 1000 registros para evitar memory overflow em arquivos grandes
- CSV parsing usa papaparse no frontend para preview local
- Backend usa csv-parser com stream para arquivos grandes (nao carrega tudo em memoria)
- ImportJob atualizado a cada batch processado para progress tracking
- Suporte a UTF-8 e Latin-1 encoding
