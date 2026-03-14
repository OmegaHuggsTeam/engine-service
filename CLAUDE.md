# CLAUDE.md — Engine Service

## Visao Geral

Engine Service e o backend de inteligencia da OmegaHuggsTeam. Processa RAG, orquestra agentes AI, gerencia grafos de conhecimento, e serve tudo via Sovereign Gateway (porta 8766).

**Repo:** `OmegaHuggsTeam/engine-service`
**Local:** `C:\labs\inteligence\chunk-generator\`
**Branch principal:** `feat/content-factory` (20+ ahead de develop)
**Producao:** `https://api.huggs.tech` (VPS 187.124.88.71, porta 8766)

## Stack

- Python 3.11+ (FastAPI)
- ChromaDB (vetorial)
- Neo4j (grafo de conhecimento)
- Docker + Docker Compose
- LiteLLM (roteamento multi-LLM)
- MCP Protocol (Model Context Protocol)

## Arquitetura de Componentes

### 1. MCP Server (`src/mcp_server/`)

Expoe o engine-service como ferramentas nativas para Claude Code e Cursor via Model Context Protocol.

**8 tools disponveis:**

| Tool | Descricao |
|------|-----------|
| `rag_search(query, top_k)` | Busca HybridRAG (semantico + graph + keyword) |
| `graph_query(cypher)` | Cypher read-only no Neo4j (write ops bloqueadas) |
| `graph_concepts(limit)` | Lista conceitos com dominios e conexoes |
| `ingest_document(file_path, category)` | Ingere documento na knowledge base |
| `list_agents()` | Lista agentes registrados |
| `agent_execute(agent_id, task)` | Despacha task para agente (timeout 30s) |
| `search_errors(error_type, error_message)` | Busca solucoes no grafo de erros |
| `pipeline_stats()` | Telemetria: cache, latencia, custo, agentes |

**Registrar no Claude Code:**
```bash
cd C:\labs\inteligence\chunk-generator
claude mcp add engine-service -- python -m src.mcp_server.server
```

**Registrar no Cursor** (`.cursor/mcp.json`):
```json
{
  "mcpServers": {
    "engine-service": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "C:\\labs\\inteligence\\chunk-generator"
    }
  }
}
```

**Gerar configs automaticamente:**
```bash
python -m src.mcp_server.config
```

### 2. Multi-Embedding Engine (`src/utils/embedding_manager.py`)

Permite rodar multiplos modelos de embedding em paralelo para A/B testing sem re-ingestao.

**Modelos suportados:**

| ID | Modelo | Dimensoes |
|----|--------|-----------|
| `openai` | text-embedding-3-small | 1536 |
| `nomic` | nomic-embed-text-v1.5 | 768 |
| `minilm` | all-MiniLM-L6-v2 | 384 |

**Config via env:**
```bash
EMBEDDING_MODELS=openai,minilm  # comma-separated
```

**Uso:**
```python
from src.utils.embedding_manager import EmbeddingManager

em = EmbeddingManager.from_env()  # singleton thread-safe
em.add_chunks(chunks)             # insere em TODAS as collections ativas
results = em.search("query")      # busca em todos, merge com cross-engine boost
em.list_models()                  # info por modelo com chunk counts
```

**Backward compat:** Com 0-1 modelos, `vector_db.py` funciona identico ao anterior. Multi-embedding so ativa com 2+ modelos.

### 3. LiteLLM Router (`src/utils/litellm_router.py`)

Roteamento inteligente multi-LLM com fallback chain e cost tracking.

**Tiers:**

| Tier | Modelos | Uso |
|------|---------|-----|
| fast | Groq Llama, Groq Mixtral | Triage, classificacao |
| standard | GPT-4o-mini, Gemini Flash | RAG, resumos |
| complex | Claude Sonnet, GPT-4o | Analise profunda |

**Config:** `config/litellm_models.yaml`

**Uso:**
```python
from src.utils.litellm_router import LiteLLMRouter

router = LiteLLMRouter.from_env()  # singleton
result = await router.completion("Analyze this text", model="fast")
stats = router.get_cost_stats()    # custo agregado por modelo
```

**Backward compat:** Se litellm nao instalado, `llm_client.py` usa roteamento manual original (Groq/OpenAI/Gemini).

### 4. Docling Extractor (`src/extractors/docling_extractor.py`)

Extrai texto estruturado de documentos complexos (PDF, DOCX, PPTX, HTML, imagens) via Docling Serve.

**Uso:**
```python
from src.extractors.docling_extractor import extract_with_docling, is_docling_compatible

if is_docling_compatible("report.pdf"):
    chunks = await extract_with_docling("report.pdf", category="reports")
    tables = await extract_tables("report.pdf")
```

