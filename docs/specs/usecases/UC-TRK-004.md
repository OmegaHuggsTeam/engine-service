# [UC-TRK-004] Avaliacao do Rules Engine

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-TRK-004 |
| **Domain** | tracker |
| **Repos** | smarttrack.userin.ai (branch: pedro-crm) |
| **Priority** | P0-Critical |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Motor de regras client-side que avalia condicoes sobre eventos, paginas, atributos de visitante e perfil para disparar acoes automaticas (execucao de JavaScript arbitrario e ativacao de componentes). O SegmentEvaluator processa arvores recursivas de condicoes AND/OR com 7 tipos de condicao e 10 operadores. O RulesService carrega regras da platform API, adapta o formato, gerencia deduplicacao por sessao e timer, e executa acoes via eval() de JS strings e trigger de component IDs. Integra com SmartModalService, MinigameService e SmartBlockService para exibicao de componentes.

### Data Models

- **Model**: CondicaoFolha (leaf condition)
  - Fields: `tipo: enum(evento|pagina|atributo|email|mensagem|profile_attribute|has_tag)`, `operador: enum(igual|diferente|contem|nao_contem|existe|nao_existe|maior_que|menor_que|maior_ou_igual|menor_ou_igual)`, `valor: any`
- **Model**: GrupoCondicoes (condition group)
  - Fields: `operador_logico: enum(AND|OR)`, `condicoes: (CondicaoFolha | GrupoCondicoes)[]`
  - Recursive structure: groups can contain other groups or leaf conditions
- **Model**: Rule (adapted from API)
  - Fields: `conditionGroup: GrupoCondicoes`, `action_js: string`, `action_components: string[]`, `timer: number`, `frequency: string`
- **Condition Types** (CondicaoFolha.tipo):
  - `evento` - evaluates against event properties
  - `pagina` - evaluates against current page URL/title
  - `atributo` - evaluates against visitor attributes
  - `email` - evaluates against visitor email
  - `mensagem` - evaluates against message content
  - `profile_attribute` - evaluates against profile attributes
  - `has_tag` - evaluates against visitor tags
- **Operators** (CondicaoFolha.operador):
  - `igual` (equals), `diferente` (not equals)
  - `contem` (contains), `nao_contem` (not contains)
  - `existe` (exists), `nao_existe` (not exists)
  - `maior_que` (greater than), `menor_que` (less than)
  - `maior_ou_igual` (greater or equal), `menor_ou_igual` (less or equal)

### Services (Client-Side)

- **Service**: SegmentEvaluator (repo: smarttrack, path: `client/src/utils/SegmentEvaluator.ts`)
  - Methods: `evaluateFolha(condicao, context)`, `evaluateGrupo(grupo, context)`, `segmentoCorresponde(segmento, context)`
  - Evaluates leaf conditions (`evaluateFolha`) against 7 condition types with 10 operators
  - Evaluates recursive groups (`evaluateGrupo`) with AND/OR logic
  - Top-level entry: `segmentoCorresponde()` returns boolean match result
- **Service**: RulesService (repo: smarttrack, path: `client/src/application/RulesService.ts`)
  - Methods: `loadRules()`, `adaptRuleFromAPI(apiRule)`, `evaluateAndExecute(context)`
  - **Rule Loading**: fetches from `{platformApiUrl}/api/rules/public/company/{companyId}/for-tracker`
  - **Rule Adaptation**: `adaptRuleFromAPI()` extracts `conditionGroup`, `action_js`, `action_components`, `timer`, `frequency` from raw API response
  - **Deduplication**:
    - Session dedup: via sessionStorage to prevent re-triggering same rule in session
    - Timer-based dedup: respects `timer` field to prevent rapid re-triggering
    - Click cache during timer: caches click events while timer is active
  - **Execution**:
    - `action_js`: eval() of arbitrary JavaScript string
    - `action_components`: triggers component IDs (SmartModal, Minigame, SmartBlock)
  - **Frequency Control**: `once_per_session`, `once_per_page` enforcement

### Routes/Endpoints

- `GET {platformApiUrl}/api/rules/public/company/{companyId}/for-tracker` -> fetch all rules for company (client-side)
- `GET /api/rules/:id` -> single rule by ID (backend MongoDB)
- `GET /api/rules` -> all rules (backend MongoDB)

## Acceptance Criteria

1. GIVEN RulesService inicializado com companyId
   WHEN loadRules() e chamado
   THEN regras sao buscadas de {platformApiUrl}/api/rules/public/company/{companyId}/for-tracker e adaptadas via adaptRuleFromAPI() extraindo conditionGroup, action_js, action_components, timer e frequency

