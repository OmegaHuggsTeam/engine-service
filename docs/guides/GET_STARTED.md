# GET STARTED — Bunker Intelligence / Neural Link CRM

Definitive onboarding guide. From zero to running in under 10 minutes.

## Prerequisites

| Requirement | Version | Check |
|-------------|---------|-------|
| Python | 3.11+ | `python --version` |
| Node.js | 18+ | `node --version` |
| Docker | 24+ | `docker --version` |
| Git | 2.40+ | `git --version` |

Optional:
- Chrome (for Selenium-based extractors)
- Jitbit MacroRecorder (for hardware automation)

## Quick Setup (5 minutes)

### 1. Clone & Install

```bash
git clone https://github.com/OmegaHuggsTeam/engine-service.git
cd engine-service
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env with your keys:
# - GROQ_API_KEY (required - free at console.groq.com)
# - NEO4J_URI/USER/PASSWORD (required for graph features)
# - Optional: GEMINI_API_KEY, CLAUDE_API_KEY, TELEGRAM_BOT_TOKEN
```

### 3. Start Services

```bash
# Option A: Docker (recommended)
docker compose -f infra/docker-compose.yml up -d
# Starts: Neo4j (7474/7687), ChromaDB (8000)

# Option B: Manual
# Neo4j: download from neo4j.com, run with bolt://localhost:7687
# ChromaDB: pip install chromadb && chroma run
```

### 4. Initialize

```bash
# Create Neo4j schema (constraints, indexes)
python -c "from src.neural_link.graph.schema import create_schema; print(create_schema())"

# Initialize ChromaDB with chunks
python scripts/init_vector_db.py

# Verify
python scripts/verify_intelligence.py
```

### 5. Start the Gateway

```bash
# Sovereign Gateway (port 8766)
python -m src.neural_link.api.sovereign_gateway

# Webhook Listener (port 8765, optional)
python -m automation_hub.bridge.webhook_listener
```

### 6. Verify

```bash
# Health check
curl http://localhost:8766/api/v1/cluster/health

# List agents
curl http://localhost:8766/api/v1/agents

# Submit a test task
curl -X POST http://localhost:8766/api/v1/tasks \
  -H "Content-Type: application/json" \
  -d '{"query": "What agents are available?"}'
```

## Services Overview

| Service | Port | Purpose |
|---------|------|---------|
| Sovereign Gateway | 8766 | Main API (47 REST + 5 WebSocket) |
| Webhook Listener | 8765 | IFTTT voice commands |
| Neo4j Browser | 7474 | Graph visualization |
| Neo4j Bolt | 7687 | Graph queries |
| ChromaDB | 8000 | Vector search |
| Frontend (Next.js) | 3000 | Dashboard UI |

## Feature Overview

### Core Pipeline
- **29 Agents** — Domain (12), Operators (3), Specialists (14)
- **5-Layer Optimization** — Cache -> Triage -> Context -> Quality Gate -> Full
- **Hybrid RAG** — ChromaDB vectors + Neo4j graph + TF-IDF

### CRM Module
- Lead management with trust scoring
- Flow orchestration with n8n integration
- Interaction tracking with graph relationships

### KPI Intelligence
- Model benchmarking (cost/quality/latency per model)
- Tool scorecards (Correto 40% + Completo 30% + Qualidade 30%)
- Anomaly detection with alerts

### Automation
- IFTTT voice commands via webhook
- Jitbit macro execution
- n8n workflow composition from natural language

## Development

### Run Tests

```bash
# All Neural Link tests
python -m pytest src/neural_link/tests/ -v --tb=short

# Specific module
python -m pytest src/neural_link/tests/test_crm.py -v

# Quick check (stop on first failure)
python -m pytest src/neural_link/tests/ -x -q
```

### Project Structure

```
engine-service/
  src/
    neural_link/          # Core orchestration layer
      api/                # Gateway endpoints
      graph/              # Neo4j manager, schema, queries
      orchestrator/       # Task routing, agent selection
      rag/                # Hybrid RAG (ChromaDB + TF-IDF + Graph)
      telemetry/          # KPI, metrics, cost tracking
      agents/             # Domain agents (CRM, SendSpeed)
      services/           # Sentinel, identity manager
    agents/               # Base agent implementations
    extractors/           # Data ingestion (GitHub, n8n, video)
    divine_inspiration/   # Self-healing engine
    sentinela/            # Visual monitoring
    steady_gaze/          # Anti-detection analysis
    processors/           # Text chunking, n8n validation
    middleware/           # GroqRouter task classification
  automation_hub/         # Voice commands, IFTTT
  frontend/               # Next.js dashboard
  infra/                  # Docker, K8s manifests
  docs/                   # Documentation
  tools/                  # Utility scripts
  scripts/                # Setup scripts
```

## API Quick Reference

Full reference: `docs/api/sovereign-gateway-endpoints.md`
Postman collection: `docs/api/sovereign-gateway.postman_collection.json`

### Most Used Endpoints

```bash
# List agents
GET /api/v1/agents

# Search RAG
GET /api/v1/rag/search?q=how+to+create+campaign&top_k=5

# Create lead
POST /api/v1/crm/leads
{"name": "John", "email": "john@example.com"}

# Pipeline stats
GET /api/v1/pipeline/stats

# Model recommendations
GET /api/v1/kpi/recommend?task_type=generation&min_quality=7
```

## Troubleshooting

### Neo4j connection refused
```
# Check if running
docker ps | grep neo4j
# Verify .env
echo $NEO4J_URI  # should be bolt://localhost:7687
```

### ChromaDB not found
```
# Check if running
curl http://localhost:8000/api/v1/heartbeat
# Restart
docker restart chroma
```

### Groq 429 (rate limit)
The system handles this automatically with key rotation. Add multiple keys:
```
GROQ_KEY_1=gsk_xxx
GROQ_KEY_2=gsk_xxx
```

### Import errors
```
# Ensure you're in the project root
cd engine-service
# Install missing deps
pip install -r requirements.txt
```

### Tests failing
```
# Known pre-existing failure:
# test_handler_init_without_token (thread state assertion)
# This is NOT a regression — ignore it

# Run excluding known failure:
python -m pytest src/neural_link/tests/ -v --ignore=src/neural_link/tests/test_telegram_command_handler.py
```
