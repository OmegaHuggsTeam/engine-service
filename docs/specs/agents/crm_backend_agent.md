# CRM Backend Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | CrmBackendAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.crm_domain_agent` |

---

## Funcao Core

O CrmBackendAgent e especialista no backend CRM (pedro-crm), dominando Express, MongoDB, Kafka e o journey engine. Analisa e gera codigo para campanhas, jornadas e gestao de contatos no servidor.

### Responsabilidades
- Analisar e gerar codigo Express para APIs de campanhas e jornadas
- Implementar operacoes CRUD em MongoDB para contatos e leads
- Configurar producers/consumers Kafka para eventos CRM
- Projetar e depurar fluxos do journey engine
- Integrar com servicos externos via webhooks e APIs REST

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| crm_backend | Desenvolvimento e manutencao do backend CRM |
| campaigns | Logica de campanhas (criacao, disparo, tracking) |
| journeys | Motor de jornadas (steps, triggers, conditions) |
| contacts | Gestao de contatos e listas no MongoDB |
| kafka | Producers/consumers para eventos assincronos |
| mongodb | Operacoes e modelagem de dados MongoDB |
| express | APIs REST com Express.js |
| journey_engine | Orquestracao de fluxos multi-step |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: CrmBackendAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: crm_backend, express, mongodb, kafka

## Integracao

- **UseCase Coverage**: UC-CAM-001 a UC-CAM-004, UC-JRN-001 a UC-JRN-004, UC-CON-001 a UC-CON-004
- **Depends On**: ChromaDB (code chunks), Neo4j (graph context)
- **Used By**: NeuralLinkOrchestrator, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_crm_domain_agents.py`
- **Coverage**: Unit tests para code analysis e context injection
