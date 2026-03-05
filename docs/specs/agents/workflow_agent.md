# Workflow Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | WorkflowAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O WorkflowAgent e especialista em orquestracao de workflows, gerenciando agendamento de tarefas, cron jobs e arquiteturas event-driven. Projeta e otimiza fluxos de automacao usando n8n, Airflow e sistemas de filas.

### Responsabilidades
- Projetar workflows de automacao multi-step
- Configurar e gerenciar cron jobs e agendamentos
- Implementar arquiteturas event-driven com filas de mensagens
- Analisar e otimizar workflows n8n existentes
- Monitorar execucao de workflows e tratar falhas

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| workflow | Design e gestao de workflows de automacao |
| task_scheduling | Agendamento e orquestracao de tarefas |
| cron | Configuracao e gestao de cron jobs |
| event_driven | Arquiteturas event-driven e pub/sub |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="workflow", **kwargs)`
- **Knowledge Categories**: workflow, n8n, cron, event_driven, automation

## Integracao

- **UseCase Coverage**: Transversal (automacao)
- **Depends On**: n8n (workflow engine), RabbitMQ/Kafka (mensageria)
- **Used By**: NeuralLinkOrchestrator, MaestroService (task watcher)

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
