# [UC-TRK-001] Coleta de Eventos Client-Side (SDK)

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-TRK-001 |
| **Domain** | tracker |
| **Repos** | smarttrack.userin.ai (branch: pedro-crm) |
| **Priority** | P0-Critical |
| **Complexity** | XL |
| **Status** | Spec |

## Domain Context

SDK JavaScript client-side (`window.__SmartTrack`) que coleta 25+ tipos de eventos de usuario no browser e envia em batch para o backend Express (porta 5002) via REST. O backend persiste em MongoDB, emite via Socket.IO para o servidor externo (socket-stg.userin.ai) e encaminha para Kafka. O SDK inclui subsistema de fingerprinting (audio, canvas, WebGL, fonts, navigator, screen), deteccao de padroes comuns (GTM, Shopify, NextJS, WordPress) e captura automatica de formularios.

### Data Models

- **Entity**: Event (repo: smarttrack, path: `backend/src/domain/entities/`)
  - Fields: `apiKey: string`, `deviceFingerprint: string`, `deviceInfo: object`, `localstorageId: string`, `companyId: string`, `visitorId: string`, `externalUserId: string`, `sessionId: string`, `type: string`, `originalEventType: string`, `referrer: string`, `url: string`, `url_params: object`, `title: string`, `metadata: object`, `userIntentionAnalysis: object`, `confidence: number`, `epoch_time: number`, `receivedAt: Date`, `createdAt: Date`
- **Entity**: Visitor (repo: smarttrack, path: `backend/src/domain/entities/`)
  - Fields: `companyId: string`, `deviceFingerprint: string`, `deviceInfo: object`, `externalId: string`, `metadata: object`, `localstorageId: string`, `externalUserId: string`, `externalUserInfo: object`, `createdAt: Date`
- **Entity**: VisitorContact (repo: smarttrack, path: `backend/src/domain/entities/`)
  - Fields: `companyId: string`, `localstorageId: string`, `deviceFingerprint: string`, `sessionId: string`, `externalUserId: string`, `type: enum(form|whatsapp|phone|email)`, `ticket_number: string`, `formData: object`, `formMetadata: object`, `captureConfig: object`
- **Entity**: ExternalUser (repo: smarttrack, path: `backend/src/domain/entities/`)
  - Fields: `localStorageId: string`, `sessionStorageId: string`, `external_id: string`, `metadata: object`, `companyId: string`

### Services (Client-Side) - Event Collectors

- **Collector**: PageViewCollector (repo: smarttrack, path: `client/src/utils/PageViewCollector.ts`)
  - Tracks page navigation and view events
- **Collector**: ClickCollector (repo: smarttrack, path: `client/src/utils/ClickCollector.ts`)
  - Tracks element clicks with selector, coordinates, text content
- **Collector**: ClickIntentCollector (repo: smarttrack, path: `client/src/utils/ClickIntentCollector.ts`)
  - Detects 10 intent types: ADD_TO_CART_ATTEMPT, START_CHECKOUT, PURCHASE_ATTEMPT, PRODUCT_DETAIL_CLICK, SIGNUP_ATTEMPT, LOGIN_ATTEMPT, SUBSCRIBE_ATTEMPT, CONTACT_ATTEMPT, WHATSAPP_CLICK, DOWNLOAD_ATTEMPT
- **Collector**: ScrollDensityCollector (repo: smarttrack, path: `client/src/utils/ScrollDensityCollector.ts`)
  - Tracks scroll depth and density patterns
- **Collector**: HoverOrFocusFrequencyCollector (repo: smarttrack, path: `client/src/utils/HoverOrFocusFrequencyCollector.ts`)
  - Tracks hover and focus frequency on elements
- **Collector**: ClipboardOrSelectionCollector (repo: smarttrack, path: `client/src/utils/ClipboardOrSelectionCollector.ts`)
  - Tracks clipboard copy/paste and text selection events
- **Collector**: KeyboardUsageCollector (repo: smarttrack, path: `client/src/utils/KeyboardUsageCollector.ts`)
  - Tracks keyboard interaction patterns
