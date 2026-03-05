"""
Telemetria de Agente na Inicialização do Driver (undetected-chromedriver).

Checkpoints de Observação em cada etapa:
- Salto 1: Criação do subprocesso do Chrome
- Salto 2: Hook da porta de depuração (ChromiumService.start)
- Salto 3: Troca do binário do driver (Patcher.auto)

Se t.join() falhar ou demorar > 10s em qualquer salto, o Paladino é invocado.
"""

from __future__ import annotations

import logging
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable

logger = logging.getLogger("uc_telemetry")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CHECKPOINT_TIMEOUT = 10
_SALTOS = {
    1: "Salto 1: Troca do binário (Patcher.auto)",
    2: "Salto 2: Criação do subprocesso do Chrome",
    3: "Salto 3: Hook da porta de depuração (ChromiumService.start)",
}

_telemetry_enabled = False
_last_checkpoint: list[int] = [0]
_uc_telemetry_logs: list[str] = []


def _log_checkpoint(salto: int, msg: str, extra: str = "") -> None:
    line = f"[CHECKPOINT {salto}] {msg} {extra}".strip()
    logger.info(line)
    _uc_telemetry_logs.append(line)
    if len(_uc_telemetry_logs) > 50:
        _uc_telemetry_logs.pop(0)
    _last_checkpoint[0] = salto


def _run_with_timeout(
    fn: Callable[[], Any],
    salto: int,
    timeout: int = CHECKPOINT_TIMEOUT,
) -> tuple[bool, Any, str | None]:
    """
    Executa fn em thread. Se demorar > timeout, retorna (False, None, erro).
    Retorna (True, resultado, None) em sucesso.
    """
    result: list[Any] = [None]
    exc_holder: list[BaseException | None] = [None]

    def target() -> None:
        try:
            result[0] = fn()
        except BaseException as e:
            exc_holder[0] = e

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout=timeout)

    if t.is_alive():
        return False, None, f"Timeout {timeout}s no {_SALTOS.get(salto, salto)}"
    if exc_holder[0]:
        return False, None, str(exc_holder[0])
    return True, result[0], None


def _invoke_paladino_for_lib(salto: int, error: str, logs: list[str]) -> str | None:
    """
    Invoca o Paladino com contexto da lib.
    RAG: "Por que no Python 3.14 o soquete não está liberando o handle?"
    Retorna proposta de Monkey Patch ou None.
    """
    try:
        from src.utils.groq_reporter import (
            _load_grimoire,
            _sanitize_utf8,
        )
        from src.utils.llm_client import chat_completion, _load_groq_keys, DEFAULT_MODELS
    except ImportError:
        return None

    if not _load_groq_keys():
        return None

    grimoire = _load_grimoire()
    python_ver = f"{sys.version_info.major}.{sys.version_info.minor}"
    logs_text = "\n".join(logs[-30:]) if logs else "(nenhum log)"

    system_content = f"""{grimoire}

---
CONTEXTO DA BIBLIOTECA:
- Checkpoint que falhou: {_SALTOS.get(salto, salto)}
- Erro: {_sanitize_utf8(error[:500])}
- Python: {python_ver}

PERGUNTA RAG: Por que no Python {python_ver} o soquete não está liberando o handle?

PROPOSTA: O Agente NÃO deve apenas sugerir try/except. Deve propor um MONKEY PATCH
(sobrescrever a função da lib em tempo de execução) para usar subprocess.PIPE ou
um método de conexão mais resiliente. Responda com código Python que pode ser
exec(utado) para aplicar o patch em runtime."""

    user_content = f"""Logs:
```
{_sanitize_utf8(logs_text)}
```

Gere o Monkey Patch em Python para aplicar em tempo de execução (ex: subprocess.PIPE, conexão resiliente)."""

    try:
        response = chat_completion(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            model=DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile"),
        )
        if response:
            return _sanitize_utf8(response.strip())
    except Exception:
        pass
    return None


def _apply_monkey_patch_suggestion(code: str) -> bool:
    """
    Tenta aplicar o código sugerido pelo Paladino (exec em contexto seguro).
    """
    if not code or "exec(" in code or "eval(" in code or "__import__" in code:
        return False
    try:
        import re
        match = re.search(r"```(?:python)?\s*\n(.*?)```", code, re.DOTALL | re.IGNORECASE)
        if match:
            code = match.group(1).strip()
        safe_globals: dict[str, Any] = {
            "subprocess": subprocess,
            "sys": sys,
        }
        exec(code, safe_globals)
        return True
    except Exception:
        return False


