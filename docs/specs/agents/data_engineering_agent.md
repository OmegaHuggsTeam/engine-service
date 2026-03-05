# Data Engineering Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | DataEngineeringAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O DataEngineeringAgent e especialista em engenharia de dados, projetando pipelines ETL, orquestrando workflows com Airflow e processando dados em larga escala com Spark. Garante qualidade, linhagem e governanca dos dados.

### Responsabilidades
- Projetar e implementar pipelines ETL/ELT
- Configurar e orquestrar workflows com Apache Airflow
- Processar datasets em larga escala com Apache Spark
- Garantir qualidade e linhagem de dados (data lineage)
- Otimizar performance de queries e storage

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| data_engineering | Engenharia de dados end-to-end |
| etl | Pipelines de Extract, Transform, Load |
| data_pipeline | Arquitetura de pipelines de dados |
| spark | Processamento distribuido com Apache Spark |
| airflow | Orquestracao de workflows com Apache Airflow |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="data_engineering", **kwargs)`
- **Knowledge Categories**: data_engineering, etl, spark, airflow

## Integracao

- **UseCase Coverage**: Transversal (dados)
- **Depends On**: CrmDataAgent (segmentos), ClickHouse, Kafka
- **Used By**: NeuralLinkOrchestrator, AnalyticsAgent, AiEngineerAgent

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