- **Collector**: FormInteractionCollector (repo: smarttrack, path: `client/src/utils/FormInteractionCollector.ts`)
  - Tracks form field focus, blur, change, and submit events
- **Collector**: ApiFetchCollector (repo: smarttrack, path: `client/src/utils/ApiFetchCollector.ts`)
  - Intercepts and tracks outgoing API/fetch calls from the page
- **Collector**: CheckoutStartCollector (repo: smarttrack, path: `client/src/utils/CheckoutStartCollector.ts`)
  - Detects checkout flow initiation
- **Collector**: VisibilityChangeCollector (repo: smarttrack, path: `client/src/utils/VisibilityChangeCollector.ts`)
  - Tracks tab visibility changes (focus/blur, hidden/visible)
- **Collector**: ElementViewCollector (repo: smarttrack, path: `client/src/utils/ElementViewCollector.ts`)
  - Tracks element viewport visibility via IntersectionObserver
- **Collector**: PurchaseCompletedCollector (repo: smarttrack, path: `client/src/utils/PurchaseCompletedCollector.ts`)
  - Detects purchase completion events
- **Collector**: RageClickCollector (repo: smarttrack, path: `client/src/utils/RageClickCollector.ts`)
  - Detects rapid repeated clicks (frustration indicator)
- **Collector**: IdleCollector (repo: smarttrack, path: `client/src/utils/IdleCollector.ts`)
  - Detects user idle/inactivity periods
- **Collector**: PageExitCollector (repo: smarttrack, path: `client/src/utils/PageExitCollector.ts`)
  - Tracks beforeunload and page exit events
- **Collector**: OffScreenMouseCollector (repo: smarttrack, path: `client/src/utils/OffScreenMouseCollector.ts`)
  - Detects mouse leaving the viewport (exit intent)
- **Collector**: CustomEventCollector (repo: smarttrack, path: `client/src/utils/CustomEventCollector.ts`)
  - Allows tracking of arbitrary custom events
- **Collector**: BuyerAgentEventCollector (repo: smarttrack, path: `client/src/utils/BuyerAgentEventCollector.ts`)
  - 11 event types for buyer agent interactions (PREVIEW_BOX, OPEN/CLOSE_CHAT_BOX, NEW_CARD, CARD_CLICK, etc.)
- **Collector**: BreadcrumbCollector (repo: smarttrack, path: `client/src/utils/BreadcrumbCollector.ts`)
  - Extracts page breadcrumb navigation data
- **Collector**: FaviconCollector (repo: smarttrack, path: `client/src/utils/FaviconCollector.ts`)
  - Extracts favicon metadata
- **Collector**: InlineDataCollector (repo: smarttrack, path: `client/src/utils/InlineDataCollector.ts`)
  - Extracts inline structured data from page
- **Collector**: JsonLdCollector (repo: smarttrack, path: `client/src/utils/JsonLdCollector.ts`)
  - Extracts JSON-LD structured data
- **Collector**: OgMetadataCollector (repo: smarttrack, path: `client/src/utils/OgMetadataCollector.ts`)
  - Extracts OpenGraph metadata tags
- **Collector**: SeoPatternCollector (repo: smarttrack, path: `client/src/utils/SeoPatternCollector.ts`)
  - Extracts SEO patterns and meta tags
- **Collector**: TrackingPixelCollector (repo: smarttrack, path: `client/src/utils/TrackingPixelCollector.ts`)
  - Detects third-party tracking pixels on page
- **Collector**: TwitterCardCollector (repo: smarttrack, path: `client/src/utils/TwitterCardCollector.ts`)
  - Extracts Twitter Card metadata
- **Collector**: EventContextInjector (repo: smarttrack, path: `client/src/utils/EventContextInjector.ts`)
  - Enriches events with contextual data before propagation

### Services (Client-Side) - Core

- **Service**: EventPropagationService (repo: smarttrack, path: `client/src/utils/EventPropagationService.ts`)
  - Batching: BATCH_SIZE=10 events, BATCH_TIMEOUT=5000ms
  - Sends POST to `{apiBaseUrl}/api` with `x-api-key` header