2. GIVEN regra com conditionGroup contendo CondicaoFolha tipo=pagina, operador=contem, valor="/checkout"
   WHEN SegmentEvaluator.evaluateFolha() avalia contra URL atual contendo "/checkout"
   THEN condicao retorna true e regra e elegivel para execucao

3. GIVEN regra com GrupoCondicoes recursivo (AND de [tipo=evento igual "click", OR de [tipo=pagina contem "/produto", tipo=atributo existe "cart_total"]])
   WHEN SegmentEvaluator.evaluateGrupo() avalia recursivamente
   THEN grupo AND retorna true somente se todos sub-grupos e folhas retornam true, grupo OR retorna true se qualquer retornar true

4. GIVEN regra avaliada como match com action_js="showPromo()" e action_components=["modal-123", "minigame-456"]
   WHEN execucao e disparada
   THEN action_js e executado via eval() e action_components disparam SmartModalService.show("modal-123") e MinigameService.show("minigame-456")

5. GIVEN regra com frequency=once_per_session ja executada na sessao atual
   WHEN mesma regra e avaliada novamente
   THEN deduplicacao via sessionStorage impede re-execucao na mesma sessao

6. GIVEN regra com timer=5000 executada ha 3 segundos
   WHEN mesma regra e avaliada novamente
   THEN timer-based dedup impede re-execucao ate completar 5000ms, clicks durante timer sao cacheados

7. GIVEN regra com frequency=once_per_page ja executada na pagina atual
   WHEN navegacao permanece na mesma pagina e regra e avaliada novamente
   THEN regra nao e re-executada ate usuario navegar para outra pagina

## Required Skills

1. **RuleEvaluation** - nova
   - Spec: docs/specs/skills/rule_evaluation.md
   - Avaliacao recursiva de arvores de condicoes AND/OR com 7 tipos e 10 operadores

2. **ActionExecution** - nova
   - Spec: docs/specs/skills/action_execution.md
   - Execucao de acoes via eval() de JS strings e trigger de component IDs

## Required Agent Capabilities

- **Primary**: `rules_engine_agent` - capabilities: [condition_evaluation, recursive_tree_traversal, action_execution, frequency_control]
- **Secondary**: `tracker_frontend_agent` - capabilities: [modal_triggering, minigame_triggering, smartblock_triggering]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'SegmentEvaluator'`
- `category: crm_backend` + `source_file CONTAINS 'RulesService'`
- `category: crm_backend` + `source_file CONTAINS 'CondicaoFolha'`
- `category: crm_backend` + `source_file CONTAINS 'GrupoCondicoes'`
- `category: usecase` + `domain: tracker`

## Related Use Cases

- **Depends on**: UC-TRK-001 (Coleta de Eventos - eventos alimentam contexto de avaliacao de regras), UC-TRK-003 (Buyer Agent - intencoes de compra enriquecem contexto para condicoes tipo=evento)
- **Enables**: UC-TRK-002 (SmartModal/Minigames - action_components disparam exibicao de modais e minigames), UC-SEG-001 (Segmentacao - regras com tipo=atributo e has_tag avaliam segmentos)
- **Conflicts with**: nenhum

## Implementation Notes

- SegmentEvaluator e puramente client-side, sem chamadas de rede durante avaliacao
- Arvore de condicoes e recursiva: GrupoCondicoes pode conter outros GrupoCondicoes ou CondicaoFolha em qualquer profundidade
- 7 tipos de condicao cobrem: eventos, paginas, atributos de visitante, email, mensagens, atributos de perfil e tags
- 10 operadores incluem comparacao (igual/diferente), busca textual (contem/nao_contem), existencia (existe/nao_existe) e numericos (maior_que/menor_que/maior_ou_igual/menor_ou_igual)
- action_js usa eval() para executar JavaScript arbitrario - potencial vetor de seguranca que depende de sanitizacao no backend
- action_components recebe array de IDs que sao despachados para SmartModalService, MinigameService ou SmartBlockService
- Deduplicacao em 3 niveis: sessionStorage (por sessao), timer (intervalo minimo entre execucoes), once_per_page (por navegacao)
- Click cache durante timer armazena eventos de click que ocorrem enquanto timer esta ativo
- Regras sao carregadas de endpoint publico: /api/rules/public/company/{companyId}/for-tracker
- adaptRuleFromAPI() normaliza formato da API para modelo interno (conditionGroup, action_js, action_components, timer, frequency)
- Backend tambem expoe /api/rules e /api/rules/:id via MongoDB para acesso direto
