# Audit Report: src/processors/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `src/processors/` |
| **Purpose** | Text processing — chunking, n8n flow validation, knowledge generation |
| **Files** | 4 Python files |
| **LOC** | ~700 |
| **Tests** | 0 dedicated test files |

## File Inventory

| File | Classes/Functions | Key Purpose | LOC |
|------|-------------------|-------------|-----|
| `processor.py` | 4 functions | Recursive character splitting (chunk_size=900, overlap=100), LangChain fallback | 200 |
| `cleaner.py` | 5 functions | Groq-powered transcript cleaning (llama-3.3-70b), parallel file processing | 200 |
| `n8n_validator.py` | `ValidationIssue`, `ValidationResult`, `N8nFlowValidator` | Validates n8n workflow JSON structure | 200 |
| `n8n_knowledge.py` | 4 functions | Classifies workflows, generates n8n_capabilities.md and n8n_recipes.md | 150 |

## Dependencies

- `langchain` (optional) — RecursiveCharacterTextSplitter
- `groq` — Transcript cleaning via LLM

## Issues

1. **Zero test coverage** — No dedicated unit tests for any processor
2. **No error handling** — Malformed JSON in n8n_validator not handled gracefully
3. **API dependency** — `cleaner.py` requires Groq API (single point of failure)
4. **No chunk validation** — Post-split chunks not validated for completeness

## Recommendations

1. Add pytest suite covering: split boundaries, validation edge cases, cleaning accuracy
2. Add try/catch around JSON parsing in n8n_validator
3. Add offline fallback for cleaner.py (regex-based cleaning)
4. Validate chunk boundaries don't split mid-sentence

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 75 | 40% | 30.0 |
| Completo | 55 | 30% | 16.5 |
| Qualidade | 60 | 30% | 18.0 |
| **Nota Geral** | | | **64.5** |
