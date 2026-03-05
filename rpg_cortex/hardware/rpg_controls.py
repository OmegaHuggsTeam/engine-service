"""
RPG Controls - Primitivas de hardware (clique, digitação, captura de tela).
Medula Espinhal - Phase 1. Cada acao gera log em logs/hardware.log.
"""

import random
import time
from pathlib import Path
from typing import Optional, Tuple

try:
    import pyautogui
    pyautogui.FAILSAFE = True  # Mover mouse ao canto = abortar
    pyautogui.PAUSE = 0.05
except ImportError:
    pyautogui = None

ROOT = Path(__file__).resolve().parent.parent
LOG_FILE = ROOT / "logs" / "hardware.log"


def _log(action: str, **kwargs):
    """Registra acao em hardware.log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    params = " ".join(f"{k}={v}" for k, v in kwargs.items())
    line = f"[{ts}] {action} {params}\n"
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line)


def check_emergency_stop() -> bool:
    """Verifica se Emergency Stop foi acionado."""
    from .emergency import check
    return check()


def trigger_emergency_stop():
    """Aciona Emergency Stop (ESC ou Ctrl+C)."""
    from .emergency import trigger
    trigger()
    _log("EMERGENCY_STOP", triggered=True)


def reset_emergency_stop():
    """Reseta o flag de Emergency Stop."""
    from .emergency import reset
    reset()


def get_screen_dimensions() -> Tuple[int, int]:
    """Retorna (largura, altura) da tela."""
    if not pyautogui:
        raise RuntimeError("pyautogui nao instalado. pip install pyautogui")
    w, h = pyautogui.size()
    return (w, h)


def validate_coordinates(x: int, y: int) -> bool:
    """Valida se coordenadas estao dentro dos limites da tela."""
    w, h = get_screen_dimensions()
    return 0 <= x < w and 0 <= y < h


def take_vision(
    region: Optional[Tuple[int, int, int, int]] = None,
    output_path: Optional[Path] = None,
) -> Path:
    """
    Captura screenshot (tela inteira ou regiao).
    region: (x, y, width, height) ou None para tela inteira.
    """
    if check_emergency_stop():
        raise RuntimeError("Emergency Stop ativo")
    if not pyautogui:
        raise RuntimeError("pyautogui nao instalado")
    out = output_path or (ROOT / "temp" / "vision.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if region:
            x, y, w, h = region
            img = pyautogui.screenshot(region=(x, y, w, h))
        else:
            img = pyautogui.screenshot()
        img.save(str(out))
        _log("take_vision", path=str(out), region=region)
        return out
    except Exception as e:
        _log("take_vision", error=str(e))
        raise


def click_at(x: int, y: int, button: str = "left") -> None:
    """Clica nas coordenadas (x, y)."""
    if check_emergency_stop():
        raise RuntimeError("Emergency Stop ativo")
    if not validate_coordinates(x, y):
        _log("click_at", error="coordenadas_fora_da_tela", x=x, y=y)
        raise ValueError(f"Coordenadas ({x}, {y}) fora da tela")
    if not pyautogui:
        raise RuntimeError("pyautogui nao instalado")
    pyautogui.click(x, y, button=button)
    _log("click_at", x=x, y=y, button=button)


def type_text(text: str, delay_ms: int = 50) -> None:
    """Digita texto com delay humanizado entre teclas."""
    if check_emergency_stop():
        raise RuntimeError("Emergency Stop ativo")
    if not pyautogui:
        raise RuntimeError("pyautogui nao instalado")
    base_delay = delay_ms / 1000.0
    for char in text:
        if check_emergency_stop():
            break
        pyautogui.press(char) if len(char) == 1 else pyautogui.write(char)
        time.sleep(base_delay + random.uniform(-0.02, 0.05))
    _log("type_text", length=len(text), delay_ms=delay_ms)


def move_to_coord(x: int, y: int, speed: float = 1.0) -> None:
    """
    Move o mouse para (x, y) com movimento suave.
    speed: float 0.5=slow, 1.0=normal, 2.0=fast
    """
    if check_emergency_stop():
        raise RuntimeError("Emergency Stop ativo")
    if not validate_coordinates(x, y):
        _log("move_to_coord", error="coordenadas_fora_da_tela", x=x, y=y)
        raise ValueError(f"Coordenadas ({x}, {y}) fora da tela")
    speed_str = "slow" if speed < 0.7 else ("fast" if speed > 1.5 else "normal")
    try:
        from .smooth_movement import travel_to
        travel_to(x, y, speed=speed_str)
    except ImportError:
        if pyautogui:
            pyautogui.moveTo(x, y)
        _log("move_to_coord", x=x, y=y, speed=speed, fallback="pyautogui")
    else:
        _log("move_to_coord", x=x, y=y, speed=speed_str)
