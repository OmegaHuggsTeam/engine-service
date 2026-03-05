# [UC-SEG-002] Computacao de Sinais Dinamicos

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SEG-002 |
| **Domain** | segments |
| **Repos** | segment-engine |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Sistema de computacao de campos dinamicos em 3 camadas (AGG -> SIGNAL -> OUTPUT) que enriquece perfis de usuario com agregacoes, sinais booleanos/enum/trend/numericos e scores ponderados. O FieldRegistrySyncService mantém um cache TTL de 5 minutos do field_registry com 5 tipos de campo (ATTRIBUTE, AGG, SIGNAL, OUTPUT, AI_SCORING). O ObjectEnricherService adiciona dados de objetos customizados (Game Vendor, Payment Method). Todos os resultados sao armazenados na secao DynamicFields do UserProfile.

### Data Models

- **Model**: UserProfile.DynamicFields (repo: segment-engine, path: `src/models/user-profile.model.ts`)
  - Fields: `Record<string, any>` - armazena resultados de AGG, SIGNAL, OUTPUT e AI_SCORING computados dinamicamente
- **Model**: FieldRegistry (repo: segment-engine, via FieldRegistrySyncService)
  - Types: `ATTRIBUTE`, `AGG`, `SIGNAL`, `OUTPUT`, `AI_SCORING`
  - Cache: 5-minute TTL, synced by FieldRegistrySyncService
- **Model**: UserProfile.Objects (repo: segment-engine, path: `src/models/user-profile.model.ts`)
  - Fields: `Record<string, any>` - custom objects (Game Vendor, Payment Method, etc.)

### Services

- **Service**: DynamicAggService (repo: segment-engine, path: `src/services/dynamic-agg.service.ts`)
  - Aggregation operators: `SUM`, `COUNT`, `AVG`, `MIN`, `MAX`, `COUNT_DISTINCT`, `LAST`, `FIRST`
  - Sources: events, attributes, objectRelation
  - Layer 1 of pipeline: computes raw aggregations from ClickHouse/MongoDB data
- **Service**: DynamicSignalService (repo: segment-engine, path: `src/services/dynamic-signal.service.ts`)
  - Signal types: `boolean`, `enum`, `trend`, `number`
  - Operators: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `in`, `contains`, `exists`
  - Layer 2 of pipeline: evaluates signals against AGG values or raw attributes
- **Service**: DynamicOutputService (repo: segment-engine, path: `src/services/dynamic-output.service.ts`)
  - Weighted scores: 0-1 or 0-100 scale
  - Normalization methods: `ratio_to_benchmark`, `boolean_flag`, `enum_map`, `linear_scale`
  - Layer 3 of pipeline: combines signals into final weighted output scores
- **Service**: FieldRegistrySyncService (repo: segment-engine, path: `src/services/field-registry-sync.service.ts`)
  - 5-minute TTL cache of `field_registry` collection
  - Field kinds: ATTRIBUTE, AGG, SIGNAL, OUTPUT, AI_SCORING
  - Provides field definitions to all Dynamic*Services
- **Service**: ObjectEnricherService (repo: segment-engine, path: `src/services/object-enricher.service.ts`)
  - Enriches profiles with custom objects: Game Vendor, Payment Method, etc.
  - Results stored in UserProfile.Objects section

### SegmentEvaluator Integration

- **Evaluator**: SegmentEvaluator (repo: segment-engine, path: `src/segments/`)
  - Recursive AND/OR rule evaluation with `$now_minus` temporal support
  - CompareOperator: `eq`, `ne`, `gt`, `gte`, `lt`, `lte`, `exists`, `in`, `nin`
  - FeatureType: `ROLLING_SUM`, `ROLLING_COUNT`, `LAST_TIMESTAMP`, `FIXED_VALUE`
  - Evaluates dynamic fields as segment conditions

### Routes/Endpoints

- `GET /api/company-variables` -> FieldRegistrySyncService (field registry definitions)
- `GET /api/profiles` -> ProfileService (includes DynamicFields in response)
- `GET /api/user-profiles?reprocess=true` -> Forces recomputation of all dynamic fields

### Frontend Components

- Nenhum componente frontend direto (segment-engine e backend puro, port 3055)

## Acceptance Criteria

1. GIVEN um field_registry com campo tipo AGG configurado (ex: source=events, operator=SUM, field=deposit_amount)
   WHEN o DynamicAggService computa a agregacao para um usuario
   THEN retorna o valor agregado correto usando o operador especificado (SUM/COUNT/AVG/MIN/MAX/COUNT_DISTINCT/LAST/FIRST) a partir da source definida (events/attributes/objectRelation)

