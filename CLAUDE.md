# CLAUDE.md — engine-service

## Projeto

**Produto**: MCP Engine Service — Plataforma multi-agente AI
**Repo**: OmegaHuggsTeam/engine-service
**Wiki**: https://github.com/OmegaHuggsTeam/engine-service/wiki

## Stack

- **Backend**: Python 3.11+, FastAPI (Sovereign Gateway)
- **Banco Vetorial**: ChromaDB (RAG)
- **Banco Grafo**: Neo4j (Knowledge Graph)
- **LLM**: Groq (Llama 3), OpenAI, Gemini, Claude
- **Frontend**: Next.js 16, Tailwind CSS, D3.js
- **Infra**: Docker Compose (5 servicos), Telegram Bot
- **Testes**: pytest (924+ testes), Hypothesis

## Estrutura

```
src/
  neural_link/
    orchestrator/     — Pipeline de otimizacao 5 camadas
    agents/           — 29 agentes especializados
    graph/            — Neo4j manager
    rag/              — HybridRAG (vetor + grafo)
    api/              — Sovereign Gateway (47 REST + 5 WS)
    telemetry/        — Custos, KPI, Telegram
  extractors/         — GitHub, video, PDF, web
  middleware/          — GroqRouter, cache
  sentinela/          — Selenium automation
  processors/         — Chunking, cleaning
automation_hub/       — Voice/IFTTT/Hardware
frontend/             — Next.js dashboard
tests/                — unit/, integration/, property/
```

## Comandos

```bash
make install          # Instalar dependencias
make init             # Bootstrap (run_init.py)
make test             # Rodar todos os testes
make test-fast        # Testes rapidos (sem slow/integration)
make test-cov         # Testes com cobertura
make lint             # ruff + black check
make format           # ruff --fix + black
make check            # lint + test (CI)
make docker-up        # Subir stack Docker
make gateway          # Sovereign Gateway (porta 8766)
```

## Convencoes de Codigo

- Arquivos: `snake_case.py`
- Classes: `PascalCase`
- Funcoes/variaveis: `snake_case`
- Constantes: `UPPER_SNAKE_CASE`
- Type hints obrigatorios
- Docstrings Google style para funcoes publicas
- Formatter: black (line-length=100)
- Linter: ruff (E, F, W, I)
- Cobertura minima: 80% (novo codigo), 90% (critico)

## Commits

Conventional Commits obrigatorio:
```
feat(orchestrator): adiciona camada de cache semantico
fix(rag): corrige ranking de chunks duplicados
test(agents): adiciona testes para MarketingAgent
```

## Regras

1. SEMPRE rodar `make check` antes de push
2. NUNCA commitar .env ou secrets (usar .env.example como referencia)
3. Consultar wiki para arquitetura, API, guias de agentes
4. Consultar CONTRIBUTING.md para workflow completo
5. Branches: feat/*, fix/*, docs/* a partir de develop
6. PRs obrigatorios para main e develop
7. Testes obrigatorios para novo codigo
