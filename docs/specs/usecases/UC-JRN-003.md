# [UC-JRN-003] Motor de Execucao de Journey

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-JRN-003 |
| **Domain** | journeys |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P0-Critical |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Engine que executa journeys em runtime, processando contatos atraves dos nodes do grafo. Cada tipo de node tem um executor especializado. O FlowTracker mantem o estado de cada contato na journey. Suporta execucao offsite (server-side) e avaliacao de condicoes baseada em eventos.

### Data Models

- **Model**: JourneyExecution (repo: platform-backend, path: `backend/src/domain/models/JourneyExecution.js`)
  - Fields: `journey_id: ObjectId`, `contact_id: ObjectId`, `current_node: string`, `status: enum[active|completed|exited|error]`, `history: array`
- **Model**: FlowTracker (repo: platform-backend, path: `backend/src/domain/models/FlowTracker.js`)
  - Fields: `journey_id: ObjectId`, `contact_id: ObjectId`, `node_id: string`, `entered_at: Date`, `exited_at: Date`
- **Model**: ABTestResult (repo: platform-backend, path: `backend/src/domain/models/ABTestResult.js`)
  - Fields: `journey_id: ObjectId`, `variant_id: string`, `contact_id: ObjectId`, `assigned_at: Date`

### Services

- **Engine**: BaseNodeExecutor (repo: platform-backend, path: `backend/src/domain/journey-builder/engine/BaseNodeExecutor.js`)
  - Methods: `execute()`, `validate()`, `canExecute()`
- **Engine**: NodeEngine (repo: platform-backend, path: `backend/src/domain/journey-builder/engine/NodeEngine.js`)
  - Methods: `processNode()`, `getNextNodes()`, `handleError()`
- **Service**: journeyOffsiteProcessor (repo: platform-backend, path: `backend/src/application/services/journeyOffsiteProcessor.js`)
  - Methods: `processContact()`, `evaluateConditions()`, `advanceFlow()`
- **Service**: EventConditionEvaluator (repo: platform-backend, path: `backend/src/application/services/EventConditionEvaluator.js`)
  - Methods: `evaluate()`, `matchEvent()`, `checkCondition()`

### Routes/Endpoints

- `POST /api/journeys/:id/execute` -> `NodeEngine.processNode()`
- `GET /api/journeys/:id/executions` -> lista de JourneyExecution
- `GET /api/journeys/:id/executions/:contactId` -> status do contato na journey

### Frontend Components

- **Component**: JourneySimulator (repo: engage-ai-flow, path: `client/src/components/journey-builder/JourneySimulator.tsx`)
- **Component**: ExecutionTimeline (repo: engage-ai-flow, path: `client/src/components/journey-builder/ExecutionTimeline.tsx`)

## Acceptance Criteria

1. GIVEN uma journey ativa com trigger configurado
   WHEN um contato dispara o evento do trigger
   THEN o NodeEngine inicia execucao, FlowTracker registra entrada, e o contato avanca pelo grafo ate encontrar Delay, Exit ou JourneyEnd

2. GIVEN um contato em node de Delay (ex: "esperar 24h")
   WHEN o tempo de delay expira
   THEN o journeyOffsiteProcessor retoma execucao e avanca para o proximo node

3. GIVEN um node de condicao (HasTag, UserAttribute, RuleMatch)
   WHEN o EventConditionEvaluator avalia
   THEN o contato segue pelo branch correto (true/false) baseado nos dados atuais do contato

## Required Skills

1. **JourneyOrchestration** - existente
   - Spec: docs/specs/skills/journey_orchestration.md
   - Execucao de nodes no Journey Builder engine

2. **NodeExecution** - nova
   - Spec: docs/specs/skills/node_execution.md
   - Implementacao de executors para cada tipo de node

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, journeys, execution_engine]
- **Secondary**: `crm_data_agent` - capabilities: [kafka, event_processing]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'journey-builder/engine'`
- `category: crm_backend` + `source_file CONTAINS 'services/journeyOffsiteProcessor'`
- `category: crm_backend` + `source_file CONTAINS 'services/EventConditionEvaluator'`
- `category: crm_model` + `domain: journeys`
- `category: usecase` + `domain: journeys`

## Related Use Cases

- **Depends on**: UC-JRN-001 (Journey Builder - journey precisa estar construida e validada)
- **Enables**: UC-JRN-004 (Analytics - execucao gera dados de KPI), UC-CAM-002 (A/B Testing - engine executa variantes)
- **Conflicts with**: nenhum

## Implementation Notes

- BaseNodeExecutor e classe abstrata; cada tipo de node implementa seu proprio executor
- NodeEngine usa pattern Strategy para selecionar executor correto
- FlowTracker persiste em MongoDB com TTL de 90 dias para execucoes finalizadas
- Delay nodes usam scheduled jobs via Bull queue (nao setTimeout)
- Execucao offsite (server-side) para nodes que nao dependem do browser
- EventConditionEvaluator suporta operadores: equals, contains, gt, lt, regex, exists
- Error handling: node com erro e marcado, contato pode ser re-processado manualmente
