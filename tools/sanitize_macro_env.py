"""
Reset de Ambiente para Macro Jitbit - Sanitização entre rodadas.

Abstração de Limpeza (Garbage Collector): restaura o Home State (443, 422)
para garantir idempotência do loop. Ver docs/MACRO_JITBIT_DEBUG.md.

Executa antes/depois do macro para garantir estado limpo:
- Fecha abas excedentes (Ctrl+W em loop)
- Move cursor para Home State (443, 422)
- Opcional: foca janela alvo

Uso:
  python tools/sanitize_macro_env.py
  python tools/sanitize_macro_env.py --close-tabs 5 --cursor 443 422
  python tools/sanitize_macro_env.py --focus "Chrome"
"""

import argparse
import time
from pathlib import Path

# pyautogui para controle de teclado/mouse
try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.1
except ImportError:
    pyautogui = None


def close_tabs(count: int = 5, delay_ms: int = 150) -> None:
    """Envia Ctrl+W N vezes para fechar abas excedentes."""
    if not pyautogui:
        print("pyautogui não instalado. Use: pip install pyautogui")
        return
    for _ in range(count):
        pyautogui.hotkey("ctrl", "w")
        time.sleep(delay_ms / 1000.0)


def move_cursor(x: int, y: int) -> None:
    """Move cursor para coordenada (x, y)."""
    if not pyautogui:
        return
    pyautogui.moveTo(x, y, duration=0.2)


def focus_window(title_substring: str) -> bool:
    """Foca janela cujo título contenha title_substring (Windows)."""
    try:
        import ctypes
        from ctypes import wintypes

        user32 = ctypes.windll.user32
        EnumWindows = user32.EnumWindows
        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, wintypes.HWND, wintypes.LPARAM)
        GetWindowTextW = user32.GetWindowTextW
        GetWindowTextLengthW = user32.GetWindowTextLengthW
        SetForegroundWindow = user32.SetForegroundWindow

        def callback(hwnd, lparam):
            length = GetWindowTextLengthW(hwnd) + 1
            buf = ctypes.create_unicode_buffer(length)
            GetWindowTextW(hwnd, buf, length)
            if title_substring.lower() in buf.value.lower():
                SetForegroundWindow(hwnd)
                return False  # stop enum
            return True

        EnumWindows(EnumWindowsProc(callback), 0)
        return True
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset de ambiente para macro Jitbit")
    parser.add_argument("--close-tabs", type=int, default=5, help="Quantidade de Ctrl+W (default: 5)")
    parser.add_argument("--tab-delay", type=int, default=150, help="Delay entre Ctrl+W em ms (default: 150)")
    parser.add_argument("--cursor", type=int, nargs=2, default=[443, 422], metavar=("X", "Y"),
                        help="Coordenada final do cursor (default: 443 422)")
    parser.add_argument("--focus", type=str, default="", help="Focar janela com título contendo este texto")
    parser.add_argument("--no-close", action="store_true", help="Não executar Ctrl+W")
    parser.add_argument("--no-cursor", action="store_true", help="Não mover cursor")
    args = parser.parse_args()

    if not pyautogui:
        print("Instale pyautogui: pip install pyautogui")
        return 1

    if args.focus:
        focus_window(args.focus)
        time.sleep(0.5)

    if not args.no_close:
        close_tabs(args.close_tabs, args.tab_delay)
        time.sleep(0.3)

    if not args.no_cursor:
        move_cursor(args.cursor[0], args.cursor[1])

    print("Sanitização concluída.")
    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
