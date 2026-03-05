# Documentation Index — Bunker Intelligence / Neural Link CRM

**Last updated**: 2026-03-04 | **Version**: 2.0

## Quick Links

- **[GET STARTED](guides/GET_STARTED.md)** — Setup in 5 minutes
- **[How I'm Doing This](HOW_IM_DOING_THIS.md)** — Project narrative & philosophy
- **[API Reference](api/sovereign-gateway-endpoints.md)** — 47 REST + 5 WebSocket endpoints
- **[Audit Summary](audit/SUMMARY.md)** — Folder scores & critical gaps

---

## Guides (Onboarding & Best Practices)

| Document | Audience | Description |
|----------|----------|-------------|
| [GET_STARTED](guides/GET_STARTED.md) | New Developer | Prerequisites, quick setup, services, troubleshooting |
| [Agent Best Practices](guides/agent-best-practices.md) | Agent Developer | Taxonomy, 5 init patterns, creation workflow, testing |
| [FAQ](FAQ.md) | Everyone | Common questions and quick answers |

## API Reference

| Document | Format | Description |
|----------|--------|-------------|
| [Endpoint Reference](api/sovereign-gateway-endpoints.md) | Markdown | All 47 REST + 5 WS endpoints |
| [Postman Collection](api/sovereign-gateway.postman_collection.json) | JSON | Import into Postman for testing |

## Architecture & Overview

| Document | Description |
|----------|-------------|
| [HOW_IM_DOING_THIS](HOW_IM_DOING_THIS.md) | First-person narrative: problem, multi-tool approach, cost strategy, KPI, vision |
| [EXECUTIVE_SUMMARY](EXECUTIVE_SUMMARY.md) | High-level overview, ROI, capabilities |
| [WORKFLOW_DIAGRAMS](WORKFLOW_DIAGRAMS.md) | Visual architecture and data flows |

## Audit Reports (UC-AUDIT-001)

| Report | Score | Folder |
|--------|-------|--------|
| [SUMMARY](audit/SUMMARY.md) | — | Aggregated scores, top 5 gaps, priorities |
| [middleware](audit/middleware.md) | 90.5 | src/middleware/ (GroqRouter) |
| [divine_inspiration](audit/divine_inspiration.md) | 80.5 | src/divine_inspiration/ |
| [sentinela](audit/sentinela.md) | 80.5 | src/sentinela/ |
| [steady_gaze](audit/steady_gaze.md) | 74.0 | src/steady_gaze/ |
| [extractors](audit/extractors.md) | 71.0 | src/extractors/ |
| [automation_hub](audit/automation_hub.md) | 67.5 | automation_hub/ |
| [processors](audit/processors.md) | 64.5 | src/processors/ |
| [tools](audit/tools.md) | 63.0 | tools/ |
| [scripts](audit/scripts.md) | 59.5 | scripts/ |
| [infra_k8s](audit/infra_k8s.md) | 59.5 | infra/k8s/ |
| [Kiro Specs Audit](audit/kiro_specs_audit.md) | — | 18 spec suites analyzed |

## Specs

### UseCase Specs (39 specs)

| Domain | Count | IDs |
|--------|-------|-----|
| Campaigns | 4 | UC-CAM-001..004 |
| Journeys | 4 | UC-JRN-001..004 |
| Segments | 4 | UC-SEG-001..004 |
| Contacts | 4 | UC-CON-001..004 |
| Tracker | 4 | UC-TRK-001..004 |
| Integrations | 3 | UC-INT-001..003 |
| Analytics | 1 | UC-ANA-001 |
| SendSpeed | 8 | UC-SS-001..008 |
| Marketing | 2 | UC-MKT-001..002 |
| Social | 2 | UC-SOC-001..002 |
| AI Engineer | 2 | UC-AIE-001..002 |
| Audit | 1 | UC-AUDIT-001 |

Location: `docs/specs/usecases/`

### Agent Specs (29 specs)

| Category | Count | Location |
|----------|-------|----------|
| Template | 1 | `docs/specs/agents/TEMPLATE.md` |
| Domain Agents | 12 | Individual .md files |
| Operator Agents | 3 | Individual .md files |
| Specialist Agents | 13 | Individual .md files |

Location: `docs/specs/agents/`

### Skill Specs

Location: `docs/specs/skills/`

## Kiro Specs (.kiro/specs/)

| Status | Count | Details |
|--------|-------|---------|
| Complete | 4 | agent-layer-upgrade, crm-crud, delivery-email, pipeline-optimization |
| Nearly Done | 2 | divine-inspiration (80%), n8n-k8s-monitoring (95%) |
| In Progress | 2 | agent-factory (63%), rag-abstraction-vow (28%) |
| Not Started | 9 | See [Kiro Specs Audit](audit/kiro_specs_audit.md) |
| Design Only | 1 | vigilant-eye |

## Product Documentation

| Document | Location | Description |
|----------|----------|-------------|
| CRM Product | `docs/product/crm/README.md` | Self-sovereign CRM product docs |
| SendSpeed Platform | `data/raw/docs-main/` | Mint-based SendSpeed platform docs |

## Infrastructure

| Document | Description |
|----------|-------------|
| [INFRASTRUCTURE_SETUP](INFRASTRUCTURE_SETUP.md) | K8s, Docker, service configuration |
| [infra/k8s/ audit](audit/infra_k8s.md) | K8s manifest review and gaps |
| `infra/docker-compose.yml` | Docker services (Neo4j, ChromaDB) |

## Legacy Documents (Pre-v2.0)

| Document | Status | Notes |
|----------|--------|-------|
| QUICKSTART_INTELLIGENCE.md | Superseded | Use GET_STARTED instead |
| INTELLIGENCE_SETUP.md | Reference | Detailed but outdated |
| IMPLEMENTATION_CHECKLIST.md | Reference | Phase 1 complete, rest outdated |
| CALIBRATION_GUIDE.md | Reference | Sentinela calibration |
