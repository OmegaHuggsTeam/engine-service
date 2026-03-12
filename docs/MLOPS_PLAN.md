# MLOps Plan — OmegaHuggsTeam

**Principio**: GitHub-first. Tudo que o GitHub Teams resolve, usamos GitHub.

## Diagnostico Atual

| Recurso GitHub | Status | Acao |
|----------------|--------|------|
| Issues | Habilitado, 0 issues | Criar labels MLOps + templates |
| Projects v2 | Habilitado, 0 projects | Criar project "MLOps Roadmap" |
| Wiki | Habilitado | Documentar cada fase |
| Discussions | DESABILITADO | Habilitar (decisoes tecnicas) |
| Environments | Nenhum | Criar staging + production |
| Branch Protection | NENHUMA | Configurar para main |
| Milestones | Nenhum | Criar por fase |
| CODEOWNERS | Nao existe | Criar |
| Dependabot | Existe config | Verificar |
| Secret Scanning | ? | Habilitar |
| Code Scanning | ? | Habilitar |

## Stack MLOps (GitHub-first + complementos)

```
┌─────────────────────────────────────────────────────────┐
│                    GITHUB (nativo)                       │
├─────────────────────────────────────────────────────────┤
│ Projects v2    │ Roadmap MLOps, boards por fase          │
│ Issues         │ Tasks, bugs, alertas automaticos        │
│ Actions        │ CI/CD, eval pipeline, cron monitoring   │
│ Environments   │ staging + production (secrets isolados) │
│ Packages       │ ghcr.io para Docker images              │
│ Wiki           │ Documentacao de processos               │
│ Discussions    │ ADRs (Architecture Decision Records)    │
│ Releases       │ Versionamento semantico                 │
│ CODEOWNERS     │ Review automatico por area              │
│ Branch Rules   │ CI obrigatorio + review                 │
│ Dependabot     │ Seguranca de deps                       │
│ Code Scanning  │ CodeQL para vulnerabilidades            │
│ Secret Scan    │ Deteccao de credenciais vazadas         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              COMPLEMENTOS (onde GitHub nao cobre)        │
├─────────────────────────────────────────────────────────┤
│ LangFuse       │ LLM tracing, prompt versioning, evals  │
│ Grafana        │ Dashboards operacionais real-time       │
│ Prometheus     │ Metricas de infra (scraping)            │
│ Evidently AI   │ Drift detection de RAG/embeddings       │
└─────────────────────────────────────────────────────────┘
```

## Fases de Implementacao

### Fase 0 — GitHub Foundation (AGORA)
Configurar tudo que e nativo do GitHub Teams.

**0.1 — Labels MLOps**
```
mlops:observability    #0E8A16
mlops:alerting         #D93F0B
mlops:eval-pipeline    #1D76DB
mlops:drift-detection  #5319E7
mlops:infra            #006B75
mlops:security         #B60205
priority:critical      #B60205
priority:high          #D93F0B
priority:medium        #FBCA04
priority:low           #0E8A16
type:adr               #C5DEF5  (Architecture Decision Record)
type:runbook           #BFD4F2
```

**0.2 — Milestones**
- `v0.2.0 — GitHub Foundation` (Fase 0)
- `v0.3.0 — LLM Observability` (Fase 1)
- `v0.4.0 — Monitoring & Alerting` (Fase 2)
- `v0.5.0 — Eval Pipeline` (Fase 3)
- `v0.6.0 — Drift Detection` (Fase 4)

**0.3 — GitHub Project "MLOps Roadmap"**
Board com colunas: Backlog | In Progress | Review | Done
Views: Board (por status), Table (por milestone), Roadmap (timeline)

**0.4 — Branch Protection (main)**
- Require PR before merge
- Require 1 approval
- Require status checks: CI Tests, CI SonarCloud
- Require conversation resolution
- No force push

**0.5 — CODEOWNERS**
```
# Core (Hugo + Henrique aprovam tudo em main)
*                       @OmegaHuggsTeam/core

# Pipeline e agentes
src/neural_link/        @OmegaHuggsTeam/engineering
src/agents/             @OmegaHuggsTeam/engineering

# RAG e dados
src/rag/                @OmegaHuggsTeam/data-ai
src/neural_link/rag/    @OmegaHuggsTeam/data-ai

# Frontend
frontend/               @OmegaHuggsTeam/engineering

# Infra e CI
infra/                  @OmegaHuggsTeam/core
.github/                @OmegaHuggsTeam/core

# Testes e seguranca
tests/                  @OmegaHuggsTeam/qa-review
```

**0.6 — Discussions**
Habilitar e criar categorias:
- ADR (Architecture Decision Records)
- RFCs (Request for Comments)
- Q&A

**0.7 — Environments**
- `staging` — deploy automatico em develop
- `production` — deploy manual com approval de @OmegaHuggsTeam/core

**0.8 — Security**
- Habilitar Secret Scanning
- Habilitar Code Scanning (CodeQL)
- Verificar Dependabot alerts

### Fase 1 — LLM Observability (LangFuse)
- Deploy LangFuse via Docker (ou cloud free tier)
- Integrar no `llm_client.py` (5 linhas)
- Dashboard de custo/latencia/qualidade por modelo
- Prompt versioning
- GitHub Action: criar Issue automatica se custo > threshold

### Fase 2 — Monitoring & Alerting (Grafana + GitHub Issues)
- Prometheus exporter no Sovereign Gateway
- Grafana dashboards (ou GitHub Actions cron + Issue alerts)
- Alertas: custo spike, latencia alta, erros rate, qualidade drop
- Webhook Grafana → GitHub Issue auto-criada

### Fase 3 — Eval Pipeline (GitHub Actions)
- Workflow `ci-eval.yml`: roda em PRs que mudam `src/agents/` ou prompts
- Batch de queries → score → pass/fail gate
- Resultados como PR comment (via gh api)
- Baseline de qualidade versionada no repo

### Fase 4 — Drift Detection (Evidently + GitHub Actions)
- CronJob semanal via GitHub Actions
- Evidently AI analisa: embedding quality, retrieval relevance, query distribution
- Relatorio como GitHub Issue com label `mlops:drift-detection`
- Threshold de alerta configuravel

## Owners por Fase

| Fase | Owner | Reviewer |
|------|-------|----------|
| 0 — GitHub Foundation | @HuggsF | @Bh0bh11 |
| 1 — LLM Observability | @HuggsF + @Vr-Farias | @Bh0bh11 |
| 2 — Monitoring | @HuggsF | @rodolfogf-dev |
| 3 — Eval Pipeline | @Vr-Farias | @HuggsF |
| 4 — Drift Detection | @Vr-Farias | @Bh0bh11 |
