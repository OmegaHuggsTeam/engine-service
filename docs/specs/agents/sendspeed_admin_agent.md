# SendSpeed Admin Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | SendSpeedAdminAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.sendspeed_agent` |

---

## Funcao Core

O SendSpeedAdminAgent e especialista nas funcoes administrativas da plataforma SendSpeed, incluindo gestao de fornecedores, campanhas, billing, deteccao de fraude e sistema de blacklist. Analisa codigo do backoffice e portal-cliente-api.

### Responsabilidades
- Gerenciar cadastro e configuracao de fornecedores SMS
- Administrar campanhas (aprovacao, pausar, cancelar)
- Analisar e depurar sistema de billing e cobranca
- Implementar regras de deteccao de fraude e alertas
- Manter e consultar sistema de blacklist de numeros

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| supplier_management | Cadastro e configuracao de fornecedores |
| campaign_management | Administracao de campanhas (CRUD, status) |
| billing | Sistema de cobranca e faturamento |
| fraud_detection | Regras de deteccao de fraude e anomalias |
| blacklist | Gestao de blacklist de numeros e dominios |
| alerting | Sistema de alertas para operacoes criticas |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: SendSpeedAdminAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: sendspeed, admin, billing, backoffice

## Integracao

- **UseCase Coverage**: UC-SS-004, UC-SS-006, UC-SS-007
- **Depends On**: ChromaDB (code chunks), Neo4j (graph context)
- **Used By**: NeuralLinkOrchestrator, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_sendspeed_agents.py`
- **Coverage**: Unit tests para admin operations e context injection
