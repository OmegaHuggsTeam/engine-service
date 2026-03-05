# 🧠 Bunker Intelligence Setup - Cérebro Operacional n8n

Este documento descreve o processo completo de transformação do Bunker em um Cérebro Operacional capaz de criar workflows n8n inteligentes.

## 📋 Visão Geral

O sistema é composto por três pilares principais:

1. **Ingestão em Massa** - Alimenta o RAG com 4.300+ workflows do repositório zie619
2. **Geração de Conhecimento** - Cria arquivos de referência e contexto mestre
3. **Composição Inteligente** - ComposerAgent cria novos workflows combinando templates

## 🏗️ Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    BUNKER INTELLIGENCE                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   GitHub     │─────▶│   ChromaDB   │─────▶│  Agentes  │ │
│  │  Ingestor    │      │   (Vector)   │      │           │ │
│  └──────────────┘      └──────────────┘      │ Specialist│ │
│         │                      │              │ Composer  │ │
│         │                      │              │ Viajante  │ │
│         ▼                      ▼              └───────────┘ │
│  ┌──────────────┐      ┌──────────────┐             │      │
│  │  n8n_master  │      │   Neo4j      │             │      │
│  │  _context    │      │   (Graph)    │             │      │
│  └──────────────┘      └──────────────┘             │      │
│         │                      │                     │      │
│         └──────────────────────┴─────────────────────┘      │
│                                │                             │
│                                ▼                             │
│                      ┌──────────────────┐                   │
│                      │  Telegram Bot    │                   │
│                      │  /create_n8n     │                   │
│                      │  /explain_workflow│                  │
│                      └──────────────────┘                   │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Setup Rápido

### Pré-requisitos

```bash
# Variáveis de ambiente necessárias
export GITHUB_TOKEN="seu_token_github"          # Opcional, mas recomendado
export TELEGRAM_BOT_TOKEN="seu_token_telegram"  # Obrigatório para bot
export GROQ_API_KEY="sua_chave_groq"           # Obrigatório para LLM
```

### Instalação

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Executar setup completo
python scripts/setup_intelligence.py

# 3. (Opcional) Testar ComposerAgent
python scripts/setup_intelligence.py --test-composer
```

### Uso Manual (Passo a Passo)

Se preferir executar cada etapa manualmente:

```bash
# Etapa 1: Ingestão em massa
python scripts/mass_ingestion.py

# Etapa 2: Verificar ChromaDB
python -c "from src.utils.vector_db import get_collection_stats; print(get_collection_stats())"

# Etapa 3: Iniciar bot Telegram
python -m src.neural_link.telemetry.telegram_command_handler
```

## 📚 Componentes Principais

### 1. GitHub Ingestor

**Arquivo:** `src/extractors/github_ingestor.py`

Responsável por:
- Baixar workflows do repositório zie619/zie619.github.io
- Extrair módulos de operação de cada workflow
- Salvar chunks no ChromaDB com categoria `external_template`
- Manter metadados de source_url para citação

**Uso:**
```python
from src.extractors.github_ingestor import ingest_repository

stats = ingest_repository(
    "https://github.com/zie619/zie619.github.io",
    save_to_chromadb=True
)
```

### 2. n8n Knowledge Processor

**Arquivo:** `src/processors/n8n_knowledge.py`

Gera três tipos de arquivos:

#### a) `n8n_capabilities.md`
- Integrações possíveis entre serviços
- Padrões de conexão mais comuns
- Catálogo de serviços disponíveis
- Node types de referência
- Credenciais necessárias

#### b) `n8n_recipes.md`
- Biblioteca de receitas agrupadas por categoria
- Workflows classificados (AI/LLM, Marketing, DevOps, etc.)
- Descrição de fluxos e serviços utilizados

#### c) `n8n_master_context.json`
- Chunks de best practices por categoria
- Padrões globais de conexão
- Usado pelo SpecialistAgent para contexto

**Uso:**
```python
from src.processors.n8n_knowledge import (
    generate_capabilities_md,
    generate_recipes_md,
    generate_master_context
)

# Carregar módulos do ChromaDB
from src.utils.vector_db import get_all_chunks
modules = [c for c in get_all_chunks() if c.get("category") == "external_template"]

# Gerar arquivos
generate_capabilities_md(modules, vault_path="vault")
generate_recipes_md(modules, vault_path="vault")
generate_master_context(modules, output_dir="data/chunks")
```

### 3. ComposerAgent

**Arquivo:** `src/neural_link/agents/composer_agent.py`

Agente especializado em compor workflows n8n:

**Processo:**
1. Recebe objetivo em linguagem natural
2. Busca templates relevantes no ChromaDB via HybridRAG
3. Identifica componentes necessários (trigger, processadores, output)
4. Compõe JSON n8n válido combinando templates
5. Valida e enriquece com metadados
6. Retorna workflow pronto para importação

**Uso:**
```python
from src.neural_link.agents.composer_agent import ComposerAgent

