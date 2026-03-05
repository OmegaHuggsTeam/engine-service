# MCP Engine Service

[![CI Tests](https://github.com/psFournier/engine-service/actions/workflows/ci-tests.yml/badge.svg)](https://github.com/psFournier/engine-service/actions/workflows/ci-tests.yml)
[![CI Frontend](https://github.com/psFournier/engine-service/actions/workflows/ci-frontend.yml/badge.svg)](https://github.com/psFournier/engine-service/actions/workflows/ci-frontend.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Multi-agent AI platform with RAG, Neo4j knowledge graph, and 5-layer optimization pipeline for training and evaluating specialized agents.

```
                         ┌──────────────────┐
                         │ Sovereign Gateway │
                         │  47 REST + 5 WS   │
                         └────────┬─────────┘
                                  │
         ┌────────────────────────┼────────────────────────┐
         │                        │                        │
         v                        v                        v
   ┌───────────┐          ┌──────────────┐          ┌───────────┐
   │  HybridRAG │          │  Orchestrator │          │   Neo4j   │
   │  ChromaDB  │          │   5-Layer     │          │   Graph   │
   └───────────┘          └──────────────┘          └───────────┘
         │                        │                        │
         │              ┌─────────┼─────────┐              │
         │              v         v         v              │
         │         ┌────────┐ ┌────────┐ ┌────────┐        │
         └────────>│ Domain │ │Special.│ │Operator│<───────┘
                   │ Agents │ │ Agents │ │ Agents │
                   └────────┘ └────────┘ └────────┘
                        29 Specialized Agents
```

## Quick Start

```bash
git clone https://github.com/psFournier/engine-service.git
cd engine-service
python -m venv .venv && source .venv/bin/activate  # or .venv\Scripts\activate on Windows
make install
python run_init.py       # self-bootstrap: installs deps, configures env, inits ChromaDB
make docker-up           # starts Neo4j
make gateway             # starts Sovereign Gateway on :8766
```

See [ONBOARDING.md](docs/guides/ONBOARDING.md) for the full setup guide.

## Features

- **29 Specialized Agents** — Domain (CRM, Marketing, SendSpeed), Specialist (DevOps, Security, NLP), Operator (Groq, Gemini, Claude)
- **5-Layer Optimization Pipeline** — Cache, triage (8B), specialist routing, quality gate, feedback loop
- **Hybrid RAG** — ChromaDB vector search + Neo4j graph retrieval with adaptive truncation
- **Sovereign Gateway** — 47 REST + 5 WebSocket endpoints (FastAPI)
- **Telemetry** — Per-request cost tracking, model benchmarks, KPI anomaly detection
- **Self-Sovereign CRM** — Lead scoring, flow canvas, graph-powered contact management
- **Next.js Dashboard** — Real-time metrics, agent cards, orchestrator chat, use case roadmap
- **924+ Tests** — Unit, integration, property-based, and E2E

## Project Structure

```
src/                     # Python core
  agents/                # Domain agents (marketing, social, CRM)
  extractors/            # Data extraction (GitHub, n8n, video)
  neural_link/           # Neural Link core
    agents/              # Specialist agents (15+)
    orchestrator/        # 5-layer pipeline, agent selector
    graph/               # Neo4j schema, queries, migrations
    rag/                 # Hybrid RAG, query router
    api/                 # Sovereign Gateway, webhooks
    telemetry/           # Cost tracker, model benchmark, KPI
  processors/            # Chunking and cleaning
  rag/                   # TF-IDF RAG system
  utils/                 # LLM client, vector DB, cost context
automation_hub/          # Voice commands, IFTTT, Groq operators
frontend/                # Next.js dashboard
infra/                   # Docker, Kubernetes manifests
tests/                   # 924+ tests
docs/                    # Specs, guides, audits
```

## Development

```bash
make test                # run all tests
make test-fast           # skip slow/integration tests
make lint                # ruff + black check
make format              # auto-format
make benchmark           # offline pipeline benchmark
make validate            # verify core imports
```

## Guides

- [Onboarding](docs/guides/ONBOARDING.md) — Zero to first agent
- [How to Prompt](docs/guides/HOW_TO_PROMPT.md) — Prompt engineering with statistical evidence
- [Training Agents](docs/guides/COMO_TREINAR_AGENTES.md) — Create and register custom agents
- [Evaluating Responses](docs/guides/COMO_AVALIAR_RESPOSTAS.md) — Scoring rubric (Correto 40% + Completo 30% + Qualidade 30%)

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) and [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md).

## License

MIT
