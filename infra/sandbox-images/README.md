# Sandbox Container Images

Minimal Docker containers for Journey Builder node sandboxing. Each journey node type runs inside an isolated container that reads configuration from environment variables and writes its result to `/tmp/result.json`.

Related: [INFRA-ES-001](https://github.com/OmegaHuggsTeam/engine-service/issues/16)

## Images

| Image | Purpose | Extra Deps | Expected Size |
|-------|---------|------------|---------------|
| `huggsai/trigger` | Trigger node evaluation (manual, webhook, schedule) | None | ~55MB |
| `huggsai/condition` | Boolean condition evaluation (field checks, expressions) | None | ~55MB |
| `huggsai/action` | CRM action execution (tag, score, notify, webhook) | `httpx`, `curl` | ~75MB |
| `huggsai/transform` | Data transformation (jmespath, jq, field mapping) | `jmespath`, `jq` | ~70MB |

## Build All Images

```bash
cd infra/sandbox-images
docker compose -f docker-compose.sandbox.yml build
```

Or build individually:

```bash
docker build -t huggsai/trigger:latest trigger/
docker build -t huggsai/condition:latest condition/
docker build -t huggsai/action:latest action/
docker build -t huggsai/transform:latest transform/
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
docker run --rm -e NODE_SUBTYPE=manual huggsai/trigger:latest

# Condition (should return result=true since 75 >= 50)
docker run --rm \
  -e NODE_SUBTYPE=field_check \
  -e NODE_CONFIG='{"field":"score","operator":"gte","value":50,"context":{"score":75}}' \
  huggsai/condition:latest

# Action (dry-run mode without CRM_API_URL)
docker run --rm \
  -e NODE_SUBTYPE=add_tag \
  -e NODE_CONFIG='{"payload":{"contact_id":"c1","tag":"vip"}}' \
  huggsai/action:latest

# Transform (jmespath filter)
docker run --rm \
  -e NODE_SUBTYPE=jmespath \
  -e NODE_CONFIG='{"expression":"contacts[?score > `50`].name","data":{"contacts":[{"name":"Alice","score":80}]}}' \
  huggsai/transform:latest
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
    image="huggsai/trigger:latest",
    tenant_id="tenant-001",
    node_id="node-abc",
    memory_limit_mb=128,
    env={"NODE_SUBTYPE": "manual", "NODE_CONFIG": "{}"},
)
result = orchestrator.spawn(config)
```
