# [UC-SS-006] Blacklist e Phone Maturation Pipeline

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-SS-006 |
| **Domain** | anti_fraud |
| **Repos** | sendspeed0/blacklist-sendspeed (branch: main) |
| **Priority** | P1-High |
| **Complexity** | M |
| **Status** | Production |

## Domain Context

Sistema de blacklisting com pipeline de maturacao multi-estagio para numeros de telefone problematicos. O blacklist-sendspeed (Fastify + SQLite) gerencia um pipeline de 5 estagios que progressivamente restringe numeros baseado em falhas de entrega, reclamacoes e padroes de fraude. Inclui 3 cron jobs para maturacao automatica e sync diario com producao.

### Data Models

- **Model**: PhoneEntry (blacklist-sendspeed: `src/models/`)
  - Fields: `phone: string`, `status: enum(active|strike_watch|cooling_1|cooling_2|blacklisted)`, `strike_count: integer`, `last_failure_at: datetime`, `reason: string`, `source: enum(delivery_failure|complaint|fraud|manual)`, `matured_at: datetime`, `created_at`
- **Enum**: MaturationStage
  - `active` → telefone normal, sem restricoes
  - `strike_watch` → 2+ falhas recentes, monitorado (pode enviar com aviso)
  - `cooling_1` → 5+ falhas, cooling period 7 dias (envio bloqueado)
  - `cooling_2` → reincidente apos cooling_1, cooling period 30 dias
  - `blacklisted` → permanente, nunca mais envia
- **Config**: MaturationRules
  - `strike_threshold: 2` → move para strike_watch
  - `cooling_1_threshold: 5` → move para cooling_1
  - `cooling_1_duration: 7 days`
  - `cooling_2_duration: 30 days`
  - `blacklist_threshold: 3 cycles` → apos 3x cooling, blacklisted permanente

### Services

- **Service**: BlacklistAPI (blacklist-sendspeed: `src/routes/`)
  - Fastify REST API
  - Methods: `checkPhone(phone)`, `addEntry(phone, reason, source)`, `removeEntry(phone)`, `getStatus(phone)`, `bulkCheck(phones[])`
  - bulkCheck: aceita array de ate 10K phones, retorna map {phone: status}
- **Service**: MaturationEngine (blacklist-sendspeed: `src/services/`)
  - Processa transicoes entre estagios baseado em regras e timestamps
  - Methods: `processMaturation()`, `advanceStage(phone)`, `resetToActive(phone)`
  - Cron 1: a cada 1h verifica phones em strike_watch → cooling_1 (se threshold atingido)
  - Cron 2: a cada 6h verifica cooling_1 expired → active (se sem novas falhas) ou → cooling_2
  - Cron 3: diario verifica cooling_2 expired → active ou → blacklisted (se 3+ cycles)
- **Service**: ProductionSync (blacklist-sendspeed: `src/services/`)
  - Sync diario com banco MySQL de producao (app-send-speed)
  - Methods: `syncFromProduction()`, `exportToProduction()`
  - Import: busca novos delivery failures das ultimas 24h
  - Export: publica lista atualizada de blacklisted phones para producao
- **Service**: FraudDetector (blacklist-sendspeed: `src/services/`)
  - Detecta padroes de fraude automaticamente
  - Methods: `detectPattern(phone_batch)`, `flagFraud(phone, pattern_type)`
  - Patterns: burst sending (>100 msgs/min para mesmo numero), sequential numbers, known spam patterns

### Routes/Endpoints

- `GET /api/check/:phone` → BlacklistAPI.checkPhone
- `POST /api/check/bulk` → BlacklistAPI.bulkCheck (array ate 10K)
- `POST /api/entries` → BlacklistAPI.addEntry
- `DELETE /api/entries/:phone` → BlacklistAPI.removeEntry
- `GET /api/status/:phone` → BlacklistAPI.getStatus (historico completo)
- `POST /api/sync/production` → ProductionSync.syncFromProduction (admin)
- `GET /api/stats` → estatisticas por stage (counts, trends)

## Acceptance Criteria

1. GIVEN phone com 2 delivery failures nas ultimas 48h
   WHEN MaturationEngine.processMaturation() executa (cron 1h)
   THEN phone e movido de 'active' para 'strike_watch' com strike_count=2

2. GIVEN phone em 'strike_watch' com 5+ falhas acumuladas
   WHEN MaturationEngine.advanceStage() e acionado
   THEN phone e movido para 'cooling_1', envios sao bloqueados por 7 dias, e alerta e logado

3. GIVEN phone em 'cooling_1' que completou 7 dias sem novas falhas
   WHEN cron de 6h verifica expiration
   THEN phone retorna para 'active' com strike_count resetado

4. GIVEN phone que entrou em cooling pela 3a vez
   WHEN MaturationEngine processa o 3o ciclo cooling_2
   THEN phone e movido para 'blacklisted' permanentemente, nunca mais recebe SMS

5. GIVEN campanha com 50K numeros prestes a ser enviada
   WHEN BlacklistAPI.bulkCheck(phones[]) e chamado com os 50K numeros
   THEN resposta retorna map {phone: status} em < 2 segundos, e numeros com status != 'active' sao filtrados

6. GIVEN FraudDetector detecta burst de 150 msgs/min para mesmo numero
   WHEN detectPattern() identifica o padrao
   THEN phone e flagado como fraude, movido direto para 'blacklisted' com source='fraud'

7. GIVEN sync diario com producao executado
   WHEN ProductionSync.syncFromProduction() roda
   THEN delivery failures das ultimas 24h sao importadas, phones afetados tem strike_count incrementado, e lista de blacklisted e exportada para producao

## Required Skills

1. **PhoneBlacklisting** - existente
   - Spec: docs/specs/skills/phone_blacklisting.md
   - Pipeline de maturacao multi-estagio com regras configuraveis

2. **FraudDetection** - nova
   - Spec: docs/specs/skills/fraud_detection.md
   - Deteccao de padroes de fraude em envios SMS

## Required Agent Capabilities

- **Primary**: `sendspeed_admin_agent` - capabilities: [blacklist_management, fraud_detection, phone_maturation]
- **Secondary**: `sendspeed_pipeline_agent` - capabilities: [production_sync, batch_processing]

## RAG Chunk References

- `category: sendspeed_blacklist` + `source_file CONTAINS 'MaturationEngine'`
- `category: sendspeed_blacklist` + `source_file CONTAINS 'BlacklistAPI'`
- `category: sendspeed_blacklist` + `source_file CONTAINS 'FraudDetector'`
- `category: sendspeed_blacklist` + `source_file CONTAINS 'ProductionSync'`

## Related Use Cases

- **Depends on**: UC-SS-005 (Delivery Service - fornece dados de falha), UC-SS-002 (Webhooks - status de delivery)
- **Enables**: UC-SS-001 (Pipeline SMS - filtra phones antes do envio)
- **Conflicts with**: nenhum

## Implementation Notes

- Fastify para performance maxima na API de check (< 1ms per query)
- SQLite para simplicidade e portabilidade — dataset cabe em memoria (< 5M phones)
- Pipeline de maturacao e state machine: active → strike_watch → cooling_1 → cooling_2 → blacklisted
- Cron jobs sao idempotentes — podem rodar multiplas vezes sem efeito colateral
- Production sync via MySQL direct connection (read-only) — nao usa API
- Bulk check otimizado com IN query + index em phone column
- FraudDetector roda inline com addEntry — nao e cron separado
