# Design: Omega Content Factory + Workflow Products Platform

**Data**: 2026-03-07
**Autor**: Hugo (@HuggsF) + Claude
**Status**: Aprovado
**Repo**: OmegaHuggsTeam/engine-service

---

## 1. Contexto

A Omega precisa de um pipeline 100% automatizado que:
1. Pesquisa papers/trends semanalmente (Arxiv, HuggingFace, GitHub, ProductHunt)
2. Gera podcast em audio (TTS) com tom da marca Omega
3. Deriva conteudo para multiplos formatos (clips, carrossel IG, thread X, post LinkedIn)
4. Publica automaticamente em cada canal

Alem disso, o podcast e o **primeiro produto** de uma plataforma maior de
**Workflow Products** baseada em n8n, onde:
- Os 4700+ templates ja indexados sao o catalogo
- ComposerAgent gera novos workflows via linguagem natural
- O CRM frontend configura e ativa workflows por cliente
- n8n executa, engine-service fornece inteligencia

---

## 2. Arquitetura de 2 Camadas

### Camada 1: Workflow Products Platform

```
┌─────────────────────────────────────────────────────┐
│  Engine-Service (Neural Link)                       │
│                                                     │
│  ┌───────────────────────────────────────────┐      │
│  │  Workflow Registry (CRUD REST API)         │      │
│  │  POST/GET/PUT/DELETE /api/v1/workflows     │      │
│  │  POST /api/v1/workflows/{id}/deploy        │      │
│  │  POST /api/v1/workflows/{id}/run           │      │
│  │  GET  /api/v1/workflows/templates (RAG)    │      │
│  └───────────────┬───────────────────────────┘      │
│                   │                                  │
│  ┌────────────────▼──────────────────────────┐      │
│  │  Content Agents (novos)                    │      │
│  │  ResearchAgent | ScriptAgent | AudioAgent  │      │
│  │  ClipAgent | CarouselAgent | ThreadAgent   │      │
│  │  LinkedInAgent | PublishAgent              │      │
│  └───────────────┬───────────────────────────┘      │
│                   │                                  │
│  ┌────────────────▼──────────────────────────┐      │
│  │  Infra existente                           │      │
│  │  ComposerAgent | N8nValidator              │      │
│  │  inject_n8n_workflow | HybridRAG           │      │
│  │  AgentSelector | CostTracker | Pipeline    │      │
│  └───────────────────────────────────────────┘      │
└─────────────────────────┬───────────────────────────┘
                          │ Webhooks (bidirecional)
┌─────────────────────────▼───────────────────────────┐
│  n8n Runtime (porta 5678)                           │
│  → Executa workflow products                        │
│  → Schedule triggers (cron)                         │
│  → Chama engine-service via webhook                 │
│  → Recebe callbacks com resultados                  │
└─────────────────────────────────────────────────────┘

### Camada 2: CRM Frontend

┌─────────────────────────────────────────────────────┐
│  HuggsAI CRM (huggsai-crm)                         │
│  → CRUD de Workflow Products                        │
│  → Configuracao via formularios                     │
│  → Dashboard de execucoes e custos                  │
│  → Ativacao/desativacao por cliente                 │
│  → Busca nos 4700 templates via RAG                 │
└─────────────────────────────────────────────────────┘
```

---

## 3. Workflow Product: Modelo de Dados

```python
@dataclass
class WorkflowProduct:
    id: str                        # "omega-weekly-podcast"
    name: str                      # "Podcast Semanal Omega"
    description: str               # Descricao para catalogo
    category: str                  # "content" | "sales" | "support" | "ops"
    n8n_workflow_json: dict        # JSON completo do workflow n8n
    config: dict                   # Parametros configuraveis pelo front
    schedule: Optional[str]        # Cron expression (ex: "0 6 * * 5")
    agents_used: list[str]         # ["research", "script", "audio", ...]
    webhook_urls: list[str]        # URLs que o n8n chama no engine
    status: str                    # "draft" | "active" | "paused" | "error"
    created_from_template: str     # ID do template original
    brand_voice_file: str          # Arquivo no vault/Knowledge/
    executions: list[Execution]    # Historico de execucoes
    cost_per_run: float           # Custo estimado por execucao ($)
    created_at: datetime
    updated_at: datetime

@dataclass
class Execution:
    id: str
    workflow_product_id: str
    started_at: datetime
    completed_at: Optional[datetime]
    status: str                    # "running" | "success" | "failed"
    outputs: dict                  # URLs dos assets gerados
    cost_actual: float             # Custo real da execucao
    error: Optional[str]
```

---

## 4. Content Agents (8 novos agentes)

### 4.1 ResearchAgent

