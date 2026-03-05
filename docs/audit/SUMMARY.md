# Audit Summary — Project Folder Scores

**Audited**: 2026-03-04
**Scoring**: Correto 40% + Completo 30% + Qualidade 30% (same as ToolScorecard)
**UseCase**: UC-AUDIT-001

## Aggregated Scores

| # | Folder | Correto | Completo | Qualidade | Nota Geral | Files | Tests |
|---|--------|---------|----------|-----------|------------|-------|-------|
| 1 | `src/middleware/` | 95 | 85 | 90 | **90.5** | 2 | 31 |
| 2 | `src/divine_inspiration/` | 85 | 75 | 80 | **80.5** | 8 | 3 |
| 3 | `src/sentinela/` | 85 | 80 | 75 | **80.5** | 8 | 5 |
| 4 | `src/steady_gaze/` | 80 | 65 | 75 | **74.0** | 6 | 3 |
| 5 | `src/extractors/` | 80 | 70 | 60 | **71.0** | 11 | 1 |
| 6 | `automation_hub/` | 75 | 65 | 60 | **67.5** | 6 | 1 |
| 7 | `src/processors/` | 75 | 55 | 60 | **64.5** | 4 | 0 |
| 8 | `tools/` | 75 | 55 | 55 | **63.0** | 10 | 0 |
| 9 | `scripts/` | 70 | 55 | 50 | **59.5** | 12 | 0 |
| 10 | `infra/k8s/` | 70 | 50 | 55 | **59.5** | 9 | 0 |

### Averages

| Metric | Value |
|--------|-------|
| **Average Nota Geral** | 71.2 |
| **Total Files** | 89 |
| **Total Test Files** | 46 |
| **Folders with Tests** | 7/11 (64%) |
| **Folders > 80** | 3 (27%) |
| **Folders < 65** | 4 (36%) |

## Top 5 Critical Gaps

| Priority | Gap | Affected Folders | Impact |
|----------|-----|-----------------|--------|
| **P1** | Zero test coverage | processors, tools, scripts, infra/k8s | 4 folders with 0 tests — regressions undetectable |
| **P2** | web_extractor.py is 2,700 LOC | extractors | God file — unmaintainable, untestable |
| **P3** | No resource limits in K8s | infra/k8s | OOM/CPU starvation risk in production |
| **P4** | No retry/circuit breaker patterns | extractors, automation_hub, sentinela | Single failures cascade silently |
| **P5** | Hardcoded paths/configs | scripts, tools | Not portable across machines |

## Priority Ranking (by urgency)

1. **infra/k8s** (59.5) — Production risk: no probes, no limits, no backups
2. **scripts** (59.5) — Setup reliability: hardcoded paths, no idempotency
3. **tools** (63.0) — Developer experience: no error messages, no progress
4. **processors** (64.5) — Core pipeline: zero tests for chunking logic
5. **automation_hub** (67.5) — Reliability: no timeouts, no audit logging

## Recommendations by Category

### Testing (4 folders affected)
- Add pytest suites to processors, tools, scripts
- Add kubeval/kubeconform for K8s manifest validation
- Target: every folder has at least 1 test file

### Reliability (3 folders affected)
- Add retry middleware with exponential backoff (extractors, automation_hub)
- Implement circuit breaker pattern (sentinela IFTTT, GitHub API)
- Add configurable timeouts everywhere

### Code Quality (2 folders affected)
- Split web_extractor.py (2,700 LOC) into 4 focused modules
- Add thread safety to pyautogui calls where applicable

### Infrastructure (1 folder affected)
- Add resource requests/limits to all K8s containers
- Add liveness/readiness probes
- Implement backup CronJob for Neo4j/ChromaDB
- Migrate secrets to SealedSecrets or Vault
