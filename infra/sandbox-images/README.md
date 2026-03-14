# Sandbox Container Images

Minimal Docker containers for Journey Builder node sandboxing. Each journey node type runs inside an isolated container that reads configuration from environment variables and writes its result to `/tmp/result.json`.

Related: [INFRA-ES-001](https://github.com/OmegaHuggsTeam/engine-service/issues/16)

## Images

| Image | Purpose | Extra Deps | Expected Size |
|-------|---------|------------|---------------|
| `ghcr.io/omegahuggsteam/sandbox-trigger` | Trigger node evaluation (manual, webhook, schedule) | None | ~55MB |
| `ghcr.io/omegahuggsteam/sandbox-condition` | Boolean condition evaluation (field checks, expressions) | None | ~55MB |
| `ghcr.io/omegahuggsteam/sandbox-action` | CRM action execution (tag, score, notify, webhook) | `httpx`, `curl` | ~75MB |
| `ghcr.io/omegahuggsteam/sandbox-transform` | Data transformation (jmespath, jq, field mapping) | `jmespath`, `jq` | ~70MB |

## CI/CD — GitHub Packages (ghcr.io)

Images are automatically built and pushed to GitHub Container Registry on every push to `main` or `develop` that modifies files under `infra/sandbox-images/`. The workflow can also be triggered manually via `workflow_dispatch`.

**Workflow:** `.github/workflows/build-sandbox-images.yml`

Pull pre-built images:

```bash
docker pull ghcr.io/omegahuggsteam/sandbox-trigger:latest
docker pull ghcr.io/omegahuggsteam/sandbox-condition:latest
docker pull ghcr.io/omegahuggsteam/sandbox-action:latest
docker pull ghcr.io/omegahuggsteam/sandbox-transform:latest
```

Or pull all via compose:

```bash
cd infra/sandbox-images
docker compose -f docker-compose.sandbox.yml pull
```

## Build All Images (local)

```bash
cd infra/sandbox-images
docker compose -f docker-compose.sandbox.yml build
```

Or build individually:

```bash
docker build -t ghcr.io/omegahuggsteam/sandbox-trigger:latest trigger/
docker build -t ghcr.io/omegahuggsteam/sandbox-condition:latest condition/
docker build -t ghcr.io/omegahuggsteam/sandbox-action:latest action/
docker build -t ghcr.io/omegahuggsteam/sandbox-transform:latest transform/
```

## Test All Images

Run all containers with test configurations:

```bash
docker compose -f docker-compose.sandbox.yml up --abort-on-container-exit
```

Each container prints its result to stdout and writes to `/tmp/result.json`. Expected output format:

```json
{
  "result": true,
  "type": "trigger",
  "subtype": "manual_trigger",
  "timestamp": "2026-03-12T10:00:00+00:00"
}
```

## Test Individual Images

```bash
# Trigger
docker run --rm -e NODE_SUBTYPE=manual ghcr.io/omegahuggsteam/sandbox-trigger:latest

# Condition (should return result=true since 75 >= 50)
docker run --rm \
  -e NODE_SUBTYPE=field_check \
  -e NODE_CONFIG='{"field":"score","operator":"gte","value":50,"context":{"score":75}}' \
  ghcr.io/omegahuggsteam/sandbox-condition:latest

# Action (dry-run mode without CRM_API_URL)
docker run --rm \
  -e NODE_SUBTYPE=add_tag \
  -e NODE_CONFIG='{"payload":{"contact_id":"c1","tag":"vip"}}' \
  ghcr.io/omegahuggsteam/sandbox-action:latest

# Transform (jmespath filter)
docker run --rm \
  -e NODE_SUBTYPE=jmespath \
  -e NODE_CONFIG='{"expression":"contacts[?score > `50`].name","data":{"contacts":[{"name":"Alice","score":80}]}}' \
  ghcr.io/omegahuggsteam/sandbox-transform:latest
```

## Security Model

All containers follow these security principles:

- **Non-root execution** — runs as `sandbox` user (UID 999)
- **Read-only filesystem** — only `/tmp` is writable (via tmpfs)
- **No new privileges** — `no-new-privileges` security opt enabled
- **Memory limited** — 128MB cap per container
- **CPU limited** — 0.25 CPU per container
- **Network isolated** — internal bridge network, no external access
- **Minimal base** — `python:3.11-slim`, no unnecessary packages
- **Health checks** — each image has a health check verifying `/tmp/result.json` exists

## Environment Variables

All containers read these standard env vars:

| Variable | Description | Default |
|----------|-------------|---------|
| `NODE_TYPE` | Node type identifier | Set per image |
| `NODE_SUBTYPE` | Node subtype (e.g., `manual`, `field_check`) | `""` |
| `NODE_CONFIG` | JSON string with node configuration | `"{}"` |

The **action** container has additional vars:

| Variable | Description | Default |
|----------|-------------|---------|
| `CRM_API_URL` | Base URL for CRM API calls | `""` (dry-run mode) |
| `CRM_API_TOKEN` | Bearer token for CRM API auth | `""` |

## Result Convention

All containers write their output to `/tmp/result.json` with this schema:

```json
{
  "result": true,
  "type": "string",
  "subtype": "string",
  "timestamp": "ISO-8601"
}
```

The `result` field is always a boolean indicating success/failure. Additional fields vary by node type.

## Integration with ContainerOrchestrator

The `ContainerOrchestrator` module (`src/neural_link/containers/orchestrator.py`) spawns these images with:

```python
config = ContainerConfig(
    image="ghcr.io/omegahuggsteam/sandbox-trigger:latest",
    tenant_id="tenant-001",
    node_id="node-abc",
    memory_limit_mb=128,
    env={"NODE_SUBTYPE": "manual", "NODE_CONFIG": "{}"},
)
result = orchestrator.spawn(config)
```
