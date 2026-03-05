# Computer Use Agent - Especificacao Tecnica

## Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | ComputerUseAgent |
| **Tipo** | Specialist |
| **Versao** | 1.0.0 |
| **Status** | Active |
| **Modulo** | `src.agents.specialist_agent` |

---

## Funcao Core

O ComputerUseAgent e especialista em automacao de interface grafica, controlando mouse, teclado e janelas programaticamente. Realiza tarefas que requerem interacao visual com aplicacoes desktop e web via Playwright e pygetwindow.

### Responsabilidades
- Automatizar interacoes com interfaces graficas (click, type, scroll)
- Capturar e analisar screenshots para verificacao visual
- Controlar posicionamento e dimensionamento de janelas
- Executar sequencias de acoes em aplicacoes desktop
- Coordenar com MaestroService para posicionamento multi-monitor

---

## Capabilities

| Capability | Descricao |
|------------|-----------|
| ui_automation | Automacao de interacoes com interface grafica |
| screenshot | Captura e analise de screenshots |
| typing | Digitacao automatizada em campos de texto |
| mouse_control | Controle preciso de mouse (click, drag, scroll) |
| window_management | Posicionamento e redimensionamento de janelas |

---

## Inicializacao

- **Pattern**: No-arg (herda SpecialistAgent)
- **Invoke**: `execute(task, chunk_type="computer_use", **kwargs)`
- **Knowledge Categories**: computer_use, ui_automation, playwright

## Integracao

- **UseCase Coverage**: Transversal (automacao visual)
- **Depends On**: MaestroService (window arranger), GeminiOperator (screenshot analysis)
- **Used By**: MaestroService (e2e_runner), IdentityManager (provisioning)

## Testes

- **Test File**: `tests/test_specialist_agent.py`
- **Coverage**: Coberto via testes do SpecialistAgent base
