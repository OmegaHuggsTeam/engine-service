# Analytics Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | AnalyticsAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.analytics_agent` |

---

## Funcao Core

O AnalyticsAgent e especializado em analise de dados, consultando ClickHouse para KPIs semanais, analise de coortes e metricas em tempo real. Fornece insights acionaveis para tomada de decisao baseada em dados.

### Responsabilidades
- Executar consultas analiticas em ClickHouse (userin-analytics-v2)
- Gerar relatorios de KPIs semanais com comparativos
- Realizar analise de coortes para retencao e conversao
- Monitorar metricas em tempo real (active users, events/sec)
- Identificar anomalias e tendencias nos dados comportamentais

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| analytics | Analise geral de dados e geracao de insights |
| data_analysis | Processamento e interpretacao de datasets |
| clickhouse | Consultas otimizadas em ClickHouse |
| weekly_kpis | Geracao automatica de relatorios KPI semanais |
| real_time_analytics | Monitoramento de metricas em tempo real |
| cohort_analysis | Analise de coortes para retencao e LTV |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class em AGENT_REGISTRY)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: analytics, clickhouse, data_analysis

## Integracao

- **UseCase Coverage**: UC-ANA-001
- **Depends On**: CrmDataAgent (segmentos), ClickHouse (datasource)
- **Used By**: NeuralLinkOrchestrator, CrmBackendAgent, MarketingAgent

## Testes

- **Test File**: `src/neural_link/tests/test_analytics_agent.py`
- **Coverage**: Unit tests para queries ClickHouse e KPI generation
