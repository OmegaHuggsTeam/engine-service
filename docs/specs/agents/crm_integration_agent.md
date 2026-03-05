# CRM Integration Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | CrmIntegrationAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.crm_domain_agent` |

---

## Funcao Core

O CrmIntegrationAgent e especialista no smarttrack (tracker SDK), dominando coleta de eventos, fingerprinting, rules engine, smart modals e buyer agent. Analisa e gera codigo para integracao client-side e automacoes baseadas em comportamento.

### Responsabilidades
- Analisar e configurar coleta de eventos via tracker SDK (25+ collectors)
- Implementar e depurar regras no Rules Engine (SegmentEvaluator, 7 condition types)
- Configurar smart modals e exibicoes (card, modal, smartblock)
- Orquestrar o Buyer Agent (Chain of Responsibility + Fly.io scripts)
- Gerenciar fingerprinting e identificacao de usuarios anonimos

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| event_collection | Coleta de eventos client-side via SDK |
| fingerprinting | Identificacao e tracking de usuarios |
| rules_engine | Motor de regras com 7 tipos de condicao |
| smart_modals | Exibicoes contextuais (card, modal, smartblock) |
| buyer_agent | Automacao de compra via Chain of Responsibility |
| tracker_sdk | SDK JavaScript com 25+ collectors e Rollup bundle |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: CrmIntegrationAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: crm_integration, tracker, rules_engine, smarttrack

## Integracao

- **UseCase Coverage**: UC-TRK-001 a UC-TRK-004, UC-INT-001 a UC-INT-003
- **Depends On**: ChromaDB (code chunks), Neo4j (graph context), Socket.IO
- **Used By**: NeuralLinkOrchestrator, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_crm_domain_agents.py`
- **Coverage**: Unit tests para tracker analysis e context injection
