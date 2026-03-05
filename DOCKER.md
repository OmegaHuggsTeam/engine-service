# Bunker - Docker

## Serviços

| Serviço | Porta | Descrição |
|---------|-------|-----------|
| **app** | - | Sentinela/Agentes, Telegram Command Handler |
| **chroma** | 8000 | ChromaDB (chunks n8n) |
| **neo4j** | 7474 (HTTP), 7687 (Bolt) | Neo4j (grafos) |
| **evidence** | 5000 | Evidence Server (fotos de falha) |

## Uso

```bash
# Subir todos os serviços
docker compose up -d

# Ver logs
docker compose logs -f app

# Parar
docker compose down
```

## Variáveis de Ambiente

Crie `.env` na raiz do projeto:

```env
# Obrigatório para Telegram /explain_workflow
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...

# LLM (Groq ou OpenAI)
GROQ_API_KEY=gsk_xxx
# ou OPENAI_API_KEY=sk-xxx

# Opcional: GitHub para ingest
GITHUB_TOKEN=ghp_xxx
```

## Rede Interna

Os agentes usam nomes de serviço:

- **ChromaDB**: `http://chroma:8000` (CHROMA_HOST=chroma)
- **Neo4j**: `bolt://neo4j:7687` (NEO4J_URI)
- **Evidence Server**: `http://evidence:5000` (EVIDENCE_SERVER_HOST=evidence)

## Testar /explain_workflow

1. Suba o stack: `docker compose up -d`
2. Aguarde ChromaDB e Neo4j ficarem healthy
3. Envie no Telegram: `/explain_workflow https://github.com/zie619/zie619.github.io`
4. O bot deve ingerir, processar e responder

## Build Otimizado

Para rebuild mais rápido (sem cache):

```bash
docker compose build --no-cache app
```

## Volumes

- `chroma_data`: persistência do ChromaDB
- `neo4j_data`: persistência do Neo4j
- `evidence_data`: fotos de evidência (compartilhado app + evidence)
