# [UC-TRK-002] Renderizacao SmartModal e Minigames

## Metadata

| Campo | Valor |
|-------|-------|
| **ID** | UC-TRK-002 |
| **Domain** | tracker |
| **Repos** | smarttrack.userin.ai (branch: pedro-crm) |
| **Priority** | P1-High |
| **Complexity** | L |
| **Status** | Spec |

## Domain Context

Sistema de renderizacao de modais inteligentes, minigames gamificados e smart blocks no client-side do SDK SmartTrack. O SmartModalService exibe modais responsivos (image/html) com animacoes e CTA tracking. O MinigameService renderiza jogos interativos (wheel, scratch, slots, quiz, memory, roulette) com ofertas e premios. O SmartBlockService injeta blocos HTML dinamicos em posicoes especificas do DOM com fallback chain. Todos integram com o pipeline de eventos para tracking de impressoes e interacoes.

### Data Models

- **Config**: SmartModalConfig
  - Fields: `id: string`, `name: string`, `type: enum(image|html)`, `status: enum(draft|active|paused|archived)`, `desktop: { imageUrl: string, htmlContent: string, cta: object }`, `mobile: { imageUrl: string, htmlContent: string, cta: object }`, `animation: enum(fade|slide|scale|bounce)`, `closeButton: object`
- **Config**: MinigameConfig
  - Fields: `type: enum(wheel|scratch|slots|quiz|memory|roulette)`, `theme: object`, `assets: object`, `texts: object`, `offers: object[]`, `prizes: object[]`, `settings: object`
- **Config**: SmartBlockConfig
  - Fields: `id: string`, `html: string`, `targetSelector: string`, `insertPosition: enum(append|prepend|replace)`, `duration: number`
- **Enum**: ExhibitionType
  - Values: `CARD`, `MODAL`, `SMARTBLOCK`

### Services (Client-Side)

- **Service**: SmartModalService (repo: smarttrack, path: `client/src/application/SmartModalService.ts`)
  - Methods: `show(modalId)`
  - Fetches config from: `{platformApiUrl}/api/engine/smart-modals/{modalId}`
  - Emitted events: `SMART_MODAL_IMPRESSION`, `SMART_MODAL_CLOSE`, `SMART_MODAL_CTA_CLICK`
  - Supports responsive rendering: separate `desktop` and `mobile` configs
  - Animation types: `fade`, `slide`, `scale`, `bounce`
- **Service**: MinigameService (repo: smarttrack, path: `client/src/application/MinigameService.ts`)
  - Methods: `show(gameId)`
  - Fetches config from: `{platformApiUrl}/api/engine/minigames/{gameId}`
  - Emitted events: `MINIGAME_IMPRESSION`, `MINIGAME_CLOSE`, `MINIGAME_PLAY`, `MINIGAME_RESULT`
  - Game types: `wheel` (fully implemented), `scratch` (placeholder), `slots` (placeholder), `quiz`, `memory`, `roulette`
  - Wheel renderer: full CSS conic-gradient with spin animation
- **Service**: SmartBlockService (repo: smarttrack, path: `client/src/application/SmartBlockService.ts`)
  - Methods: `show(config: SmartBlockConfig)`
  - Exhibition types: CARD, MODAL, SMARTBLOCK
  - DOM injection fallback chain:
    1. `[data-smartblock-container]`
    2. `[data-smarttrack-smartblock]`
    3. `#smartblock-container`
    4. `.smartblock-container`
    5. `document.body`
  - Insert positions: `append`, `prepend`, `replace`
- **Service**: GenericModal (repo: smarttrack, path: `client/src/application/`)
  - Generic modal rendering used by BuyerAgent and other services
- **Legacy**: ModalRoleta (repo: smarttrack, path: `client/src/`)
  - Legacy roulette/wheel modal implementation
- **Legacy**: ModalJogaoCobra (repo: smarttrack, path: `client/src/`)
  - Legacy snake game modal implementation
- **Legacy**: ModalJogaoTigre (repo: smarttrack, path: `client/src/`)
  - Legacy tiger game modal implementation

### Routes/Endpoints (Platform API)

- `GET {platformApiUrl}/api/engine/smart-modals/{modalId}` -> SmartModal config fetch
- `GET {platformApiUrl}/api/engine/minigames/{gameId}` -> Minigame config fetch