2. GIVEN um campo tipo SIGNAL configurado com tipo `boolean` e operador `gt` contra um valor AGG
   WHEN o DynamicSignalService avalia o sinal
   THEN retorna true/false baseado na comparacao do valor AGG com o threshold usando o operador correto (eq/ne/gt/gte/lt/lte/in/contains/exists)

3. GIVEN campos tipo SIGNAL avaliados e um OUTPUT configurado com pesos e normalizacao `linear_scale`
   WHEN o DynamicOutputService computa o score final
   THEN retorna score ponderado normalizado na escala correta (0-1 ou 0-100) usando o metodo de normalizacao especificado (ratio_to_benchmark/boolean_flag/enum_map/linear_scale)

4. GIVEN o FieldRegistrySyncService com cache ativo
   WHEN uma requisicao chega dentro do TTL de 5 minutos
   THEN usa o cache em memoria sem consultar MongoDB
   AND WHEN o TTL expira
   THEN re-sincroniza o field_registry completo com os 5 tipos (ATTRIBUTE, AGG, SIGNAL, OUTPUT, AI_SCORING)

5. GIVEN um perfil com objectRelation configurado (ex: Game Vendor)
   WHEN o ObjectEnricherService processa o perfil
   THEN enriquece a secao Objects do UserProfile com dados do objeto customizado

6. GIVEN o pipeline completo AGG -> SIGNAL -> OUTPUT executando via ProfileService.compileProfile()
   WHEN todos os 3 layers completam
   THEN os resultados sao armazenados na secao DynamicFields do UserProfile em MongoDB

## Required Skills

1. **DynamicFieldComputation** - nova
   - Spec: docs/specs/skills/dynamic_field_computation.md
   - Pipeline de 3 camadas (AGG -> SIGNAL -> OUTPUT) com operadores dinamicos

2. **FieldRegistryManagement** - nova
   - Spec: docs/specs/skills/field_registry_management.md
   - Sync e cache de field_registry com 5 tipos de campo

3. **SegmentEvaluation** - nova
   - Spec: docs/specs/skills/segment_evaluation.md
   - Avaliacao recursiva AND/OR com CompareOperator e FeatureType

## Required Agent Capabilities

- **Primary**: `crm_data_agent` - capabilities: [segmentation, dynamic_signals, clickhouse, aggregation]
- **Secondary**: `crm_backend_agent` - capabilities: [crm_backend, segments, mongodb]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/dynamic-agg.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/dynamic-signal.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/dynamic-output.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/field-registry-sync.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/services/object-enricher.service'`
- `category: crm_backend` + `source_file CONTAINS 'segment-engine/src/segments/'`
- `category: crm_model` + `source_file CONTAINS 'user-profile.model'`
- `category: usecase` + `domain: segments`

## Related Use Cases

- **Depends on**: UC-SEG-001 (Pipeline de Segmentacao - perfis base e compileProfile() que orquestra o pipeline dinamico)
- **Enables**: UC-SEG-003 (Best-Time-to-Send - sinais podem alimentar scoring de best-time), UC-JRN-003 (Motor de Execucao - sinais dinamicos como condicoes de journey)
- **Conflicts with**: nenhum

## Implementation Notes

- Pipeline de 3 camadas estritamente ordenado: AGG primeiro (valores brutos), SIGNAL segundo (avaliacao booleana/enum/trend/number), OUTPUT terceiro (scores ponderados)
- DynamicAggService suporta 8 operadores de agregacao e 3 fontes de dados (events, attributes, objectRelation)
- DynamicSignalService suporta 4 tipos de sinal (boolean, enum, trend, number) e 9 operadores de comparacao
- DynamicOutputService normaliza scores via 4 metodos (ratio_to_benchmark, boolean_flag, enum_map, linear_scale) em escala 0-1 ou 0-100
- FieldRegistrySyncService mantém cache em memoria com TTL de 5 minutos para evitar queries repetidas ao MongoDB
- ObjectEnricherService enriquece perfis com objetos customizados (Game Vendor, Payment Method) na secao Objects
- SegmentEvaluator usa os DynamicFields para avaliacao de regras de segmento com suporte a `$now_minus` para janelas temporais
- FeatureType ROLLING_SUM e ROLLING_COUNT dependem do ExpirationWorker para expirar FeatureBuckets
- Todos os resultados dinamicos persistidos no campo DynamicFields do UserProfile (Record<string, any>)
- Integrado no step de compileProfile() do ProfileService - executa como parte do pipeline de 10 etapas