**Tipo**: domain
**Capabilities**: `{"research", "papers", "trends", "curation"}`
**LLM**: Sonnet (classificacao/ranqueamento)
**Input**: Config de fontes + periodo
**Output**: `ResearchDigest`

```python
SOURCES = {
    "arxiv": {
        "api": "http://export.arxiv.org/api/query",
        "categories": ["cs.AI", "cs.CL", "cs.LG"],
        "max_results": 20,
        "sort": "submittedDate"
    },
    "huggingface": {
        "api": "https://huggingface.co/api/models",
        "sort": "trending",
        "limit": 15
    },
    "github_trending": {
        "api": "https://api.github.com/search/repositories",
        "query": "language:python topic:ai topic:llm",
        "sort": "stars",
        "period": "weekly"
    },
    "producthunt": {
        "api": "https://api.producthunt.com/v2/api/graphql",
        "topic": "artificial-intelligence",
        "period": "weekly"
    }
}
```

**Processo**:
1. Coleta ultimas 7 dias de cada fonte
2. Deduplica (titulo similar > 0.8 cosine)
3. Ranqueia por relevancia para publico Omega (empresarios que usam IA pra vender)
4. Seleciona top 5-8 items
5. Para cada: titulo, resumo 2 frases, por que importa pro publico, fonte

```python
@dataclass
class ResearchDigest:
    items: list[ResearchItem]      # 5-8 items ranqueados
    period: str                    # "2026-03-01 a 2026-03-07"
    total_collected: int           # Quantos foram analisados
    sources_status: dict           # {"arxiv": "ok", "hf": "ok", ...}

@dataclass
class ResearchItem:
    title: str
    source: str                    # "arxiv" | "huggingface" | "github" | "producthunt"
    url: str
    summary: str                   # 2 frases
    relevance_score: float         # 0-1
    relevance_reason: str          # Por que importa pro publico Omega
    category: str                  # "paper" | "model" | "tool" | "product"
```

### 4.2 ScriptAgent

**Tipo**: domain
**Capabilities**: `{"copywriting", "script", "podcast", "brand_voice"}`
**LLM**: Opus (criatividade + tom de voz)
**Input**: `ResearchDigest` + brand voice (via RAG)
**Output**: `PodcastScript`

**Processo**:
1. Consulta `vault/Knowledge/omega_brand_voice.txt` via RAG
2. Gera roteiro de 5-8 minutos com:
   - Abertura (15-20s): gancho + contexto da semana
   - 3-5 blocos (60-90s cada): 1 item do digest por bloco
   - Fechamento (15-20s): resumo + CTA
3. Marca pausas com `[...]`, enfases com `**palavra**`
4. Gera SSML tags para TTS (velocidade, pausas, enfase)

```python
@dataclass
class PodcastScript:
    title: str                     # "Omega Weekly #12: O paper que muda tudo"
    duration_estimate: int         # Segundos estimados
    sections: list[ScriptSection]
    ssml: str                      # Script com SSML tags
    plain_text: str                # Script sem markup
    metadata: dict                 # digest_id, items_used, etc
```

### 4.3 AudioAgent

**Tipo**: specialist
**Capabilities**: `{"tts", "audio", "elevenlabs"}`
**LLM**: Nenhum (API TTS)
**Input**: `PodcastScript`
**Output**: `AudioAsset`

**Processo**:
1. Envia SSML para ElevenLabs (ou OpenAI TTS como fallback)
2. Voice: pt-BR, estilo conversacional
3. Gera MP3 + calcula duracao real
4. Gera metadata (ID3 tags: titulo, artista "Omega", episodio)

```python
@dataclass
class AudioAsset:
    file_path: str                 # Caminho do MP3
    duration_seconds: int
    size_bytes: int
    voice_id: str                  # ID da voz no ElevenLabs
    transcript: str                # Texto falado
    metadata: dict                 # ID3 tags
```

### 4.4 ClipAgent

**Tipo**: specialist
**Capabilities**: `{"clips", "short_form", "reels"}`
**LLM**: Haiku (selecao de trechos)
**Input**: `AudioAsset` + `PodcastScript`
**Output**: `list[ClipAsset]`

**Processo**:
1. Analisa script pra encontrar 3-5 "momentos clip-worthy" (frases impactantes)
2. Calcula timestamps no audio
3. Corta MP3 em segmentos de 30-60s
4. Gera titulo + descricao pra cada clip

### 4.5 CarouselAgent

**Tipo**: specialist
**Capabilities**: `{"carousel", "instagram", "visual_content"}`
**LLM**: Sonnet (copywriting)
**Input**: `ResearchDigest` + brand guide
**Output**: `CarouselAsset`

