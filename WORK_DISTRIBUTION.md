# Work Distribution — Pipeline Optimization Sprint (Phase 2)

**Date:** 2026-03-04
**Baseline:** 803 tests passing, 1 pre-existing failure
**Goal:** Agent upgrades + Frontend AI infra + UX polish

## Completed (Phase 1)
- [x] CRM CRUD (PUT/DELETE/Search/Scoring) — Kiro
- [x] DecisionTree integration + Benchmark + FeedbackLoop fix — Kiro
- [x] CostTracker wiring + Pipeline Cache + Quality Gate — Cursor
- [x] 5 test fixes (crm_domain_agents score mocks) — Claude Code

## Tool Assignment (Phase 2)

| Tool | Focus | Spec/Prompt |
|------|-------|-------------|
| **Kiro** | Agent layer upgrade (3-layer for marketing/social/ai_engineer) | `.kiro/specs/agent-layer-upgrade/` |
| **Cursor** | Frontend AI infra (SWR, Vercel AI SDK, UseCase dashboard, performance) | `.cursor/prompts/03-frontend-ai-infra.md` |
| **Anti Gravity** | Frontend UX polish (animations, agent cards, graph visuals, responsive) | `.cursor/prompts/04-antigravity-frontend-skills.md` |
| **Claude Code** | Review, integration, test fixes, MEMORY.md | Direct |

## Execution (all 3 in parallel — no file conflicts)

### Kiro: Agent Layer Upgrade
**Files touched:** `src/neural_link/agents/domain_agents.py` (NEW), `src/neural_link/orchestrator/agent_selector.py`, `src/neural_link/agents/specialist_agent.py`, `docs/specs/usecases/UC-MKT-*.md`, `UC-SOC-*.md`, `UC-AIE-*.md` (NEW), `src/neural_link/tests/test_domain_agents.py` (NEW)

### Cursor: Frontend AI Infra
**Files touched:** `frontend/package.json`, `frontend/src/lib/gateway.ts`, `frontend/src/modules/crm/hooks/useCrmApi.ts`, `frontend/src/modules/crm/hooks/useCrmWebSocket.ts`, `frontend/src/modules/ai/OrchestratorChat.tsx` (NEW), `frontend/src/modules/sovereign/UseCaseDashboard.tsx` (NEW), `frontend/src/components/PipelineStats.tsx` (NEW), `frontend/src/app/dashboard/chat/page.tsx` (NEW)

### Anti Gravity: UX Polish
**Files touched:** `frontend/src/app/dashboard/layout.tsx`, `frontend/src/components/AgentGrid.tsx`, `frontend/src/modules/crm/LeadTable.tsx`, `frontend/src/modules/crm/LeadGraph.tsx`, `frontend/src/modules/crm/FlowCanvas.tsx`, `frontend/src/modules/crm/CrmDashboard.tsx`

**CONFLICT ZONE:** Both Cursor and Anti Gravity touch frontend files. Cursor owns: `gateway.ts`, `hooks/*`, new modules. Anti Gravity owns: existing UI components, layout, animations. They should NOT edit each other's files.

## Verification

Backend:
```bash
python -m pytest src/neural_link/tests/ -v --tb=short
# Expected: 803+ all passing (+ new domain agent tests)
```

Frontend:
```bash
cd frontend && npm run build
# Expected: zero errors
```

## Files Created (Phase 2)

```
.kiro/specs/agent-layer-upgrade/tasks.md           ← Kiro (updated)
.cursor/prompts/03-frontend-ai-infra.md            ← Cursor: SWR + AI SDK + UseCase dashboard
.cursor/prompts/04-antigravity-frontend-skills.md  ← Anti Gravity: UX polish
WORK_DISTRIBUTION.md                               ← this file (updated)
```
