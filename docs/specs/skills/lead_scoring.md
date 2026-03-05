# Lead Scoring - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | LeadScoring |
| **Categoria** | Analysis |
| **Versao** | 1.0.0 |
| **Status** | Active (basico) / Development (ML) |
| **Prioridade** | Alta |
| **Modulo** | `src.neural_link.api.sovereign_gateway` (UPDATE_LEAD_TRUST) |
| **Criado em** | 2026-03-03 |
| **Ultima Atualizacao** | 2026-03-03 |

---

## Objetivo

Calcula e mantém atualizado o trust score (0.0 - 1.0) de cada Lead no grafo CRM, representando a qualidade e potencial de conversao do contato.

### Problema que Resolve
Sem scoring automatizado, leads sao tratados igualmente independente de engajamento, fonte ou historico. Isso desperdiça esforco de agentes em leads frios e deixa leads quentes sem atencao.

### Valor Agregado
- Priorizacao automatica de leads por qualidade
- Visualizacao por cores no LeadGraph (verde = alto trust, vermelho = baixo)
- Base para routing inteligente: agentes focam em leads de alto potencial
- Metricas de saude do pipeline (avg_trust no dashboard)

---

## Agentes que Utilizam

| Agente | Uso | Frequencia |
|--------|-----|------------|
| **CrmAgent** | Calcula trust em criacao e atualiza apos interacoes | Alta |
| **marketing_agent** | Consulta trust para priorizar outreach | Media |
| **analytics_agent** | Agrega trust scores para reports de pipeline | Media |
| **TaskExecutor** | Incrementa interaction_count (input para scoring) | Alta |

---

## Interface

### Input

```python
# Dados disponíveis para scoring
{
    "lead_id": "lead_abc123",
    "current_trust": 0.5,
    "interaction_count": 12,
    "source_channel": "telegram",      # telegram | email | n8n | manual | webhook
    "tags": ["enterprise", "decision-maker"],
    "days_since_creation": 15,
    "days_since_last_interaction": 2,
    "flow_count": 2,                   # quantos flows o lead participa
    "agent_interactions": 8            # quantas interacoes com agentes
}
```

### Output

```python
{
    "status": "success",
    "data": {
        "lead_id": "lead_abc123",
        "previous_trust": 0.5,
        "new_trust": 0.72,
        "factors": {
            "interaction_frequency": 0.8,   # alta atividade
            "source_quality": 0.7,          # telegram = bom
            "recency": 0.9,                 # interacao recente
            "engagement_depth": 0.6,        # 2 flows
            "tag_bonus": 0.1               # enterprise + decision-maker
        }
    },
    "metadata": {
        "execution_time_ms": 12,
        "model": "rule_based_v1"
    }
}
```

### Exceções

| Excecao | Quando Ocorre | Como Tratar |
|---------|---------------|-------------|
| Lead nao encontrado | lead_id invalido | Retornar erro, nao alterar nada |
| Neo4j indisponivel | Conexao falhou | Retornar trust anterior sem alterar |

---

## Implementacao

### Fase 1: Rule-Based (Atual)

Formula atual (basica):
```
trust = base + source_bonus + interaction_bonus + recency_bonus + tag_bonus
```

| Fator | Peso | Logica |
|-------|------|--------|
| Base | 0.3 | Todos leads comecam com 0.3 base |
| Source | 0.0-0.15 | telegram=0.15, email=0.10, webhook=0.10, n8n=0.05, manual=0.0 |
| Interactions | 0.0-0.25 | min(interaction_count / 20, 1.0) * 0.25 |
| Recency | 0.0-0.15 | 0.15 se interacao < 7 dias, decai 0.02/dia |
| Tags | 0.0-0.15 | +0.05 por tag de alto valor (enterprise, decision-maker, etc.) |

### Fase 2: ML-Based (Planejada)

Features:
- Interaction frequency (rolling 7/30 dias)
- Source channel one-hot encoding
- Flow participation count
- Agent diversity (quantos agentes diferentes interagiram)
- Temporal patterns (horarios de interacao)
- Tag embeddings

Modelo: Gradient Boosted Trees (LightGBM) treinado com labels de conversao.

### Tecnologias Utilizadas
- **Neo4j**: Queries para obter features do lead
- **NumPy** (futuro): Calculo vetorial de scores
- **LightGBM** (futuro): Modelo de scoring ML