- **Service**: FingerprintCollector (repo: smarttrack, path: `client/src/utils/fingerprint/`)
  - Methods: `getId()`, `getJson()`, `getApiKey()`
  - Sub-modules: `audio.ts`, `canvas.ts`, `webgl.ts`, `fonts.ts`, `navigator.ts`, `screen.ts`, `document.ts`, `window.ts`
  - Storage: `SmartTrack__visitor_id` key in localStorage + Cookie (365 day TTL)
- **Service**: CommonPatternCollector (repo: smarttrack, path: `client/src/utils/CommonPatternCollector.ts`)
  - Detects: dataLayer, GTM, analytics, Shopify, NextJS, WordPress, user, cart, pageType, insights
- **Service**: StateService (repo: smarttrack, path: `client/src/utils/StateService.ts`)
  - sessionStorage key: `smarttrack_state`
  - Tracks: `visited_url[]` (max 200), `last_url`, `current_url`, `current_utm`

### Services (Client-Side) - Form Capture

- **Config**: FormCaptureConfig
  - `strategy: enum(auto|whitelist|blacklist|disabled)`
  - `include: string[]` (CSS selectors for whitelist)
  - `exclude: string[]` (CSS selectors for blacklist)
  - `trigger: enum(submit|change|blur|manual)`
  - `enableWhatsapp: boolean`

### EventsConfig (SDK Initialization)

- Toggleable collectors: `click`, `submit`, `beforeunload`, `visibilitychange`, `pageshow`, `mouseout`, `scroll`, `customEvents`, `idle`, `rageClick`, `keyboardUsage`, `hoverFrequency`, `clipboardUsage`, `elementView`, `purchaseCompleted`, `checkoutStart`, `clickIntent`, `apiFetch`, `buyerAgent`

### Services (Backend)

- **UseCase**: BulkCreateEventsUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Bulk inserts events to MongoDB
- **UseCase**: BulkEmitEventsUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Forwards events to Socket.IO for real-time distribution
- **UseCase**: SendEventsToKafkaUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Forwards events to Kafka for downstream consumers
- **UseCase**: CreateVisitorUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Creates or updates Visitor records in MongoDB
- **UseCase**: SaveExternalUserContextUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Persists external user context data
- **UseCase**: SaveExternalUserUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Creates or updates ExternalUser records
- **UseCase**: SaveVisitorContactUseCase (repo: smarttrack, path: `backend/src/application/usecases/`)
  - Persists visitor contact form submissions

### Services (Backend) - Socket.IO

- **Service**: SocketIOService (repo: smarttrack, path: `backend/src/infrastructure/`)
  - Connects to external socket server: `socket-stg.userin.ai`
  - Namespace: `tracker` (configurable)
  - Send modes: `room`, `namespace`, `both`
  - Queue: max 1000 events, 50-event batches, 100ms inter-batch delay
  - Room format: `SmartTrack__local_{localstorageId}`
  - Events: `send-message-room`, `send-message-namespace`, `join-user-session`, `join-room`

### Routes/Endpoints

- `POST /api/` -> CollectController.post (JWT via `x-api-key` header + VisitorMiddleware)
- `POST /api/external-user-context` -> ExternalUserContextController.post
- `POST /api/external-users` -> ExternalUserController.post
- `POST /api/visitor-contact` -> VisitorContactController.post
- `GET /api/visitor-contact/ticket/:ticket` -> VisitorContactController.getByTicket
- `POST /api/send-contact-email` -> EmailNotificationController.sendContactNotification
- `GET /api/rules/:id` -> MongoDB rules collection (single rule)
- `GET /api/rules` -> MongoDB rules collection (all rules)

### Frontend Components

- SDK embeddable: exposes `window.__SmartTrack` global with 25+ methods
- Bundled with Rollup (TypeScript source in `client/src/index.ts`)

## Acceptance Criteria

1. GIVEN SDK inicializado em pagina web com apiKey valida
   WHEN o usuario interage com a pagina (click, scroll, form, idle, etc.)
   THEN os 25+ collectors ativos capturam eventos com deviceFingerprint, sessionId, localstorageId e metadata contextual

