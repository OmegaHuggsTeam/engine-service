# Frontend Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | FrontendAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O FrontendAgent e especialista em desenvolvimento frontend, criando interfaces React com foco em acessibilidade, performance e design responsivo. Gera componentes, hooks e estilos CSS seguindo melhores praticas de UI/UX.

### Responsabilidades
- Gerar componentes React com TypeScript e hooks customizados
- Implementar estilos responsivos com CSS/Tailwind
- Garantir acessibilidade (WCAG 2.1 AA) em todos os componentes
- Otimizar performance (lazy loading, memoization, code splitting)
- Criar prototipos de UI baseados em requisitos de produto

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| frontend | Desenvolvimento frontend geral |
| ui_design | Design de interfaces de usuario |
| react | Componentes React com TypeScript |
| css | Estilizacao com CSS, Tailwind, styled-components |
| accessibility | Conformidade com WCAG e acessibilidade web |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="frontend", **kwargs)`
- **Knowledge Categories**: frontend, react, css, accessibility, ui_design

## Integracao

- **UseCase Coverage**: Transversal (interface)
- **Depends On**: CrmFrontendAgent (CRM UI), ApiGatewayAgent (API contracts)
- **Used By**: NeuralLinkOrchestrator, CrmFrontendAgent (delegacao)

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