### Cypher Queries

```cypher
-- Atualizar trust score
MATCH (l:Lead {id: $lead_id})
SET l.trust = $trust, l.updated_at = $updated_at
RETURN l

-- Obter features para scoring
MATCH (l:Lead {id: $lead_id})
OPTIONAL MATCH (i:Interaction)-[:FOR_LEAD]->(l)
WITH l, count(i) AS interaction_count,
     max(i.timestamp) AS last_interaction
OPTIONAL MATCH (l)-[:PART_OF_FLOW]->(f:Flow)
RETURN l.trust AS current_trust,
       interaction_count,
       l.source_channel AS source,
       l.tags AS tags,
       count(f) AS flow_count,
       last_interaction
```

---

## Metricas

### KPIs
- **Execution Time**: < 50ms (p95) para scoring de um lead
- **Batch Scoring**: < 5s para 1000 leads
- **Trust Distribution**: Deve seguir distribuicao normal (nao todos em 0.5)
- **Correlation with Conversion**: > 0.7 (quando dados de conversao disponiveis)

### Monitoramento
```python
{
  "skill": "LeadScoring",
  "timestamp": "2026-03-03T10:00:00Z",
  "metrics": {
    "leads_scored": 42,
    "avg_trust": 0.62,
    "trust_distribution": {"0.0-0.3": 5, "0.3-0.7": 25, "0.7-1.0": 12},
    "avg_execution_time_ms": 15
  }
}
```

---

## Testes

### Casos de Teste

1. **Teste de Score Basico**
   - Input: Lead novo, source=telegram, 0 interactions
   - Output esperado: trust = 0.45 (0.3 base + 0.15 source)

2. **Teste de Interaction Bonus**
   - Input: Lead com 20 interactions
   - Output esperado: interaction_bonus = 0.25 (max)

3. **Teste de Recency Decay**
   - Input: Ultima interacao ha 14 dias
   - Output esperado: recency_bonus < 0.05

4. **Teste de Tag Bonus**
   - Input: Tags = ["enterprise", "decision-maker"]
   - Output esperado: tag_bonus = 0.10

5. **Teste de Bounds**
   - Output: trust sempre entre 0.0 e 1.0

### Comandos de Teste
```bash
# Quando implementado como modulo separado
pytest tests/skills/test_lead_scoring.py -v

# Teste manual via API
curl -X POST http://localhost:8766/api/v1/crm/leads \
  -H "Content-Type: application/json" \
  -d '{"name":"Test","source_channel":"telegram","tags":["enterprise"]}'
# Verificar trust no response
```

---

## Integracao

### Como Usar em Agentes

```python
# Scoring e chamado pelo gateway em criacao de lead
# e pelo TaskExecutor em cada interacao

# Futuro: modulo standalone
from src.skills.lead_scoring import LeadScorer

scorer = LeadScorer(graph_manager=graph)
new_trust = scorer.score(lead_id="lead_abc123")
# Automaticamente atualiza trust no grafo
```

### Como Usar em Workflows n8n

```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.httpRequest",
      "name": "Update Lead Trust",
      "parameters": {
        "url": "http://gateway:8766/api/v1/crm/leads/{{ $json.lead_id }}",
        "method": "PATCH",
        "body": {"trust": "{{ $json.calculated_score }}"}
      }
    }
  ]
}
```

---

## Roadmap

### Versao Atual (1.0.0)
- OK Trust basico (0.5 default) com UPDATE_LEAD_TRUST query
- OK Visualizacao por cores no LeadGraph
- OK avg_trust no dashboard stats

### Proxima Versao (1.1.0)
- Rule-based scoring com formula de 5 fatores
- Auto-scoring em criacao de lead
- Re-scoring em cada interacao
- Decay por inatividade (cron)

### Futuro (2.0.0)
- ML model treinado com dados de conversao
- A/B testing de modelos de scoring
- Scoring explicavel (SHAP values)
- Alertas para mudancas bruscas de trust

---

## Referencias

- [CRM Agent Spec](../agents/crm_agent.md)
- [CRM Product Docs](../../product/crm/README.md)
- [Neo4j Queries - UPDATE_LEAD_TRUST](../../../src/neural_link/graph/queries.py)
- [Skills Template](TEMPLATE.md)

---

**Mantido por**: Neural Link Team
**Ultima Revisao**: 2026-03-03
