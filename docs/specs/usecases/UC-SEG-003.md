# [UC-SEG-003] Calculo de Best-Time-to-Send

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SEG-003 |
| **Domain** | segments |
| **Repos** | segment-engine |
| **Priority** | P2-Medium |
| **Complexity** | M |
| **Status** | Spec |

## Domain Context

Calcula o melhor horario para contactar cada usuario utilizando um algoritmo de exponential decay (DECAY_RATE=0.01) com bonus por contagem de sessoes. Analisa padroes historicos de atividade em 3 dimensoes (hora do dia, dia da semana, combinacao dia+hora) para produzir rankings ponderados. O resultado e persistido no modelo UserBestTime e integrado na secao BestTime do UserProfile, incluindo um `proposedContactTimestamp` para agendamento de campanhas.

### Data Models

- **Model**: UserBestTime (repo: segment-engine, path: via BestTimeService)
  - Fields: `bestHour: number`, `bestDayHour: object`, `dailyRanking: object`, `topHours: number[]`, `proposedContactTimestamp: Date`
- **Model**: UserProfile.BestTime (repo: segment-engine, path: `src/models/user-profile.model.ts`)
  - Fields: `bestHour: number`, `bestDayHour: object`, `dailyRanking: object`, `topHours: number[]`, `proposedContactTimestamp: Date`

### Services

- **Service**: BestTimeService (repo: segment-engine, path: `src/services/best-time.service.ts`)
  - Algorithm: Exponential decay with `DECAY_RATE = 0.01`
  - Session-count bonus: additional weight based on number of sessions in time slot
  - 3 scoring dimensions:
    - **Hourly**: weight per hour (0-23) with decay by recency
    - **Daily**: weight per day of week (0-6) with decay by recency
    - **DayHour**: combined day+hour matrix with decay by recency
  - Output: saves computed best-time data to UserBestTime model
  - Integrated into ProfileService.compileProfile() pipeline

### Routes/Endpoints

- `GET /api/profiles` -> includes BestTime section in UserProfile response
- `GET /api/user-profiles?reprocess=true` -> forces BestTime recalculation via compileProfile()

### Frontend Components

- Nenhum componente frontend direto (segment-engine e backend puro, port 3055)

## Acceptance Criteria

1. GIVEN um usuario com historico de sessoes em ClickHouse
   WHEN o BestTimeService calcula o best-time
   THEN aplica exponential decay (DECAY_RATE=0.01) a cada sessao, ponderando sessoes recentes com peso maior que sessoes antigas

2. GIVEN um usuario com multiplas sessoes na mesma hora do dia
   WHEN o BestTimeService computa os scores horarios
   THEN aplica session-count bonus proporcional ao numero de sessoes naquele horario, alem do decay temporal

3. GIVEN o BestTimeService completando o calculo
   WHEN todas as 3 dimensoes sao computadas (hourly, daily, dayHour)
   THEN salva no UserBestTime model com `bestHour` (hora com maior score), `dailyRanking` (dias ordenados por score), `topHours` (top horas), e `bestDayHour` (combinacao dia+hora com maior score)

4. GIVEN o UserBestTime salvo com sucesso
   WHEN o ProfileService.compileProfile() integra os dados
   THEN a secao BestTime do UserProfile e populada incluindo `proposedContactTimestamp` com o proximo horario otimo para contacto

5. GIVEN uma requisicao com `reprocess=true` no endpoint /api/user-profiles
   WHEN o perfil e reprocessado
   THEN o BestTimeService recalcula todos os scores com dados atualizados do ClickHouse

## Required Skills

1. **BestTimeCalculation** - nova
   - Spec: docs/specs/skills/best_time_calculation.md
   - Calculo de janela otima de envio com exponential decay e session-count bonus

2. **SegmentPipeline** - existente
   - Spec: docs/specs/skills/segment_pipeline.md
   - Integracao com ProfileService.compileProfile() pipeline

## Required Agent Capabilities

- **Primary**: `crm_data_agent` - capabilities: [segmentation, analytics, best_time, clickhouse]
- **Secondary**: `crm_backend_agent` - capabilities: [crm_backend, scheduling, mongodb]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/best-time.service'`
- `category: crm_model` + `source_file CONTAINS 'user-profile.model'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/profile.service'`
- `category: usecase` + `domain: segments`

## Related Use Cases

- **Depends on**: UC-SEG-001 (Pipeline de Segmentacao - BestTimeService integrado no compileProfile() de 10 etapas), UC-TRK-001 (Coleta de Eventos - historico de sessoes em ClickHouse)
- **Enables**: UC-CAM-004 (Agendamento - proposedContactTimestamp alimenta scheduling inteligente de campanhas)
- **Conflicts with**: nenhum

## Implementation Notes

- Algoritmo de exponential decay usa constante DECAY_RATE=0.01, onde peso = e^(-DECAY_RATE * dias_desde_sessao)
- Session-count bonus adiciona peso extra quando multiplas sessoes ocorrem no mesmo horario, reforçando padroes consistentes
- 3 dimensoes de scoring independentes: hourly (24 slots), daily (7 slots), dayHour (168 combinacoes)
- Resultados persistidos no modelo UserBestTime em MongoDB
- Integrado como etapa do compileProfile() - nao executa isoladamente
- proposedContactTimestamp calcula o proximo momento futuro baseado no bestDayHour para agendamento
- Dados de sessao vem do ClickHouse via UserDataFetcherService (queries consolidadas)
- Nao depende de aberturas de email ou cliques em SMS - usa exclusivamente dados de sessao no site
- Recalculo forçado disponivel via query parameter `reprocess=true` no endpoint /api/user-profiles
