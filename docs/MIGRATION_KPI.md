# Migração KPI Intelligence — Extração para Repositório Separado

## 1. Problema

O módulo de **KPI Intelligence** (ToolScorecard, ModelBenchmark, CostQualityAnalyzer, MetricsTimeSeries) estava acoplado ao `engine-service` mas representa um domínio distinto:

- **Responsabilidade**: Métricas de custo/qualidade, comparação de ferramentas (Cursor, Kiro, etc.), detecção de anomalias
- **Dependências**: Neo4j (GraphManager), queries Cypher específicas para `:ModelMetric`, `:ToolReview`, `:RequestMetric`, `:DailyAggregate`
- **Uso**: Sovereign Gateway (endpoints REST), opcionalmente Orchestrator (enqueue de perfis)

O lab será separado em outro repositório para evoluir o KPI de forma independente.

---

## 2. Tópicos Abordados

| Tópico | Descrição |
|--------|-----------|
| **Injeção de dependência indireta** | Os módulos KPI usam `graph_manager=None` com fallback implícito; aceitam injeção para testes |
| **Service Locator / from_env()** | GraphManager obtido via `from_env()` em vários pontos; KPI recebe graph por parâmetro |
| **Acoplamento a queries** | Queries Cypher KPI estavam em `graph/queries.py`; extraídas para `queries_kpi.py` no pacote |
| **Interface RequestCostProfile** | MetricsTimeSeries espera objetos com `to_request_metric_params()`; definido em CostTracker (não extraído) |
| **KpiProvider** | Permanece em `telemetry/` — depende de TelemetryProvider/TelemetryHub do engine-service |

---

## 3. Por Que Isso Cai no Filtro

O filtro de extração identifica módulos que:

1. **Têm domínio próprio**: KPI é um subsistema de métricas, não core do orquestrador
2. **Podem evoluir isoladamente**: Novos dashboards, fórmulas de score, integrações (e.g. Grafana)
3. **Reduzem acoplamento**: Separar permite que o engine-service não dependa de lógica KPI pesada
4. **Facilitam testes**: Pacote extraído pode ser testado sem subir Neo4j/Orchestrator

---

## 4. Arquivos Extraídos

```
src/extracted/kpi_intelligence/
├── __init__.py
├── queries_kpi.py          # Cypher: ModelMetric, ToolReview, RequestMetric, DailyAggregate
├── tool_scorecard.py       # ToolScorecard, VALID_TOOLS
├── model_benchmark.py       # ModelBenchmark, ModelCallRecord
├── cost_quality_analyzer.py
└── metrics_timeseries.py
```

**Proxies (compatibilidade):**

```
src/neural_link/telemetry/
├── tool_scorecard.py       # from src.extracted.kpi_intelligence import ...
├── model_benchmark.py
├── cost_quality_analyzer.py
└── metrics_timeseries.py
```

---

## 5. Garantia de Funcionalidade

| Componente | Antes | Depois |
|------------|-------|--------|
| **Sovereign Gateway** | Importa de `..telemetry.model_benchmark` | Proxy re-exporta de `extracted` — **sem mudança** |
| **Orchestrator** | Recebe `metrics_timeseries`, `model_benchmark` opcionais | Idem — **sem mudança** |
| **Testes** | Importam de `src.neural_link.telemetry` | Proxy mantém imports — **sem mudança** |
| **KpiProvider** | Em `telemetry/kpi_provider.py` | **Permanece** — depende de TelemetryHub |
| **CostTracker / RequestCostProfile** | Em `telemetry/cost_tracker.py` | **Permanece** — usado pelo Orchestrator |

---

## 6. Próximos Passos (Novo Repo)

1. Copiar `src/extracted/kpi_intelligence/` para o novo repositório
2. Definir interface `GraphManager`: `execute_read(query, params)`, `execute_write(query, params)`
3. Definir protocolo `CostProfile` com `to_request_metric_params(task_type, agent_used, quality_score) -> dict`
4. Publicar como pacote pip (ex: `kpi-intelligence`) ou submódulo
5. No engine-service: `pip install kpi-intelligence` e substituir proxies por imports do pacote
