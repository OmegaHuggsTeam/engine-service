# Audit Report: rpg_cortex/

## Overview

| Field | Value |
|-------|-------|
| **Path** | `rpg_cortex/` |
| **Purpose** | Hardware control — Jitbit macro execution, screen mapping, RPG game automation |
| **Files** | 13 Python files |
| **LOC** | ~2,500 |
| **Tests** | 2 test files |

## Structure

```
rpg_cortex/
  hardware/
    __init__.py
    rpg_controls.py        # Core hardware primitives (screenshot, click, type)
    smooth_movement.py     # Bezier curve mouse movement
    jitbit_wrapper.py      # CLI interface to Jitbit MacroRecorder.exe
    cartographer.py        # Window detection, monitor enumeration
    emergency.py           # Global emergency stop (ESC / Ctrl+C)
    exceptions.py          # 7 exception classes
  knowledge/
    __init__.py
    macro_knowledge_base.py  # YAML-based macro registry with keyword search
  temp/
    heimdall_orchestration.py  # Orchestration prototype
  tests/
    first_step.py          # Bootstrap test
    test_macro_system.py   # 3 functional tests
```

## File Inventory

| File | Classes/Functions | Key Purpose | LOC |
|------|-------------------|-------------|-----|
| `rpg_controls.py` | 15 functions | `take_vision()`, `click_at()`, `type_text()`, `move_to_coord()`, emergency stop | 400 |
| `smooth_movement.py` | 4 functions | `travel_to()` with cubic Bezier interpolation (normal/slow/fast) | 200 |
| `jitbit_wrapper.py` | `JitbitWrapper` | `execute_macro()` — runs .mcr/.jmb files with timeout | 200 |
| `cartographer.py` | 5 functions | `get_all_windows()`, `find_window_centers()`, `map_interface()` | 250 |
| `emergency.py` | 3 functions | `check()`, `trigger()`, `reset()` — global stop flag | 50 |
| `exceptions.py` | 7 classes | MacroError, MacroNotFoundError, MacroCorruptedError, etc. | 60 |
| `macro_knowledge_base.py` | `MacroEntry`, `MacroKnowledgeBase` | YAML loader, query by keyword/screen state | 200 |

## Dependencies

- `pyautogui` — Mouse/keyboard control
- `pygetwindow` — Window enumeration
- `subprocess` — Jitbit process execution
- `ctypes` — EnumDisplayMonitors for multi-monitor support

## Issues

1. **Hardcoded Jitbit paths** — Brittle for different installations
2. **Not thread-safe** — pyautogui is not reentrant
3. **Screenshot validation** — Size/format not validated before processing
4. **Global emergency stop** — Not task-scoped (stops everything)
5. **No logging aggregation** — Logs to `logs/hardware.log` without rotation

## Recommendations

1. Make Jitbit path configurable via env (JITBIT_PATH)
2. Add thread lock around pyautogui calls
3. Validate screenshot dimensions before processing
4. Scope emergency stop to individual task contexts
5. Add log rotation to hardware.log

## Score

| Dimension | Score | Weight | Weighted |
|-----------|-------|--------|----------|
| Correto | 80 | 40% | 32.0 |
| Completo | 70 | 30% | 21.0 |
| Qualidade | 65 | 30% | 19.5 |
| **Nota Geral** | | | **72.5** |
