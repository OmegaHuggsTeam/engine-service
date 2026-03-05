"""
Smooth Movement - Movimento de mouse com Curvas de Bezier (humanizado).
Velocidade afeta curvatura e tempo de deslize.
"""

import math
import random
import time
from pathlib import Path
from typing import Tuple

try:
    import pyautogui
except ImportError:
    pyautogui = None

from .emergency import check as check_emergency_stop

_ROOT = Path(__file__).resolve().parent.parent
_LOG_FILE = _ROOT / "logs" / "hardware.log"


def _log(action: str, **kwargs):
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    params = " ".join(f"{k}={v}" for k, v in kwargs.items())
    with open(_LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {action} {params}\n")

# Velocidades: afetam duracao e curvatura
SPEED_PROFILES = {
    "slow": {"duration_factor": 2.0, "curve_strength": 0.4},
    "normal": {"duration_factor": 1.0, "curve_strength": 0.25},
    "fast": {"duration_factor": 0.5, "curve_strength": 0.1},
}


def _bezier_point(t: float, p0: Tuple[float, float], p1: Tuple[float, float], p2: Tuple[float, float], p3: Tuple[float, float]) -> Tuple[float, float]:
    """Ponto na curva Bezier cubica em t (0..1)."""
    u = 1 - t
    u2 = u * u
    u3 = u2 * u
    t2 = t * t
    t3 = t2 * t
    x = u3 * p0[0] + 3 * u2 * t * p1[0] + 3 * u * t2 * p2[0] + t3 * p3[0]
    y = u3 * p0[1] + 3 * u2 * t * p1[1] + 3 * u * t2 * p2[1] + t3 * p3[1]
    return (x, y)


def travel_to(x: int, y: int, speed: str = "normal") -> None:
    """
    Move o mouse organicamente ate (x, y) usando Bezier.
    speed: "slow" | "normal" | "fast" - afeta duracao e curvatura.
    """
    if check_emergency_stop():
        raise RuntimeError("Emergency Stop ativo")
    if not pyautogui:
        raise RuntimeError("pyautogui nao instalado")

    start_x, start_y = pyautogui.position()
    end_x, end_y = float(x), float(y)
    distance = math.sqrt((end_x - start_x) ** 2 + (end_y - start_y) ** 2)

    profile = SPEED_PROFILES.get(speed, SPEED_PROFILES["normal"])
    duration_factor = profile["duration_factor"]
    curve_strength = profile["curve_strength"]

    # Duracao baseada na distancia (ms)
    base_duration = 150 + distance * 0.15
    duration_ms = int(base_duration * duration_factor)
    duration_ms = max(100, min(duration_ms, 3000))

    # Pontos de controle Bezier (curvatura humanizada)
    dx = end_x - start_x
    dy = end_y - start_y
    offset = distance * curve_strength + random.uniform(-20, 20)
    ctrl1 = (
        start_x + dx * 0.25 + random.uniform(-offset, offset),
        start_y + dy * 0.25 + random.uniform(-offset, offset),
    )
    ctrl2 = (
        start_x + dx * 0.75 + random.uniform(-offset, offset),
        start_y + dy * 0.75 + random.uniform(-offset, offset),
    )

    p0 = (start_x, start_y)
    p1 = ctrl1
    p2 = ctrl2
    p3 = (end_x, end_y)

    steps = max(10, int(duration_ms / 16))
    step_delay = duration_ms / 1000.0 / steps

    for i in range(steps + 1):
        if check_emergency_stop():
            break
        t = i / steps
        # Easing: ease-in-out para inicio/fim mais suaves
        t_ease = t * t * (3 - 2 * t)
        px, py = _bezier_point(t_ease, p0, p1, p2, p3)
        pyautogui.moveTo(int(px), int(py))
        time.sleep(step_delay)

    _log("travel_to", start=(start_x, start_y), end=(x, y), speed=speed, duration_ms=duration_ms)