agent = ComposerAgent()
result = agent.compose_workflow(
    "Criar workflow que monitora webhook e envia notificação no Telegram"
)

# result contém:
# - workflow: JSON do workflow n8n
# - templates_used: Lista de templates utilizados
# - reasoning: Explicação da composição
# - metadata: Metadados do workflow
```

### 4. Telegram Command Handler

**Arquivo:** `src/neural_link/telemetry/telegram_command_handler.py`

Bot Telegram com dois comandos principais:

#### `/explain_workflow <url>`
- Ingere workflow de URL (GitHub repo ou .json)
- Usa SpecialistAgent para explicar estrutura
- Retorna análise detalhada

#### `/create_n8n <objetivo>`
- Usa ComposerAgent para criar workflow
- Salva JSON em `data/generated_workflows/`
- Retorna detalhes e instruções de importação

**Uso:**
```bash
# Iniciar bot
python -m src.neural_link.telemetry.telegram_command_handler

# No Telegram:
/create_n8n Criar workflow que recebe webhook e envia email
```

## 📊 Estatísticas Esperadas

Após a ingestão completa do repositório zie619:

- **Workflows processados:** ~4.300+
- **Chunks no ChromaDB:** ~15.000+
- **Serviços únicos:** ~200+
- **Integrações possíveis:** ~500+
- **Categorias de workflows:** 8 (AI/LLM, Marketing, Communication, DevOps, Security, Data Processing, Media, General Automation)

## 🔧 Troubleshooting

### ChromaDB vazio após ingestão

**Problema:** `get_collection_stats()` retorna count=0

**Solução:**
```bash
# Verificar se a ingestão foi executada com save_to_chromadb=True
python scripts/mass_ingestion.py

# Verificar logs
tail -f logs/bunker.log | grep "github_ingestor"
```

### ComposerAgent não encontra templates

**Problema:** `/create_n8n` retorna "Nenhum template relevante encontrado"

**Solução:**
```python
# Verificar se há templates external_template no ChromaDB
from src.utils.vector_db import get_all_chunks
external = [c for c in get_all_chunks() if c.get("category") == "external_template"]
print(f"Templates encontrados: {len(external)}")

# Se vazio, executar ingestão
python scripts/mass_ingestion.py
```

### Workflow gerado não funciona no n8n

**Problema:** Erros de validação ao importar JSON

**Solução:**
1. Verifique versões dos nodes no n8n
2. Configure credenciais necessárias (listadas na resposta do bot)
3. Ajuste parâmetros específicos manualmente
4. Use o workflow como base e customize

### Bot Telegram não responde

**Problema:** Comandos não são processados

**Solução:**
```bash
# Verificar se TELEGRAM_BOT_TOKEN está configurado
echo $TELEGRAM_BOT_TOKEN

# Verificar logs do handler
python -m src.neural_link.telemetry.telegram_command_handler

# Testar conectividade
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe
```

## 📈 Próximos Passos

### Fase 2: Containerização (Docker)

- [ ] Criar Dockerfile para o Bunker
- [ ] Docker Compose com ChromaDB, Neo4j e Bunker
- [ ] Volumes persistentes para dados
- [ ] Health checks e restart policies

### Fase 3: Sincronia de Grafos (Neo4j)

- [ ] Migrar conceitos para Neo4j
- [ ] Criar relacionamentos entre workflows
- [ ] Implementar busca por similaridade de grafos
- [ ] Visualização de dependências

### Fase 4: Agentes Avançados

- [ ] **Sentinela** - Monitora execuções e detecta anomalias
- [ ] **Viajante** - Explora e mapeia novos workflows
- [ ] **Especialista** - Otimiza workflows existentes

## 📖 Referências

- [Guia de Comandos Telegram](../vault/Guides/Telegram_Commands.md)
- [Documentação n8n](https://docs.n8n.io/)
- [Repositório zie619](https://github.com/zie619/zie619.github.io)

## 🤝 Contribuindo

Para adicionar novos templates ao sistema:

1. Use `/explain_workflow <url>` para ingerir workflows individuais
2. Execute `mass_ingestion.py` para repositórios completos
3. Regenere conhecimento: `python scripts/setup_intelligence.py --skip-ingestion`

---

**Última atualização:** 2026-03-03
**Versão:** 1.0
**Autor:** Hugo (Bunker Intelligence Team)
