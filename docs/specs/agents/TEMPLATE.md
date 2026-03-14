# [Nome do Agente] - Especificação Técnica

## 📋 Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | [Nome do Agente] |
| **Tipo** | [Domain / Specialist / Operator / System] |
| **Versão** | 1.0.0 |
| **Status** | [Active / Development / Deprecated] |
| **Módulo** | `src.agents.[nome_modulo]` |
| **Criado em** | YYYY-MM-DD |
| **Última Atualização** | YYYY-MM-DD |

---

## 🎯 Função Core

[Descrição concisa da responsabilidade principal do agente em 2-3 frases]

### Responsabilidades Primárias
- Responsabilidade 1
- Responsabilidade 2
- Responsabilidade 3

### Responsabilidades Secundárias
- Responsabilidade secundária 1
- Responsabilidade secundária 2

---

## 🧠 Skills Necessárias

### Skills Obrigatórias
1. **[Nome da Skill]**
   - Descrição: [O que faz]
   - Prioridade: Alta
   - Status: [Implementada / Pendente]

2. **[Nome da Skill]**
   - Descrição: [O que faz]
   - Prioridade: Alta
   - Status: [Implementada / Pendente]

### Skills Opcionais
1. **[Nome da Skill]**
   - Descrição: [O que faz]
   - Prioridade: Média
   - Status: [Implementada / Pendente]

---

## 📥 Input / Output

### Input Esperado

```json
{
  "query": "string - Pergunta ou comando do usuário",
  "context": {
    "session_id": "string - ID da sessão",
    "user_preferences": {},
    "history": []
  },
  "parameters": {
    "param1": "valor1",
    "param2": "valor2"
  }
}
```

### Output Esperado

```json
{
  "answer": "string - Resposta gerada",
  "confidence": 0.95,
  "sources": ["chunk_id_1", "chunk_id_2"],
  "metadata": {
    "processing_time_ms": 1234,
    "model_used": "llama3-70b-8192",
    "tokens_used": 500
  },
  "actions": [
    {
      "type": "skill_execution",
      "skill": "nome_da_skill",
      "result": "success"
    }
  ]
}
```

---

## 🔗 Contexto de Memória (Obsidian/Neo4j)

### Nodes Relacionados
- **Concepts**: [Lista de conceitos que o agente domina]
- **Skills**: [Lista de skills que o agente possui]
- **Tasks**: [Tipos de tasks que o agente executa]

### Relationships
- `(:Agent)-[:SPECIALIZES_IN]->(:Concept)`
- `(:Agent)-[:OWNS]->(:Skill)`
- `(:Agent)-[:EXECUTES]->(:Task)`

### Queries Cypher Relevantes

```cypher
// Buscar especialização do agente
MATCH (a:Agent {name: "[Nome do Agente]"})-[:SPECIALIZES_IN]->(c:Concept)
RETURN c.name, c.domain, c.confidence

// Buscar skills do agente
MATCH (a:Agent {name: "[Nome do Agente]"})-[:OWNS]->(s:Skill)
RETURN s.name, s.success_count, s.failure_count

// Buscar histórico de tasks
MATCH (a:Agent {name: "[Nome do Agente]"})<-[:ASSIGNED_TO]-(t:Task)
WHERE t.created_at > datetime() - duration('P7D')
RETURN t.description, t.status, t.priority
ORDER BY t.created_at DESC
```

---

## 🔧 Dependências Técnicas

### Bibliotecas Python
```txt
groq>=0.4.0
chromadb>=0.4.0
neo4j>=5.0.0
pydantic>=2.0.0
```

### Serviços Externos
- **ChromaDB**: Busca vetorial de contexto
- **Neo4j**: Grafo de conhecimento
- **Groq API**: LLM para geração de respostas
- **[Outros serviços]**

### Variáveis de Ambiente
```bash
GROQ_API_KEY=gsk_...
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
CHROMA_HOST=localhost
CHROMA_PORT=8000
```

---

## 📊 Métricas de Performance

### KPIs
- **Success Rate**: > 90%
- **Response Time**: < 2s (p95)
- **Token Efficiency**: < 1000 tokens/query
- **Context Relevance**: > 0.8

### Monitoramento
```python
# Exemplo de logging de métricas
{
  "agent": "[nome_agente]",
  "timestamp": "2026-03-03T10:00:00Z",
  "metrics": {
    "success_rate": 0.95,
    "avg_response_time_ms": 1234,
    "avg_tokens_used": 500,
    "context_relevance": 0.85
  }
}
```

---

## 🧪 Testes

### Casos de Teste Unitários
1. **Teste de Input Válido**
   - Input: [exemplo]
   - Output esperado: [exemplo]

2. **Teste de Input Inválido**
   - Input: [exemplo]
   - Comportamento esperado: [erro ou fallback]

### Casos de Teste de Integração
1. **Integração com ChromaDB**
   - Cenário: [descrição]
   - Validação: [critério]

2. **Integração com Neo4j**
   - Cenário: [descrição]
   - Validação: [critério]

### Comandos de Teste
```bash
# Testes unitários
pytest tests/unit/test_[nome_agente].py -v

# Testes de integração
pytest tests/integration/test_[nome_agente]_integration.py -v

# Teste manual
python -c "from src.agents.[nome_modulo] import [NomeAgente]; agent = [NomeAgente](); print(agent.ask('teste'))"
```

---

## 🔄 Integração com Outros Agentes

### Agentes Upstream (fornecem input)
- **[Nome do Agente]**: [Como interage]

### Agentes Downstream (recebem output)
- **[Nome do Agente]**: [Como interage]

### Padrões de Comunicação
- **Síncrono**: Chamada direta via método `ask()` ou `process()`
- **Assíncrono**: Fila de tasks no Neo4j
- **Event-driven**: Webhook/callback

---

## 📝 Exemplos de Uso

### Exemplo 1: [Caso de Uso Comum]
```python
from src.agents.[nome_modulo] import [NomeAgente]

agent = [NomeAgente]()
result = agent.ask(
    query="[exemplo de query]",
    context={"session_id": "test_123"}
)

print(result["answer"])
print(f"Confidence: {result['confidence']}")
```

### Exemplo 2: [Caso de Uso Avançado]
```python
# [Código de exemplo]
```

---

## 🐛 Troubleshooting

### Problema Comum 1
- **Sintoma**: [Descrição]
- **Causa**: [Explicação]
- **Solução**: [Passos]

### Problema Comum 2
- **Sintoma**: [Descrição]
- **Causa**: [Explicação]
- **Solução**: [Passos]

---

## 🗺️ Roadmap

### Versão Atual (1.0.0)
- ✅ Feature 1
- ✅ Feature 2

### Próxima Versão (1.1.0)
- ⏳ Feature 3
- ⏳ Feature 4

### Futuro (2.0.0)
- 💡 Feature 5
- 💡 Feature 6

---

## 📚 Referências

- [Link para documentação relacionada]
- [Link para issues/PRs relevantes]
- [Link para papers/artigos]

---

**Mantido por**: [Nome do time/pessoa]
**Última Revisão**: YYYY-MM-DD
