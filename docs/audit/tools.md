# Audit Report: tools/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `tools/` |
| **Purpose** | Utility scripts — pipeline diagnostics, cluster health, workflow injection |
| **Files** | 10 Python scripts |
| **LOC** | ~1,000 |
| **Tests** | 0 (self-testing scripts) |

## File Inventory

| Script | Purpose | Key Functions | Dependencies |
|--------|---------|---------------|--------------|
| `benchmark_pipeline.py` | ROI metrics (offline mocking) | Runs 20-30 queries, reports layer dist, tokens, cost, cache hit % | unittest.mock |
| `boot_sovereign.py` | Docker compose orchestration | `docker compose up`, waits 30s, gateway startup | subprocess |
| `cluster_health.py` | K8s service status | HTTP checks: ChromaDB, Neo4j, Evidence, n8n, Tailscale | httpx, subprocess |
| `system_check.py` | Gateway validation | 9 REST + 3 WS route checks to /api/v1/* | httpx, asyncio |
| `inject_n8n_workflow.py` | Workflow deployment | Parse n8n JSON, POST to n8n API | json, httpx |
| `mcr_patch.py` | Jitbit macro patching | Binary MCR file editing | struct, pathlib |
| `sanitize_macro_env.py` | Environment cleanup | Remove jitbit temp files, reset macro state | os, shutil |
| `vault_design_extractor.py` | Obsidian vault parsing | Extract design specs from markdown | pathlib, re |
| `workflow_scrapper.py` | n8n workflow export | Fetch workflows from n8n API | httpx, json |
| `workflow_searcher.py` | Full-text search in workflows | Query ChromaDB for n8n modules | chromadb |

## Issues

1. **Zero test coverage** — No pytest tests for any script
2. **Hardcoded timeouts** — HTTP timeouts fixed at 15s/30s
3. **No progress indicators** — Long operations run silently
4. **Error messages** — Not user-friendly (raw exceptions)
5. **Assumes .env** — Scripts fail without .env file

## Recommendations

1. Add --dry-run flag to destructive scripts
2. Make HTTP timeouts configurable via env/CLI args
3. Add progress bars (tqdm) for long operations
4. Wrap exceptions with user-friendly messages
5. Add .env validation at script startup

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 75 | 40% | 30.0 |
| Completo | 55 | 30% | 16.5 |
| Qualidade | 55 | 30% | 16.5 |
| **Nota Geral** | | | **63.0** |
