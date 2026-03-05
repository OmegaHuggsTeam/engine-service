# [UC-JRN-002] Journey Intelligence (Sugestoes IA)

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-JRN-002 |
| **Domain** | journeys |
| **Repos** | platform-backend, sendspeed-engage-ai-flow-08 |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Usa inteligencia artificial para sugerir otimizacoes em journeys existentes e gerar journeys completas a partir de descricao em linguagem natural. Compara performance com benchmarks de industria para identificar oportunidades de melhoria.

### Data Models

- **Model**: JourneyBenchmark (repo: platform-backend, path: `backend/src/domain/models/JourneyBenchmark.js`)
  - Fields: `industry: string`, `metric: string`, `average: number`, `p90: number`, `updated_at: Date`

### Services

- **Service**: journeyIntelligenceService (repo: platform-backend, path: `backend/src/application/services/journeyIntelligenceService.js`)
  - Methods: `suggestOptimizations()`, `generateJourney()`, `analyzePerformance()`
- **Service**: journeyBenchmarkService (repo: platform-backend, path: `backend/src/application/services/journeyBenchmarkService.js`)
  - Methods: `getBenchmarks()`, `compareWithBenchmark()`, `updateBenchmarks()`

### Routes/Endpoints

- `POST /api/journeys/:id/intelligence/suggest` -> `journeyIntelligenceService.suggestOptimizations()`
- `POST /api/journeys/intelligence/generate` -> `journeyIntelligenceService.generateJourney()`
- `GET /api/journeys/:id/intelligence/benchmarks` -> `journeyBenchmarkService.compareWithBenchmark()`

### Frontend Components

- **Component**: AiJourneyGenerator (repo: engage-ai-flow, path: `client/src/components/journey-builder/AiJourneyGenerator.tsx`)
- **Utility**: journeyAiService (repo: engage-ai-flow, path: `client/src/services/journeyAiService.ts`)

## Acceptance Criteria

1. GIVEN uma journey ativa com dados de performance
   WHEN o usuario clica em "AI Suggestions" no canvas
   THEN o sistema retorna 3-5 sugestoes concretas com impacto estimado baseado em benchmarks

2. GIVEN o usuario no modo de geracao de journey
   WHEN descreve o objetivo em linguagem natural (ex: "onboarding para novos usuarios com 3 emails")
   THEN a IA gera uma journey completa com nodes, edges e configuracoes pre-preenchidas

3. GIVEN benchmarks de industria disponiveis
   WHEN o sistema compara performance da journey
   THEN exibe metricas abaixo da media em vermelho com sugestao de acao especifica

## Required Skills

1. **JourneyOrchestration** - existente
   - Spec: docs/specs/skills/journey_orchestration.md
   - Construcao e validacao de grafos de journey

2. **AiGeneration** - nova
   - Spec: docs/specs/skills/ai_generation.md
   - Geracao de journeys via LLM com prompt engineering

## Required Agent Capabilities

- **Primary**: `crm_backend_agent` - capabilities: [crm_backend, journeys, ai_intelligence]
- **Secondary**: `crm_frontend_agent` - capabilities: [crm_frontend, react, journey_builder]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'services/journeyIntelligenceService'`
- `category: crm_backend` + `source_file CONTAINS 'services/journeyBenchmarkService'`
- `category: crm_frontend` + `source_file CONTAINS 'AiJourneyGenerator'`
- `category: usecase` + `domain: journeys`

## Related Use Cases

- **Depends on**: UC-JRN-001 (Journey Builder - canvas precisa existir para sugestoes)
- **Enables**: UC-JRN-004 (Analytics - sugestoes usam dados de analytics)
- **Conflicts with**: nenhum

## Implementation Notes

- LLM usado para geracao de journeys (modelo configuravel por empresa)
- Benchmarks atualizados semanalmente via batch job
- Sugestoes sao contextuais: consideram nodes existentes, audiencia e historico
- journeyAiService.ts no frontend faz streaming de respostas via SSE
- Rate limit de 10 geracoes por empresa por hora
