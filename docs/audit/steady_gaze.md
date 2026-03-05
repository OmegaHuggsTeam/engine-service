# Audit Report: src/steady_gaze/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `src/steady_gaze/` |
| **Purpose** | Anti-detection analysis — 20-dimensional defense assessment via Selenium + Chrome DevTools Protocol |
| **Files** | 6 Python files |
| **LOC** | ~2,000 |
| **Tests** | 3 test files |

## File Inventory

| File | Classes | Key Purpose | LOC |
|------|---------|-------------|-----|
| `recon.py` | `SteadyGazeRecon` | Main orchestrator — 4 phases (Defense Anatomy, Flow Structure, Identity/Persistence, Behavior/Timing) | 500 |
| `cdp_connection.py` | `CDPConnectionError`, `CDPConnection` | Chrome DevTools Protocol connection management | 200 |
| `cache.py` | `AnalysisCache` | In-memory TTL cache (default 3600s) | 100 |
| `models.py` | 24 Pydantic dataclasses | Full defense analysis model hierarchy | 600 |
| `exceptions.py` | 5 exception classes | SteadyGazeError, CDPConnectionError, AnalysisTimeoutError, etc. | 50 |
| `__init__.py` | — | Module init | 5 |

## Models Breakdown (models.py)

- **Defense Anatomy**: HoneypotElement, ShadowDOMRoot, EventListenerInfo, IsTrustedValidator, WAFDetection
- **Flow Structure**: SPAFramework, StateObject, IframeInfo, RedirectPattern, MonitoringScript
- **Identity/Persistence**: APICallInfo, CookieInfo, StorageAnalysis, FingerprintTechnique, TLSEvent
- **Behavior/Timing**: DOMComplexity, IdleDetector, HotZone, PoWChallenge
- **Rollups**: DefenseAnatomyReport, FlowStructureReport, IdentityPersistenceReport, BehaviorTimingReport, AnalysisReport, ActionRecommendation

## Dependencies

- `selenium.webdriver` — Browser automation
- Chrome DevTools Protocol (CDP) — Low-level browser introspection

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `tests/unit/test_steady_gaze_cache.py` | Cache TTL, eviction |
| `tests/unit/test_steady_gaze_cdp.py` | CDP connection, domain enabling |
| `tests/unit/test_steady_gaze_models.py` | Pydantic model validation |

## Issues

1. **Silent CDP fallback** — CDP connection fails without warning, falls back to Selenium
2. **Fixed timeout** — 10s analysis timeout may be insufficient for large DOMs
3. **No persistence** — Analysis cache is in-memory only, lost on restart
4. **Model complexity** — 24 dataclasses create maintenance burden

## Recommendations

1. Add explicit logging when CDP falls back to Selenium
2. Make analysis timeout configurable via env or constructor
3. Consider Neo4j persistence for analysis results
4. Evaluate consolidating related dataclasses

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 80 | 40% | 32.0 |
| Completo | 65 | 30% | 19.5 |
| Qualidade | 75 | 30% | 22.5 |
| **Nota Geral** | | | **74.0** |
