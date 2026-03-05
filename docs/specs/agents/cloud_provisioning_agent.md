# Cloud Provisioning Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | CloudProvisioningAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O CloudProvisioningAgent e especialista em infraestrutura cloud, gerenciando recursos via Terraform, Kubernetes e provedores cloud. Automatiza provisionamento, scaling e configuracao de ambientes de producao e staging.

### Responsabilidades
- Gerar e validar configuracoes Terraform para infraestrutura
- Criar e gerenciar manifestos Kubernetes (deployments, services, ingress)
- Provisionar recursos em provedores cloud (AWS, GCP, Azure)
- Automatizar scaling e configuracao de ambientes
- Documentar arquitetura de infraestrutura como codigo

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| cloud | Gestao de recursos em provedores cloud |
| infrastructure | Provisionamento de infraestrutura como codigo |
| terraform | Configuracoes Terraform (HCL) |
| kubernetes | Manifestos e operacoes Kubernetes |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="cloud", **kwargs)`
- **Knowledge Categories**: cloud, terraform, kubernetes, infrastructure

## Integracao

- **UseCase Coverage**: Transversal (infraestrutura)
- **Depends On**: DevOpsAgent (monitoring), SecurityAuditAgent (compliance)
- **Used By**: NeuralLinkOrchestrator, DevOpsAgent

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
