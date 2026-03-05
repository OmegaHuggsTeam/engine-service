# Review Template — Multi-Tool Sprint Cycle

## Workflow

```
1. PLAN    → Claude Code cria specs (.kiro/) e prompts (.cursor/)
2. EXECUTE → Kiro, Cursor, Anti Gravity rodam em paralelo
3. REVIEW  → Claude Code roda testes, lê código, avalia e pontua
4. FIX     → Claude Code corrige bugs/gaps encontrados no review
5. UPDATE  → Claude Code atualiza MEMORY.md e WORK_DISTRIBUTION.md
```

## Review Card Template

| Componente | Correto | Completo | Qualidade | Nota |
|---|---|---|---|---|
| [arquivo/módulo] | X/10 | X/10 | X/10 | **X/10** |
| **Nota Geral** | | | | **XX/100** |

## Scoring Criteria

### Correto (Correctness) — "Funciona?"
- 10: Zero bugs, lógica impecável
- 8-9: Funciona, edge cases cobertos
- 6-7: Funciona no happy path, gaps em edge cases
- 4-5: Funciona parcialmente, bugs encontrados
- 1-3: Quebrado, não roda

### Completo (Completeness) — "Fez tudo que foi pedido?"
- 10: Todos os itens da spec implementados
- 8-9: 90%+ implementado, gaps menores
- 6-7: Core implementado, features secundárias faltando
- 4-5: Metade feita
- 1-3: Quase nada entregue

### Qualidade (Code Quality) — "Código limpo e sustentável?"
- 10: Clean code, bem documentado, segue padrões do projeto
- 8-9: Bom código, minor style issues
- 6-7: Funcional mas precisa de refactor
- 4-5: Code smells significativos
- 1-3: Espaguete

### Nota Geral
- Media ponderada: Correto(40%) + Completo(30%) + Qualidade(30%)
- Arredondado para escala 0-100

## Issue Severity

| Severity | Ação | Exemplo |
|----------|------|---------|
| **Critical** | Bloqueia release, fix imediato | Crash, data loss, security hole |
| **Medium** | Fix no próximo sprint | Schema inconsistente, coverage gap |
| **Low** | Nice to have | Missing edge case test, comment clarity |

## Acceptance Criteria

- **Release:** Nota >= 70/100, zero Critical issues
- **Aprovado com follow-up:** Nota 60-69, ação planejada para Medium issues
- **Rejeitar:** Nota < 60, ou qualquer Critical issue

## Tool Responsibility Matrix

| Ferramenta | Força | Dar pra ela |
|------------|-------|-------------|
| **Kiro** | Spec-driven, structured | Features novas com requirements claros, CRUD, schemas |
| **Cursor** | Bulk code, fast | Refactors, tests, infra, integrations, prompts complexos |
| **Anti Gravity** | Frontend, UX | Visual polish, animations, responsive, design system |
| **Claude Code** | Context profundo | Review, integration, fine-tuning, wiring, memory |

## Conflict Prevention

Cada ferramenta recebe uma lista de **arquivos que pode tocar**. Se dois tools precisam do mesmo arquivo, Claude Code faz a merge manual.

## Sprint Cadence

```
T+0min   Claude Code distribui tasks
T+10min  Tools em paralelo (Kiro + Cursor + Anti Gravity)
T+30min  Claude Code review parcial (se possível)
T+60min  Tools entregam
T+65min  Claude Code roda testes
T+70min  Claude Code review + fix + score
T+80min  MEMORY.md atualizado, próximo sprint planejado
```
