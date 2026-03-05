"""
Macro Executor - Executa macros single ou em cadeia.
Integra Jitbit + Knowledge Base. Suporta .mcr, .jmb e .ahk.
"""

import subprocess
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .emergency import check as check_emergency_stop
from .jitbit_wrapper import JitbitWrapper
from .rpg_controls import _log

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class ExecutionResult:
    """Resultado de uma execucao de macro."""

    success: bool
    action_type: str
    timestamp: datetime
    duration_ms: int
    macro_name: str
    error_message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


@dataclass
class ChainExecutionResult:
    """Resultado de execucao de cadeia."""

    overall_success: bool
    results: List[ExecutionResult]
    failed_at_step: Optional[int] = None


class MacroExecutor:
    """Executa macros com validacao e suporte a cadeias."""

    def __init__(
        self,
        jitbit_wrapper: Optional[JitbitWrapper] = None,
        knowledge_base=None,
    ):
        self.jitbit = jitbit_wrapper
        self.kb = knowledge_base
        self.action_history: List[Dict[str, Any]] = []
        self._failure_count: Dict[str, int] = {}

    def execute_single(
        self,
        macro_name: str,
        validate_state: bool = False,
    ) -> ExecutionResult:
        """
        Executa uma macro por nome.
        validate_state: ignora por enquanto (Vision Loop nao implementado).
        """
        if check_emergency_stop():
            return ExecutionResult(
                success=False,
                action_type="macro",
                timestamp=datetime.now(),
                duration_ms=0,
                macro_name=macro_name,
                error_message="Emergency Stop ativo",
            )

        start = time.time()
        try:
            if self.kb:
                kb = self.kb
                entry = kb.get_macro(macro_name)
                if not entry:
                    return ExecutionResult(
                        success=False,
                        action_type="macro",
                        timestamp=datetime.now(),
                        duration_ms=int((time.time() - start) * 1000),
                        macro_name=macro_name,
                        error_message=f"Macro '{macro_name}' nao encontrada na knowledge base",
                    )
                macro_path = kb.get_macro_path(macro_name)
                timeout = entry.timeout_seconds
            else:
                macro_path = Path(macro_name)
                timeout = 60

            if not macro_path or not macro_path.exists():
                return ExecutionResult(
                    success=False,
                    action_type="macro",
                    timestamp=datetime.now(),
                    duration_ms=int((time.time() - start) * 1000),
                    macro_name=macro_name,
                    error_message=f"Arquivo nao encontrado: {macro_path}",
                )

            # Jitbit (.mcr, .jmb) ou AutoHotkey (.ahk)
            suffix = macro_path.suffix.lower()
            if suffix in (".mcr", ".jmb") and self.jitbit:
                ok = self.jitbit.execute_macro(macro_path, timeout=timeout)
            elif suffix == ".ahk":
                ok = self._run_ahk(macro_path)
            else:
                if self.jitbit:
                    ok = self.jitbit.execute_macro(macro_path, timeout=timeout)
                else:
                    raise RuntimeError("Jitbit nao configurado e macro nao e AHK")

            duration_ms = int((time.time() - start) * 1000)
            result = ExecutionResult(
                success=ok,
                action_type="macro",
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                macro_name=macro_name,
                details={"path": str(macro_path)},
            )
            self.action_history.append(result)
            return result

        except Exception as e:
            duration_ms = int((time.time() - start) * 1000)
            result = ExecutionResult(
                success=False,
                action_type="macro",
                timestamp=datetime.now(),
                duration_ms=duration_ms,
                macro_name=macro_name,
                error_message=str(e),
            )
            self._failure_count[macro_name] = self._failure_count.get(macro_name, 0) + 1
            self.action_history.append(result)
            _log("execute_single", macro=macro_name, error=str(e))
            return result

    def _run_ahk(self, path: Path) -> bool:
        """Executa script AutoHotkey."""
        for exe in ["AutoHotkey.exe", "AutoHotkey64.exe"]:
            try:
                r = subprocess.run([exe, str(path)], capture_output=True, timeout=60)
                return r.returncode == 0
            except FileNotFoundError:
                continue
        for p in [
            r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
        ]:
            if Path(p).exists():
                r = subprocess.run([p, str(path)], capture_output=True, timeout=60)
                return r.returncode == 0
        return False

    def execute_chain(
        self,
        macro_names: List[str],
        stop_on_failure: bool = True,
    ) -> ChainExecutionResult:
        """Executa sequencia de macros."""

        results: List[ExecutionResult] = []
        for i, name in enumerate(macro_names):
            if check_emergency_stop():
                break
            r = self.execute_single(name)
            results.append(r)
            if not r.success and stop_on_failure:
                return ChainExecutionResult(
                    overall_success=False,
                    results=results,
                    failed_at_step=i,
                )
        return ChainExecutionResult(
            overall_success=all(r.success for r in results),
            results=results,
        )

    def execute_chain_by_name(self, macro_name: str) -> ChainExecutionResult:
        """Executa cadeia a partir do nome (resolve chain_after)."""
        if not self.kb:
            return self.execute_chain([macro_name])
        chain = self.kb.get_chain(macro_name)
        return self.execute_chain(chain or [macro_name])

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Retorna historico recente."""
        recent = self.action_history[-limit:]
        return [
            {
                "macro_name": r.macro_name,
                "success": r.success,
                "timestamp": r.timestamp.isoformat(),
                "duration_ms": r.duration_ms,
            }
            for r in recent
        ]
