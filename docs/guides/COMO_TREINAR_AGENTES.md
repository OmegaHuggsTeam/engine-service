# Como Treinar Agentes

## 1. O que é um Agente?

**Taxonomia**:

| Tipo | Descrição | Exemplo |
|------|-----------|---------|
| **Domain** | Especialista em um domínio (CRM, Marketing) | CrmDomainAgent |
| **Specialist** | Combina RAG + expertise em tarefa específica | SpecialistAgent |
| **Operator** | Executa ações (n8n, webhooks) | ComposerAgent |
| **Generalist** | Fallback quando nenhum specialist tem confiança suficiente | — |

---

## 2. Anatomia Técnica

### AGENT_REGISTRY

Cada agente é registrado com:

- `id`: identificador único
- `name`: nome legível
- `class`: classe Python
- `domains`: lista de domínios que o agente cobre
- `description`: descrição para o selector

### Classe Base

```python
class BaseAgent:
    def execute(self, query: str, context: dict | None = None) -> str:
        """Implementação obrigatória."""
        raise NotImplementedError
```

### Método execute()

- **Input**: `query` (str), `context` (opcional: RAG chunks, graph concepts)
- **Output**: string com a resposta
- **Side effects**: podem persistir no grafo, chamar APIs, etc.

---

## 3. 5 Padrões de Init

1. **From Env**: `Agent.from_env()` — carrega config de variáveis de ambiente
2. **With Graph**: `Agent(graph_manager=gm)` — injeta GraphManager para persistência
3. **With RAG**: `Agent(hybrid_rag=rag)` — injeta retriever ChromaDB + Neo4j
4. **Stateless**: `Agent()` — sem dependências externas, stateless
5. **Factory**: `AgentFactory.get_or_create(domain)` — criação lazy via factory

---

## 4. Criando do Zero (7 passos)

1. **Crie** `src/neural_link/agents/meu_agent.py`
2. **Estenda** `BaseAgent`
3. **Implemente** `execute(query, context)`
4. **Registre** em `AGENT_REGISTRY` (em `src/neural_link/agents/__init__.py` ou equivalente)
5. **Adicione testes** em `src/neural_link/tests/test_meu_agent.py`
6. **Rode** `make test`
7. **Documente** no README ou em `docs/agents/`

### Paths exatos

- Agente: `src/neural_link/agents/meu_agent.py`
- Registry: `src/neural_link/orchestrator/agent_selector.py` (AGENT_REGISTRY ou similar)
- Testes: `src/neural_link/tests/test_meu_agent.py`

---

## 5. Adicionando Knowledge

### ChromaDB (chunks)

1. Processe documentos em chunks (ver pipeline de chunking)
2. Gere embeddings e insira no ChromaDB
3. O `HybridRAG` ou `GraphRetriever` injeta chunks no `context` do `execute()`

### Neo4j (conceitos)

1. Defina nós e relações no schema (`src/neural_link/graph/schema.py`)
2. Use `GraphManager` para inserir conceitos
3. O `GraphRetriever` busca conceitos relacionados à query e injeta no contexto

---

## 6. Armadilhas Comuns

| Armadilha | Solução |
|-----------|---------|
| **Import circular** | Use lazy import dentro do método ou factory |
| **Neo4j indisponível** | Sempre aceite `graph_manager=None` e degrade gracefully |
| **Chunks vazios** | Verifique `if context and context.get("chunks")` antes de usar |
| **Timeout em LLM** | Configure `LLM_PROVIDER`, use modelos menores para triage |
| **Alucinações** | Use rubric de avaliação, cite fontes, limite temperatura |
