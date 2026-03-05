# CRM Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | CrmAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.api.sovereign_gateway` (endpoints) + `src.neural_link.orchestrator.task_executor` (hook) |
| **Criado em** | 2026-03-03 |
| **Ultima Atualizacao** | 2026-03-03 |

---

## Funcao Core

O CRM Agent gerencia o ciclo de vida de leads, flows e interacoes dentro do grafo Neo4j. Ele atua como camada de dominio entre o frontend (Next.js) e o grafo de conhecimento, expondo operacoes CRUD via REST e eventos em tempo real via WebSocket.

### Responsabilidades Primarias
- **Lead Management**: CRUD de leads no grafo Neo4j com trust scoring, tags e source tracking
- **Flow Orchestration**: Criacao e gerenciamento de flows (campanhas/funnels) com vinculacao de leads
- **Interaction Recording**: Registro automatico e manual de interacoes lead-agente com incremento de counters
- **Graph Visualization**: Fornecimento de subgrafos CRM otimizados para renderizacao D3/React Flow
- **Real-time Broadcasting**: Emissao de eventos CRM via WebSocket para atualizacao instantanea do frontend

### Responsabilidades Secundarias
- Fulltext search de leads (nome, email, empresa)
- Trust score updates e decaimento
- Integracao com n8n: ativacao automatica de flows apos deploy de workflows
- Alimentacao do TelemetryHub via CrmEventProvider

---

## Skills Necessarias

### Skills Obrigatorias
1. **LeadScoring**
   - Descricao: Calcula e atualiza trust score (0-1) baseado em interacoes, fonte e comportamento
   - Prioridade: Alta
   - Status: Implementada (basico), evolucao planejada
   - Spec: [docs/specs/skills/lead_scoring.md](../skills/lead_scoring.md)

2. **GraphCRUD**
   - Descricao: Operacoes MERGE-based idemopotentes em nodes Lead, Flow, Interaction
   - Prioridade: Alta
   - Status: Implementada

3. **EventBroadcast**
   - Descricao: Emissao de CrmEvent via WebSocket e TelemetryHub simultaneamente
   - Prioridade: Alta
   - Status: Implementada

### Skills Opcionais
1. **SocialAnalysis**
   - Descricao: Analise de rede social do lead (conexoes, influencia, comunidades)
   - Prioridade: Media
   - Status: Especificada
   - Spec: [docs/specs/skills/social_analysis.md](../skills/social_analysis.md)

2. **RAGEnrichment**
   - Descricao: Enriquecimento de leads com contexto RAG (rag_context_id)
   - Prioridade: Media
   - Status: Pendente

---

## Input / Output

### Input Esperado

```python
# Criacao de Lead (via REST)
{
    "name": "Alice Santos",
    "email": "alice@empresa.com",
    "company": "Acme Corp",
    "source_channel": "telegram",  # telegram | email | n8n | manual | webhook
    "tags": ["enterprise", "decision-maker"]
}

# Criacao de Flow
{
    "name": "Onboarding Q2",
    "objective": "Converter leads enterprise em 30 dias",
    "n8n_workflow_id": "wf_abc123"
}

# Registro de Interacao
{
    "lead_id": "lead_abc123",
    "agent_id": "marketing_agent",
    "channel": "telegram",
    "action": "outreach",
    "detail": "Enviada proposta comercial via DM"
}

# Via TaskExecutor (automatico)
Task(
    description="Analisar perfil do lead",
    input_data={"lead_id": "lead_abc123"},  # trigger CRM hook
    type=TaskType.ANALYSIS
)
```

### Output Esperado

```python
# Lead Response
{
    "id": "lead_a1b2c3d4e5f6",
    "name": "Alice Santos",
    "email": "alice@empresa.com",
    "company": "Acme Corp",
    "trust": 0.5,
    "interaction_count": 0,
    "source_channel": "telegram",
    "tags": ["enterprise", "decision-maker"],
    "created_at": "2026-03-03T10:00:00",
    "updated_at": "2026-03-03T10:00:00"
}

# CRM Graph (para D3 visualization)
{
    "nodes": [
        {"id": "lead_abc", "labels": ["Lead"], "properties": {"name": "Alice", "trust": 0.8}},
        {"id": "flow_xyz", "labels": ["Flow"], "properties": {"name": "Onboarding Q2"}}
    ],
    "edges": [
        {"source": "lead_abc", "target": "flow_xyz", "type": "PART_OF_FLOW"}
    ]
}

# CRM Stats
{
    "total_leads": 42,
    "total_flows": 5,
    "total_interactions": 187,
    "avg_trust": 0.62
}

# WebSocket Event
{
    "type": "lead_created",
    "payload": {"id": "lead_abc", "name": "Alice Santos"},
    "timestamp": "2026-03-03T10:00:00"
}
```

