# [UC-CAM-002] Configuracao de A/B Testing

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-CAM-002 |
| **Domain** | campaigns |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P2-Medium |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Permite configurar variantes de A/B test em campanhas e journeys sem limite de variantes. Inclui auto-otimizacao com "logica vendedor" que redistribui trafego para a variante vencedora. Um cron job de 5 minutos avalia resultados e ajusta distribuicao automaticamente.

### Data Models

- **Model**: ABTestResult (repo: platform-backend, path: `backend/src/domain/models/ABTestResult.js`)
  - Fields: `journey_id: ObjectId`, `variant_id: string`, `impressions: number`, `conversions: number`, `revenue: number`, `winner: boolean`

### Services

- **Service**: journeyEvaluatorService (repo: platform-backend, path: `backend/src/application/services/journeyEvaluatorService.js`)
  - Methods: `evaluate()`, `selectVariant()`, `getResults()`
- **Service**: abTestEvaluatorService (repo: platform-backend, path: `backend/src/application/services/abTestEvaluatorService.js`)
  - Methods: `evaluateTest()`, `autoOptimize()`, `declareWinner()`, `redistributeTraffic()`

### Routes/Endpoints

- `POST /api/campaigns/:id/ab-test` -> `abTestEvaluatorService.evaluateTest()`
- `GET /api/campaigns/:id/ab-test/results` -> `abTestEvaluatorService.getResults()`

### Frontend Components

- **Component**: ABTestNode (repo: engage-ai-flow, path: `client/src/components/journey-builder/nodes/ABTestNode.tsx`)
- **Component**: ABTestConfig (repo: engage-ai-flow, path: `client/src/components/journey-builder/configs/ABTestConfig.tsx`)

## Acceptance Criteria

1. GIVEN uma campanha ou journey existente
   WHEN o usuario configura A/B test com N variantes (sem limite)
   THEN todas as variantes sao salvas com distribuicao percentual valida (soma = 100%)

2. GIVEN um A/B test ativo com dados suficientes
   WHEN o cron de 5 minutos executa auto-otimizacao
   THEN a "logica vendedor" redistribui trafego favorecendo a variante com melhor conversao

3. GIVEN variantes com diferenca estatistica significativa
   WHEN o sistema declara vencedor
   THEN 100% do trafego e direcionado para a variante vencedora e as demais sao pausadas

## Required Skills

1. **CrmBackendCRUD** - existente
   - Spec: docs/specs/skills/crm_backend_crud.md
   - Operacoes CRUD em MongoDB via Express routes

2. **ABTestEvaluation** - nova
   - Spec: docs/specs/skills/ab_test_evaluation.md
   - Avaliacao estatistica e auto-otimizacao de variantes

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, campaigns, ab_testing]
- **Secondary**: `crm_data_agent` - capabilities: [analytics, statistical_evaluation]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/abTestEvaluatorService'`
- `category: crm_backend` + `source_file CONTAINS 'services/journeyEvaluatorService'`
- `category: crm_model` + `domain: campaigns`
- `category: usecase` + `domain: campaigns`

## Related Use Cases

- **Depends on**: UC-CAM-001 (Criar Campanha - necessario ter campanha para testar)
- **Enables**: UC-CAM-003 (Analytics - A/B test gera metricas comparativas)
- **Conflicts with**: nenhum

## Implementation Notes

- Sem limite de variantes (diferente de ferramentas tradicionais com maximo de 5)
- Cron de auto-otimizacao roda a cada 5 minutos via node-cron
- "Logica vendedor" e um algoritmo proprietario de redistribuicao baseado em conversao e revenue
- Resultados armazenados em MongoDB, metricas detalhadas em ClickHouse
