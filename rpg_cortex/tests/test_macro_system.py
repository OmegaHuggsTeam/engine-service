"""
Teste do sistema de macros (Fase 2 - Memoria Muscular).
Valida Knowledge Base e Macro Executor sem exigir Jitbit instalado.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def test_knowledge_base():
    """Testa carregamento e consultas da Macro Knowledge Base."""
    from knowledge.macro_knowledge_base import MacroKnowledgeBase

    kb = MacroKnowledgeBase()
    kb.load()

    print("Macros carregadas:", list(kb.macros.keys()))
    assert "abrir_spotify" in kb.macros
    assert "foco_cursor" in kb.macros

    # Query por keyword
    spotify = kb.query_by_keyword("spotify")
    assert len(spotify) >= 1
    assert spotify[0].name == "abrir_spotify"

    # Query por estado
    desktop = kb.query_by_screen_state("desktop")
    print("Macros para desktop:", [m.name for m in desktop])

    # get_macro_path
    p = kb.get_macro_path("foco_cursor")
    print("Path foco_cursor:", p)
    assert p is not None
    assert "macros" in str(p)

    # validate_all
    valid = kb.validate_all()
    print("Validacao:", valid)

    print("[OK] Knowledge Base")


def test_macro_executor_without_jitbit():
    """Testa MacroExecutor com KB, sem Jitbit - deve falhar graciosamente."""
    from knowledge.macro_knowledge_base import MacroKnowledgeBase
    from hardware.macro_executor import MacroExecutor

    kb = MacroKnowledgeBase()
    executor = MacroExecutor(jitbit_wrapper=None, knowledge_base=kb)

    # Macro que nao existe na KB
    r = executor.execute_single("macro_inexistente")
    assert not r.success
    assert "nao encontrada" in (r.error_message or "")

    # Macro na KB mas arquivo nao existe
    r = executor.execute_single("foco_cursor")
    assert not r.success
    assert r.error_message  # "Arquivo nao encontrado" ou similar

    print("[OK] Macro Executor (sem Jitbit)")


def test_chain_resolution():
    """Testa resolucao de chain_after."""
    from knowledge.macro_knowledge_base import MacroKnowledgeBase

    kb = MacroKnowledgeBase()
    chain = kb.get_chain("abrir_spotify")
    print("Chain abrir_spotify:", chain)
    assert "abrir_spotify" in chain

    print("[OK] Chain resolution")


if __name__ == "__main__":
    test_knowledge_base()
    test_chain_resolution()
    test_macro_executor_without_jitbit()
    print("\nTodos os testes passaram!")