---

## Contexto de Memoria (Obsidian/Neo4j)

### Nodes Relacionados
- **Lead**: Contatos/prospects com trust score e tags
- **Flow**: Campanhas/funnels com status e workflow reference
- **Interaction**: Eventos discretos entre agentes e leads
- **Agent**: Os 19 agentes que podem interagir com leads
- **N8nNode**: Workflows n8n vinculados a flows

### Relationships
- `(:Lead)-[:PART_OF_FLOW]->(:Flow)` — Lead em campanha
- `(:Lead)-[:INTERACTED_WITH]->(:Lead)` — Leads conectados
- `(:Interaction)-[:FOR_LEAD]->(:Lead)` — Interacao com lead
- `(:Interaction)-[:BY_AGENT]->(:Agent)` — Interacao por agente
- `(:Flow)-[:USES_WORKFLOW]->(:N8nNode)` — Flow usa workflow n8n
- `(:Flow)-[:MENTIONED_IN]->(:Chunk)` — Flow referenciado em chunk

### Queries Cypher Relevantes

```cypher
-- Buscar lead com historico de interacoes
MATCH (l:Lead {id: $lead_id})
OPTIONAL MATCH (i:Interaction)-[:FOR_LEAD]->(l)
OPTIONAL MATCH (i)-[:BY_AGENT]->(a:Agent)
RETURN l, collect({interaction: i, agent: a.name}) AS history

-- Grafo CRM completo para visualizacao
MATCH (l:Lead)
OPTIONAL MATCH (l)-[r1:PART_OF_FLOW]->(f:Flow)
OPTIONAL MATCH (l)-[r2:INTERACTED_WITH]-(l2:Lead)
RETURN l, f, l2, r1, r2 LIMIT 200

-- Fulltext search de leads
CALL db.index.fulltext.queryNodes('lead_search', $query)
YIELD node, score
RETURN node.name, node.email, node.company, score
ORDER BY score DESC LIMIT 20

-- Stats dashboard
OPTIONAL MATCH (l:Lead) WITH count(l) AS leads, avg(l.trust) AS trust
OPTIONAL MATCH (f:Flow) WITH leads, trust, count(f) AS flows
OPTIONAL MATCH (i:Interaction)
RETURN leads, flows, count(i) AS interactions, trust
```

---

## Dependencias Tecnicas

### Bibliotecas Python
```txt
fastapi>=0.100.0         # REST endpoints
pydantic>=2.0.0          # Request/response models
neo4j>=5.0.0             # Graph database driver
```

### Servicos Externos
- **Neo4j**: Armazenamento de todos os nodes CRM (obrigatorio para operacao)
- **Sovereign Gateway**: FastAPI router que hospeda os endpoints CRM
- **TelemetryHub**: Dispatcher de eventos para broadcast via WebSocket

### Variaveis de Ambiente
```bash
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

---

## Metricas de Performance

### KPIs
- **Lead CRUD Latency**: < 100ms (p95)
- **Graph Query Latency**: < 500ms (p95) para GET /crm/graph com 200 nodes
- **WebSocket Broadcast**: < 50ms entre write e broadcast
- **Trust Score Accuracy**: Correlacao > 0.7 com conversao real (futuro)
- **Uptime**: 99.9% (graceful degradation sem Neo4j)

### Monitoramento
```python
{
  "agent": "CrmAgent",
  "timestamp": "2026-03-03T10:00:00Z",
  "metrics": {
    "total_leads": 42,
    "total_flows": 5,
    "avg_trust": 0.62,
    "interactions_today": 15,
    "ws_subscribers": 3
  }
}
```

---

## Testes

### Casos de Teste (34 tests em test_crm.py)

1. **TestCrmPydanticModels** (7 tests)
   - Validacao de defaults, bounds de trust, status values, lead sources

2. **TestCrmLeadQueries** (7 tests)
   - MERGE idempotencia, fulltext search, trust update, interaction count

3. **TestCrmFlowQueries** (4 tests)
   - MERGE idempotencia, status transitions, lead count, add lead

4. **TestCrmInteractionRecording** (4 tests)
   - Criacao com lead_id, relationships FOR_LEAD e BY_AGENT, TaskExecutor hook

5. **TestCrmSchema** (3 tests)
   - 9 entries em SCHEMA_QUERIES (constraints + indexes + fulltext)

6. **TestCrmEventProvider** (4 tests)
   - Provider ID, health check, push/poll, buffer drain

7. **TestCrmGatewayEndpoints** (5 tests)
   - List leads, create lead, stats, graph visualization

### Comandos de Teste
```bash
# Testes unitarios CRM
pytest src/neural_link/tests/test_crm.py -v

