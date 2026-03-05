# SendSpeed SMS Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | SendSpeedSmsAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.sendspeed_agent` |

---

## Funcao Core

O SendSpeedSmsAgent e especialista no pipeline de envio de SMS da plataforma SendSpeed. Domina roteamento de fornecedores, execucao de campanhas, gestao de creditos e integracao com RabbitMQ para processamento assincrono de mensagens.

### Responsabilidades
- Analisar e otimizar roteamento de fornecedores SMS
- Configurar e monitorar execucao de campanhas de envio
- Gerenciar sistema de creditos e consumo por cliente
- Integrar com RabbitMQ para filas de mensagens
- Diagnosticar falhas de entrega e rotas alternativas

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| sms_delivery | Pipeline de entrega de mensagens SMS |
| supplier_routing | Roteamento inteligente entre fornecedores |
| campaign_execution | Execucao e monitoramento de campanhas |
| credit_management | Gestao de creditos e billing por cliente |
| rabbitmq | Filas de mensagens com RabbitMQ |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: SendSpeedSmsAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: sendspeed, sms, delivery, rabbitmq

## Integracao

- **UseCase Coverage**: UC-SS-001, UC-SS-003, UC-SS-005
- **Depends On**: ChromaDB (code chunks), Neo4j (graph context), RabbitMQ
- **Used By**: NeuralLinkOrchestrator, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_sendspeed_agents.py`
- **Coverage**: Unit tests para SMS delivery analysis e context injection
