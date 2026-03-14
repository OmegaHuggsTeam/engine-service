# Guia Rapido - Engine Service (Codespaces)

Oi Mateus! Este guia vai te ajudar a comecar a trabalhar no Engine Service usando GitHub Codespaces.

## O que e este projeto?

O **Engine Service** e o cerebro de IA da plataforma HuggsAI. Ele processa documentos, gera conteudo e responde perguntas usando um pipeline inteligente de 4 camadas:

- **Layer 0 (Cache)**: Respostas ja conhecidas, custo zero
- **Layer 1 (Triage)**: Classificacao por palavras-chave, sem IA
- **Layer 2 (RAG)**: Busca em documentos com ChromaDB e Neo4j
- **Layer 3 (LLM)**: Chamada direta para modelos de IA (Haiku/Sonnet/Opus)

O projeto e construido com Python (FastAPI) e e o backend de inteligencia que o CRM consome.

## Como comecar

### 1. Abrir no Codespaces

1. Va ate o repositorio no GitHub: `OmegaHuggsTeam/engine-service`
2. Clique no botao verde **"Code"**
3. Selecione a aba **"Codespaces"**
4. Clique em **"Create codespace on feat/content-factory"**
5. Aguarde o ambiente carregar (primeira vez demora uns 5-8 minutos por causa do Python + Docker)

### 2. O que acontece automaticamente

Quando o Codespace iniciar, ele vai:
- Instalar Python 3.11, Node.js 20, Docker e todas as ferramentas
- Rodar `pip install -r requirements.txt` para instalar as dependencias Python
- Configurar as extensoes do VS Code (Python, Pylance, GitLens, Docker, etc.)

### 3. Rodar o projeto

Depois que tudo carregar, abra o terminal e rode:

```bash
python -m uvicorn app.main:app --port 8766 --reload
```

A API vai estar disponivel em `http://localhost:8766`.

Para ver a documentacao interativa da API, acesse: `http://localhost:8766/docs`

### 4. Entender a estrutura

```
app/
  main.py           # Ponto de entrada da API (FastAPI)
  routers/          # Endpoints da API
  services/         # Logica de negocio
  models/           # Modelos de dados
  pipeline/         # Pipeline de 4 camadas
tests/              # Testes automatizados
docs/               # Documentacao e planos
requirements.txt    # Dependencias Python
```

## Extensoes instaladas

| Extensao | Para que serve |
|----------|---------------|
| **Python** | Suporte completo a Python (debug, run, etc.) |
| **Pylance** | Autocomplete inteligente e type checking para Python |
| **Black Formatter** | Formata codigo Python automaticamente ao salvar |
| **GitLens** | Mostra quem alterou cada linha e historico do git |
| **Thunder Client** | Testar APIs (tipo Postman, mas dentro do VS Code) |
| **Error Lens** | Mostra erros inline no codigo (mais visivel) |
| **Docker** | Gerenciar containers Docker visualmente |

## Servicos auxiliares (Docker)

O Engine Service depende de alguns servicos que rodam em Docker:

| Servico | Porta | Para que serve |
|---------|-------|---------------|
| **ChromaDB** | 8000 | Banco de dados vetorial para busca semantica |
| **Neo4j** | 7474 | Banco de grafos para relacoes entre documentos |

Para subir esses servicos (se necessario):

```bash
docker compose up -d
```

## Comandos uteis

```bash
# API
python -m uvicorn app.main:app --port 8766 --reload   # Iniciar API
python -m pytest                                        # Rodar testes
python -m pytest --cov                                  # Testes com cobertura

# Docker
docker compose up -d       # Subir servicos auxiliares
docker compose down        # Parar servicos
docker compose logs -f     # Ver logs dos servicos
```

## Conceitos importantes para estudar

Se voce esta comecando, recomendo estudar nessa ordem:
1. **FastAPI** - Framework web Python (docs: fastapi.tiangolo.com)
2. **APIs REST** - Como funcionam requisicoes HTTP
3. **Docker** - Containers e como rodar servicos isolados
4. **RAG** - Retrieval Augmented Generation (como a IA busca em documentos)

## Duvidas?

- Consulte a [Wiki do projeto](https://github.com/OmegaHuggsTeam/engine-service/wiki)
- Fale com **@HuggsF** (Hugo) no GitHub
- Abra uma issue se encontrar um bug

Bem-vindo ao time!