2. GIVEN eventos acumulados no buffer do EventPropagationService (batch de 10 ou timeout 5000ms)
   WHEN flush e disparado
   THEN eventos sao enviados via POST /api/ com header x-api-key, processados pelo CollectController com JWT validation e VisitorMiddleware

3. GIVEN eventos recebidos pelo backend
   WHEN BulkCreateEventsUseCase executa
   THEN eventos sao persistidos em MongoDB e BulkEmitEventsUseCase encaminha para SocketIOService (room SmartTrack__local_{localstorageId}, batches de 50, 100ms inter-batch)

4. GIVEN FingerprintCollector inicializado
   WHEN getId() e chamado
   THEN fingerprint e gerado via 8 sub-modules (audio, canvas, webgl, fonts, navigator, screen, document, window) e persistido em localStorage + Cookie com TTL de 365 dias sob chave SmartTrack__visitor_id

5. GIVEN CommonPatternCollector ativo na pagina
   WHEN a pagina carrega
   THEN detecta presenca de dataLayer, GTM, analytics, Shopify, NextJS, WordPress, user, cart, pageType e insights para enriquecimento contextual

6. GIVEN FormCaptureConfig com strategy=auto e trigger=submit
   WHEN usuario submete formulario na pagina
   THEN FormInteractionCollector captura formData e formMetadata, VisitorContact e criado via SaveVisitorContactUseCase com tipo form|whatsapp|phone|email

## Required Skills

1. **EventTracking** - nova
   - Spec: docs/specs/skills/event_tracking.md
   - Coleta e processamento de 25+ tipos de eventos client-side com batching e fingerprinting

2. **KafkaOrchestration** - existente
   - Spec: docs/specs/skills/kafka_orchestration.md
   - Encaminhamento de eventos via SendEventsToKafkaUseCase

## Required Agent Capabilities

- **Primary**: `tracker_sdk_agent` - capabilities: [event_collection, fingerprinting, form_capture, pattern_detection]
- **Secondary**: `tracker_backend_agent` - capabilities: [bulk_processing, socketio_forwarding, kafka_forwarding, mongodb_persistence]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'smarttrack'`
- `category: crm_backend` + `source_file CONTAINS 'BulkCreateEventsUseCase'`
- `category: crm_backend` + `source_file CONTAINS 'EventPropagationService'`
- `category: crm_backend` + `source_file CONTAINS 'FingerprintCollector'`
- `category: crm_backend` + `source_file CONTAINS 'CollectController'`
- `category: crm_backend` + `source_file CONTAINS 'SocketIOService'`
- `category: usecase` + `domain: tracker`

## Related Use Cases

- **Depends on**: nenhum (ponto de entrada do modulo tracker)
- **Enables**: UC-TRK-002 (SmartModal/Minigames - eventos disparam regras de exibicao), UC-TRK-003 (Buyer Agent - ClickIntentCollector alimenta deteccao de intencao), UC-TRK-004 (Rules Engine - eventos alimentam SegmentEvaluator), UC-SEG-001 (Segmentacao - eventos alimentam pipeline)
- **Conflicts with**: nenhum

## Implementation Notes

- SDK expoe `window.__SmartTrack` com 25+ metodos, bundled via Rollup a partir de TypeScript
- EventsConfig permite ativar/desativar cada collector individualmente na inicializacao
- EventPropagationService acumula ate 10 eventos ou 5 segundos antes de flush via POST /api/
- Backend roda Express na porta 5002 com MongoDB como store primario
- SocketIOService conecta a socket-stg.userin.ai no namespace `tracker` com queue de 1000 eventos max
- FingerprintCollector usa 8 sub-modules (audio, canvas, webgl, fonts, navigator, screen, document, window)
- CommonPatternCollector detecta automaticamente plataformas (Shopify, GTM, NextJS, WordPress) para enriquecimento
- StateService mantém historico de ate 200 URLs visitadas em sessionStorage
- FormCaptureConfig suporta 4 strategies (auto, whitelist, blacklist, disabled) com 4 triggers (submit, change, blur, manual)
- VisitorMiddleware no backend associa eventos a Visitor existente ou cria novo via CreateVisitorUseCase
