# [UC-CON-004] Ontologia e Atributos de Contato

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CON-004 |
| **Domain** | contacts |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Sistema de ontologia flexivel que permite definir tipos de objetos customizados, relacoes, campos calculados (formulas), sinais e touchpoints. Funciona como um schema builder para o CRM, permitindo cada empresa modelar seus dados de contato de forma personalizada.

### Data Models

- **Model**: ObjectType (repo: platform-backend, path: `backend/src/domain/models/ObjectType.js`)
  - Fields: `name: string`, `company_id: ObjectId`, `fields: FieldDefinition[]`, `icon: string`
- **Model**: ObjectInstance (repo: platform-backend, path: `backend/src/domain/models/ObjectInstance.js`)
  - Fields: `type_id: ObjectId`, `data: object`, `contact_id: ObjectId`
- **Model**: ObjectRelationship (repo: platform-backend, path: `backend/src/domain/models/ObjectRelationship.js`)
  - Fields: `from_type: ObjectId`, `to_type: ObjectId`, `relationship_type: string`, `cardinality: enum[1:1|1:N|N:M]`
- **Model**: SignalDefinition (repo: platform-backend, path: `backend/src/domain/models/SignalDefinition.js`)
  - Fields: `name: string`, `source: string`, `computation: string`, `threshold: number`
- **Model**: SignalLatest (repo: platform-backend, path: `backend/src/domain/models/SignalLatest.js`)
  - Fields: `signal_id: ObjectId`, `contact_id: ObjectId`, `value: any`, `updated_at: Date`
- **Model**: Touchpoint (repo: platform-backend, path: `backend/src/domain/models/Touchpoint.js`)
  - Fields: `contact_id: ObjectId`, `channel: string`, `action: string`, `metadata: object`, `timestamp: Date`
- **Model**: FieldRegistry (repo: platform-backend, path: `backend/src/domain/models/FieldRegistry.js`)
  - Fields: `company_id: ObjectId`, `field_name: string`, `field_type: string`, `source: string`, `indexed: boolean`

### Services

- **Service**: ontologyService (repo: platform-backend, path: `backend/src/application/services/ontologyService.js`)
  - Methods: `createObjectType()`, `defineRelationship()`, `getSchema()`, `validateInstance()`
- **Service**: objectService (repo: platform-backend, path: `backend/src/application/services/objectService.js`)
  - Methods: `createInstance()`, `findInstances()`, `updateInstance()`, `linkObjects()`

### Routes/Endpoints

- `POST /api/ontology/types` -> `ontologyService.createObjectType()`
- `POST /api/ontology/relationships` -> `ontologyService.defineRelationship()`
- `GET /api/ontology/schema` -> `ontologyService.getSchema()`
- `POST /api/objects` -> `objectService.createInstance()`
- `GET /api/objects/:typeId` -> `objectService.findInstances()`

### Frontend Components

- **Component**: ObjectGraph (repo: engage-ai-flow, path: `client/src/components/segments/ontology/ObjectGraph.tsx`)
- **Component**: SchemaDetector (repo: engage-ai-flow, path: `client/src/components/segments/ontology/SchemaDetector.tsx`)
- **Component**: FormulaEditor (repo: engage-ai-flow, path: `client/src/components/segments/ontology/FormulaEditor.tsx`)
- **Component**: SignalBuilder (repo: engage-ai-flow, path: `client/src/components/segments/ontology/SignalBuilder.tsx`)
- **Component**: SimulationPanel (repo: engage-ai-flow, path: `client/src/components/segments/ontology/SimulationPanel.tsx`)
- **Component**: WebhookConfigManager (repo: engage-ai-flow, path: `client/src/components/segments/ontology/WebhookConfigManager.tsx`)
- **Component**: ApiKeysManager (repo: engage-ai-flow, path: `client/src/components/segments/ontology/ApiKeysManager.tsx`)
- **Component**: CsvCatalogImporter (repo: engage-ai-flow, path: `client/src/components/segments/ontology/CsvCatalogImporter.tsx`)

## Acceptance Criteria

1. GIVEN um usuario admin da empresa
   WHEN cria um novo ObjectType com campos customizados via ontologyService
   THEN o tipo e registrado no schema, FieldRegistry atualizado, e ObjectGraph reflete a nova entidade

2. GIVEN dois ObjectTypes existentes
   WHEN define relacao (ex: Contact -> Purchase, 1:N)
   THEN o ObjectGraph exibe a conexao e ObjectInstances podem ser linkados via objectService.linkObjects()

3. GIVEN um campo com formula definida no FormulaEditor (ex: "total_purchases / months_active")
   WHEN o SimulationPanel executa com dados de teste
   THEN calcula o valor correto e exibe preview antes de salvar a formula

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **OntologyModeling** - nova
   - Spec: docs/specs/skills/ontology_modeling.md
   - Modelagem de schemas customizados e relacoes entre entidades

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, contacts, ontology, schema]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, graph_visualization]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/ontologyService'`
- `category: crm_backend` + `source_file CONTAINS 'services/objectService'`
- `category: crm_model` + `source_file CONTAINS 'models/ObjectType'`
- `category: crm_model` + `source_file CONTAINS 'models/SignalDefinition'`
- `category: crm_frontend` + `source_file CONTAINS 'ontology/'`
- `category: usecase` + `domain: contacts`

## Related Use Cases

- **Depends on**: UC-CON-001 (Import de Contatos - contatos base), UC-CON-003 (Perfil de Contato - ontologia estende o perfil)
- **Enables**: UC-SEG-002 (Sinais Dinamicos - SignalDefinition alimenta sinais), UC-JRN-003 (Motor de Execucao - UserAttribute conditions usam ontologia)
- **Conflicts with**: nenhum

## Implementation Notes

- 18 componentes de ontologia no frontend (8 principais listados acima + 10 sub-componentes)
- ObjectGraph usa D3 force-directed graph para visualizacao de relacoes
- FormulaEditor suporta syntax highlighting e autocomplete de campos
- SignalBuilder permite definir sinais com threshold e acao automatica
- SchemaDetector infere schema a partir de dados existentes (auto-discovery)
- CsvCatalogImporter permite importar definicoes de tipo via CSV
- WebhookConfigManager configura webhooks para eventos de ontologia
- ApiKeysManager gerencia chaves de API para acesso externo ao schema
