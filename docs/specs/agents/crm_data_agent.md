# CRM Data Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | CrmDataAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.crm_domain_agent` |

---

## Funcao Core

O CrmDataAgent e especialista em dados do CRM, dominando segmentacao (segment-engine), ClickHouse analytics, Kafka workers e analise comportamental. Gera e analisa pipelines de dados para scoring e classificacao de leads.

### Responsabilidades
- Analisar e otimizar regras de segmentacao no segment-engine
- Consultar e modelar dados em ClickHouse (userin-analytics-v2)
- Configurar e depurar Kafka workers (ActiveUsers, Classifier, Expiration, WeeklyStats)
- Implementar pipelines de ML scoring para leads
- Analisar padroes comportamentais para segmentacao dinamica

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| crm_data | Engenharia de dados do ecossistema CRM |
| segmentation | Regras e pipelines de segmentacao de usuarios |
| clickhouse | Consultas analiticas em ClickHouse |
| kafka_workers | Workers assincronos (classificacao, expiracao, stats) |
| behavioral_analysis | Analise de padroes comportamentais |
| ml_scoring | Modelos de scoring para leads e segmentos |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: CrmDataAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: crm_data, segmentation, clickhouse, kafka

## Integracao

- **UseCase Coverage**: UC-SEG-001 a UC-SEG-004, UC-ANA-001
- **Depends On**: ChromaDB (code chunks), ClickHouse, Kafka (Confluent Cloud)
- **Used By**: NeuralLinkOrchestrator, AnalyticsAgent, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_crm_domain_agents.py`
- **Coverage**: Unit tests para segmentation analysis e context injection
