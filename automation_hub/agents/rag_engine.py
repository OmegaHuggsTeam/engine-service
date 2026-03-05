"""
RAG Layer - Busca simples em /knowledge para decidir acoes.
Fase 2: Consulta documentos .txt por comando (ex: Modo Leitura).
"""

import re
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE_DIR = HUB_ROOT / "knowledge"


def search_knowledge(query: str) -> dict:
    """
    Busca em arquivos .txt da pasta knowledge.
    Retorna configuracao encontrada: luz, apps, layout, etc.
    """
    query_lower = query.lower().strip()
    query_words = set(re.findall(r"\w+", query_lower))
    if not query_words:
        return _default_modo_leitura()

    best_match: dict | None = None
    best_score = 0

    if not KNOWLEDGE_DIR.exists():
        return _default_modo_leitura()

    for path in KNOWLEDGE_DIR.glob("**/*.txt"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            text_lower = text.lower()
            words = set(re.findall(r"\w+", text_lower))
            overlap = len(query_words & words)
            if overlap > best_score:
                best_score = overlap
                best_match = _parse_config(text)
        except Exception:
            continue

    if best_match:
        return best_match
    return _default_modo_leitura()


def _parse_config(text: str) -> dict:
    """Extrai luz, apps, layout do texto."""
    cfg = {"luz": "leitura", "evento_ifttt": "modo_leitura", "apps": [], "layout": "focus_layout.ahk", "silenciar_notificacoes": True}

    # luz: X
    m = re.search(r"luz:\s*(\w+)", text, re.I)
    if m:
        cfg["luz"] = m.group(1).strip()

    # evento_ifttt: X
    m = re.search(r"evento_ifttt:\s*(\w+)", text, re.I)
    if m:
        cfg["evento_ifttt"] = m.group(1).strip()

    # apps: lista
    m = re.search(r"apps:\s*\n((?:\s+-\s*[^\n]+\n?)+)", text, re.I)
    if m:
        apps = re.findall(r'-\s*"([^"]+)"', m.group(1))
        if not apps:
            apps = re.findall(r"-\s*([^\n]+)", m.group(1))
        cfg["apps"] = [a.strip() for a in apps if a.strip()]

    # layout: X
    m = re.search(r"layout:\s*(\S+)", text, re.I)
    if m:
        cfg["layout"] = m.group(1).strip()

    return cfg


def _default_modo_leitura() -> dict:
    """Config padrao quando nao encontra no knowledge."""
    return {
        "luz": "leitura",
        "evento_ifttt": "modo_leitura",
        "apps": [],
        "layout": "focus_layout.ahk",
        "silenciar_notificacoes": True,
    }


def get_error_context() -> dict:
    """
    Contexto de erro: se comando falhar ou IFTTT retornar erro.
    Luz vermelho piscante + alert.ahk no monitor principal.
    """
    cfg = {"luz_erro": "vermelho_piscante", "evento_ifttt_erro": "vermelho_piscante", "alert_ahk": "alert.ahk"}
    if not KNOWLEDGE_DIR.exists():
        return cfg
    for path in KNOWLEDGE_DIR.glob("**/*.txt"):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if "erro" in text.lower() or "contexto de erro" in text.lower():
                m = re.search(r"luz_erro:\s*(\S+)", text, re.I)
                if m:
                    cfg["luz_erro"] = m.group(1).strip()
                m = re.search(r"evento_ifttt_erro:\s*(\S+)", text, re.I)
                if m:
                    cfg["evento_ifttt_erro"] = m.group(1).strip()
                m = re.search(r"alert_ahk:\s*(\S+)", text, re.I)
                if m:
                    cfg["alert_ahk"] = m.group(1).strip()
                return cfg
        except Exception:
            continue
    return cfg
