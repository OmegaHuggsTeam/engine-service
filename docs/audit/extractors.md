# Audit Report: src/extractors/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `src/extractors/` |
| **Purpose** | Data ingestion pipeline — GitHub repos, n8n workflows, UseCase specs to ChromaDB/Neo4j |
| **Files** | 11 Python files |
| **LOC** | ~3,500 |
| **Tests** | 1 test file (13 tests) |

## File Inventory

| File | Classes/Functions | Key Purpose | LOC |
|------|-------------------|-------------|-----|
| `crm_code_extractor.py` | 27 functions | Regex-based extraction: Express routes, React components, TS services, data models, Kafka workers | 800 |
| `github_ingestor.py` | 6 functions | Downloads .json workflows from GitHub via API | 250 |
| `n8n_extractor.py` | 8 functions | Parses n8n workflows, MERGE-based sync to Neo4j graph | 300 |
| `usecase_indexer.py` | 8 functions | Parses UC-*.md specs to ChromaDB chunks + Neo4j :UseCase nodes | 400 |
| `crm_repo_ingestor.py` | 5 functions | Batch ingestion of 6 sendspeed0 CRM repos | 200 |
| `web_extractor.py` | 50+ functions | Anti-honeypot navigation, API key rotation, identity swap via Selenium | 2,700 |
| `video_to_text.py` | 4 functions | ffmpeg + Whisper audio extraction and transcription | 150 |
| `supabase_client.py` | 2 classes | Supabase credential management (SupabaseAPIKeyManager) | 200 |
| `validators.py` | 4 functions + 1 class | Format validation, Groq/OpenAI connectivity checks | 150 |
| `__init__.py` | — | Module init | 5 |
| `tests/test_github_ingestor.py` | 13 tests | TestParseRepoUrl (8), TestIngestRepository (5) | 200 |

## Dependencies

- `httpx` — HTTP client for GitHub API
- `neo4j` — Graph database sync (via GraphManager)
- `chromadb` — Vector database ingestion
- `selenium` — Web extraction (web_extractor.py)
- `ffmpeg` / `whisper` — Video/audio processing

## Issues

1. **God file** — `web_extractor.py` is 2,700 LOC, needs splitting into focused modules
2. **No retry logic** — HTTP calls in github_ingestor fail without retry
3. **No rate limiting** — GitHub API calls can hit quota silently
4. **Duplicate logic** — URL parsing duplicated between `github_ingestor` and `crm_repo_ingestor`
5. **No dedup** — ChromaDB ingestion doesn't check for existing chunks

## Recommendations

1. Refactor `web_extractor.py` into 3-4 modules (navigation, identity, extraction, anti-detection)
2. Add httpx retry middleware with exponential backoff
3. Implement GitHub API rate limit headers checking
4. Extract shared URL parsing into a utility function
5. Add ChromaDB deduplication via content hashing

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 80 | 40% | 32.0 |
| Completo | 70 | 30% | 21.0 |
| Qualidade | 60 | 30% | 18.0 |
| **Nota Geral** | | | **71.0** |