**Processo**:
1. Seleciona 1 item do digest com mais potencial visual
2. Gera 5-7 slides em JSON (titulo, corpo, CTA)
3. Segue paleta Omega (Ink #0D0D12, Azul #1B4FFF, Off-white #F8F7F4)
4. Cada slide: max 3 linhas, tipografia Bricolage Grotesque display

### 4.6 ThreadAgent

**Tipo**: specialist
**Capabilities**: `{"twitter", "threads", "microcopy"}`
**LLM**: Sonnet (copywriting)
**Input**: `ResearchDigest` + brand voice
**Output**: `ThreadAsset`

**Processo**:
1. Seleciona top 3 items do digest
2. Gera 8-12 tweets encadeados
3. Tweet 1: gancho (pergunta ou dado impactante)
4. Tweets 2-10: conteudo (1 item por 2-3 tweets)
5. Tweet final: CTA (link pro podcast completo)

### 4.7 LinkedInAgent

**Tipo**: specialist
**Capabilities**: `{"linkedin", "professional", "b2b"}`
**LLM**: Sonnet (copywriting B2B)
**Input**: `ResearchDigest` + brand voice
**Output**: `LinkedInAsset`

**Processo**:
1. Tom mais profissional que Twitter (mas ainda Omega: direto, sem corporates)
2. Post unico de 1000-1500 caracteres
3. Hook + 3 insights + CTA
4. Hashtags relevantes (max 5)

### 4.8 PublishAgent

**Tipo**: operator
**Capabilities**: `{"publish", "social_media", "distribution"}`
**LLM**: Nenhum (APIs)
**Input**: Qualquer `*Asset`
**Output**: URLs publicadas

**APIs de publicacao**:
- Podcast: RSS feed (Anchor/Spotify via API) ou S3 + feed XML
- Instagram: Meta Graph API (carousel)
- X/Twitter: Twitter API v2 (thread)
- LinkedIn: LinkedIn Marketing API (post)
- YouTube Shorts: YouTube Data API (clips com imagem estatica)

---

## 5. n8n Workflow do Podcast

O workflow n8n orquestra a sequencia. Cada step chama o Sovereign Gateway:

```json
{
  "name": "omega-weekly-podcast",
  "nodes": [
    {
      "name": "Schedule Trigger",
      "type": "n8n-nodes-base.scheduleTrigger",
      "parameters": { "rule": { "interval": [{ "field": "cronExpression", "expression": "0 6 * * 5" }] } }
    },
    {
      "name": "Research",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:8766/api/v1/agents/research/execute",
        "method": "POST",
        "body": { "period": "7d", "sources": "all", "max_items": 8 }
      }
    },
    {
      "name": "Script",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:8766/api/v1/agents/script/execute",
        "method": "POST",
        "body": { "digest": "={{ $json.digest }}", "brand": "omega", "duration": "5-8min" }
      }
    },
    {
      "name": "Audio",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": {
        "url": "http://localhost:8766/api/v1/agents/audio/execute",
        "method": "POST",
        "body": { "script": "={{ $json.script }}", "voice": "pt-br-conversational" }
      }
    },
    {
      "name": "Parallel Split",
      "type": "n8n-nodes-base.splitInBatches"
    },
    {
      "name": "Clips",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": { "url": "http://localhost:8766/api/v1/agents/clips/execute" }
    },
    {
      "name": "Carousel",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": { "url": "http://localhost:8766/api/v1/agents/carousel/execute" }
    },
    {
      "name": "Thread",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": { "url": "http://localhost:8766/api/v1/agents/thread/execute" }
    },
    {
      "name": "LinkedIn",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": { "url": "http://localhost:8766/api/v1/agents/linkedin/execute" }
    },
    {
      "name": "Publish All",
      "type": "n8n-nodes-base.httpRequest",
      "parameters": { "url": "http://localhost:8766/api/v1/agents/publish/execute" }
    }
  ]
}
```

---

## 6. Workflow Registry API

Novos endpoints no Sovereign Gateway (8766):

```
POST   /api/v1/workflows                → Registra workflow product
GET    /api/v1/workflows                → Lista catalogo (paginado)
GET    /api/v1/workflows/{id}           → Detalhes + historico execucoes
PUT    /api/v1/workflows/{id}           → Atualiza config
DELETE /api/v1/workflows/{id}           → Desativa (soft delete)
POST   /api/v1/workflows/{id}/deploy    → Injeta no n8n via API
POST   /api/v1/workflows/{id}/run       → Trigger manual
GET    /api/v1/workflows/templates      → Busca nos 4700 templates (RAG)
GET    /api/v1/workflows/{id}/cost      → Custo estimado + historico real

POST   /api/v1/agents/{slug}/execute    → Executa agente especifico (p/ n8n chamar)
GET    /api/v1/agents/{slug}/status     → Status do agente
```

---

## 7. Brand Voice como Knowledge File

Arquivo: `vault/Knowledge/omega_brand_voice.txt`

Conteudo extraido do brand guide:
- Essencia: "Tecnologia que fecha vendas"
- Personalidade: direta, confiavel, brasileira
- Exemplos bons: "Seu agente ja respondeu 47 leads enquanto voce dormia"
- Exemplos ruins: "Nossa plataforma de IA generativa multiagente..."
- Cores como sensacao: "azul escuro serio", "laranja so pra urgencia"
- Tipografia: Bricolage Grotesque (display), Plus Jakarta Sans (corpo)

Consultado via RAG pelo ScriptAgent, CarouselAgent, ThreadAgent, LinkedInAgent.

---

## 8. Estrutura de Arquivos (novos)

```
src/neural_link/
├── agents/
│   ├── content/                        # NOVO — familia de agentes de conteudo
│   │   ├── __init__.py
│   │   ├── research_agent.py           # Coleta multi-fonte
│   │   ├── script_agent.py             # Gera roteiro podcast
│   │   ├── audio_agent.py              # TTS (ElevenLabs/OpenAI)
│   │   ├── clip_agent.py               # Corta clips 30-60s
│   │   ├── carousel_agent.py           # Gera carrossel IG
│   │   ├── thread_agent.py             # Gera thread X/Twitter
│   │   ├── linkedin_agent.py           # Gera post LinkedIn
│   │   └── publish_agent.py            # Publica em cada canal
│   └── content/models.py              # Dataclasses (ResearchDigest, PodcastScript, etc)
├── api/
│   └── workflow_registry.py            # NOVO — CRUD de workflow products
├── orchestrator/
│   └── agent_selector.py              # ATUALIZAR — registrar novos agentes

vault/Knowledge/
└── omega_brand_voice.txt               # NOVO — brand guide pra RAG

data/workflows/
└── omega-weekly-podcast.json           # NOVO — workflow n8n template
```

---

## 9. Custos

### Por episodio semanal

| Step | LLM/API | Tokens | Custo |
|------|---------|--------|-------|
| Research | Sonnet | ~2K | $0.01 |
| Script | Opus | ~8K | $0.75 |
| Audio | ElevenLabs | — | $0.30 |
| Clips | Haiku | ~1K | $0.001 |
| Carousel | Sonnet | ~2K | $0.01 |
| Thread | Sonnet | ~2K | $0.01 |
| LinkedIn | Sonnet | ~1K | $0.005 |
| **Total** | | | **~$1.08** |

### Mensal: ~$4.80 por 4 episodios + todos os derivados

---

## 10. Metamodelagem: Padrao Replicavel

O que torna isso uma **plataforma** e nao um script:

1. **Qualquer workflow product** segue o mesmo padrao:
   - Registra no Workflow Registry
   - Define agentes envolvidos
   - Configura no CRM frontend
   - n8n executa, engine fornece inteligencia

2. **Exemplos de proximos produtos**:
   - "Lead Nurture Automatico" — ResearchAgent pesquisa segmento + ScriptAgent gera emails
   - "Suporte FAQ" — RAG consulta knowledge base + ScriptAgent gera resposta
   - "Relatorio Semanal" — AnalyticsAgent coleta KPIs + ScriptAgent gera resumo executivo

3. **Time de marketing** ganha autonomia:
   - Catalogo de 4700+ templates pra descobrir automacoes
   - ComposerAgent gera workflows novos via chat
   - Frontend do CRM configura tudo sem codigo

---

## 11. Decisoes de Design

| Decisao | Escolha | Justificativa |
|---------|---------|---------------|
| Onde vivem os agentes | Dentro do Neural Link | Aproveita pipeline, RAG, cost tracker, agent registry |
| Orquestracao | n8n | Ja roda na VPS, visual pro marketing, 4700 templates |
| Comunicacao n8n ↔ engine | Webhooks HTTP | Simples, debugavel, n8n ja suporta nativamente |
| TTS | ElevenLabs (primary) + OpenAI (fallback) | Melhor qualidade pt-BR |
| Brand voice | Knowledge file no RAG | Mesmo padrao do automation_hub (modo_leitura.txt) |
| Storage de assets | S3/MinIO (VPS) | MP3, imagens de carousel, etc |
| Publicacao | APIs nativas de cada plataforma | Controle total, sem intermediario |
```

---

## 12. Riscos e Mitigacoes

| Risco | Mitigacao |
|-------|-----------|
| TTS em pt-BR com qualidade ruim | Testar 3 vozes do ElevenLabs antes de definir |
| APIs de publicacao mudam | PublishAgent isolado, troca de API nao afeta outros agentes |
| Custo Opus escala | Testar Sonnet 3.5 pro ScriptAgent se qualidade for suficiente |
| Rate limits das fontes | Cache de 24h no Layer 0 (Redis) |
| n8n cai | Health check no engine, alerta no Telegram |
