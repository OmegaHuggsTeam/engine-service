"""Excecoes do RPG-Cortex - Macro e Jitbit."""

from pathlib import Path


class RPGCortexError(Exception):
    """Base para erros do RPG-Cortex."""

    pass


class MacroError(RPGCortexError):
    """Base para erros de macro."""

    pass


class MacroNotFoundError(MacroError):
    """Macro nao encontrada."""

    def __init__(self, macro_path: Path):
        self.macro_path = macro_path
        super().__init__(f"Macro nao encontrada: {macro_path}")


class MacroCorruptedError(MacroError):
    """Arquivo de macro invalido ou corrompido."""

    pass


class MacroTimeoutError(MacroError):
    """Macro excedeu o tempo limite."""

    def __init__(self, macro_name: str, timeout_seconds: int):
        self.macro_name = macro_name
        self.timeout_seconds = timeout_seconds
        super().__init__(f"Macro '{macro_name}' excedeu timeout de {timeout_seconds}s")


class JitbitNotFoundError(MacroError):
    """Jitbit Macro Recorder nao encontrado."""

    pass


class RecordingError(MacroError):
    """Erro ao iniciar gravacao de macro."""

    pass
