# [UC-TRK-003] Deteccao de Intencao do Buyer Agent

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-TRK-003 |
| **Domain** | tracker |
| **Repos** | smarttrack.userin.ai (branch: pedro-crm) |
| **Priority** | P1-High |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

Sistema de deteccao de intencao de compra e exibicao de cards inteligentes do Buyer Agent. O ClickIntentCollector detecta 10 tipos de intencao de compra no client-side. O BuyerAgentService orquestra a inicializacao e exibicao de cards via script externo carregado dinamicamente do Fly.io. O BuyerAgentApiService comunica com o backend de cards (/api/v1/buyer-cards/) para trigger e fetch. O TriggerCardHandler implementa chain of responsibility para despachar acoes (smart block, modal, card). O BuyerAgentEventCollector rastreia 11 tipos de eventos de interacao. A comunicacao real-time usa WebSocket via Socket.IO com filtragem por room e sender.

### Data Models

- **Intent Types** (ClickIntentCollector):
  - `ADD_TO_CART_ATTEMPT` - tentativa de adicionar ao carrinho
  - `START_CHECKOUT` - inicio do checkout
  - `PURCHASE_ATTEMPT` - tentativa de compra
  - `PRODUCT_DETAIL_CLICK` - click em detalhes do produto
  - `SIGNUP_ATTEMPT` - tentativa de cadastro
  - `LOGIN_ATTEMPT` - tentativa de login
  - `SUBSCRIBE_ATTEMPT` - tentativa de assinatura
  - `CONTACT_ATTEMPT` - tentativa de contato
  - `WHATSAPP_CLICK` - click em link WhatsApp
  - `DOWNLOAD_ATTEMPT` - tentativa de download

- **Event Types** (BuyerAgentEventCollector - 11 tipos):
  - `PREVIEW_BOX` - preview box exibido
  - `OPEN_CHAT_BOX` - chat box aberto
  - `CLOSE_CHAT_BOX` - chat box fechado
  - `NEW_CARD` - novo card recebido
  - `CARD_CLICK` - click no card
  - `CARD_CTA_CLICK` - click no CTA do card
  - Plus 5 additional interaction event types

### Services (Client-Side)

- **Service**: ClickIntentCollector (repo: smarttrack, path: `client/src/utils/ClickIntentCollector.ts`)
  - Analyzes click targets to classify into 10 intent types
  - Emits enriched events with `userIntentionAnalysis` and `confidence` score
  - Pattern matching on element attributes, CSS classes, text content, URLs
- **Service**: BuyerAgentService (repo: smarttrack, path: `client/src/application/BuyerAgentService.ts`)
  - Methods: `initialize(localStorageId)`, `forceCardDisplay(message)`
  - Uses GenericModal for card rendering
  - Orchestrates external agent script lifecycle
- **Service**: BuyerAgentApiService (repo: smarttrack, path: `client/src/application/BuyerAgentApiService.ts`)
  - Methods: `triggerCard(payload)`, `getCard(cardId)`
  - Endpoints:
    - `POST /api/v1/buyer-cards/trigger-socket` - trigger card generation via WebSocket
    - `GET /api/v1/buyer-cards/{cardId}` - fetch specific card by ID
- **Service**: BuyerAgentEventCollector (repo: smarttrack, path: `client/src/utils/BuyerAgentEventCollector.ts`)
  - Tracks 11 event types for buyer agent interactions
  - Events flow through EventPropagationService for batched delivery
- **Service**: ExternalAgentRegistry (repo: smarttrack, path: `client/src/application/ExternalAgentRegistry.ts`)
  - Dynamic script loading from Fly.io with 3 environment URLs (dev, stg, prod)
  - Fallback URLs if primary fails
  - 8 second timeout for script loading
  - Manages external agent script lifecycle
- **Service**: TriggerCardHandler (repo: smarttrack, path: `client/src/application/TriggerCardHandler.ts`)
  - Chain of Responsibility pattern
  - Handler prefixes: `trigger_card_*`, `trigger_modal_*`, `trigger_smartblock_*`
  - Dispatches to: SmartBlockService, GenericModal, or BuyerAgentApiService
  - Each handler in chain evaluates if it can handle the trigger type
- **Service**: WebSocketService (repo: smarttrack, path: `client/src/application/WebSocketService.ts`)
  - Connects to Socket.IO server
  - Joins room: `SmartTrack__local_{localstorageId}`
  - Filters messages: `sender === 'buyer-agent-backend'` AND `type === 'card'`
  - Room validation: `message.room === currentLocalStorageId`

## Acceptance Criteria

