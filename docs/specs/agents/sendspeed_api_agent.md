# SendSpeed API Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | SendSpeedApiAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.sendspeed_agent` |

---

## Funcao Core

O SendSpeedApiAgent e especialista nas APIs REST da plataforma SendSpeed, dominando arquitetura multi-tenant, autenticacao, rate limiting, gestao de contatos e padrao DDD. Analisa codigo do nodejs-api-v02, webhook-api e portal-cliente-api.

### Responsabilidades
- Analisar e gerar endpoints REST seguindo padrao DDD
- Implementar autenticacao e autorizacao multi-tenant
- Configurar e otimizar rate limiting por cliente/plano
- Gerenciar APIs de contatos (CRUD, importacao, exportacao)
- Documentar e versionar APIs publicas

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| rest_api | Design e implementacao de APIs REST |
| multi_tenant | Arquitetura multi-tenant com isolamento de dados |
| authentication | Autenticacao JWT/API key com scopes |
| rate_limiting | Rate limiting por cliente e plano |
| contact_management | APIs de gestao de contatos e listas |
| ddd | Domain-Driven Design para organizacao de codigo |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: SendSpeedApiAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: sendspeed, api, rest, authentication

## Integracao

- **UseCase Coverage**: UC-SS-002, UC-SS-008
- **Depends On**: ChromaDB (code chunks), Neo4j (graph context)
- **Used By**: NeuralLinkOrchestrator, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_sendspeed_agents.py`
- **Coverage**: Unit tests para API analysis e context injection