# Suite completa Neural Link
pytest src/neural_link/tests/ -v

# Verificacao de import
python -c "from src.neural_link.api.sovereign_gateway import router; print(f'{len(router.routes)} routes')"
```

---

## Integracao com Outros Agentes

### Agentes Upstream (fornecem input)
- **NeuralLinkOrchestrator**: Delega tasks com lead_id no input_data
- **TaskDecomposer**: Identifica tasks que envolvem leads/flows
- **n8n Deploy**: Ativa flows quando workflows sao deployados

### Agentes Downstream (recebem output)
- **TaskExecutor**: Registra interacoes automaticamente no grafo
- **TelemetryHub**: Recebe eventos CRM via CrmEventProvider
- **ObsidianBridge**: Sincroniza dados CRM para vault (futuro)

### Padroes de Comunicacao
- **Sincrono**: REST endpoints via Gateway
- **Assincrono**: WebSocket broadcast para frontend
- **Event-driven**: CrmEventProvider -> TelemetryHub -> /ws/telemetry

---

## Exemplos de Uso

### Exemplo 1: Criar Lead via REST
```bash
curl -X POST http://localhost:8766/api/v1/crm/leads \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice Santos","email":"alice@acme.com","source_channel":"telegram","tags":["enterprise"]}'
```

### Exemplo 2: Consultar Grafo CRM
```bash
curl http://localhost:8766/api/v1/crm/graph | python -m json.tool
```

### Exemplo 3: Registrar Interacao
```bash
curl -X POST http://localhost:8766/api/v1/crm/interactions \
  -H "Content-Type: application/json" \
  -d '{"lead_id":"lead_abc123","agent_id":"marketing_agent","channel":"email","action":"followup","detail":"Enviado case study"}'
```

### Exemplo 4: Adicionar Lead a Flow
```bash
curl -X POST http://localhost:8766/api/v1/crm/flows/flow_xyz/leads/lead_abc123
```

---

## Troubleshooting

### Problema 1: Endpoints retornam listas vazias
- **Sintoma**: GET /crm/leads retorna `[]`
- **Causa**: Neo4j nao conectado ou sem nodes Lead
- **Solucao**: Verificar conexao Neo4j e criar leads via POST

### Problema 2: WebSocket nao recebe eventos
- **Sintoma**: Frontend nao atualiza em tempo real
- **Causa**: Nenhum subscriber conectado ao canal "crm-events"
- **Solucao**: Verificar conexao WS no console do browser

### Problema 3: Trust score nao atualiza
- **Sintoma**: Trust permanece em 0.5 apos interacoes
- **Causa**: Lead Scoring skill ainda nao implementada (apenas basico)
- **Solucao**: Usar UPDATE_LEAD_TRUST manualmente ou aguardar skill completa

---

## Roadmap

### Versao Atual (1.0.0)
- OK Lead CRUD com trust e tags
- OK Flow CRUD com status lifecycle
- OK Interaction recording (manual + automatico via TaskExecutor)
- OK Graph visualization endpoint
- OK WebSocket real-time events
- OK CrmEventProvider no TelemetryHub
- OK n8n deploy -> Flow activation hook

### Proxima Versao (1.1.0)
- Fulltext search UI no LeadTable
- Lead merge/dedup via graph similarity
- Flow analytics (conversion rate, avg time-to-convert)
- Bulk import de leads via CSV/webhook

### Futuro (2.0.0)
- ML-based Lead Scoring (interaction patterns + source quality)
- Social Network Analysis (community detection, influence scoring)
- Obsidian Bridge sync para CRM notes
- n8n workflow auto-generation a partir de Flow definition

---

## Referencias

- [CRM Product Docs](../../product/crm/README.md)
- [Lead Scoring Skill](../skills/lead_scoring.md)
- [Social Analysis Skill](../skills/social_analysis.md)
- [Sovereign Command Center Spec](../../../vault/Specs/SovereignCommandCenter.md)
- [SpecialistAgent Spec](specialist-agent.md)
- [Neo4j Queries](../../../src/neural_link/graph/queries.py)
- [Test Suite](../../../src/neural_link/tests/test_crm.py)

---

**Mantido por**: Neural Link Team
**Ultima Revisao**: 2026-03-03
