# [UC-JRN-001] Journey Builder Canvas

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-JRN-001 |
| **Domain** | journeys |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P0-Critical |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Editor visual de journeys baseado em canvas com 20+ tipos de nodes. O usuario arrasta nodes para construir fluxos de automacao que combinam triggers, acoes, condicoes e controle de fluxo. Suporta undo/redo, multi-select, reconexao de edges e simulacao de execucao.

### Data Models

- **Model**: Journey (repo: platform-backend, path: `backend/src/domain/models/Journey.js`)
  - Fields: `name: string`, `status: enum[draft|active|paused]`, `nodes: array`, `edges: array`, `company_id: ObjectId`

### Services

- **Service**: journeyService (repo: platform-backend, path: `backend/src/application/services/journeyService.js`)
  - Methods: `create()`, `findById()`, `update()`, `activate()`, `pause()`, `duplicate()`, `validateGraph()`

### Routes/Endpoints

- `POST /api/journeys` -> `journeyService.create()`
- `GET /api/journeys/:id` -> `journeyService.findById()`
- `PUT /api/journeys/:id` -> `journeyService.update()`
- `POST /api/journeys/:id/activate` -> `journeyService.activate()`
- `POST /api/journeys/:id/validate` -> `journeyService.validateGraph()`

### Frontend Components

- **Triggers**: EventTrigger, RuleMatchTrigger, SegmentTrigger (path: `client/src/components/journey-builder/nodes/triggers/`)
- **Actions**: AddTag, RemoveTag, SendEmail, SendSms, ShowBlock, ShowMinigame, ShowModal, ExecuteJs, InjectHtml (path: `client/src/components/journey-builder/nodes/actions/`)
- **Conditions**: ABTest, HasTag, RuleMatch, UserAttribute (path: `client/src/components/journey-builder/nodes/conditions/`)
- **Flow Control**: Delay, Exit, Split, WaitForEvent (path: `client/src/components/journey-builder/nodes/flow/`)
- **Tracking**: JourneyInit, JourneyEnd, TrackConversion, TrackEvent (path: `client/src/components/journey-builder/nodes/tracking/`)
- **Canvas**: JourneyBuilderCanvas (path: `client/src/components/journey-builder/JourneyBuilderCanvas.tsx`)
- **Header**: JourneyBuilderHeader (path: `client/src/components/journey-builder/JourneyBuilderHeader.tsx`)
- **Panel**: NodePanel (path: `client/src/components/journey-builder/NodePanel.tsx`)
- **Simulator**: JourneySimulator (path: `client/src/components/journey-builder/JourneySimulator.tsx`)
- **Analytics**: JourneyAnalyticsPanel (path: `client/src/components/journey-builder/JourneyAnalyticsPanel.tsx`)

## Acceptance Criteria

1. GIVEN o usuario no Journey Builder canvas
   WHEN arrasta um node do painel lateral para o canvas
   THEN o node e adicionado ao grafo com posicao correta e conexoes disponiveis

2. GIVEN um journey com nodes conectados
   WHEN o usuario clica em "Validate" no header
   THEN o backend valida o grafo (sem ciclos infinitos, todos os caminhos terminam em Exit ou JourneyEnd) e retorna erros especificos por node

3. GIVEN acoes de edicao no canvas
   WHEN o usuario pressiona Ctrl+Z / Ctrl+Y
   THEN undo/redo funciona corretamente para adicao, remocao, movimentacao e reconexao de nodes

## Required Skills

1. **JourneyOrchestration** - nova
   - Spec: docs/specs/skills/journey_orchestration.md
   - Construcao e validacao de grafos de journey

2. **ReactFlowCanvas** - nova
   - Spec: docs/specs/skills/react_flow_canvas.md
   - Manipulacao do canvas React Flow com custom nodes

## Required Agent Capabilities

- **Primary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, react_flow, journey_builder]
- **Secondary**: `crm_backend_agent` - capabilities: [crm_backend, journeys, graph_validation]

## RAG Chunk References

- `category: crm_frontend` + `source_file CONTAINS 'journey-builder'`
- `category: crm_backend` + `source_file CONTAINS 'services/journeyService'`
- `category: crm_model` + `domain: journeys`
- `category: usecase` + `domain: journeys`

## Related Use Cases

- **Depends on**: nenhum (ponto de entrada do modulo journeys)
- **Enables**: UC-JRN-002 (Intelligence - sugestoes no canvas), UC-JRN-003 (Motor de Execucao - journey precisa existir), UC-JRN-004 (Analytics - journey gera dados)
- **Conflicts with**: nenhum

## Implementation Notes

- Frontend usa React Flow (reactflow) para o canvas
- 20+ tipos de nodes organizados em 5 categorias: triggers, actions, conditions, flow, tracking
- Undo/redo implementado com useUndoRedo hook customizado
- Multi-select com Shift+Click e area de selecao
- Edge reconnect via drag-and-drop nativo do React Flow
- Validacao de grafo no backend usa BFS para detectar ciclos e caminhos sem saida
- Nodes salvos como JSON no campo `nodes` do Journey model
