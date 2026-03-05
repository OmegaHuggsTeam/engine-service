"""
Cartographer - Mapeador de janelas.
Localiza janelas "Cursor" e "Kiro" (Chrome/Edge) e salva coordenadas centrais.
"""

import ctypes
import ctypes.wintypes
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "knowledge" / "mapa_interface.json"

user32 = ctypes.windll.user32


def get_all_windows() -> List[Dict]:
    """Lista todas as janelas visiveis."""
    results = []

    def callback(hwnd, lparam):
        if not user32.IsWindowVisible(hwnd):
            return True
        length = user32.GetWindowTextLengthW(hwnd) + 1
        buf = ctypes.create_unicode_buffer(length)
        user32.GetWindowTextW(hwnd, buf, length)
        title = buf.value
        if not title:
            return True
        rect = ctypes.wintypes.RECT()
        if user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            w, h = rect.right - rect.left, rect.bottom - rect.top
            if w > 50 and h > 50 and rect.left > -32000:  # Ignora minimizados/off-screen
                results.append({
                    "hwnd": int(hwnd),
                    "title": title,
                    "left": rect.left,
                    "top": rect.top,
                    "right": rect.right,
                    "bottom": rect.bottom,
                    "width": w,
                    "height": h,
                })
        return True

    WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    user32.EnumWindows(WNDENUMPROC(callback), 0)
    return results


def find_window_centers(
    cursor_title: str = "Cursor",
    kiro_titles: Tuple[str, ...] = ("Kiro", "Chrome", "Edge", "Cursor"),
) -> Dict:
    """
    Localiza janelas Cursor e Kiro e retorna coordenadas centrais.
    kiro_titles: titulos alternativos para a janela do chat (Chrome com Kiro, etc).
    """
    windows = get_all_windows()
    mapa = {
        "cursor": None,
        "kiro": None,
        "windows_found": [],
    }

    for w in windows:
        title = w.get("title", "")
        if not title:
            continue
        cx = w["left"] + (w["width"] // 2)
        cy = w["top"] + (w["height"] // 2)
        entry = {
            "title": title,
            "center": {"x": cx, "y": cy},
            "rect": {"left": w["left"], "top": w["top"], "width": w["width"], "height": w["height"]},
        }
        if cursor_title.lower() in title.lower() and "Cursor" in title:
            mapa["cursor"] = entry
        for kt in kiro_titles:
            if kt.lower() in title.lower() and mapa["kiro"] is None:
                mapa["kiro"] = entry
                break
        mapa["windows_found"].append({"title": title[:50], "center": {"x": cx, "y": cy}})

    return mapa


def map_interface(save: bool = True) -> Dict:
    """
    Mapeia janelas e salva em knowledge/mapa_interface.json.
    Retorna o mapa com coordenadas centrais.
    """
    mapa = find_window_centers()
    if save:
        MAP_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(MAP_FILE, "w", encoding="utf-8") as f:
            json.dump(mapa, f, indent=2, ensure_ascii=False)
    return mapa


def get_kiro_chat_coords() -> Optional[Tuple[int, int]]:
    """Retorna (x, y) do centro da janela Kiro (campo de chat). Ajuste fino pode ser feito no mapa."""
    if not MAP_FILE.exists():
        map_interface()
    with open(MAP_FILE, "r", encoding="utf-8") as f:
        mapa = json.load(f)
    kiro = mapa.get("kiro")
    if not kiro:
        return None
    c = kiro["center"]
    # Aproximacao: campo de chat costuma estar na parte inferior da janela
    rect = kiro.get("rect", {})
    h = rect.get("height", 600)
    chat_y = c["y"] + int(h * 0.35)  # Abaixo do centro
    return (c["x"], chat_y)


def get_screen_center() -> Tuple[int, int]:
    """Retorna o centro da tela principal."""
    try:
        import pyautogui
        w, h = pyautogui.size()
        return (w // 2, h // 2)
    except ImportError:
        return (960, 540)