1. GIVEN ClickIntentCollector ativo na pagina
   WHEN usuario clica em botao de adicionar ao carrinho (detectado via pattern matching em atributos, classes, texto)
   THEN evento e emitido com intent type ADD_TO_CART_ATTEMPT, userIntentionAnalysis e confidence score

2. GIVEN BuyerAgentService inicializado com localStorageId
   WHEN ExternalAgentRegistry carrega script do Fly.io (fallback URLs, timeout 8s)
   THEN agente externo e registrado e pronto para receber triggers

3. GIVEN intencao de compra detectada (ex: START_CHECKOUT)
   WHEN BuyerAgentApiService.triggerCard() e chamado
   THEN POST /api/v1/buyer-cards/trigger-socket dispara geracao de card no backend e resposta chega via WebSocket

4. GIVEN WebSocket conectado ao room SmartTrack__local_{localstorageId}
   WHEN mensagem chega com sender=buyer-agent-backend e type=card
   THEN TriggerCardHandler avalia chain of responsibility (trigger_card_* -> trigger_modal_* -> trigger_smartblock_*) e despacha para SmartBlockService, GenericModal ou BuyerAgentApiService

5. GIVEN card exibido para o usuario
   WHEN usuario interage (click, CTA click, open/close chat)
   THEN BuyerAgentEventCollector emite evento correspondente (CARD_CLICK, CARD_CTA_CLICK, OPEN_CHAT_BOX, etc.) via EventPropagationService

6. GIVEN ExternalAgentRegistry tentando carregar script de URL primaria
   WHEN script falha em carregar dentro de 8 segundos
   THEN sistema tenta fallback URLs automaticamente, mantendo funcionalidade do buyer agent

7. GIVEN BuyerAgentService.forceCardDisplay(message) chamado programaticamente
   WHEN mensagem e fornecida
   THEN GenericModal renderiza card imediatamente sem necessidade de trigger via WebSocket

## Required Skills

1. **IntentDetection** - nova
   - Spec: docs/specs/skills/intent_detection.md
   - Classificacao de intencao de compra via pattern matching em elementos DOM

2. **BuyerAgentOrchestration** - nova
   - Spec: docs/specs/skills/buyer_agent_orchestration.md
   - Orquestracao de agente externo com script loading dinamico e chain of responsibility

## Required Agent Capabilities

- **Primary**: `buyer_agent` - capabilities: [intent_detection, card_triggering, websocket_communication, chain_of_responsibility]
- **Secondary**: `tracker_sdk_agent` - capabilities: [event_collection, dom_pattern_matching]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'BuyerAgentService'`
- `category: crm_backend` + `source_file CONTAINS 'BuyerAgentApiService'`
- `category: crm_backend` + `source_file CONTAINS 'BuyerAgentEventCollector'`
- `category: crm_backend` + `source_file CONTAINS 'ClickIntentCollector'`
- `category: crm_backend` + `source_file CONTAINS 'TriggerCardHandler'`
- `category: crm_backend` + `source_file CONTAINS 'ExternalAgentRegistry'`
- `category: usecase` + `domain: tracker`

## Related Use Cases

- **Depends on**: UC-TRK-001 (Coleta de Eventos - EventPropagationService e FingerprintCollector para localstorageId), UC-TRK-002 (SmartModal/Minigames - GenericModal e SmartBlockService reutilizados para exibicao de cards)
- **Enables**: UC-TRK-004 (Rules Engine - intencoes de compra alimentam avaliacao de regras), UC-SEG-001 (Segmentacao - eventos de intencao enriquecem perfil de visitante)
- **Conflicts with**: nenhum

## Implementation Notes

- ClickIntentCollector classifica cliques em 10 tipos de intencao via pattern matching em atributos HTML, CSS classes, texto e URLs
- BuyerAgentService depende de script externo do Fly.io com 3 ambientes (dev, stg, prod)
- ExternalAgentRegistry tem timeout de 8 segundos com fallback automatico para URLs alternativas
- TriggerCardHandler usa Chain of Responsibility: cada handler verifica se o prefixo do trigger corresponde (trigger_card_*, trigger_modal_*, trigger_smartblock_*)
- WebSocket filtra mensagens rigorosamente: sender deve ser 'buyer-agent-backend', type deve ser 'card', e room deve corresponder ao localStorageId atual
- BuyerAgentApiService usa 2 endpoints: POST trigger-socket para disparar e GET {cardId} para buscar
- Os 11 event types do BuyerAgentEventCollector fluem pelo mesmo pipeline de batching (10 eventos, 5s timeout)
- GenericModal e compartilhado entre BuyerAgent e SmartModalService
- forceCardDisplay() permite exibicao programatica sem depender de WebSocket
- Room format segue padrao SmartTrack__local_{localstorageId} consistente com SocketIOService do backend
