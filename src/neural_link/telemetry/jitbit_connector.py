"""
JitbitConnector - Ponte entre Mission Zero e Jitbit Macro Recorder.

Converte logs de movimento Python em comandos Jitbit CLI e gerencia
execução de macros. Suporta o formato Mission Zero com movimentos
Bézier e cliques.

run_macro: Se Jitbit executável presente, usa subprocess; senão Virtual Driver (pyautogui).
"""

import json
import logging
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)

# Caminhos comuns do Jitbit (espelhado de rpg_cortex para evitar dependência)
def _find_jitbit_exe() -> Optional[Path]:
    import os
    paths = [
        Path(r"C:\Program Files\Jitbit\MacroRecorder\MacroRecorder.exe"),
        Path(r"C:\Program Files (x86)\Jitbit\MacroRecorder\MacroRecorder.exe"),
    ]
    env_path = os.environ.get("JITBIT_PATH", "")
    if env_path:
        paths.insert(0, Path(env_path))
    for p in paths:
        if p and p.exists():
            return p
    return None

# Emojis para log visual (Mission Zero style)
EMOJI_INFO = "🛡️"
EMOJI_SUCCESS = "✓"
EMOJI_COMPLETE = "✅"
EMOJI_WARNING = "⚠️"
EMOJI_ERROR = "❌"


def _resolve_jitbit_wrapper():
    """Resolve JitbitWrapper de forma lazy para evitar import circular."""
    try:
        from rpg_cortex.hardware.jitbit_wrapper import JitbitWrapper
        return JitbitWrapper
    except ImportError:
        return None


