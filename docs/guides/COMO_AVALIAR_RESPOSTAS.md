# Como Avaliar Respostas

## 1. A Fórmula

**Score Total** = Correto × 0.40 + Completo × 0.30 + Qualidade × 0.30

Cada dimensão é avaliada de 0 a 10.

---

## 2. Rubric Detalhado

### Correto (40%)

| Score | Critério |
|-------|----------|
| 9-10 | Resposta factualmente correta, sem erros |
| 7-8 | Pequenos erros ou imprecisões |
| 5-6 | Erros significativos, mas direção geral correta |
| 3-4 | Maioria incorreta |
| 0-2 | Totalmente incorreta ou alucinação |

### Completo (30%)

| Score | Critério |
|-------|----------|
| 9-10 | Cobre todos os aspectos da pergunta |
| 7-8 | Cobre a maior parte, falta 1-2 pontos |
| 5-6 | Cobre ~50%, omissões relevantes |
| 3-4 | Resposta superficial |
| 0-2 | Não responde à pergunta |

### Qualidade (30%)

| Score | Critério |
|-------|----------|
| 9-10 | Clara, bem estruturada, sem redundância |
| 7-8 | Boa clareza, pequenas melhorias possíveis |
| 5-6 | Aceitável, mas confusa em partes |
| 3-4 | Difícil de entender |
| 0-2 | Incoerente ou ilegível |

---

## 3. Exemplos Pontuados

### Exemplo 1: Score 8.5

**Pergunta**: "Como criar um webhook no n8n?"

**Resposta**: "No n8n, adicione o node Webhook. Configure o path (ex: /meu-hook). Conecte ao próximo node. O webhook gera uma URL que você pode usar em POST requests."

- **Correto**: 9 (factualmente correto)
- **Completo**: 8 (cobre o essencial, poderia mencionar método HTTP)
- **Qualidade**: 8 (clara, direta)
- **Total**: 9×0.4 + 8×0.3 + 8×0.3 = **8.4**

### Exemplo 2: Score 5.0

**Resposta**: "Use um node. Configure e pronto."

- **Correto**: 6 (não está errado, mas vago)
- **Completo**: 4 (muito superficial)
- **Qualidade**: 5 (curta demais)
- **Total**: **5.1**

### Exemplo 3: Score 2.0 (Alucinação)

**Resposta**: "No n8n v5, o webhook foi removido. Use o node HTTP Request."

- **Correto**: 2 (incorreto — webhook existe)
- **Completo**: 2 (desvia da pergunta)
- **Qualidade**: 4 (estrutura ok, conteúdo errado)
- **Total**: **2.6**

---

## 4. Avaliação Automática

- **QualityGate**: Pipeline rejeita respostas abaixo de threshold (ex: 7.0)
- **success_rate**: Métrica agregada por agente
- **FeedbackLoop**: Ajusta prompts com base em scores históricos

---

## 5. Avaliação Manual (ToolScorecard)

Use o `ToolScorecard` para comparar ferramentas (Cursor, Kiro, etc.):

```python
from src.neural_link.telemetry.tool_scorecard import ToolScorecard

sc = ToolScorecard(graph_manager=None)
sc.submit_review(tool="cursor", task="frontend", score=8.5, comment="Bom")
```

---

## 6. Workflow de Melhoria Iterativa

1. **Avalie** respostas com a fórmula
2. **Identifique** dimensão mais fraca (Correto/Completo/Qualidade)
3. **Ajuste** prompt ou contexto (chunks, conceitos)
4. **Re-teste** com mesmas queries
5. **Compare** scores antes/depois
