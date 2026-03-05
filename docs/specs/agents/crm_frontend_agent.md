# CRM Frontend Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | CrmFrontendAgent |
| **Tipo** | Domain |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.neural_link.agents.crm_domain_agent` |

---

## Funcao Core

O CrmFrontendAgent e especialista no frontend CRM, dominando React, React Flow, Tailwind, shadcn/ui e D3. Analisa componentes existentes e gera codigo para dashboards, journey builders e visualizacoes interativas.

### Responsabilidades
- Analisar e gerar componentes React para o frontend CRM
- Construir journey builders interativos com React Flow
- Implementar dashboards com graficos D3 e tabelas responsivas
- Estilizar interfaces com Tailwind CSS e componentes shadcn/ui
- Criar visualizacoes de dados (grafos, charts, heatmaps)

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| crm_frontend | Desenvolvimento frontend do CRM |
| react | Componentes React e hooks customizados |
| react_flow | Editor visual de fluxos com React Flow |
| tailwind | Estilizacao responsiva com Tailwind CSS |
| shadcn | Componentes UI com shadcn/ui |
| journey_builder | Interface drag-and-drop para jornadas |
| dashboards | Paineis de metricas e KPIs |
| d3_visualizations | Graficos interativos com D3.js |

---

## Inicializacao

- **Pattern**: Dynamic Import (agent_class: CrmFrontendAgent)
- **Invoke**: `execute(task, **kwargs)`
- **Knowledge Categories**: crm_frontend, react, d3, tailwind

## Integracao

- **UseCase Coverage**: UC-CAM-001 a UC-CAM-004 (UI), UC-JRN-001 a UC-JRN-004 (builder)
- **Depends On**: ChromaDB (code chunks), CrmBackendAgent (API contracts)
- **Used By**: NeuralLinkOrchestrator, TaskExecutor

## Testes

- **Test File**: `src/neural_link/tests/test_crm_domain_agents.py`
- **Coverage**: Unit tests para component generation e context injection