**Docker:** Servico `docling` ja configurado no `docker-compose.yml` (porta 5001).

**Fallback:** Se Docling Serve indisponivel, tenta `docling` local. Se ambos falharem, RuntimeError.

### 5. Python SDK (`sdk/`)

SDK cliente para consumir o Sovereign Gateway programaticamente.

**Instalacao:**
```bash
pip install -e sdk/
```

**Uso (async):**
```python
from engine_sdk import EngineClient

async with EngineClient(base_url="http://localhost:8766", api_key="...") as client:
    results = await client.rag.search("multi-agent patterns")
    agents = await client.agents.list()
    stats = await client.telemetry.pipeline_stats()
```

**Uso (sync):**
```python
from engine_sdk import EngineSyncClient

client = EngineSyncClient(base_url="http://localhost:8766")
results = client.rag.search("cost optimization")
```

**Resources:** rag, agents, graph, ingest, telemetry
**Models:** 22 Pydantic v2 models
**Testes:** 107 testes

## Testes

```bash
# Rodar todos os testes
cd C:\labs\inteligence\chunk-generator
python -m pytest src/neural_link/tests/ -q

# Testes por componente
python -m pytest src/neural_link/tests/test_embedding_manager.py -q   # 36 testes
python -m pytest src/neural_link/tests/test_litellm_router.py -q      # 30 testes
python -m pytest src/neural_link/tests/test_docling_extractor.py -q   # 30+ testes

# SDK
python sdk/tests/run_tests.py                                         # 107 testes
```

## Docker Compose

```bash
docker compose up -d  # sobe Neo4j, ChromaDB, Docling, Evidence
```

| Servico | Porta | Descricao |
|---------|-------|-----------|
| Neo4j | 7474/7687 | Grafo de conhecimento |
| ChromaDB | 8000 | Banco vetorial |
| Docling | 5001 | Parser de documentos |
| Evidence | 5000 | Dashboard analytics |

## Env Vars Importantes

```bash
# Obrigatorias
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Opcionais (novos componentes)
EMBEDDING_MODELS=openai,minilm           # Multi-embedding (default: detecta automatico)
DOCLING_SERVE_URL=http://localhost:5001   # Docling (default: localhost:5001)
LITELLM_CONFIG=config/litellm_models.yaml # LiteLLM (default: config/litellm_models.yaml)

# API Keys
OPENAI_API_KEY=...
GROQ_API_KEY=...
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
```

## Referencias SSOT (caminhos exatos)

NAO inventar patterns ou configs. Consultar antes de gerar codigo:

| Arquivo | O que governa |
|---------|-------------|
| `config/litellm_models.yaml` | Modelos LLM, tiers, fallback chains, router settings |
| `.cursor/rules/kiro-cortex.mdc` | Automation orchestrator, RAG knowledge, controle |
| `src/mcp_server/tools.py` | Tools MCP disponiveis (8 tools) — nao criar duplicados |
| `src/utils/llm_client.py` | Roteamento manual (fallback quando LiteLLM indisponivel) |
| `src/neural_link/rag/hybrid_rag.py` | HybridRAG — pattern de busca fusionada |
| `src/neural_link/graph/manager.py` | GraphManager — pattern singleton Neo4j |
| `.env.example` | Todas as env vars documentadas |

## Convencoes

- **SSOT-First:** Consultar Referencias SSOT acima antes de gerar codigo
- **NAO inventar:** Usar apenas patterns documentados. Citar fonte quando usar
- **Singletons:** Usar pattern `from_env()` com thread-safety (ver `GraphManager`, `EmbeddingManager`, `LiteLLMRouter`)
- **Testes:** pytest, classes com `Test` prefix, fixtures com `tmp_path`, mocks para HTTP/DB
- **Backward compat:** Todo novo componente DEVE funcionar como no-op se dependencia nao instalada
- **Async:** Funcoes sync rodadas via `asyncio.to_thread()` dentro de handlers async
- **Seguranca:** graph_query bloqueia keywords de escrita (CREATE, MERGE, DELETE, SET, REMOVE, DROP, CALL, DETACH)

## Estrutura de Diretorios (principais)

```
src/
  mcp_server/          # MCP Protocol server (8 tools)
  extractors/          # Docling, n8n, whisper extractors
  utils/               # vector_db, llm_client, embedding_manager, litellm_router
  neural_link/
    rag/               # HybridRAG, graph_retriever
    graph/             # GraphManager, Neo4j operations
    orchestrator/      # Agent selector, pipeline cache
    telemetry/         # Cost tracker, metrics
    tests/             # Todos os testes
sdk/                   # Python SDK cliente
config/                # litellm_models.yaml, outros configs
```
