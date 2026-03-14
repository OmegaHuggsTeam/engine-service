"""
Computer Use Agent - Controle fisico do computador via Neural Link.

Integra pyautogui, AHK scripts e primitivas de automação de UI
em um agente orquestravel pelo NeuralLinkOrchestrator.

Protocolo Heimdall: Consciencia de dual-monitor, mapeamento espacial
de janelas, e navegacao inteligente entre monitores.

Capabilities: computer_use, ui_automation, screenshot, typing, mouse_control,
              dual_monitor, window_management, spatial_awareness
"""

import ctypes
import json
import logging
import math
import os
import subprocess
import sys
import time

if sys.platform == "win32":
    import ctypes.wintypes as wt
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent
AHK_DIR = PROJECT_ROOT / "automation_hub" / "hardware"
TEMP_DIR = PROJECT_ROOT / "temp" / "computer_use"


def _ensure_pyautogui():
    """Importa e configura pyautogui com safety."""
    import pyautogui
    pyautogui.FAILSAFE = True   # Mover mouse para canto superior esquerdo = ABORT
    pyautogui.PAUSE = 0.05      # Pausa minima entre acoes
    return pyautogui


class MonitorLayout:
    """Mapeamento espacial de todos os monitores via Win32 API."""

    def __init__(self):
        self.monitors: list[dict] = []
        self.virtual_screen: dict = {}
        self._detect()

    def _detect(self):
        if sys.platform != "win32":
            return
        user32 = ctypes.windll.user32
        SM_XVIRTUALSCREEN = 76
        SM_YVIRTUALSCREEN = 77
        SM_CXVIRTUALSCREEN = 78
        SM_CYVIRTUALSCREEN = 79

        self.virtual_screen = {
            "x": user32.GetSystemMetrics(SM_XVIRTUALSCREEN),
            "y": user32.GetSystemMetrics(SM_YVIRTUALSCREEN),
            "width": user32.GetSystemMetrics(SM_CXVIRTUALSCREEN),
            "height": user32.GetSystemMetrics(SM_CYVIRTUALSCREEN),
        }

        class MONITORINFOEX(ctypes.Structure):
            _fields_ = [
                ("cbSize", ctypes.c_ulong),
                ("rcMonitor", wt.RECT),
                ("rcWork", wt.RECT),
                ("dwFlags", ctypes.c_ulong),
                ("szDevice", ctypes.c_wchar * 32),
            ]

        monitors = self.monitors

        @ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_ulong, ctypes.c_ulong,
                            ctypes.POINTER(wt.RECT), ctypes.c_double)
        def enum_cb(hMonitor, hdcMonitor, lprcMonitor, dwData):
            info = MONITORINFOEX()
            info.cbSize = ctypes.sizeof(MONITORINFOEX)
            user32.GetMonitorInfoW(hMonitor, ctypes.byref(info))
            rc = info.rcMonitor
            work = info.rcWork
            monitors.append({
                "device": info.szDevice,
                "primary": bool(info.dwFlags & 1),
                "bounds": {"left": rc.left, "top": rc.top,
                           "right": rc.right, "bottom": rc.bottom},
                "width": rc.right - rc.left,
                "height": rc.bottom - rc.top,
                "work_area": {"left": work.left, "top": work.top,
                              "right": work.right, "bottom": work.bottom},
            })
            return True

        user32.EnumDisplayMonitors(None, None, enum_cb, 0)

    @property
    def count(self) -> int:
        return len(self.monitors)

    def get_primary(self) -> Optional[dict]:
        for m in self.monitors:
            if m["primary"]:
                return m
        return self.monitors[0] if self.monitors else None

    def get_secondary(self) -> Optional[dict]:
        for m in self.monitors:
            if not m["primary"]:
                return m
        return None

    def monitor_for_point(self, x: int, y: int) -> Optional[int]:
        """Returns monitor index (0-based) for a given virtual coordinate."""
        for i, m in enumerate(self.monitors):
            b = m["bounds"]
            if b["left"] <= x <= b["right"] and b["top"] <= y <= b["bottom"]:
                return i
        return None

    def center_of(self, monitor_index: int) -> tuple[int, int]:
        """Returns center (x, y) of a monitor in virtual coords."""
        m = self.monitors[monitor_index]
        b = m["bounds"]
        return ((b["left"] + b["right"]) // 2, (b["top"] + b["bottom"]) // 2)

    def to_dict(self) -> dict:
        return {
            "virtual_screen": self.virtual_screen,
            "monitors": self.monitors,
            "count": self.count,
        }


class ComputerUseAgent:
    """
    Agente que converte intencoes em acoes fisicas no computador.
    Protocolo Heimdall: consciencia dual-monitor, navegacao espacial,
    e gerenciamento inteligente de janelas.
    Todos os metodos sao seguros (FAILSAFE=True) e logados.
    """

    def __init__(self):
        self._gui = _ensure_pyautogui()
        self.layout = MonitorLayout()
        self._session_log: list[dict] = []
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        self._log_action("init", {"monitors": self.layout.count,
                                   "virtual": self.layout.virtual_screen})

    def _log_action(self, action: str, details: dict = None):
        """Registra acao no session log interno."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details or {},
        }
        self._session_log.append(entry)
        logger.info(f"[Heimdall] {action}: {details}")

    def get_session_log(self) -> list[dict]:
        return list(self._session_log)

    # ================================================================
    # SPATIAL AWARENESS (Protocolo Heimdall)
    # ================================================================

    def get_monitor_layout(self) -> dict:
        """Retorna mapeamento completo dos monitores."""
        return self.layout.to_dict()

    def get_window_map(self) -> list[dict]:
        """Enumera todas as janelas visiveis com monitor assignment."""
        user32 = ctypes.windll.user32
        windows = []

        @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int),
                            ctypes.POINTER(ctypes.c_int))
        def enum_cb(hwnd, _):
            if user32.IsWindowVisible(hwnd):
                buf = ctypes.create_unicode_buffer(256)
                user32.GetWindowTextW(hwnd, buf, 256)
                title = buf.value.strip()
                if title and len(title) > 3:
                    rect = wt.RECT()
                    user32.GetWindowRect(hwnd, ctypes.byref(rect))
                    cx = (rect.left + rect.right) // 2
                    cy = (rect.top + rect.bottom) // 2
                    mon_idx = self.layout.monitor_for_point(cx, cy)
                    windows.append({
                        "title": title[:80],
                        "hwnd": ctypes.cast(hwnd, ctypes.c_void_p).value or 0,
                        "rect": {"left": rect.left, "top": rect.top,
                                 "right": rect.right, "bottom": rect.bottom},
                        "center": (cx, cy),
                        "monitor": mon_idx,
                        "minimized": rect.left < -10000,
                    })
            return True

        user32.EnumWindows(enum_cb, 0)
        return windows

    def find_window(self, *keywords: str) -> Optional[dict]:
        """Encontra janela cujo titulo contenha todos os keywords."""
        windows = self.get_window_map()
        for w in windows:
            title_lower = w["title"].lower()
            if all(k.lower() in title_lower for k in keywords):
                return w
        return None

    def move_window_to_monitor(self, title_substring: str,
                                monitor_index: int) -> dict:
        """Move janela para monitor especifico via Win32 SetWindowPos."""
        user32 = ctypes.windll.user32
        w_info = self.find_window(title_substring)
        if not w_info:
            return {"success": False, "error": f"Window '{title_substring}' not found"}

        if monitor_index >= self.layout.count:
            return {"success": False, "error": f"Monitor {monitor_index} does not exist"}

        target_mon = self.layout.monitors[monitor_index]
        tb = target_mon["work_area"]
        target_w = tb["right"] - tb["left"]
        target_h = tb["bottom"] - tb["top"]

        hwnd = w_info["hwnd"]
        # Restore if minimized
        user32.ShowWindow(hwnd, 9)
        time.sleep(0.2)

        # Move and resize to fill target monitor
        user32.SetWindowPos(hwnd, 0, tb["left"], tb["top"],
                            target_w, target_h, 0x0040)  # SWP_SHOWWINDOW
        time.sleep(0.3)

        self._log_action("move_window", {
            "window": title_substring,
            "to_monitor": monitor_index,
            "bounds": tb,
        })
        return {"success": True, "window": title_substring,
                "monitor": monitor_index}

    def snap_window(self, title_substring: str,
                    position: str = "maximize") -> dict:
        """Snap janela: maximize, left, right."""
        user32 = ctypes.windll.user32
        w_info = self.find_window(title_substring)
        if not w_info:
            return {"success": False, "error": f"Window '{title_substring}' not found"}

        hwnd = w_info["hwnd"]
        user32.ShowWindow(hwnd, 9)  # Restore first
        time.sleep(0.1)

        mon_idx = w_info["monitor"] or 0
        tb = self.layout.monitors[mon_idx]["work_area"]
        mw = tb["right"] - tb["left"]
        mh = tb["bottom"] - tb["top"]

        if position == "maximize":
            user32.ShowWindow(hwnd, 3)  # SW_MAXIMIZE
        elif position == "left":
            user32.SetWindowPos(hwnd, 0, tb["left"], tb["top"],
                                mw // 2, mh, 0x0040)
        elif position == "right":
            user32.SetWindowPos(hwnd, 0, tb["left"] + mw // 2, tb["top"],
                                mw // 2, mh, 0x0040)

        self._log_action("snap_window", {"window": title_substring,
                                          "position": position})
        return {"success": True, "window": title_substring,
                "position": position}

    # ================================================================
    # SMART CLIPBOARD (Skill de Area de Transferencia Inteligente)
    # ================================================================

    def smart_clipboard_transfer(self, source_window: str,
                                  target_window: str,
                                  select_all: bool = False) -> dict:
        """
        Copia conteudo de source_window e cola em target_window.
        Flow: Focus source -> [Select All] -> Ctrl+C -> Focus target -> Ctrl+V
        """
        # 1. Focus source
        result = self.focus_window(source_window)
        if not result.get("success"):
            return {"success": False, "error": f"Could not focus source: {source_window}"}
        time.sleep(0.4)

        # 2. Select + Copy
        if select_all:
            self._gui.hotkey("ctrl", "a")
            time.sleep(0.2)
        self._gui.hotkey("ctrl", "c")
        time.sleep(0.3)

        # 3. Read clipboard
        try:
            import pyperclip
            content = pyperclip.paste()
        except ImportError:
            content = "(clipboard read unavailable)"

        # 4. Focus target
        result = self.focus_window(target_window)
        if not result.get("success"):
            return {"success": False, "error": f"Could not focus target: {target_window}"}
        time.sleep(0.4)

        # 5. Paste
        self._gui.hotkey("ctrl", "v")
        time.sleep(0.2)

        self._log_action("smart_clipboard", {
            "from": source_window, "to": target_window,
            "chars": len(content), "select_all": select_all,
        })
        return {"success": True, "from": source_window,
                "to": target_window, "chars_transferred": len(content),
                "preview": content[:200]}

    def grab_and_analyze(self, source_window: str,
                          target_window: str) -> dict:
        """
        Captura log/erro de source, cola em target para analise.
        Otimizado para workflow: Terminal -> Cursor/Kiro.
        """
        # Focus source, select last output
        self.focus_window(source_window)
        time.sleep(0.4)

        # Select all visible text in terminal
        self._gui.hotkey("ctrl", "shift", "a")  # Select all in most terminals
        time.sleep(0.2)
        self._gui.hotkey("ctrl", "c")
        time.sleep(0.3)

        try:
            import pyperclip
            content = pyperclip.paste()
        except ImportError:
            content = ""

        # Navigate to target
        self.focus_window(target_window)
        time.sleep(0.4)

        # Go to end of file and paste
        self._gui.hotkey("ctrl", "End")
        time.sleep(0.1)
        self._gui.press("enter")
        self._gui.press("enter")
        self._gui.hotkey("ctrl", "v")
        time.sleep(0.2)
        self._gui.hotkey("ctrl", "s")
        time.sleep(0.3)

        self._log_action("grab_and_analyze", {
            "from": source_window, "to": target_window,
            "chars": len(content),
        })
        return {"success": True, "chars": len(content),
                "preview": content[:300]}

    # ================================================================
    # PRIMITIVAS DE VISAO
    # ================================================================

    def screenshot(self, region: Optional[tuple] = None,
                   monitor: Optional[int] = None) -> str:
        """
        Captura screenshot da tela inteira, regiao, ou monitor especifico.
        Retorna path do arquivo salvo.
        """
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")

        if monitor is not None and monitor < self.layout.count:
            # Screenshot de monitor especifico
            b = self.layout.monitors[monitor]["bounds"]
            region = (b["left"], b["top"],
                      b["right"] - b["left"], b["bottom"] - b["top"])
            path = TEMP_DIR / f"vision_mon{monitor}_{ts}.png"
        else:
            path = TEMP_DIR / f"vision_{ts}.png"

        if region:
            img = self._gui.screenshot(region=region)
        else:
            img = self._gui.screenshot()

        img.save(str(path))
        self._log_action("screenshot", {"path": str(path),
                                         "monitor": monitor})
        return str(path)

    def get_screen_info(self) -> dict:
        """Retorna informacoes completas da tela incluindo layout dual-monitor."""
        w, h = self._gui.size()
        mx, my = self._gui.position()
        current_monitor = self.layout.monitor_for_point(mx, my)
        return {
            "virtual_width": w,
            "virtual_height": h,
            "mouse_x": mx,
            "mouse_y": my,
            "mouse_on_monitor": current_monitor,
            "monitors": self.layout.to_dict(),
        }

    # ================================================================
    # PRIMITIVAS DE MOUSE
    # ================================================================

    def move_to(self, x: int, y: int, duration: float = 0.3,
                monitor: Optional[int] = None) -> dict:
        """
        Move mouse para coordenada com movimento suave.
        Se monitor for especificado, x/y sao relativos ao monitor.
        """
        if monitor is not None and monitor < self.layout.count:
            b = self.layout.monitors[monitor]["bounds"]
            x = b["left"] + x
            y = b["top"] + y

        vs = self.layout.virtual_screen
        max_x = vs["x"] + vs["width"]
        max_y = vs["y"] + vs["height"]
        if not (vs["x"] <= x <= max_x and vs["y"] <= y <= max_y):
            return {"success": False,
                    "error": f"Coordinates ({x},{y}) out of virtual screen"}

        self._gui.moveTo(x, y, duration=duration)
        self._log_action("move_to", {"x": x, "y": y, "monitor": monitor})
        return {"success": True, "x": x, "y": y}

    def click(self, x: int, y: int, button: str = "left") -> dict:
        """Click em coordenada."""
        self._gui.click(x, y, button=button)
        logger.info(f"Clicked ({x}, {y}) button={button}")
        return {"success": True, "x": x, "y": y, "button": button}

    def double_click(self, x: int, y: int) -> dict:
        """Double-click em coordenada."""
        self._gui.doubleClick(x, y)
        logger.info(f"Double-clicked ({x}, {y})")
        return {"success": True, "x": x, "y": y}

    # ================================================================
    # PRIMITIVAS DE TECLADO
    # ================================================================

    def type_text(self, text: str, interval: float = 0.03) -> dict:
        """
        Digita texto caractere a caractere com intervalo humanizado.
        Para caracteres especiais/unicode, usa pyperclip + ctrl+v.
        """
        # pyautogui.write() nao suporta unicode. Usar clipboard.
        try:
            import pyperclip
            pyperclip.copy(text)
            self._gui.hotkey("ctrl", "v")
            time.sleep(0.1)
            logger.info(f"Typed {len(text)} chars via clipboard")
            return {"success": True, "chars": len(text), "method": "clipboard"}
        except ImportError:
            # Fallback: typewrite para ASCII, hotkey para o resto
            ascii_safe = text.encode("ascii", errors="ignore").decode()
            if ascii_safe == text:
                self._gui.typewrite(text, interval=interval)
                logger.info(f"Typed {len(text)} chars via typewrite")
                return {"success": True, "chars": len(text), "method": "typewrite"}
            else:
                # Ultimo recurso: write via powershell clipboard
                subprocess.run(
                    ["powershell", "-Command", f"Set-Clipboard -Value '{text}'"],
                    capture_output=True, timeout=5
                )
                self._gui.hotkey("ctrl", "v")
                time.sleep(0.1)
                logger.info(f"Typed {len(text)} chars via powershell clipboard")
                return {"success": True, "chars": len(text), "method": "powershell_clipboard"}

    def press_key(self, key: str) -> dict:
        """Pressiona uma tecla (enter, tab, escape, f1, etc)."""
        self._gui.press(key)
        logger.info(f"Pressed key: {key}")
        return {"success": True, "key": key}

    def hotkey(self, *keys: str) -> dict:
        """Pressiona combinacao de teclas (ex: ctrl, shift, p)."""
        self._gui.hotkey(*keys)
        logger.info(f"Hotkey: {'+'.join(keys)}")
        return {"success": True, "keys": list(keys)}

    # ================================================================
    # ACOES COMPOSTAS
    # ================================================================

    def open_app_via_start(self, app_name: str) -> dict:
        """Abre aplicativo via Windows Start Menu."""
        self._gui.press("win")
        time.sleep(0.5)
        self.type_text(app_name)
        time.sleep(0.8)
        self._gui.press("enter")
        time.sleep(1.0)
        logger.info(f"Opened app via Start: {app_name}")
        return {"success": True, "app": app_name}

    def open_file_in_cursor(self, filepath: str) -> dict:
        """Abre arquivo no Cursor IDE via terminal."""
        try:
            result = subprocess.run(
                ["cursor", filepath],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode != 0:
                # Fallback: code command (VS Code compatible)
                subprocess.run(
                    ["code", filepath],
                    capture_output=True, text=True, timeout=5
                )
            logger.info(f"Opened in Cursor: {filepath}")
            return {"success": True, "file": filepath}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def focus_window(self, title_substring: str) -> dict:
        """Foca janela pelo titulo (parcial)."""
        try:
            import ctypes
            from ctypes import wintypes

            user32 = ctypes.windll.user32
            EnumWindows = user32.EnumWindows
            GetWindowTextW = user32.GetWindowTextW
            SetForegroundWindow = user32.SetForegroundWindow
            ShowWindow = user32.ShowWindow
            IsWindowVisible = user32.IsWindowVisible

            target_hwnd = None
            title_lower = title_substring.lower()

            @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.POINTER(ctypes.c_int), ctypes.POINTER(ctypes.c_int))
            def enum_callback(hwnd, lParam):
                nonlocal target_hwnd
                if IsWindowVisible(hwnd):
                    buf = ctypes.create_unicode_buffer(256)
                    GetWindowTextW(hwnd, buf, 256)
                    if title_lower in buf.value.lower():
                        target_hwnd = hwnd
                        return False  # Stop enumeration
                return True

            EnumWindows(enum_callback, 0)

            if target_hwnd:
                ShowWindow(target_hwnd, 9)  # SW_RESTORE
                SetForegroundWindow(target_hwnd)
                time.sleep(0.3)
                logger.info(f"Focused window: {title_substring}")
                return {"success": True, "window": title_substring}
            else:
                return {"success": False, "error": f"Window '{title_substring}' not found"}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def run_ahk_script(self, script_name: str) -> dict:
        """Executa script AHK do automation_hub/hardware/."""
        script_path = AHK_DIR / script_name
        if not script_path.exists():
            return {"success": False, "error": f"Script not found: {script_path}"}

        for exe in ["AutoHotkey.exe", "AutoHotkey64.exe"]:
            try:
                result = subprocess.run(
                    [exe, str(script_path)],
                    capture_output=True, text=True, timeout=10,
                    cwd=str(AHK_DIR)
                )
                return {"success": result.returncode == 0, "script": script_name}
            except FileNotFoundError:
                continue

        # Fallback: absolute paths
        for path in [
            r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe"
        ]:
            if os.path.exists(path):
                result = subprocess.run(
                    [path, str(script_path)],
                    capture_output=True, text=True, timeout=10,
                    cwd=str(AHK_DIR)
                )
                return {"success": result.returncode == 0, "script": script_name}

        return {"success": False, "error": "AutoHotkey not found"}

    # ================================================================
    # SEQUENCIAS DE ACOES
    # ================================================================

    def execute_sequence(self, actions: list[dict]) -> list[dict]:
        """
        Executa sequencia de acoes.
        Cada acao: {"action": "click|type|move|key|hotkey|wait|screenshot|
                     focus|open_app|move_window|snap|clipboard|grab", ...params}
        """
        results = []
        for action in actions:
            act = action.get("action", "")
            try:
                if act == "click":
                    r = self.click(action["x"], action["y"],
                                   action.get("button", "left"))
                elif act == "type":
                    r = self.type_text(action["text"],
                                       action.get("interval", 0.03))
                elif act == "move":
                    r = self.move_to(action["x"], action["y"],
                                     action.get("duration", 0.3),
                                     action.get("monitor"))
                elif act == "key":
                    r = self.press_key(action["key"])
                elif act == "hotkey":
                    r = self.hotkey(*action["keys"])
                elif act == "wait":
                    time.sleep(action.get("seconds", 1))
                    r = {"success": True, "waited": action.get("seconds", 1)}
                elif act == "screenshot":
                    path = self.screenshot(action.get("region"),
                                           action.get("monitor"))
                    r = {"success": True, "path": path}
                elif act == "focus":
                    r = self.focus_window(action["title"])
                elif act == "open_app":
                    r = self.open_app_via_start(action["name"])
                elif act == "move_window":
                    r = self.move_window_to_monitor(
                        action["title"], action["monitor"])
                elif act == "snap":
                    r = self.snap_window(action["title"],
                                         action.get("position", "maximize"))
                elif act == "clipboard":
                    r = self.smart_clipboard_transfer(
                        action["from"], action["to"],
                        action.get("select_all", False))
                elif act == "grab":
                    r = self.grab_and_analyze(action["from"], action["to"])
                else:
                    r = {"success": False, "error": f"Unknown action: {act}"}
            except Exception as e:
                r = {"success": False, "error": str(e), "action": act}

            results.append(r)

            if not r.get("success", False) and action.get("abort_on_fail", False):
                break

        return results

    # ================================================================
    # ORCHESTRATOR INTERFACE
    # ================================================================

    def execute(self, command: str) -> dict:
        """Entry point para o orchestrator. Aceita JSON ou texto."""
        try:
            parsed = json.loads(command)
            if isinstance(parsed, list):
                return {"results": self.execute_sequence(parsed)}
            elif isinstance(parsed, dict):
                return {"results": self.execute_sequence([parsed])}
        except (json.JSONDecodeError, TypeError):
            pass

        # Texto simples: interpretar como descricao
        cmd = command.lower().strip()
        if cmd in ("screenshot", "screen", "vision"):
            return {"path": self.screenshot()}
        elif cmd in ("info", "status", "where"):
            return self.get_screen_info()
        elif cmd in ("monitors", "layout", "spatial"):
            return self.get_monitor_layout()
        elif cmd in ("windows", "map"):
            return {"windows": self.get_window_map()}
        elif cmd in ("log", "session_log"):
            return {"log": self.get_session_log()}
        else:
            return {"info": self.get_screen_info(),
                    "hint": "Commands: screenshot, info, monitors, windows, "
                            "log, or pass JSON actions"}


def ask_agent(query: str) -> str:
    """Entry point compativel com o pattern dos domain agents."""
    agent = ComputerUseAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
