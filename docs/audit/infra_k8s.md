# Audit Report: infra/k8s/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `infra/k8s/` |
| **Purpose** | Kubernetes manifests — deployments, services, storage, secrets |
| **Files** | 9 YAML files |
| **LOC** | ~1,000 |
| **Tests** | 0 |

## File Inventory

| File | Resources | Purpose |
|------|-----------|---------|
| `namespace.yaml` | Namespace: bunker | Cluster namespace isolation |
| `app-deployment.yaml` | Deployment (1 replica) | Main app container with init containers (ChromaDB/Neo4j wait) |
| `chroma-deployment.yaml` | StatefulSet (1 replica) | ChromaDB vector DB, 8GB persistent storage |
| `neo4j-deployment.yaml` | StatefulSet (1 replica) | Neo4j graph DB, 10GB storage, auth secrets |
| `evidence-deployment.yaml` | Deployment | Evidence storage for screenshots/logs |
| `pvc.yaml` | 3 PVCs | Persistent volumes: chroma (8GB), neo4j (10GB), evidence |
| `secret-app.yaml` | Secret | GROQ_API_KEY, TELEGRAM_BOT_TOKEN, etc. (base64) |
| `secret-tailscale.yaml` | Secret | Tailscale AUTH_KEY (base64) |
| `kustomization.yaml` | Kustomize overlay | Patches, configMaps, replicas override |

## Architecture

- Init containers wait for service availability before app starts
- Internal DNS: `chroma`, `neo4j`, `evidence` resolve via CoreDNS
- Kustomize used for environment-specific overlays

## Issues

1. **No resource limits** — Pods can consume unlimited CPU/memory (OOM risk)
2. **Secrets as base64** — Not encrypted at rest (use SealedSecrets or Vault)
3. **No backup strategy** — StatefulSets have persistent storage but no backup/restore
4. **Single replicas** — No horizontal scaling or HA for any service
5. **No probes** — Missing liveness/readiness probes for all deployments
6. **No network policies** — No pod-to-pod traffic restrictions

## Recommendations

1. Add resource requests/limits to all containers
2. Migrate secrets to SealedSecrets or external vault
3. Add CronJob for Neo4j/ChromaDB backup
4. Add liveness/readiness probes (HTTP or TCP)
5. Add network policies restricting inter-pod traffic
6. Consider adding HPA for the app deployment

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 70 | 40% | 28.0 |
| Completo | 50 | 30% | 15.0 |
| Qualidade | 55 | 30% | 16.5 |
| **Nota Geral** | | | **59.5** |
