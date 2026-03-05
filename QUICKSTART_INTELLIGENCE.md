# 🚀 Quick Start - Bunker Intelligence

Transforme seu Bunker em um Cérebro Operacional em 3 passos.

## ⚡ Setup em 5 Minutos

### 1. Configure o Ambiente

```bash
# Copie o .env.example e configure suas chaves
cp .env.example .env

# Edite o .env e adicione:
# GROQ_API_KEY=sua_chave_groq
# TELEGRAM_BOT_TOKEN=seu_token_telegram
# GITHUB_TOKEN=seu_token_github (opcional)
```

### 2. Execute o Setup

```bash
# Setup completo automático
python scripts/setup_intelligence.py

# Ou com teste do ComposerAgent
python scripts/setup_intelligence.py --test-composer
```

### 3. Inicie o Bot

```bash
# Iniciar bot Telegram
python -m src.neural_link.telemetry.telegram_command_handler
```

## 🎯 Uso Básico

### No Telegram

```
# Criar novo workflow
/create_n8n Criar workflow que recebe webhook e envia notificação no Telegram

# Explicar workflow existente
/explain_workflow https://github.com/zie619/zie619.github.io
```

### Via Python

```python
# Criar workflow programaticamente
from src.neural_link.agents.composer_agent import ComposerAgent

agent = ComposerAgent()
result = agent.compose_workflow(
    "Workflow que monitora Google Sheets e envia email"
)

print(result["workflow"])  # JSON do workflow n8n
```

## 🔍 Verificação

```bash
# Verificar se tudo está funcionando
python scripts/verify_intelligence.py

# Verificação detalhada
python scripts/verify_intelligence.py --verbose
```

## 📊 O Que Foi Criado?

Após o setup, você terá:

```
vault/Knowledge/
├── n8n_capabilities.md    # Catálogo de integrações e serviços
└── n8n_recipes.md         # Biblioteca de receitas por categoria

data/chunks/
└── n8n_master_context.json  # Contexto mestre para agentes

data/generated_workflows/
└── *.json                   # Workflows gerados pelo ComposerAgent
```

## 🐛 Troubleshooting Rápido

### ChromaDB vazio?
```bash
python scripts/mass_ingestion.py
```

### ComposerAgent não funciona?
```bash
python scripts/setup_intelligence.py --skip-ingestion
```

### Bot não responde?
```bash
# Verificar token
echo $TELEGRAM_BOT_TOKEN

# Testar conectividade
curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe
```

## 📚 Documentação Completa

- [Setup Detalhado](docs/INTELLIGENCE_SETUP.md)
- [Comandos Telegram](vault/Guides/Telegram_Commands.md)

## 🎓 Exemplos

### Exemplo 1: Notificação Simples
```
/create_n8n Receber webhook e enviar mensagem no Telegram
```

### Exemplo 2: Integração com Sheets
```
/create_n8n Monitorar Google Sheets e enviar email quando houver nova linha
```

### Exemplo 3: Pipeline Completo
```
/create_n8n Webhook -> Supabase -> Telegram notification
```

## 🔥 Próximos Passos

1. **Adicione mais templates:** Use `/explain_workflow <url>` para ingerir novos workflows
2. **Customize workflows:** Edite os JSONs gerados em `data/generated_workflows/`
3. **Explore o conhecimento:** Abra `vault/Knowledge/n8n_capabilities.md` no Obsidian

---

**Dúvidas?** Consulte [docs/INTELLIGENCE_SETUP.md](docs/INTELLIGENCE_SETUP.md)
