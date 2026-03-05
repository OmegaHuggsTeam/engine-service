# Testing Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | TestingAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O TestingAgent e especialista em qualidade de software, gerando testes unitarios, de integracao e E2E. Analisa codigo existente para identificar gaps de cobertura e propoe estrategias de teste automatizado.

### Responsabilidades
- Gerar testes unitarios para funcoes e classes Python
- Criar testes de integracao para APIs e servicos
- Identificar gaps de cobertura de testes no codebase
- Propor estrategias de automacao de QA
- Gerar fixtures e mocks para ambientes de teste

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| testing | Estrategias gerais de teste de software |
| unit_testing | Geracao de testes unitarios (pytest) |
| integration_testing | Testes de integracao para APIs e servicos |
| qa | Processos e estrategias de quality assurance |
| test_automation | Automacao de pipelines de teste (CI/CD) |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="testing", **kwargs)`
- **Knowledge Categories**: testing, pytest, qa, test_automation

## Integracao

- **UseCase Coverage**: Transversal (qualidade)
- **Depends On**: Codebase source files, pytest framework
- **Used By**: NeuralLinkOrchestrator, QualityGate (test generation)

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
