"""
Jitbit Wrapper - Interface para Jitbit Macro Recorder CLI.
Executa macros .mcr e .jmb via linha de comando.
MacroRecorder.exe "path\\macro.mcr" /a /c
"""

import os
import subprocess
import time
from pathlib import Path
from typing import Optional

from .exceptions import (
    JitbitNotFoundError,
    MacroCorruptedError,
    MacroNotFoundError,
    MacroTimeoutError,
)
from .rpg_controls import _log

ROOT = Path(__file__).resolve().parent.parent

# Caminhos comuns do Jitbit
JITBIT_PATHS = [
    Path(r"C:\Program Files\Jitbit\MacroRecorder\MacroRecorder.exe"),
    Path(r"C:\Program Files (x86)\Jitbit\MacroRecorder\MacroRecorder.exe"),
    Path(os.environ.get("JITBIT_PATH", "")),
]


class JitbitWrapper:
    """Interface para Jitbit Macro Recorder CLI."""

    def __init__(self, jitbit_exe_path: Optional[Path] = None, timeout_seconds: int = 60):
        self.jitbit_path = jitbit_exe_path or self._find_jitbit()
        self.default_timeout = timeout_seconds
        if not self.jitbit_path or not self.jitbit_path.exists():
            raise JitbitNotFoundError()

    def _find_jitbit(self) -> Optional[Path]:
        """Localiza o executavel do Jitbit."""
        for p in JITBIT_PATHS:
            if p and p.exists():
                return p
        return None

    def validate_macro(self, macro_path: Path) -> bool:
        """Verifica se o arquivo de macro existe e nao esta vazio."""
        p = Path(macro_path)
        if not p.exists():
            return False
        if p.stat().st_size == 0:
            return False
        return p.suffix.lower() in (".mcr", ".jmb")

    def execute_macro(
        self,
        macro_path: Path,
        timeout: Optional[int] = None,
    ) -> bool:
        """
        Executa um arquivo de macro Jitbit.
        MacroRecorder.exe "path" /a /c
        """
        p = Path(macro_path).resolve()
        if not p.exists():
            _log("execute_macro", error="not_found", path=str(p))
            raise MacroNotFoundError(p)
        if not self.validate_macro(p):
            _log("execute_macro", error="invalid", path=str(p))
            raise MacroCorruptedError(f"Arquivo invalido: {p}")

        timeout_s = timeout or self.default_timeout
        cmd = [str(self.jitbit_path), str(p), "/a", "/c"]

        _log("execute_macro", path=str(p), timeout=timeout_s)
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(p.parent),
            )
            start = time.time()
            while proc.poll() is None:
                if time.time() - start > timeout_s:
                    proc.kill()
                    proc.wait()
                    raise MacroTimeoutError(p.name, timeout_s)
                time.sleep(0.1)

            ok = proc.returncode == 0
            _log("execute_macro", path=str(p), returncode=proc.returncode, ok=ok)
            return ok
        except MacroTimeoutError:
            raise
        except Exception as e:
            _log("execute_macro", error=str(e), path=str(p))
            raise MacroCorruptedError(str(e))

    def record_macro(self, output_path: Path) -> None:
        """
        Inicia Jitbit em modo gravacao.
        Abre a interface para o usuario gravar manualmente.
        """
        if not self.jitbit_path or not self.jitbit_path.exists():
            raise JitbitNotFoundError()
        out = Path(output_path).resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        if out.suffix.lower() not in (".mcr", ".jmb"):
            out = out.with_suffix(".mcr")
        subprocess.Popen([str(self.jitbit_path), str(out)], cwd=str(out.parent))
        _log("record_macro", output=str(out))
