# Audit Report: scripts/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `scripts/` |
| **Purpose** | Setup & maintenance — initial setup, data ingestion, health checks, bot startup |
| **Files** | 12 Python scripts |
| **LOC** | ~1,200 |
| **Tests** | 0 (manual integration scripts) |

## File Inventory

| Script | Purpose | Key Functions |
|--------|---------|---------------|
| `setup_intelligence.py` | Full pipeline init | `check_environment()`, `run_ingestion()`, `verify_setup()` |
| `init_vector_db.py` | Migrate chunks to ChromaDB | Reads `data/chunks/*.json`, calls `add_chunks()` |
| `mass_ingestion.py` | Batch repo ingestion (zie619) | `ingest_repository()`, `generate_capabilities_md()`, `generate_recipes_md()` |
| `health_check.py` | API validation | 6 `check_*()` functions (Groq, OpenAI, Telegram, Selenium), Markdown report |
| `run_telegram_bot.py` | Bot startup | Telegram command handlers (e.g., /cluster_status) |
| `test_extractor.py` | Manual extractor testing | Calls `extract_api_key()`, validates output |
| `verify_intelligence.py` | Verify ChromaDB + Neo4j | `count_chunks()`, `query_graph()` |
| `demo_composer.py` | ComposerAgent demo | Simulates workflow composition requests |
| `test_rotation_flow.py` | Groq key rotation (manual) | Validates identity swapping |
| `test_rotation_simple.py` | Simple key rotation test | Single API key test |
| `generate_bot_evolution_workflow.py` | n8n workflow generation | Creates evolution.json with 15+ nodes |
| `selenium/test_selum_field.py` | Selenium field automation | Locates form fields, simulates input |

## Issues

1. **Hardcoded paths** — Project paths not portable across machines
2. **No parallel execution** — Sequential processing only
3. **Verbose logging** — Output hard to parse
4. **No idempotency** — Re-running scripts may duplicate data
5. **Test scripts mixed with setup** — `test_*.py` naming conflicts with pytest discovery

## Recommendations

1. Use `pathlib` with relative paths for portability
2. Add `--parallel` flag to mass_ingestion.py
3. Add structured logging (JSON format) option
4. Add idempotency checks (hash-based dedup)
5. Rename test scripts to `manual_*` or move to `scripts/manual/`

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 70 | 40% | 28.0 |
| Completo | 55 | 30% | 16.5 |
| Qualidade | 50 | 30% | 15.0 |
| **Nota Geral** | | | **59.5** |
