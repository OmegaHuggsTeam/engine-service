# MCP Engine Service

[![CI Tests](https://github.com/OmegaHuggsTeam/engine-service/actions/workflows/ci-tests.yml/badge.svg)](https://github.com/OmegaHuggsTeam/engine-service/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Plataforma multi-agente para extração, chunking e RAG. Processa vídeos, transcrições e textos, gerando chunks indexados no ChromaDB para consulta por agentes especialistas. Inclui pipeline de 5 camadas, Neo4j e Sovereign Gateway.

```
                    ┌─────────────┐
                    │   Gateway   │
                    │  (REST+WS)  │
                    └──────┬──────┘
                           │
    ┌──────────────────────┼──────────────────────┐
    │                      │                      │
    ▼                      ▼                      ▼
┌───────┐            ┌──────────┐           ┌─────────┐
│  RAG  │            │ Pipeline │           │  Neo4j  │
│ChromaDB│            │ 5-Layer  │           │  Graph  │
└───────┘            └──────────┘           └─────────┘
```

## Features

- **RAG Pipeline**: ChromaDB + Neo4j hybrid retrieval
- **29+ Agentes**: Domain, Specialist, Operator
- **5-Layer Optimization**: Cache, triage, specialist, eval, refine
- **Sovereign Gateway**: 47 REST + 5 WebSocket endpoints
- **Self-Bootstrap**: `run_init.py` configura tudo em um comando

## Quick Start

```bash
cd engine-service
python run_init.py
```

📖 **Novo por aqui?** → [ONBOARDING.md](docs/guides/ONBOARDING.md) | **Contribuir** → [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)

O **run_init.py** é um script de **Self-Bootstrap** que configura tudo do zero:

1. Verifica ambiente virtual (venv)
2. Instala dependências automaticamente (`pip install -r requirements.txt`)
3. Configura GROQ_API_KEY (pede para colar se faltar)
4. Cria estrutura de pastas
5. Inicializa ChromaDB (migra JSONs se existirem)
6. Testa a API Groq
7. Oferece iniciar o dashboard

**Não é necessário** rodar `pip install`, `setup_project.py` ou configurar `.env` manualmente antes. O run_init.py faz tudo.

---

## Pré-requisitos

- **Python 3.10+**
- **Conexão com internet** (para pip e APIs)

---

## Configuração Manual (opcional)

Se preferir configurar manualmente:

```bash
# 1. Ambiente virtual (recomendado)
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/Mac

# 2. Dependências
pip install -r requirements.txt

# 3. Chave Groq (obrigatória)
# Crie .env com:
GROQ_API_KEY=gsk_sua-chave
# Obtenha em: https://console.groq.com

# 4. Executar
python run_init.py
```

---

## Fluxo de Dados

```
data/raw/                    (várias pastas e subpastas)
  IA_Basica/
    aula_01.mp4
  Marketing/
    modulo_01.txt
        |
        v  [Transcrição - Whisper]  ou  [Cópia TXT]
        |
data/processed/
  IA_Basica/
    aula_01.txt
    aula_01_clean.txt
        |
        v  [Chunking - Recursive Split]
        |
data/chunks/
  IA_Basica_aula_01_chunks.json
        |
        v  [Embeddings + ChromaDB]
        |
db/chroma/                   (Vector Database persistente)
```

---

## Como Adicionar Novos Cursos

1. Abra o dashboard (`streamlit run dashboard.py`)
2. Aba **Upload**: arraste MP4 ou TXT
3. Organize em subpastas: `data/raw/NovoCurso/aula_01.mp4`
4. Aba **Pipeline**: clique em **Processar Tudo**

---

## Agentes

| Agente | Persona | Função |
|--------|---------|--------|
| **Marketing** | Diretor de Marketing | Estratégias, ROI |
| **Social Media** | Social Media Manager | Threads, Reels, Legendas |
| **Analytics** | Growth Hacker | Métricas, funil |
| **IA Engineer** | Prompt Engineer | Automação, Make/n8n |
| **ComposerAgent** | n8n Specialist | Cria workflows n8n combinando templates |

LLM padrão: **Groq** (llama3-70b-8192) - custo zero, alta velocidade.

---

## 🧠 Bunker Intelligence - Cérebro Operacional n8n

Sistema avançado de criação de workflows n8n usando IA. Ingere 4.300+ workflows do repositório zie619 e cria novos workflows combinando templates inteligentemente.

### Quick Start Intelligence

```bash
# Setup completo em um comando
python scripts/setup_intelligence.py

# Verificar se tudo está funcionando
python scripts/verify_intelligence.py

# Testar ComposerAgent localmente
python scripts/demo_composer.py
```

### Comandos Telegram

```
# Criar novo workflow
/create_n8n Criar workflow que recebe webhook e envia notificação no Telegram

# Explicar workflow existente
/explain_workflow https://github.com/zie619/zie619.github.io
```

### Documentação Completa

- [Quick Start Intelligence](QUICKSTART_INTELLIGENCE.md)
- [Setup Detalhado](docs/INTELLIGENCE_SETUP.md)
- [Comandos Telegram](vault/Guides/Telegram_Commands.md)

---

## Scripts Úteis

| Comando | Descrição |
|---------|-----------|
| `python run_init.py` | **Self-Bootstrap** - configura tudo do zero |
| `streamlit run dashboard.py` | Inicia o dashboard |
| `python -m src.agents.marketing_agent` | Chat no terminal |

---

## Estrutura do Projeto

```
engine-service/
  run_init.py           # Self-Bootstrap - unico comando necessario
  dashboard.py          # Interface Streamlit
  setup_project.py      # Criação de pastas
  requirements.txt
  .env / .env.example
  data/raw, processed, chunks
  db/chroma
  src/extractors, processors, agents, utils
```
