# HOW TO PROMPT — Guia Técnico de Qualidade

## 1. Evidência Estatística

Nosso benchmark multi-ferramenta demonstra o impacto direto da qualidade do prompt:

| Tool        | Structured Prompt Score | Vague Prompt Score | Delta |
|-------------|--------------------------|--------------------|-------|
| Cursor      | 91/100 (Frontend AI)     | ~55/100 (MVP Plan) | **+36** |
| Kiro        | 92/100 (Agent Upgrade)   | N/A                | —     |
| Anti Gravity| 97/100 (UX Polish)       | N/A                | —     |

**Insight central**: Mesma ferramenta (Cursor), variação de **36 pontos** apenas pela qualidade do prompt.

---

## 2. O Anti-Pattern "Muito Raso"

### Case Study: PLANO_MVP_GITHUB_5MESES.md

- **O que foi pedido**: "crie um plano" (vago)
- **O que foi entregue**: tabela de nomes de workflows, sem YAML/config real
- **Causa raiz**: o prompt não tinha formato de saída, granularidade, critérios de sucesso ou exemplos negativos

### Como evitar

1. Especifique o **formato de saída** (YAML, Markdown, paths de arquivos)
2. Liste **critérios de sucesso** mensuráveis
3. Inclua **exemplos negativos** (o que NÃO fazer)
4. Quebre tarefas complexas em **camadas verificáveis**

---

## 3. Os 5 Padrões de Prompt

### 1. Contextual Loading

Carregue contexto relevante **antes** da pergunta. Exemplo:

```
@src/neural_link/orchestrator/agent_selector.py
@src/neural_link/agents/base_agent.py

Com base nos arquivos acima, implemente o método select_agent()...
```

### 2. Spec-Driven Generation

Escreva critérios de aceitação **primeiro**. Padrão Kiro:

```
Acceptance criteria:
- [ ] Retorna JSON com {agent_id, confidence, reasoning}
- [ ] confidence >= 0.7 para seleção
- [ ] Fallback para generalist se nenhum specialist >= 0.7
```

### 3. Scoring-Rubric Constrained

Informe ao LLM como a saída será avaliada:

- **Correto** (40%): Resposta factualmente correta
- **Completo** (30%): Cobre todos os aspectos da pergunta
- **Qualidade** (30%): Clareza, estrutura, ausência de alucinações

### 4. Template-Constrained

Forneça um template para preencher:

```markdown
## TEMPLATE.md
# [Nome do Agente]
## Persona
[Descreva em 2-3 frases]
## execute(query: str) -> str
[Implementação]
## Testes
[3 casos de teste obrigatórios]
```

### 5. Pipeline-Decomposed

Quebre tarefas complexas em camadas (padrão 5-layer):

1. **Layer 0**: Cache (0 tokens)
2. **Layer 1**: Triage com modelo 8B
3. **Layer 2**: Especialista por domínio
4. **Layer 3**: Avaliação 70B
5. **Layer 4**: Refinamento e persistência

---

## 4. ROI Por Token

| Camada | Custo aproximado | Requisito |
|--------|------------------|-----------|
| Layer 0 cache | 0 tokens | Queries bem estruturadas |
| Layer 1 triage | ~$0.00001/query (8B) | — |
| Layer 3 full eval | ~$0.001/query (70B) | Queries vagas |

- Queries bem promptadas atingem Layer 0/1 ~50% do tempo
- Queries mal promptadas vão sempre para Layer 3
- **A 1000 queries/dia**: $0.10 vs $1.00

---

## 5. Templates por Tipo de Agente

### Domain Agent

```
Você é um especialista em [DOMÍNIO].
Responda com base APENAS no contexto fornecido.
Se não souber, diga "Não tenho informação suficiente".
Formato: JSON com {answer, sources, confidence}.
```

### Specialist Agent

```
Você é um [ESPECIALISTA] com acesso a chunks de conhecimento.
Combine o contexto RAG com sua expertise.
Cite fontes quando usar chunks.
```

### Operator Agent

```
Execute a tarefa [TAREFA] com os parâmetros [PARAMS].
Retorne: {status, output, error?, duration_ms}.
```

---

## 6. Benchmarking

Use `tools/benchmark_pipeline.py` para medir a efetividade dos prompts:

```bash
make benchmark
# ou
python tools/benchmark_pipeline.py
```

O benchmark executa offline com LLM mockado e gera métricas de:
- Latência por layer
- Taxa de cache hit
- Custo estimado por query