class JitbitConnector:
    """
    Conector entre logs de movimento do Mission Zero e Jitbit Macro Recorder.
    Converte ações Python em comandos Jitbit CLI e gerencia execução de macros.
    """

    def __init__(
        self,
        jitbit_wrapper: Optional[Any] = None,
        log_file: Optional[Path] = None,
        macros_dir: Optional[Path] = None,
        verbose: bool = False,
    ):
        """
        Inicializa o conector.

        Args:
            jitbit_wrapper: Instância de JitbitWrapper para execução de macros.
                           Se None, tenta instanciar automaticamente (pode falhar se Jitbit não instalado).
            log_file: Caminho do arquivo de log Mission Zero.
            macros_dir: Diretório para salvar macros geradas.
            verbose: Habilitar logs verbosos no console.
        """
        self._jitbit_wrapper = jitbit_wrapper
        self.log_file = Path(log_file) if log_file else Path("logs/mission_zero.log")
        self.macros_dir = Path(macros_dir) if macros_dir else Path("macros")
        self.verbose = verbose

        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        self.macros_dir.mkdir(parents=True, exist_ok=True)

    def run_macro(
        self,
        macro_path: Path,
        timeout: Optional[int] = None,
        on_command_debug: Optional[Callable[[int, str, str, str, float], None]] = None,
    ) -> bool:
        """
        Executa macro: Jitbit subprocess se .mcr/.jmb e exe presente;
        senão Virtual Driver (pyautogui) lê JSON e reproduz.

        Args:
            macro_path: Caminho do arquivo de macro (.json, .mcr, .jmb).
            timeout: Timeout em segundos (para subprocess).
            on_command_debug: Callback(index, command, start_iso, end_iso, duration_ms)
                              para cada comando executado (popula Gantt em tempo real).

        Returns:
            True se execução bem-sucedida.
        """
        macro_path = Path(macro_path)
        if not macro_path.exists():
            self.log(f"Macro não encontrada: {macro_path}", level="ERROR", emoji=EMOJI_ERROR)
            return False

        suffix = macro_path.suffix.lower()
        jitbit_exe = _find_jitbit_exe()

        if suffix in (".mcr", ".jmb") and jitbit_exe:
            return self._run_via_subprocess(macro_path, timeout)
        return self._run_virtual_driver(macro_path, on_command_debug)

    def _run_via_subprocess(self, macro_path: Path, timeout: Optional[int]) -> bool:
        """Executa macro .mcr/.jmb via Jitbit subprocess."""
        timeout_s = timeout or 60
        cmd = [str(_find_jitbit_exe()), str(macro_path.resolve()), "/a", "/c"]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(macro_path.parent),
            )
            start = time.time()
            while proc.poll() is None:
                if time.time() - start > timeout_s:
                    proc.kill()
                    proc.wait()
                    self.log(f"Timeout ao executar macro ({timeout_s}s)", level="ERROR", emoji=EMOJI_ERROR)
                    return False
                time.sleep(0.1)
            ok = proc.returncode == 0
            self.log(f"Macro executada via Jitbit: {macro_path.name} (ok={ok})", emoji=EMOJI_SUCCESS if ok else EMOJI_WARNING)
            return ok
        except Exception as e:
            self.log(f"Erro subprocess Jitbit: {e}", level="ERROR", emoji=EMOJI_ERROR)
            return False

    def _run_virtual_driver(
        self,
        macro_path: Path,
        on_command_debug: Optional[Callable[[int, str, str, str, float], None]] = None,
    ) -> bool:
        """Virtual Driver: lê JSON e reproduz comandos via pyautogui."""
        return self._execute_json_macro(macro_path, None, on_command_debug)

    def _get_jitbit_wrapper(self):
        """Obtém JitbitWrapper (instância ou cria nova)."""
        if self._jitbit_wrapper is not None:
            return self._jitbit_wrapper
        JitbitWrapperClass = _resolve_jitbit_wrapper()
        if JitbitWrapperClass is None:
            raise ImportError(
                "JitbitWrapper não disponível. Instale rpg_cortex ou passe jitbit_wrapper."
            )
        return JitbitWrapperClass()

    def log(
        self,
        message: str,
        level: str = "INFO",
        emoji: str = EMOJI_INFO,
    ) -> None:
        """
        Log com estilo visual Mission Zero.

        Args:
            message: Mensagem de log.
            level: Nível (INFO, WARNING, ERROR, etc.).
            emoji: Prefixo emoji para identificação visual.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        log_entry = f"[{timestamp}] [{level:8}] {emoji} {message}"

        if self.verbose or level in ("WARNING", "ERROR", "CRITICAL"):
            print(log_entry)

        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry + "\n")

    def parse_movement_logs(self, log_entries: list[str]) -> list[dict]:
        """
        Parse entradas de log Mission Zero em dicionários de ação estruturados.

        Suporta formatos:
        - "Posição alvo: (x, y)" / "Moving to (x, y)" -> move
        - "Posição final: (x, y)" -> move (confirmação)
        - "Clicando em (x, y)..." / "Clicking at (x, y)" -> click
        - "Mensagem: \"...\"" / "Digitando mensagem" com texto -> type
        - "Aguardando" com duração implícita -> wait

        Args:
            log_entries: Lista de linhas de log do Mission Zero.

        Returns:
            Lista de ações com keys: type, params, timestamp.
        """
        actions: list[dict] = []
        coords_re = re.compile(r"\((\d+),\s*(\d+)\)")
        msg_re = re.compile(r'Mensagem:\s*"([^"]*)"')
        timestamp_re = re.compile(r"\[(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d{3})\]")

        for line in log_entries:
            line = line.strip()
            if not line:
                continue

            ts_match = timestamp_re.search(line)
            timestamp = ts_match.group(1) if ts_match else datetime.now().isoformat()

            # Move: Posição alvo / Moving to / Posição final
            if "Posição alvo:" in line or "Moving to" in line or "Posição final:" in line:
                m = coords_re.search(line)
                if m:
                    x, y = int(m.group(1)), int(m.group(2))
                    actions.append({
                        "type": "move",
                        "params": {"x": x, "y": y},
                        "timestamp": timestamp,
                    })
                continue

            # Click: Clicando em / Clicking at
            if "Clicando em" in line or "Clicking at" in line:
                m = coords_re.search(line)
                if m:
                    x, y = int(m.group(1)), int(m.group(2))
                    actions.append({
                        "type": "click",
                        "params": {"x": x, "y": y, "button": "left", "clicks": 1},
                        "timestamp": timestamp,
                    })
                continue

            # Type: Mensagem com texto entre aspas
            if "Mensagem:" in line:
                msg_m = msg_re.search(line)
                if msg_m:
                    text = msg_m.group(1)
                    actions.append({
                        "type": "type",
                        "params": {"text": text, "interval": 0.05},
                        "timestamp": timestamp,
                    })
                continue

            # Wait: Aguardando (extrai duração se houver número)
            if "Aguardando" in line or "Wait" in line:
                dur_match = re.search(r"(\d+(?:\.\d+)?)\s*s", line)
                duration = float(dur_match.group(1)) if dur_match else 0.5
                actions.append({
                    "type": "wait",
                    "params": {"duration": duration},
                    "timestamp": timestamp,
                })
                continue

        return actions

    def convert_to_jitbit_commands(
        self,
        actions: list[dict],
        window_handle: Optional[int] = None,
    ) -> list[str]:
        """
        Converte ações estruturadas em comandos Jitbit CLI.

        Mapeamento exato mission_zero -> Jitbit:
        - move (Bézier target) -> MouseMove x y
        - click -> MouseClick x y button clicks
        - type -> KeyboardType "text"
        - press -> KeyboardPress key count
        - wait -> Wait milliseconds

        Args:
            actions: Lista de ações de parse_movement_logs.
            window_handle: Handle de janela opcional para WindowActivate.

        Returns:
            Lista de strings de comando Jitbit.
        """
        commands: list[str] = []

        if window_handle is not None:
            commands.append(f"WindowActivate {window_handle}")

        for action in actions:
            atype = action.get("type", "")
            params = action.get("params", {})

            try:
                if atype == "move":
                    x = int(params.get("x", 0))
                    y = int(params.get("y", 0))
                    commands.append(f"MouseMove {x} {y}")

                elif atype == "click":
                    x = int(params.get("x", 0))
                    y = int(params.get("y", 0))
                    button = str(params.get("button", "left"))
                    clicks = int(params.get("clicks", 1))
                    commands.append(f"MouseClick {x} {y} {button} {clicks}")

                elif atype == "type":
                    text = params.get("text", "")
                    # Escapar aspas no texto para Jitbit
                    escaped = text.replace("\\", "\\\\").replace('"', '\\"')
                    commands.append(f'KeyboardType "{escaped}"')

                elif atype == "press":
                    key = str(params.get("key", ""))
                    presses = int(params.get("presses", 1))
                    commands.append(f"KeyboardPress {key} {presses}")

                elif atype == "wait":
                    duration = float(params.get("duration", 0))
                    ms = int(duration * 1000)
                    commands.append(f"Wait {ms}")

                else:
                    self.log(
                        f"Tipo de ação desconhecido ignorado: {atype}",
                        level="WARNING",
                        emoji=EMOJI_WARNING,
                    )
            except (KeyError, TypeError, ValueError) as e:
                self.log(
                    f"Falha ao converter ação: {action} - {e}",
                    level="WARNING",
                    emoji=EMOJI_WARNING,
                )

        return commands

    def generate_macro_file(
        self,
        commands: list[str],
        output_path: Path,
        metadata: Optional[dict] = None,
    ) -> Path:
        """
        Gera arquivo de macro em formato JSON intermediário.

        Args:
            commands: Lista de comandos Jitbit.
            output_path: Caminho de saída.
            metadata: Metadados opcionais (name, created, phases_included, etc.).

        Returns:
            Path do arquivo gerado.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        meta = metadata or {}
        meta.setdefault("name", f"mission_zero_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}")
        meta.setdefault("created", datetime.now().isoformat())

        payload = {
            "metadata": meta,
            "commands": [
                {"index": i, "command": cmd}
                for i, cmd in enumerate(commands)
            ],
        }

        # Escrita atômica
        tmp = output_path.with_suffix(output_path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)
        tmp.replace(output_path)

        self.log(
            f"Macro gerada: {output_path} ({len(commands)} comandos)",
            emoji=EMOJI_SUCCESS,
        )
        return output_path

    @staticmethod
    def read_macro_coordinates(macro_path: Path) -> list[tuple[int, int]]:
        """
        Lê arquivo de macro JSON e extrai coordenadas de MouseMove e MouseClick.
        Returns: [(x, y), ...] na ordem dos comandos.
        """
        macro_path = Path(macro_path)
        if not macro_path.exists():
            return []
        try:
            with open(macro_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        coords: list[tuple[int, int]] = []
        for item in data.get("commands", []):
            cmd = item.get("command", "")
            parts = cmd.split()
            if not parts:
                continue
            op = parts[0]
            if op in ("MouseMove", "MouseClick") and len(parts) >= 3:
                try:
                    x, y = int(parts[1]), int(parts[2])
                    coords.append((x, y))
                except ValueError:
                    pass
        return coords

    @staticmethod
    def read_macro_mouse_move_coordinates(macro_path: Path) -> list[tuple[int, int]]:
        """Extrai apenas coordenadas de comandos MouseMove."""
        macro_path = Path(macro_path)
        if not macro_path.exists():
            return []
        try:
            with open(macro_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return []
        coords: list[tuple[int, int]] = []
        for item in data.get("commands", []):
            cmd = item.get("command", "")
            if not cmd.startswith("MouseMove "):
                continue
            parts = cmd.split()
            if len(parts) >= 3:
                try:
                    coords.append((int(parts[1]), int(parts[2])))
                except ValueError:
                    pass
        return coords

    def execute_macro_sync(
        self,
        macro_path: Path,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Executa macro de forma síncrona via JitbitWrapper.

        O JitbitWrapper espera arquivos .mcr ou .jmb. Se o arquivo for .json,
        o connector pode precisar de conversão - por ora, aceita apenas .mcr/.jmb
        ou delega para execução via sequência (fallback).

        Args:
            macro_path: Caminho do arquivo de macro.
            timeout: Timeout em segundos.

        Returns:
            True se execução bem-sucedida.
        """
        macro_path = Path(macro_path)
        if not macro_path.exists():
            self.log(f"Macro não encontrada: {macro_path}", level="ERROR", emoji=EMOJI_ERROR)
            return False

        suffix = macro_path.suffix.lower()
        if suffix == ".json":
            return self._run_virtual_driver(macro_path, None)
        if suffix in (".mcr", ".jmb"):
            try:
                wrapper = self._get_jitbit_wrapper()
                ok = wrapper.execute_macro(macro_path, timeout=timeout)
                self.log(
                    f"Macro executada: {macro_path.name} (ok={ok})",
                    emoji=EMOJI_SUCCESS if ok else EMOJI_WARNING,
                )
                return ok
            except Exception as e:
                self.log(f"Erro ao executar macro: {e}", level="ERROR", emoji=EMOJI_ERROR)
                return False

        self.log(f"Formato de macro não suportado: {suffix}", level="ERROR", emoji=EMOJI_ERROR)
        return False

    def _execute_json_macro(
        self,
        macro_path: Path,
        timeout: Optional[int],
        on_command_debug: Optional[Callable[[int, str, str, str, float], None]] = None,
    ) -> bool:
        """Virtual Driver: executa macro JSON via pyautogui."""
        try:
            with open(macro_path, encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            self.log(f"Macro JSON inválida: {e}", level="ERROR", emoji=EMOJI_ERROR)
            return False

        commands = [c["command"] for c in data.get("commands", [])]
        try:
            import pyautogui
        except ImportError:
            self.log("pyautogui não disponível para Virtual Driver", level="ERROR", emoji=EMOJI_ERROR)
            return False

        for i, cmd in enumerate(commands):
            start_iso = datetime.now().isoformat()
            start_ts = time.perf_counter()

            parts = cmd.split()
            if not parts:
                continue
            op = parts[0]
            try:
                if op == "MouseMove" and len(parts) >= 3:
                    x, y = int(parts[1]), int(parts[2])
                    pyautogui.moveTo(x, y)
                elif op == "MouseClick" and len(parts) >= 5:
                    x, y = int(parts[1]), int(parts[2])
                    pyautogui.click(x, y, button=parts[3], clicks=int(parts[4]))
                elif op == "KeyboardType":
                    match = re.search(r'KeyboardType "(.*)"', cmd, re.DOTALL)
                    if match:
                        text = match.group(1).replace('\\"', '"').replace("\\\\", "\\")
                        try:
                            import pyperclip
                            pyperclip.copy(text)
                            pyautogui.hotkey("ctrl", "v")
                        except ImportError:
                            ascii_safe = text.encode("ascii", errors="ignore").decode()
                            if ascii_safe:
                                pyautogui.write(ascii_safe, interval=0.05)
                elif op == "Wait" and len(parts) >= 2:
                    time.sleep(int(parts[1]) / 1000.0)
                elif op == "WindowActivate" and len(parts) >= 2:
                    try:
                        import ctypes
                        hwnd = int(parts[1])
                        ctypes.windll.user32.SetForegroundWindow(hwnd)
                    except Exception:
                        pass
                elif op == "KeyboardPress" and len(parts) >= 2:
                    key = parts[1].lower()
                    presses = int(parts[2]) if len(parts) >= 3 else 1
                    for _ in range(presses):
                        pyautogui.press(key)
                        if presses > 1:
                            time.sleep(0.05)
            except Exception as e:
                import sys
                err_msg = f"Virtual Driver WARNING: falha ao executar '{cmd[:60]}' - {e}"
                self.log(err_msg, level="WARNING", emoji=EMOJI_WARNING)
                print(err_msg, file=sys.stderr)
                raise

            end_ts = time.perf_counter()
            end_iso = datetime.now().isoformat()
            duration_ms = (end_ts - start_ts) * 1000

            if on_command_debug:
                on_command_debug(i, cmd, start_iso, end_iso, duration_ms)

        self.log(f"Virtual Driver: macro executada: {macro_path.name}", emoji=EMOJI_SUCCESS)
        return True