def _patched_patcher_auto(original_auto: Callable[..., Any], self: Any, *a: Any, **kw: Any) -> Any:
    """Wrapper para Patcher.auto com checkpoint 1."""
    def _call() -> Any:
        return original_auto(self, *a, **kw)

    if not _telemetry_enabled:
        return _call()

    _log_checkpoint(1, "Iniciando Patcher.auto...")

    ok, result, err = _run_with_timeout(_call, 1)
    if ok:
        _log_checkpoint(1, "Patcher.auto concluído.")
        return result

    _log_checkpoint(1, f"FALHA: {err}")
    patch = _invoke_paladino_for_lib(1, err or "Timeout", _uc_telemetry_logs)
    if patch:
        logger.warning("Paladino sugeriu patch para Salto 1. Tentando aplicar...")
        _apply_monkey_patch_suggestion(patch)
    raise RuntimeError(f"Checkpoint 1 falhou: {err}") from None


def _patched_service_start(original_start: Callable[..., None], self: Any, *a: Any, **kw: Any) -> None:
    """Wrapper para Service.start com checkpoint 3."""
    def _call() -> None:
        return original_start(self, *a, **kw)

    if not _telemetry_enabled:
        return _call()

    _log_checkpoint(3, "Iniciando ChromiumService.start (hook porta)...")

    ok, _, err = _run_with_timeout(_call, 3)
    if ok:
        _log_checkpoint(3, "ChromiumService.start concluído.")
        return

    _log_checkpoint(3, f"FALHA: {err}")
    patch = _invoke_paladino_for_lib(3, err or "Timeout", _uc_telemetry_logs)
    if patch:
        logger.warning("Paladino sugeriu patch para Salto 3. Tentando aplicar...")
        _apply_monkey_patch_suggestion(patch)
    raise RuntimeError(f"Checkpoint 3 falhou: {err}") from None


def _patched_popen(*args: Any, **kwargs: Any) -> subprocess.Popen:
    """Wrapper para subprocess.Popen com checkpoint 2."""
    if not _telemetry_enabled:
        return _original_popen(*args, **kwargs)

    cmd = args[0] if args else kwargs.get("args", [])
    cmd_str = str(cmd) if isinstance(cmd, (list, tuple)) else str(cmd)
    is_chrome = "chrome" in cmd_str.lower() and "chromedriver" not in cmd_str.lower()

    if not is_chrome:
        return _original_popen(*args, **kwargs)

    import traceback
    tb = "".join(traceback.format_stack())
    if "undetected_chromedriver" not in tb:
        return _original_popen(*args, **kwargs)

    _log_checkpoint(2, "Criando subprocesso Chrome...")

    result_holder: list[subprocess.Popen] = []
    exc_holder: list[BaseException | None] = [None]

    def run() -> None:
        try:
            result_holder.append(_original_popen(*args, **kwargs))
        except BaseException as e:
            exc_holder[0] = e

    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(timeout=CHECKPOINT_TIMEOUT)

    if t.is_alive():
        err = f"Timeout {CHECKPOINT_TIMEOUT}s no Salto 2 (subprocesso Chrome)"
        _log_checkpoint(2, f"FALHA: {err}")
        patch = _invoke_paladino_for_lib(2, err, _uc_telemetry_logs)
        if patch:
            logger.warning("Paladino sugeriu patch para Salto 2. Tentando aplicar...")
            _apply_monkey_patch_suggestion(patch)
        raise RuntimeError(err) from None
    if exc_holder[0]:
        raise exc_holder[0]
    _log_checkpoint(2, "Subprocesso Chrome criado.")
    return result_holder[0]


_original_popen = subprocess.Popen


def install_telemetry(timeout_seconds: int = 10) -> None:
    """
    Instala os monkey patches para telemetria no undetected-chromedriver.
    Deve ser chamado ANTES de importar undetected_chromedriver.
    """
    global _telemetry_enabled, CHECKPOINT_TIMEOUT
    _telemetry_enabled = True
    CHECKPOINT_TIMEOUT = timeout_seconds

    try:
        import undetected_chromedriver as uc
        from undetected_chromedriver import patcher

        original_auto = patcher.Patcher.auto

        def patched_auto(self, *a, **kw):
            return _patched_patcher_auto(original_auto, self, *a, **kw)

        patcher.Patcher.auto = patched_auto
        _log_checkpoint(0, "Telemetria: Patcher.auto patched")

        import selenium.webdriver.common.service as svc
        original_start = svc.Service.start

        def patched_start(self, *a, **kw):
            return _patched_service_start(original_start, self, *a, **kw)

        svc.Service.start = patched_start
        _log_checkpoint(0, "Telemetria: Service.start patched")

        subprocess.Popen = _patched_popen
        _log_checkpoint(0, "Telemetria: subprocess.Popen patched")

        logger.info("Telemetria de Agente instalada (3 checkpoints, timeout=%ds)", timeout_seconds)
    except Exception as e:
        logger.warning("Telemetria falhou ao instalar: %s", e)
        _telemetry_enabled = False


def get_telemetry_logs() -> list[str]:
    """Retorna os logs de checkpoint para o Paladino."""
    return list(_uc_telemetry_logs)


def get_last_checkpoint() -> int:
    """Retorna o último checkpoint executado."""
    return _last_checkpoint[0]
