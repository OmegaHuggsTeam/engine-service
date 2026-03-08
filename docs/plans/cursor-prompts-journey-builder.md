# Cursor Prompts — Journey Builder Ecosystem

> Cole cada prompt no Cursor Composer (Cmd+I) na raiz do engine-service.
> Ordem recomendada: #10 → #11 → #12 → #13 → #14 → #15 → #16 → #17
> Paralelizaveis: (#10 + #12 + #16) podem rodar juntos.

---

## Issue #10 — UC-ES-001: ContainerOrchestrator (Docker SDK)

```
Crie o modulo ContainerOrchestrator com Docker SDK no engine-service.

CONTEXTO:
- Projeto Python FastAPI em src/neural_link/
- Sovereign Gateway roda na porta 8766
- Endpoints existentes em src/neural_link/api/sovereign_gateway.py
- Padrao: Pydantic v2 models, try/except com logger.warning, _ws_manager.broadcast()

CRIAR ESTES ARQUIVOS:

1. src/neural_link/containers/__init__.py
   Exporta: ContainerOrchestrator, ContainerConfig, ContainerInfo, ContainerMetrics, ContainerExecResult

2. src/neural_link/containers/models.py
   Pydantic models:
   - ContainerConfig: image(str), tenant_id(str), node_id(str), journey_id(str|None), memory_limit_mb(int=128), cpu_period(int=100000), cpu_quota(int=50000), env(dict[str,str]), timeout_seconds(int=30)
   - ContainerInfo: container_id(str), node_id(str), tenant_id(str), image(str), status(str), started_at(str|None)
   - ContainerMetrics: container_id(str), status(str), memory_mb(float), cpu_percent(float), started_at(str|None), finished_at(str|None), exit_code(int|None), logs(str)
   - ContainerExecResult: container_id(str), exit_code(int), stdout(str), stderr(str), duration_ms(float)

3. src/neural_link/containers/orchestrator.py
   Classe ContainerOrchestrator com lazy docker.from_env():
   - spawn(config: ContainerConfig) -> ContainerInfo — containers.run(detach=True, labels com huggsai.tenant_id/node_id/journey_id, mem_limit, cpu_period/quota)
   - get_status(container_id) -> ContainerMetrics — stats(stream=False), calcula mem_mb e cpu_pct
   - stop(container_id) -> None — container.stop(timeout=5) + remove(force=True)
   - exec_in_container(container_id, cmd) -> ContainerExecResult — exec_run com demux=True, mede duration_ms
   - get_logs(container_id, tail=100) -> str
   - list_by_tenant(tenant_id) -> list[ContainerInfo] — filtra por label huggsai.tenant_id
   - cleanup_journey(journey_id) -> int — lista por label journey_id, stop+remove cada, retorna count
   Labels usam prefixo "huggsai" (ex: huggsai.tenant_id, huggsai.node_id)

4. src/neural_link/tests/test_container_orchestrator.py
   4 testes com unittest.mock (patch docker.from_env):
   - test_spawn_container_returns_id
   - test_get_status_returns_metrics
   - test_stop_and_remove
   - test_list_containers_by_tenant

5. MODIFICAR src/neural_link/api/sovereign_gateway.py — adicionar endpoints:
   Pydantic request/response models: ContainerSpawnRequest, ContainerSpawnResponse, ContainerStatusResponse, ContainerListResponse

   Endpoints:
   - POST /api/v1/containers/spawn — spawna container, broadcast "container_spawned" no WS journey-events
   - GET /api/v1/containers/{container_id}/status — retorna status + logs (tail=50)
   - GET /api/v1/containers — lista containers (query param tenant_id)
   - DELETE /api/v1/containers/{container_id} — stop + remove, broadcast "container_stopped"

   Padrao: usa _svc.container_orch (lazy init se None), try/except com logger.warning, HTTPException

6. src/neural_link/tests/test_container_endpoints.py
   4 testes com TestClient do FastAPI + patch _svc

7. Adicionar "docker>=7.0.0" ao requirements.txt

Roda: python -m pytest src/neural_link/tests/test_container_orchestrator.py src/neural_link/tests/test_container_endpoints.py -v
```

---

## Issue #11 — UC-ES-002: JourneyExecutor (DAG Walker)

```
Crie o JourneyExecutor que executa jornadas como DAGs spawnando containers Docker.

CONTEXTO:
- ContainerOrchestrator ja existe em src/neural_link/containers/orchestrator.py
- Sovereign Gateway em src/neural_link/api/sovereign_gateway.py
- WebSocket broadcast: _ws_manager.broadcast("journey-events", data)
- Padrao: Pydantic v2, async/await, logger.warning

CRIAR ESTES ARQUIVOS:

1. src/neural_link/containers/journey_models.py
   Pydantic models:
   - DAGNode: id(str), type(str), subtype(str), config(dict[str,Any]), label(str="")
   - DAGEdge: source(str), target(str), label(str="")
   - JourneyDAG: journey_id(str), tenant_id(str), nodes(list[DAGNode]), edges(list[DAGEdge])
   - NodeResult: node_id(str), status(str), container_id(str|None), latency_ms(float), output(dict), error(str)
   - JourneyExecutionResult: journey_id(str), tenant_id(str), status(str), node_results(list[NodeResult]), total_latency_ms(float), total_cost(float), containers_spawned(int)

2. src/neural_link/containers/journey_executor.py

   Constante NODE_IMAGES: dict mapeando 20 subtypes para Docker images:
   trigger_manual/event/segment/schedule -> huggsai/trigger:latest
   condition_if/split -> huggsai/condition:latest
   action_sms -> huggsai/action-sms:latest
   action_email -> huggsai/action-email:latest
   action_whatsapp -> huggsai/action-wa:latest
   action_webhook -> huggsai/action-webhook:latest
   action_tag/action_score -> huggsai/action-crm:latest
   control_loop -> huggsai/control:latest
   int_sendspeed -> huggsai/int-sendspeed:latest
   int_meta -> huggsai/int-meta:latest
   int_ga -> huggsai/int-ga:latest
   track_pageview/click/conversion -> huggsai/tracker:latest

   NATIVE_NODES = {"control_end", "control_wait"} — sem container

   Classe JourneyExecutor(__init__(self, orchestrator, broadcast_fn)):

   - topological_sort(dag) -> list[str] — Kahn's algorithm (defaultdict + deque)

   - async execute_node(node, journey_id, tenant_id, context) -> dict:
     Se NATIVE_NODES: control_wait faz asyncio.sleep(seconds), control_end retorna success
     Se container: spawn com env NODE_TYPE/NODE_SUBTYPE/NODE_CONFIG/JOURNEY_ID/TENANT_ID,
     broadcast node_started, poll status ate exited/dead (0.5s intervals, timeout_seconds),
     exec "cat /tmp/result.json", stop container, broadcast node_completed

   - async execute_journey(dag) -> JourneyExecutionResult:
     topological_sort, iterate order, execute_node cada,
     broadcast journey_started no inicio, journey_completed no fim,
     fail-fast (para no primeiro failure),
     coleta containers_spawned, total_latency_ms

3. Atualizar src/neural_link/containers/__init__.py com novos exports

4. src/neural_link/tests/test_journey_executor.py
   4 testes:
   - test_parse_dag_nodes (topological sort: trigger first)
   - test_execute_node_spawns_container (mock orch, valida spawn+exec+stop)
   - test_control_end_skips_container (sem container)
   - test_control_wait_delays (asyncio.sleep)

5. MODIFICAR src/neural_link/api/sovereign_gateway.py — adicionar endpoints:

   Pydantic models: JourneyExecuteRequest, JourneyGenerateRequest, JourneySuggestRequest

   Endpoints:
   - POST /api/v1/journeys/execute — recebe {journey_id, tenant_id, nodes[], edges[]}, instancia JourneyExecutor com _svc.container_orch e broadcast fn, executa, retorna result.model_dump()
   - POST /api/v1/journeys/generate — recebe {prompt, tenant_id, constraints}, usa _svc.interface.process_query com prompt enhanced pedindo DAG JSON
   - POST /api/v1/journeys/suggest — recebe {current_dag, selected_node_id, tenant_id}, usa _svc.interface.process_query pedindo 3 sugestoes JSON

6. src/neural_link/tests/test_journey_endpoints.py
   2 testes: execute_journey (mock executor), generate_journey (mock interface)

Roda: python -m pytest src/neural_link/tests/test_journey_executor.py src/neural_link/tests/test_journey_endpoints.py -v
```

---

## Issue #12 — UC-ES-003: Canvas Components (Types + Hooks + NodeSandbox + AnimatedEdge)

```
Crie os tipos TypeScript, hooks, e componentes base do Journey Builder canvas.

CONTEXTO:
- Frontend Next.js 16 em frontend/src/
- @xyflow/react v12 ja instalado (import de "@xyflow/react")
- SWR para data fetching (nao Zustand, nao React Query)
- Framer Motion para animacoes
- CSS custom properties em globals.css: --color-primary:#e94560, --color-accent:#448aff, --color-success:#00e676, --color-warning:#ffab00, --color-error:#ff1744, --color-bg:#0e1117, --color-surface:#1a1a2e, --color-surface-alt:#16213e, --color-text:#ffffff, --color-text-secondary:#a0a0b0, --color-text-muted:#606070, --color-border:#606070
- Fontes: Inter (body) + JetBrains Mono (mono)
- Padrao de hooks SWR: ver frontend/src/modules/crm/hooks/useCrmApi.ts
- Padrao WebSocket: ver frontend/src/modules/crm/hooks/useCrmWebSocket.ts (exponential backoff)
- API client: frontend/src/lib/gateway.ts (BASE = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8766")
- Padrao de custom node React Flow: ver frontend/src/modules/crm/FlowCanvas.tsx

CRIAR ESTES ARQUIVOS:

1. frontend/src/types/journey.ts

   Types: NodeType (6 tipos), NodeSubtype (20 subtypes), NodeStatus (6 estados)

   Interfaces:
   - NodeSandboxData: type, subtype, label, config, tenantId, containerId?, status, metrics?, testCode?
   - JourneyDAG: journeyId, tenantId, nodes[], edges[]
   - NodeResult: nodeId, status, containerId?, latencyMs, output?, error?
   - JourneyExecutionResult: journeyId, tenantId, status, nodeResults[], totalLatencyMs, totalCost, containersSpawned
   - JourneyEvent: type (journey_started|node_started|node_completed|journey_completed|container_spawned|container_stopped), journeyId?, nodeId?, containerId?, status?, latencyMs?
   - TenantConfig: tenantId, name, plan (starter|pro|enterprise), sla {maxLatencyMs, maxContainers, containerMemoryMb}, branding {primaryColor, logo}, allowedNodeTypes[], integrations[]
   - ContainerStatus: containerId, status, memoryMb, cpuPercent, logs

   Constantes exportadas:
   - NODE_ICONS: Record<NodeSubtype, string> — Lucide icon names (Play, Zap, Users, Clock, GitBranch, Split, MessageSquare, Mail, MessageCircle, Globe, Tag, TrendingUp, Timer, Square, RefreshCw, Send, Facebook, BarChart3, Eye, MousePointer, Target)
   - NODE_CATEGORIES: Record<string, {label, subtypes[]}> — 6 categorias com labels PT-BR (Gatilhos, Condicoes, Acoes, Controle, Integracoes, Rastreamento)
   - SUBTYPE_LABELS: Record<NodeSubtype, string> — labels PT-BR (Manual, Evento, Segmento, Agendado, Condicional, Split A/B, SMS, Email, WhatsApp, Webhook, Tag, Score, Esperar, Finalizar, Loop, SendSpeed, Meta, Analytics, PageView, Click, Conversao)

2. MODIFICAR frontend/src/lib/gateway.ts — adicionar funcoes (append no final):
   - executeJourney(dag) — POST BASE/api/v1/journeys/execute (converte camelCase para snake_case: journey_id, tenant_id)
   - generateJourney(prompt, tenantId, constraints?) — POST BASE/api/v1/journeys/generate
   - suggestNextNode(currentDag, selectedNodeId, tenantId) — POST BASE/api/v1/journeys/suggest
   - fetchContainerStatus(containerId) — GET BASE/api/v1/containers/{id}/status
   - fetchContainers(tenantId) — GET BASE/api/v1/containers?tenant_id={id}

3. frontend/src/modules/journey/hooks/useJourneyApi.ts
   SWR hooks (mesma pattern de useCrmApi.ts):
   - useContainers(tenantId) — refreshInterval: 5000
   - useContainerStatus(containerId | null) — refreshInterval: 2000
   - usePipelineStats() — refreshInterval: 15000
   - useKpiCostQuality() — refreshInterval: 30000
   - useKpiTrends() — refreshInterval: 60000
   - useKpiAnomalies() — refreshInterval: 30000
   - useKpiHeatmap() — refreshInterval: 60000
   - useClusterHealth() — refreshInterval: 10000

4. frontend/src/modules/journey/hooks/useJourneyWebSocket.ts
   COPIAR A PATTERN de useCrmWebSocket.ts mas conectar a ws://localhost:8766/api/v1/ws/journey-events
   Exponential backoff (min 1s, max 30s)
   Retorna: { events: JourneyEvent[], connected: boolean, clearEvents: () => void }
   Buffer maximo 200 eventos

5. frontend/src/modules/journey/NodeSandbox.tsx
   "use client", memo, React Flow custom node
   Props via NodeProps com data: NodeSandboxData

   Renderiza:
   - Handle target (top)
   - Div com border color = STATUS_COLORS[status] (idle:#606070, provisioning:#448aff, running:#448aff, success:#00e676, failure:#ff1744, timeout:#ffab00)
   - Status dot (pulsante via framer-motion quando provisioning/running/failure)
   - Label (SUBTYPE_LABELS[subtype] ou data.label)
   - Type em texto muted
   - Mini-metricas: latencyMs em ms, cor por faixa SLA (verde <500, amarelo 500-1000, vermelho >1000), font mono
   - ContainerId badge (primeiros 12 chars, font mono, muted)
   - Handle source (bottom)
   - Se type === "condition": Handle extra position Right id="false" com cor error
   - motion.div com initial scale:0.8 opacity:0, animate scale:1 opacity:1
   - Background: var(--color-surface), borderRadius: 12, padding: 12px 16px, minWidth: 160
   - boxShadow: selected ? glow : subtle

6. frontend/src/modules/journey/AnimatedEdge.tsx
   "use client", memo, React Flow custom edge
   Data: { status: 'idle'|'running'|'success'|'failure', latencyMs?: number, slaMaxMs?: number }

   - BaseEdge com getBezierPath
   - Cor: idle=#606070, failure=#ff1744, running=#448aff, success por SLA (<500ms verde, 500-1000 amarelo, >1000 vermelho)
   - strokeDasharray: idle="8 4", outros="none"
   - filter: running = drop-shadow glow
   - SVG circle com animateMotion no path quando running (dur="1.5s" repeatCount="indefinite")
   - foreignObject no labelX,labelY com latencyMs quando success (background semi-transparente, font mono, 10px)

Nao instalar nenhum pacote novo — tudo ja existe no package.json.
```

---

## Issue #13 — UC-ES-004: JourneyBuilder Page (Canvas + Toolbar + Palette + Debug)

```
Crie a pagina principal do Journey Builder com canvas, toolbar, palette e debug panel.

CONTEXTO:
- Componentes base ja existem: NodeSandbox.tsx, AnimatedEdge.tsx em frontend/src/modules/journey/
- Types em frontend/src/types/journey.ts
- Hooks em frontend/src/modules/journey/hooks/
- Gateway functions em frontend/src/lib/gateway.ts
- Pagina atual em frontend/src/app/dashboard/jornadas/page.tsx renderiza o JourneyCanvas ANTIGO de sovereign/
- Dynamic import pattern: ver frontend/src/modules/crm/CrmDashboard.tsx (dynamic(() => import(...), { ssr: false }))
- Layout tabs em frontend/src/app/dashboard/layout.tsx (array TABS)
- proOptions={{ hideAttribution: true }}, colorMode="dark" (padrao dos 2 canvas existentes)
- Background, Controls, MiniMap de "@xyflow/react"
- Framer Motion para animacoes (motion.div, AnimatePresence)
- Nao usa Zustand — usa useState + useRef para state local, SWR para server state, useNodesState/useEdgesState do React Flow

CRIAR ESTES ARQUIVOS:

1. frontend/src/modules/journey/NodePalette.tsx
   "use client", sidebar esquerda, width: 220px

   - Header "Componentes" (uppercase, letter-spacing, muted)
   - 6 categorias de NODE_CATEGORIES expandiveis (um de cada vez)
   - Cada categoria: botao com label + seta (expanded: down, collapsed: right)
   - AnimatePresence + motion.div height auto para expand/collapse
   - Cada subtype dentro da categoria: div draggable
   - onDragStart seta dataTransfer: "application/reactflow-subtype" e "application/reactflow-type"
   - effectAllowed = "move"
   - Hover: background var(--color-surface-alt)
   - Label: SUBTYPE_LABELS[subtype]
   - Props: onDragStart callback
   - Default expanded: "trigger"

2. frontend/src/modules/journey/DebugPanel.tsx
   "use client", painel inferior absolute bottom:0 left:0 right:0

   - Botao toggle collapse/expand (seta up/down)
   - Header: "Debug: {nodeId} ({containerId primeiros 12 chars})"
   - 3 tabs: logs, metrics, test
   - Tab logs: <pre> com status.logs ou "No logs available..."
   - Tab metrics: Status, Memory MB, CPU % — dados de useContainerStatus(containerId)
   - Tab test: <pre> com testCode ou "// No test code defined"
   - Height quando expandido: 200px, overflowY: auto
   - Background: var(--color-surface), border-top
   - Se nodeId null: retorna null (nao renderiza)
   - Font mono para logs e test

3. frontend/src/modules/journey/JourneyBuilder.tsx
   "use client", componente principal que integra TUDO

   STATE:
   - useNodesState, useEdgesState do React Flow
   - selectedNode (string | null)
   - journeyStatus ('idle'|'running'|'completed'|'failed')
   - journeyName (string, default "Nova Jornada")
   - tenantId (string, default "default-tenant")
   - useJourneyWebSocket() para eventos real-time

   LAYOUT (flex, height 100%):
   - NodePalette (esquerda, 220px)
   - Area principal (flex: 1, position relative):
     - Toolbar (absolute top, z-index 10, backdrop-filter blur):
       - Input nome editavel (transparente, bold, 16px)
       - StatusBadge (pill com cor por status)
       - Spacer
       - Run button (verde, disabled quando running ou 0 nos, framer-motion whileHover/whileTap)
     - ReactFlow (nodeTypes={sandbox: NodeSandbox}, edgeTypes={animated: AnimatedEdge}):
       - onConnect: addEdge com type "animated" e data {status: "idle"}
       - onDrop: le dataTransfer subtype+type, cria node sandbox na posicao do mouse
       - onDragOver: preventDefault, dropEffect="move"
       - onNodeClick: seta selectedNode
       - proOptions={{ hideAttribution: true }}, colorMode="dark"
       - Background gap=20 size=1 color="#ffffff08"
       - Controls position="bottom-right"
       - MiniMap com nodeColor por status (success=verde, failure=vermelho, running=azul, default=cinza)
     - DebugPanel (bottom, dados do selectedNode)

   WEBSOCKET EVENT HANDLING:
   - node_started: atualiza node status para "running", seta containerId, edge para "running"
   - node_completed: atualiza node status (success/failure), seta metrics, edge para success/failure com latencyMs
   - journey_completed: atualiza journeyStatus
   Usar useRef para lastProcessed index (evitar re-processar eventos)

   RUN HANDLER:
   - Reseta todos os nodes para idle, edges para idle
   - Serializa nodes/edges para DAG format (snake_case)
   - Chama executeJourney() do gateway.ts
   - Seta journeyStatus para "running"
   - Catch error: seta journeyStatus "failed"

   NODE ID GENERATOR: let counter, nextId() retorna "node-{++counter}"

4. MODIFICAR frontend/src/app/dashboard/jornadas/page.tsx
   Substituir import do JourneyCanvas ANTIGO por:
   ```
   import dynamic from "next/dynamic";
   const JourneyBuilder = dynamic(() => import("@/modules/journey/JourneyBuilder"), { ssr: false });
   export default function JornadasPage() {
     return <div style={{ height: "calc(100vh - 120px)" }}><JourneyBuilder /></div>;
   }
   ```

Nao modificar o layout.tsx — a tab "Jornadas" ja aponta para /dashboard/jornadas.
```

---

## Issue #14 — UC-ES-005: AI Copilot Sidebar

```
Crie o CopilotSidebar e integre no JourneyBuilder.

CONTEXTO:
- JourneyBuilder.tsx ja existe em frontend/src/modules/journey/
- Gateway functions: generateJourney(), suggestNextNode() ja existem em lib/gateway.ts
- Framer Motion para animacoes (AnimatePresence, motion.div)
- Nao usa @ai-sdk/react aqui — usa fetch direto via gateway functions
- CSS custom properties para cores

CRIAR:

1. frontend/src/modules/journey/CopilotSidebar.tsx
   "use client", sidebar direita, AnimatePresence com width 0→320px

   Props: open, onClose, tenantId, currentDag, selectedNodeId, onDAGGenerated callback

   HEADER: "AI Copilot" + botao X para fechar

   3 TABS: Gerar | Sugerir | Chat

   Tab "Gerar":
   - Texto instrucao: "Descreva a jornada em linguagem natural"
   - Textarea (min-height 80, bg var(--color-bg), border, font inherit)
   - Botao "Gerar Jornada" (accent, disabled quando loading ou vazio)
   - Chama generateJourney(prompt, tenantId) do gateway
   - onDAGGenerated(result.dag) para renderizar no canvas
   - Adiciona mensagens ao historico local

   Tab "Sugerir":
   - Se nao tem selectedNodeId: "Selecione um no no canvas"
   - Ao ativar tab: chama suggestNextNode(currentDag, selectedNodeId, tenantId)
   - Renderiza sugestoes como cards (subtype, label, reason)
   - Background var(--color-surface-alt), border-radius 8

   Tab "Chat":
   - Historico de mensagens (user=accent bg, assistant=surface-alt bg)
   - Simples display — sem input por enquanto (futuro: conectar ao OrchestratorChat)

   Loading state: botoes disabled, texto "Gerando..."/"Buscando..."

2. MODIFICAR frontend/src/modules/journey/JourneyBuilder.tsx
   Adicionar:
   - State: copilotOpen (boolean, default false)
   - Na toolbar: botao toggle copilot (icone sparkle/brain, antes do Run button)
   - Apos a div do canvas: <CopilotSidebar open={copilotOpen} onClose={...} tenantId={...} currentDag={serializacao dos nodes/edges} selectedNodeId={selectedNode} onDAGGenerated={handler que adiciona nodes/edges ao canvas} />
   - Handler onDAGGenerated: recebe {nodes, edges}, converte para React Flow format, setNodes/setEdges
```

---

## Issue #15 — UC-ES-006: Journey KPI Dashboard

```
Crie o JourneyKPI dashboard e integre como tab no JourneyBuilder.

CONTEXTO:
- Hooks SWR ja existem em frontend/src/modules/journey/hooks/useJourneyApi.ts
- Endpoints EXISTENTES no gateway (nao precisa criar nenhum novo):
  GET /api/v1/kpi/cost-quality, /kpi/trends, /kpi/anomalies, /kpi/agents/heatmap, /pipeline/stats, /cluster/health
- CSS custom properties para cores
- Sem biblioteca de charts — fazer visualizacoes com divs estilizados (progress bars, cards)
- Pattern de cards: ver frontend/src/components/PipelineStats.tsx

CRIAR:

1. frontend/src/modules/journey/JourneyKPI.tsx
   "use client", consome hooks existentes

   LAYOUT:

   KPI CARDS (grid 4 colunas, gap 12):
   - Cost/Exec: costQuality?.avg_cost formatado como $X.XXXX, cor accent
   - Avg SLA: pipeline?.avg_latency em ms, cor success
   - Success Rate: pipeline?.success_rate * 100 em %, cor success
   - Active Containers: health?.services?.length, cor warning
   Card style: surface bg, border, border-radius 12, padding 16
   Label: 11px muted, Value: 24px bold colored

   PIPELINE FUNNEL (surface card, margin-bottom 12):
   - Titulo "Pipeline Funnel" (13px bold)
   - 4 linhas: L0 Cache, L1 Triage, L2 RAG, L3 LLM
   - Cada linha: label (80px) + progress bar (flex 1, height 8, accent fill) + percentual (30px)
   - Se pipeline data disponivel, usa valores reais; senao placeholder [45, 30, 20, 5]%

   ANOMALY ALERTS (surface card com border error translucido):
   - So aparece se anomalies array tem itens
   - Titulo "Anomalies" (13px bold, cor error)
   - Lista primeiros 5 itens, fontSize 11

   Se dados nao carregaram: mostra "—" nos cards

2. MODIFICAR frontend/src/modules/journey/JourneyBuilder.tsx
   Adicionar tab switching no toolbar:
   - State: activeTab ('canvas' | 'kpi'), default 'canvas'
   - No toolbar, apos o nome: dois botoes tab "Canvas" e "KPI"
   - Tab ativa: accent color + surface-alt bg; inativa: text-muted
   - Quando activeTab === 'canvas': renderiza ReactFlow + DebugPanel
   - Quando activeTab === 'kpi': renderiza <JourneyKPI /> (importar com dynamic ssr:false se necessario)
   - NodePalette e CopilotSidebar ficam visiveis em ambas as tabs
```

---

## Issue #16 — INFRA-ES-001: Sandbox Container Images

```
Crie os Dockerfiles minimos para os containers sandbox do Journey Builder.

CONTEXTO:
- Infra Docker em infra/ no engine-service
- Containers sao minimos (Alpine), executam logica simples e escrevem resultado em /tmp/result.json
- JourneyExecutor faz "cat /tmp/result.json" para ler o resultado
- Env vars disponiveis: NODE_TYPE, NODE_SUBTYPE, NODE_CONFIG, JOURNEY_ID, TENANT_ID

CRIAR ESTA ESTRUTURA:

infra/containers/
  trigger/
    Dockerfile
    run.sh
  condition/
    Dockerfile
    run.sh
  action-crm/
    Dockerfile
    run.sh

1. infra/containers/trigger/Dockerfile
   FROM alpine:3.19
   RUN apk add --no-cache jq
   COPY run.sh /run.sh
   RUN chmod +x /run.sh
   CMD ["/run.sh"]

2. infra/containers/trigger/run.sh (#!/bin/sh)
   Escreve JSON em /tmp/result.json:
   {"result": true, "type": "trigger", "subtype": "$NODE_SUBTYPE", "timestamp": "$(date -Iseconds)"}
   sleep 0.1

3. infra/containers/condition/Dockerfile
   Mesmo padrao (alpine + jq)

4. infra/containers/condition/run.sh (#!/bin/sh)
   Avalia NODE_CONFIG: se contem "true" → result=true, senao result=false
   Escreve: {"result": $RESULT, "type": "condition", "evaluated": "$NODE_CONFIG"}
   sleep 0.05

5. infra/containers/action-crm/Dockerfile
   Mesmo padrao (alpine + jq + curl)

6. infra/containers/action-crm/run.sh (#!/bin/sh)
   Escreve: {"result": true, "type": "action", "subtype": "$NODE_SUBTYPE", "action": "completed"}
   sleep 0.2

7. Criar infra/containers/build-all.sh (#!/bin/bash):
   cd "$(dirname "$0")"
   docker build -t huggsai/trigger:latest trigger/
   docker build -t huggsai/condition:latest condition/
   docker build -t huggsai/action-crm:latest action-crm/
   echo "All sandbox images built."

IMPORTANTE: todos os run.sh devem ter line endings LF (nao CRLF) e permissao +x.
```

---

## Issue #17 — UC-ES-007: E2E Smoke Test

```
Crie o script de teste E2E que valida o Journey Builder ponta a ponta.

CONTEXTO:
- Gateway na porta 8766 com endpoints: /cluster/health, /journeys/execute
- Container images: huggsai/trigger:latest, huggsai/condition:latest, huggsai/action-crm:latest
- Python, usa httpx async

CRIAR:

1. tools/e2e_journey_test.py

   Docstring: E2E Smoke Test para Journey Builder. Requer Gateway rodando + Docker disponivel + images built.
   Executar: python tools/e2e_journey_test.py

   BASE = "http://localhost:8766/api/v1"

   DAG de teste (4 nos, 3 edges):
   n1: trigger/trigger_manual
   n2: condition/condition_if (config: field=tag, value=vip)
   n3: action/action_tag (config: tag=premium)
   n4: control/control_end
   Edges: n1→n2, n2→n3 (label "true"), n2→n4 (label "false")

   async def main() com httpx.AsyncClient(timeout=60):

   [1/3] Health check:
   - GET /cluster/health → assert 200
   - Print summary

   [2/3] Execute journey:
   - POST /journeys/execute com DAG → assert 200
   - Print: status, total_latency_ms, containers_spawned
   - Para cada node_result: print [+] ou [x] com node_id, status, latency_ms

   [3/3] Verification:
   - all node_results success? → "E2E SMOKE TEST PASSED" exit 0
   - senao → "E2E SMOKE TEST FAILED" exit 1

   if __name__ == "__main__": sys.exit(asyncio.run(main()))

2. Adicionar httpx ao requirements.txt se nao existir.

Formato do output:
[1/3] Checking gateway health...
  OK — healthy
[2/3] Executing journey DAG...
  Status: completed
  Total latency: 420ms
  Containers spawned: 3
  [+] n1: success (50ms)
  [+] n2: success (80ms)
  [+] n3: success (320ms)
  [+] n4: success (1ms)
[3/3] Verification...

  E2E SMOKE TEST PASSED
```
