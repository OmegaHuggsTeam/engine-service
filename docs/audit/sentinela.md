# Audit Report: src/sentinela/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `src/sentinela/` |
| **Purpose** | Visual monitoring — screenshot analysis, template matching, IFTTT connectivity watchdog |
| **Files** | 8 Python files |
| **LOC** | ~1,800 |
| **Tests** | 5 test files |

## File Inventory

| File | Classes | Key Purpose | LOC |
|------|---------|-------------|-----|
| `config.py` | `SentinelaConfig` | Dataclass with env loading (neo4j_log_path, templates_dir, jitbit_path) | 80 |
| `exceptions.py` | 7 exception classes | SentinelaError, ScreenshotError, CatarataError, VisualDetectionError, etc. | 50 |
| `screenshot_analyzer.py` | `ScreenshotAnalyzer` | PIL/CV2 capture, catarata detection (black screen), in-memory processing | 300 |
| `visual_detector.py` | `VisualMatchResult`, `AnchorPoint`, `VisualDetector` | Template matching with learning mode, 0.85 confidence threshold | 400 |
| `ifttt_connector.py` | `AlertStatus`, `ConnectivityStatus`, `RetryConfig`, `AlertAttempt`, `Alert`, `IFTTTConnector` | Connectivity watchdog with TelemetryHub integration, exponential backoff | 500 |
| `tools/capture_templates.py` | `TemplateCaptureSession` | Interactive template capture UI | 200 |
| `tools/__init__.py` | — | Module init | 5 |
| `__init__.py` | — | Module init | 5 |

## Dependencies

- `PIL` / `cv2` / `numpy` — Image processing and template matching
- `urllib` / `httpx` — HTTP requests for IFTTT webhooks
- `TelemetryHub` — Event dispatching for alerts

## Test Coverage

| Test File | Coverage |
|-----------|----------|
| `tests/sentinela/test_visual_detector.py` | Template matching, confidence thresholds |
| `tests/sentinela/test_screenshot_analyzer.py` | Capture, catarata detection |
| `tests/sentinela/test_ifttt_connector.py` | Webhook sending, retry logic |
| `tests/sentinela/stress_test_vision.py` | Performance under load |
| `tests/sentinela/test_stress_test.py` | Stress test validation |

## Issues

1. **Template path hardcoded** — `./templates` with no graceful fallback
2. **Limited detection** — Catarata only checks black screen, not other failure modes (white screen, freeze)
3. **No circuit breaker** — Repeated IFTTT failures not short-circuited
4. **IFTTT key exposure** — Key may be embedded in code (should be env-only)

## Recommendations

1. Add configurable template directory with fallback to default
2. Extend catarata detection: white screen, frozen state, partial render
3. Implement circuit breaker pattern for IFTTT connector
4. Audit IFTTT key handling — ensure env-only access

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 85 | 40% | 34.0 |
| Completo | 80 | 30% | 24.0 |
| Qualidade | 75 | 30% | 22.5 |
| **Nota Geral** | | | **80.5** |