## Acceptance Criteria

1. GIVEN SmartModalService inicializado e regra acionada com modalId
   WHEN show(modalId) e chamado
   THEN modal e buscado via GET /api/engine/smart-modals/{modalId}, renderizado com config desktop/mobile conforme viewport, animacao aplicada (fade|slide|scale|bounce) e evento SMART_MODAL_IMPRESSION emitido

2. GIVEN modal renderizado com CTA configurado
   WHEN usuario clica no CTA do modal
   THEN evento SMART_MODAL_CTA_CLICK e emitido com modalId e CTA metadata

3. GIVEN usuario fecha o modal (botao close ou overlay)
   WHEN close e acionado
   THEN evento SMART_MODAL_CLOSE e emitido e modal e removido do DOM

4. GIVEN MinigameService inicializado com gameId do tipo wheel
   WHEN show(gameId) e chamado
   THEN roda da sorte e renderizada com CSS conic-gradient, premios configurados em prizes[], e eventos MINIGAME_IMPRESSION e MINIGAME_PLAY sao emitidos na interacao

5. GIVEN minigame completado pelo usuario
   WHEN resultado e determinado
   THEN evento MINIGAME_RESULT e emitido com tipo do jogo, premio selecionado e metadata da sessao

6. GIVEN SmartBlockConfig com targetSelector e insertPosition
   WHEN SmartBlockService.show() e chamado
   THEN HTML e injetado no DOM usando fallback chain ([data-smartblock-container] -> [data-smarttrack-smartblock] -> #smartblock-container -> .smartblock-container -> document.body) na posicao especificada (append|prepend|replace)

## Required Skills

1. **ModalRendering** - nova
   - Spec: docs/specs/skills/modal_rendering.md
   - Renderizacao responsiva de modais com animacoes CSS e tracking de impressoes/CTA

2. **GameRendering** - nova
   - Spec: docs/specs/skills/game_rendering.md
   - Renderizacao de minigames gamificados (wheel, scratch, slots, quiz, memory, roulette)

## Required Agent Capabilities

- **Primary**: `tracker_frontend_agent` - capabilities: [modal_rendering, dom_injection, css_animation, gamification]
- **Secondary**: `tracker_sdk_agent` - capabilities: [event_emission, config_fetching]

## RAG Chunk References

- `category: crm_backend` + `source_file CONTAINS 'SmartModalService'`
- `category: crm_backend` + `source_file CONTAINS 'MinigameService'`
- `category: crm_backend` + `source_file CONTAINS 'SmartBlockService'`
- `category: crm_backend` + `source_file CONTAINS 'GenericModal'`
- `category: usecase` + `domain: tracker`

## Related Use Cases

- **Depends on**: UC-TRK-001 (Coleta de Eventos - pipeline de eventos para tracking de impressoes), UC-TRK-004 (Rules Engine - regras disparam exibicao de modais e minigames)
- **Enables**: UC-TRK-003 (Buyer Agent - GenericModal reutilizado para exibicao de cards), UC-CAM-002 (Campanhas - modais e minigames como veiculos de campanha)
- **Conflicts with**: nenhum

## Implementation Notes

- SmartModalService busca configuracao via platform API, nao do backend tracker diretamente
- Modais suportam 2 tipos: `image` (URL de imagem) e `html` (conteudo HTML arbitrario)
- Cada modal tem config separada para desktop e mobile (responsive)
- 4 tipos de animacao suportados: fade, slide, scale, bounce
- Status do modal (draft, active, paused, archived) controla se e elegivel para exibicao
- MinigameService tem renderer completo apenas para Wheel (CSS conic-gradient + spin animation)
- Scratch e Slots sao placeholders aguardando implementacao completa
- Quiz, Memory e Roulette sao tipos adicionais no enum
- SmartBlockService usa ExhibitionType para diferenciar CARD, MODAL e SMARTBLOCK
- Fallback chain garante que smart blocks sao injetados mesmo sem container dedicado
- Legacy modals (ModalRoleta, ModalJogaoCobra, ModalJogaoTigre) coexistem com novos services
- Todos os eventos de impressao/interacao fluem pelo EventPropagationService (batch de 10, timeout 5s)
