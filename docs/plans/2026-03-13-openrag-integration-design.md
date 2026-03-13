# OpenRAG-Inspired Integration Design

**Date:** 2026-03-13
**Author:** Claude (Opus) + Hugo @HuggsF
**Status:** Approved
**Scope:** 5 new components for engine-service inspired by [OpenRAG](https://github.com/langflow-ai/openrag)

---

## Context

OpenRAG (langflow-ai, 1.9k stars, Apache 2.0) packages RAG as a turnkey platform using OpenSearch + Langflow + Docling + LiteLLM. Our engine-service HybridRAG is more sophisticated (3-engine fusion, graph traversal, 29 agents, 4-layer pipeline) but lacks certain production conveniences that OpenRAG offers out-of-the-box.

This design extracts the 5 most valuable patterns from OpenRAG and integrates them into our architecture without replacing any existing capabilities.

## What We're NOT Changing

- HybridRAG core (ChromaDB + Neo4j + TF-IDF fusion) stays
- QueryRouter + ResultMerger stay
- Sovereign Gateway stays at port 8766
- Agent architecture stays
- Docker Compose structure stays (additive only)

---

## Component 1: Docling Extractor

### Problem
Our extractors (web_extractor, n8n_extractor, crm_code_extractor) are domain-specific and excellent for their targets. But for generic document parsing (complex PDFs with tables, PPTX, DOCX with layouts), we lack a robust universal parser.

### Solution
Add Docling as a new extractor option alongside existing ones.

### Files
```
src/extractors/docling_extractor.py    # New — Docling HTTP client + chunking
docker-compose.yml                      # Modified — add docling service
.env.example                            # Modified — add DOCLING_SERVE_URL
```

### Architecture
```
                    ┌─────────────────┐
                    │  File Upload    │
                    └────────┬────────┘
                             │
                    ┌────────▼────────┐
                    │  Type Detection │
                    └────────┬────────┘
                             │
          ┌──────────────────┼──────────────────┐
          │                  │                  │
  ┌───────▼───────┐ ┌───────▼───────┐ ┌───────▼───────┐
  │ CRM Extractor │ │ n8n Extractor │ │   Docling     │
  │ (TS/JS code)  │ │ (JSON wflows) │ │ (PDF/DOCX/PPT)│
  └───────┬───────┘ └───────┬───────┘ └───────┬───────┘
          │                  │                  │
          └──────────────────┼──────────────────┘
                             │
                    ┌────────▼────────┐
                    │  add_chunks()   │
                    │  (vector_db.py) │
                    └─────────────────┘
```

### Interface
```python
# src/extractors/docling_extractor.py

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".png", ".jpg", ".jpeg", ".tiff"}

def is_docling_compatible(file_path: str | Path) -> bool:
    """Returns True if file extension is supported by Docling."""

async def extract_with_docling(
    file_path: str | Path,
    chunk_size: int = 3600,
    chunk_overlap: int = 400,
    category: str = "documents",
) -> list[dict]:
    """
    Sends file to Docling Serve for parsing, then chunks result.

    Returns list of chunks matching existing schema:
    [{'content': str, 'source_file': str, 'category': str,
      'chunk_index': int, 'char_count': int, 'docling_metadata': dict}]
    """

async def extract_tables(file_path: str | Path) -> list[dict]:
    """Extracts tables as structured data (for graph enrichment)."""
```

### Docker Service
```yaml
docling:
  image: ds4sd/docling-serve:latest
  ports:
    - "5001:5001"
  environment:
    - DOCLING_BACKEND=docling
    - DOCLING_OCR=easyocr
  networks:
    - bunker
  restart: unless-stopped
```

### Fallback
If Docling Serve is unavailable, falls back to `pip install docling` local processing (slower but works).

---

## Component 2: Multi-Embedding Engine

### Problem
We use a single embedding model (text-embedding-3-small or MiniLM fallback). OpenRAG stores multiple embeddings per chunk, enabling A/B testing and ensemble retrieval without re-ingestion.

### Solution
`EmbeddingManager` that handles N models, stores in separate ChromaDB collections, and merges results via existing `ResultMerger`.

### Files
```
src/utils/embedding_manager.py    # New — multi-model orchestration
src/utils/vector_db.py            # Modified — delegate to EmbeddingManager
.env.example                      # Modified — EMBEDDING_MODELS config
```

### Architecture
```
                    ┌─────────────┐
                    │  add_chunks │
                    └──────┬──────┘
                           │
                  ┌────────▼────────┐
                  │ EmbeddingManager│
                  │  (orchestrator) │
                  └────────┬────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
  ┌───────▼───────┐ ┌─────▼───────┐ ┌──────▼──────┐
  │   OpenAI      │ │   Nomic     │ │  Future     │
  │ 3-small       │ │ embed-text  │ │  Model N    │
  │ (1536 dim)    │ │ (768 dim)   │ │             │
  └───────┬───────┘ └─────┬───────┘ └──────┬──────┘
          │                │                │
  ┌───────▼───────┐ ┌─────▼───────┐ ┌──────▼──────┐
  │ course_chunks │ │course_chunks│ │course_chunks│
  │ _openai       │ │_nomic       │ │_modelN      │
  └───────────────┘ └─────────────┘ └─────────────┘
```

### Interface
```python
# src/utils/embedding_manager.py

class EmbeddingManager:
    def __init__(self, models: list[str] | None = None):
        """
        models: ['openai', 'nomic'] from EMBEDDING_MODELS env var
        Each model gets its own ChromaDB collection.
        """

    @classmethod
    def from_env(cls) -> "EmbeddingManager":
        """Reads EMBEDDING_MODELS=openai,nomic from .env"""

    def add_chunks(self, chunks: list[dict], batch_size: int = 100) -> dict[str, int]:
        """Inserts chunks into ALL active model collections. Returns {model: count}."""

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Searches all collections, merges via ResultMerger with equal weights.
        Cross-model boost: +10% when same chunk found by 2+ models.
        """

    def search_with_model(self, query: str, model: str, top_k: int = 5) -> list[dict]:
        """Search a specific model's collection only (for A/B comparison)."""

    def list_models(self) -> list[dict]:
        """Returns [{name, dimensions, collection, chunk_count}]"""

    def remove_model(self, model: str) -> bool:
        """Drops a model's collection. Data for other models unaffected."""
```

### Config
```bash
# .env
EMBEDDING_MODELS=openai,nomic    # Comma-separated, first is primary
# If only one model, behaves exactly like current code (backward compat)
```

### Backward Compatibility
`vector_db.py` functions (`add_chunks`, `search_with_scores`) become thin wrappers:
- If `EMBEDDING_MODELS` has 1 model → identical to current behavior
- If `EMBEDDING_MODELS` has 2+ → delegates to `EmbeddingManager`

---

## Component 3: MCP Server

### Problem
Our engine-service is only accessible via REST API. OpenRAG provides an MCP server so Claude Desktop and Cursor can query the knowledge base directly. This is the biggest missing feature.

### Solution
FastMCP server that exposes HybridRAG, Neo4j, and agent dispatch as MCP tools.

### Files
```
src/mcp_server/                 # New package
  __init__.py
  server.py                     # FastMCP app definition
  tools.py                      # Tool implementations
  config.py                     # MCP config helpers
requirements.txt                # Modified — add mcp[cli]
```

### Tools
```python
# src/mcp_server/tools.py

@mcp.tool()
async def rag_search(query: str, top_k: int = 5) -> list[dict]:
    """Search the knowledge base using HybridRAG (semantic + graph + keyword).
    Returns ranked results with source, score, and engine attribution."""

@mcp.tool()
async def graph_query(cypher: str) -> list[dict]:
    """Execute a read-only Cypher query against Neo4j knowledge graph.
    Returns list of records as dictionaries."""

@mcp.tool()
async def graph_concepts(limit: int = 50) -> list[dict]:
    """List all concepts in the knowledge graph with their domains and connection counts."""

@mcp.tool()
async def ingest_document(file_path: str, category: str = "documents") -> dict:
    """Ingest a document into the knowledge base. Supports PDF, DOCX, PPTX, TXT, MD, JSON.
    Returns {chunks_created: int, source_file: str}."""

@mcp.tool()
async def list_agents() -> list[dict]:
    """List all available AI agents with their capabilities and status."""

@mcp.tool()
async def agent_execute(agent_id: str, task: str) -> dict:
    """Dispatch a task to a specific agent. Returns agent response with execution metadata."""

@mcp.tool()
async def search_errors(error_type: str, error_message: str = "") -> list[dict]:
    """Search the error resolution graph for known fixes.
    Uses Neo4j Error→RESOLVED_BY→Skill relationships."""

@mcp.tool()
async def pipeline_stats() -> dict:
    """Get current pipeline statistics: cache hit rate, avg latency, cost per request, active agents."""
```

### Server Definition
```python
# src/mcp_server/server.py

from mcp.server.fastmcp import FastMCP

mcp = FastMCP(
    "engine-service",
    description="HybridRAG knowledge base with 29 AI agents, graph-augmented retrieval, and 4-layer cost-optimized pipeline",
)

# Register all tools from tools.py
# Lazy-init HybridRAG + GraphManager on first tool call
```

### Config Output (auto-generated)
```json
{
  "mcpServers": {
    "engine-service": {
      "command": "python",
      "args": ["-m", "src.mcp_server.server"],
      "cwd": "C:\\labs\\inteligence\\chunk-generator",
      "env": {
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_PASSWORD": "neural_link_2024",
        "CHROMA_HOST": "localhost",
        "CHROMA_PORT": "8000"
      }
    }
  }
}
```

### Security
- `graph_query` only allows READ operations (blocks CREATE, MERGE, DELETE, SET, REMOVE)
- `ingest_document` validates file exists and extension is supported
- `agent_execute` has timeout (30s default)
- Flag `--allow-writes` enables write operations for trusted environments

---

## Component 4: LiteLLM Router

### Problem
Our `llm_client.py` manually handles provider routing, key rotation, and fallback. OpenRAG uses LiteLLM which provides all of this plus cost tracking, retries, and 100+ provider support in one package.

### Solution
Replace manual routing with `litellm.Router` while keeping the same interface.

### Files
```
src/utils/litellm_router.py     # New — LiteLLM Router wrapper
src/utils/llm_client.py         # Modified — delegate to LiteLLM
config/litellm_models.yaml      # New — model configuration
requirements.txt                # Modified — add litellm
```

### Model Configuration
```yaml
# config/litellm_models.yaml

model_list:
  # Layer: Fast/Cheap (default for triage, classification)
  - model_name: "fast"
    litellm_params:
      model: "groq/llama-3.3-70b-versatile"
      api_key: "os.environ/GROQ_API_KEY"
    model_info:
      max_tokens: 8192
      input_cost_per_token: 0.0
      output_cost_per_token: 0.0

  - model_name: "fast"  # fallback
    litellm_params:
      model: "groq/llama-3.1-8b-instant"
      api_key: "os.environ/GROQ_KEY_2"

  # Layer: Standard (RAG synthesis, agent responses)
  - model_name: "standard"
    litellm_params:
      model: "openai/gpt-4o-mini"
      api_key: "os.environ/OPENAI_API_KEY"

  - model_name: "standard"  # fallback
    litellm_params:
      model: "gemini/gemini-1.5-flash"
      api_key: "os.environ/GEMINI_API_KEY"

  # Layer: Complex (deep analysis, multi-step reasoning)
  - model_name: "complex"
    litellm_params:
      model: "anthropic/claude-sonnet-4-20250514"
      api_key: "os.environ/ANTHROPIC_API_KEY"

  - model_name: "complex"  # fallback
    litellm_params:
      model: "openai/gpt-4o"
      api_key: "os.environ/OPENAI_API_KEY"

router_settings:
  routing_strategy: "latency-based-routing"
  num_retries: 3
  retry_after: 5
  timeout: 30
  fallbacks:
    - fast: ["standard"]
    - standard: ["fast"]
    - complex: ["standard"]
  enable_pre_call_checks: true
```

### Interface
```python
# src/utils/litellm_router.py

class LiteLLMRouter:
    def __init__(self, config_path: str = "config/litellm_models.yaml"):
        """Initialize litellm.Router from YAML config."""

    @classmethod
    def from_env(cls) -> "LiteLLMRouter":
        """Creates singleton from config file path."""

    async def completion(
        self,
        prompt: str,
        model_tier: str = "fast",  # fast | standard | complex
        temperature: float = 0.3,
        max_tokens: int = 2048,
        **kwargs,
    ) -> dict:
        """
        Routes to appropriate model based on tier.
        Returns: {content: str, model: str, usage: {tokens, cost}, latency_ms: float}
        """

    async def completion_with_messages(
        self,
        messages: list[dict],
        model_tier: str = "fast",
        **kwargs,
    ) -> dict:
        """Chat completion with message history."""

    def get_cost_stats(self) -> dict:
        """Returns {total_cost, requests, avg_latency, by_model: {...}}"""

    def get_available_models(self) -> list[dict]:
        """Returns healthy models with latency stats."""
```

### Backward Compatibility
`llm_client.py` updated:
```python
# Old interface preserved:
def call_llm(prompt, model=None, temperature=0.3) -> str:
    # Now delegates to LiteLLMRouter.completion()
    # model param mapped: None→"fast", "gpt-4o-mini"→"standard", "claude"→"complex"
```

### Key Rotation
LiteLLM Router natively handles multiple keys per model (via duplicate model_list entries with different api_key). Our `KeyManager` class becomes unnecessary for Groq — LiteLLM handles cooldown and rotation automatically.

---

## Component 5: Python SDK

### Problem
Consuming engine-service requires knowing the REST API. OpenRAG ships SDKs (Python + TS) for frictionless integration. If we productize, SDK is essential.

### Solution
Lightweight async Python SDK wrapping Sovereign Gateway endpoints.

### Files
```
sdk/                            # New top-level package
  pyproject.toml                # SDK-specific deps (httpx, pydantic)
  engine_sdk/
    __init__.py                 # Exports EngineClient, EngineSyncClient
    client.py                   # Async client
    sync_client.py              # Sync wrapper
    models.py                   # Pydantic response models
    resources/
      rag.py                    # RAG operations
      agents.py                 # Agent operations
      graph.py                  # Graph operations
      ingest.py                 # Ingestion operations
      telemetry.py              # Metrics & stats
```

### Interface
```python
# sdk/engine_sdk/client.py

class EngineClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8766",
        api_key: str | None = None,
        timeout: float = 30.0,
    ): ...

    async def __aenter__(self) -> "EngineClient": ...
    async def __aexit__(self, *args) -> None: ...

    @property
    def rag(self) -> RAGResource:
        """RAG search operations."""

    @property
    def agents(self) -> AgentsResource:
        """Agent listing and execution."""

    @property
    def graph(self) -> GraphResource:
        """Neo4j graph operations."""

    @property
    def ingest(self) -> IngestResource:
        """Document ingestion."""

    @property
    def telemetry(self) -> TelemetryResource:
        """Metrics and pipeline stats."""


# Usage:
async with EngineClient() as client:
    # RAG search
    results = await client.rag.search("how does RAG work?", top_k=5)

    # Agent execution
    agents = await client.agents.list()
    response = await client.agents.execute("marketing", task="Generate campaign copy")

    # Graph query
    concepts = await client.graph.concepts(limit=50)
    custom = await client.graph.cypher("MATCH (c:Concept) RETURN c.name LIMIT 10")

    # Ingest
    result = await client.ingest.upload("report.pdf", category="documents")

    # Telemetry
    stats = await client.telemetry.pipeline_stats()
    costs = await client.telemetry.cost_report()
```

### Response Models
```python
# sdk/engine_sdk/models.py

class RAGResult(BaseModel):
    content: str
    source_file: str
    score: float
    engines: list[str]
    engine_count: int
    metadata: dict = {}

class AgentInfo(BaseModel):
    id: str
    name: str
    type: str
    status: str
    capabilities: list[str]
    success_rate: float | None

class AgentResponse(BaseModel):
    agent_id: str
    task: str
    result: str
    processing_time_ms: float
    model_used: str | None
    cost: float | None

class IngestResult(BaseModel):
    chunks_created: int
    source_file: str
    category: str
    models_embedded: list[str]

class PipelineStats(BaseModel):
    cache_hit_rate: float
    avg_latency_ms: float
    total_requests: int
    active_agents: int
    cost_today: float
```

### Sync Client
```python
# sdk/engine_sdk/sync_client.py

class EngineSyncClient:
    """Sync wrapper using asyncio.run() under the hood."""

    def __enter__(self) -> "EngineSyncClient": ...
    def __exit__(self, *args) -> None: ...

    # Same interface as EngineClient but sync
```

---

## Implementation Order

```
Phase 1 (parallel — no dependencies):
  ├── Component 4: LiteLLM Router (modifies llm_client.py)
  ├── Component 1: Docling Extractor (new file + docker service)
  └── Component 5: Python SDK (new package, depends only on gateway API)

Phase 2 (after Phase 1):
  ├── Component 2: Multi-Embedding (modifies vector_db.py, uses LiteLLM for embeddings)
  └── Component 3: MCP Server (uses all other components)
```

## Dependencies Added

```
litellm>=1.40.0          # Component 4
mcp[cli]>=1.0.0          # Component 3
docling>=2.0.0           # Component 1 (fallback only)
httpx>=0.26.0            # Already present
sentence-transformers    # Component 2 (nomic model)
```

## Testing Strategy

Each component gets:
- Unit tests with mocked external services
- Integration tests marked `@pytest.mark.integration`
- All tests must pass with `pytest -m "not integration"` (CI-safe)

## Documentation

- CLAUDE.md updated with new components
- Each component has docstrings following existing patterns
- MCP config JSON auto-generated for Claude Desktop + Cursor
- SDK has inline examples in docstrings
