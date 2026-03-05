"""
Modo Cartógrafo - Selum não desiste no primeiro erro.

1. Snapshot do DOM + registro no RAG
2. Pergunta ao Constructor (Groq): Shadow DOM? React Fiber? Densidade de iframes?
3. Gera brutos específicos do site (2FA, latency)
4. Relatório de Gaps ao final da rodada
"""

import re
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
BRUTOS_DIR = PROJECT_ROOT / "src" / "extractors" / "brutos"
BRUTOS_DIR.mkdir(parents=True, exist_ok=True)

# Singleton para coletar gaps durante a rodada
_GAPS: list[str] = []


def get_gaps() -> list[str]:
    """Retorna os gaps coletados na rodada atual."""
    return list(_GAPS)


def add_gap(gap: str) -> None:
    """Adiciona um gap ao relatório final."""
    if gap and gap.strip() and gap.strip() not in _GAPS:
        _GAPS.append(gap.strip())


def clear_gaps() -> None:
    """Limpa os gaps (chamar no início de nova rodada)."""
    global _GAPS
    _GAPS = []


def cartographer_on_error(
    driver: Any,
    error: str,
    url: str = "",
    target_site: str = "target_site",
) -> dict[str, Any] | None:
    """
    Modo Cartógrafo: não desiste. Tira snapshot do DOM, registra no RAG,
    pergunta ao Constructor: Shadow DOM? React Fiber? Densidade de iframes?

    Returns:
        Dict com análise (shadow_dom, react_fiber, iframe_density, suggested_gaps)
        ou None se driver inválido ou falha.
    """
    if driver is None:
        return None

    try:
        dom_snippet = driver.execute_script(
            "return document.documentElement.outerHTML;"
        ) or driver.page_source or ""
    except Exception:
        dom_snippet = ""

    if not dom_snippet:
        return None

    # Limita tamanho para análise
    dom_truncated = dom_snippet[:8000] if len(dom_snippet) > 8000 else dom_snippet

    try:
        url = url or (driver.current_url or "")
    except Exception:
        url = ""

    # Registra no RAG (coleção selum_errors)
    try:
        from src.utils.vector_db import add_error_snapshot

        add_error_snapshot(
            content=f"Erro: {error}\nURL: {url}\nDOM (snippet):\n{dom_truncated[:4000]}",
            metadata={
                "error": error[:500],
                "url": url[:200],
                "timestamp": datetime.now().isoformat(),
                "target_site": target_site,
            },
        )
    except Exception:
        pass

    # Pergunta ao Constructor (Groq)
    analysis = _ask_constructor_for_dom_analysis(
        dom_snippet=dom_truncated,
        error=error,
        url=url,
    )

    if analysis:
        # Extrai gaps sugeridos e adiciona à lista
        for gap in analysis.get("suggested_gaps", []):
            add_gap(gap)

        # Gera bruto específico se o Constructor sugerir
        bruto_type = analysis.get("bruto_type")
        if bruto_type and bruto_type != "none":
            generate_bruto_for_site(
                bruto_type=bruto_type,
                dom_snippet=dom_truncated,
                error=error,
                analysis=analysis,
                target_site=target_site,
            )

    return analysis


def _ask_constructor_for_dom_analysis(
    dom_snippet: str,
    error: str,
    url: str,
) -> dict[str, Any] | None:
    """
    Pergunta ao Constructor (Groq):
    - Esta é uma zona de Shadow DOM?
    - É React Fiber?
    - Qual a densidade de iframes aqui?
    """
    try:
        from src.utils.llm_client import chat_completion, DEFAULT_MODELS, _load_groq_keys
        from src.utils.groq_reporter import _sanitize_utf8
    except ImportError:
        return None

    if not _load_groq_keys():
        return None

    prompt = f"""Você é o Constructor. Analise este snapshot de DOM de uma página onde o Selum (Selenium) falhou.

Erro: {_sanitize_utf8(error[:800])}
URL: {url or '(desconhecida)'}

HTML (snippet, primeiros 6000 chars):
```
{_sanitize_utf8(dom_snippet[:6000])}
```

Responda em JSON com estas chaves exatas:
- "shadow_dom": true/false (há Shadow DOM?)
- "react_fiber": true/false (é React/Fiber?)
- "iframe_density": "baixa" | "media" | "alta" (quantos iframes?)
- "suggested_gaps": lista de 1 a 3 strings, cada uma uma "arma" que falta para cruzar a masmorra em <10s. Ex: "Um seletor de bypass para o Iframe de Login", "Uma skill de leitura de Fiber para o Dashboard"
- "bruto_type": "2fa" | "latency" | "iframe" | "none" (qual bruto gerar?)

Responda APENAS o JSON, sem markdown."""

    try:
        model = DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile")
        response = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
        if not response:
            return None

        # Extrai JSON da resposta
        text = response.strip()
        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            import json
            data = json.loads(match.group())
            return {
                "shadow_dom": data.get("shadow_dom", False),
                "react_fiber": data.get("react_fiber", False),
                "iframe_density": data.get("iframe_density", "desconhecida"),
                "suggested_gaps": data.get("suggested_gaps", []),
                "bruto_type": data.get("bruto_type", "none"),
            }
    except Exception:
        pass
    return None


def generate_bruto_for_site(
    bruto_type: str,
    dom_snippet: str,
    error: str,
    analysis: dict[str, Any] | None = None,
    target_site: str = "target_site",
) -> Path | None:
    """
    Gera bruto específico para o site alvo.

    - 2FA → target_site_2fa_structure.md
    - latency → target_site_latency_patterns.md
    - iframe → target_site_iframe_map.md
    """
    if not bruto_type or bruto_type == "none":
        return None

    safe_name = re.sub(r"[^\w\-]", "_", target_site or "target_site")
    filenames = {
        "2fa": f"{safe_name}_2fa_structure.md",
        "latency": f"{safe_name}_latency_patterns.md",
        "iframe": f"{safe_name}_iframe_map.md",
    }
    filename = filenames.get(bruto_type)
    if not filename:
        return None

    path = BRUTOS_DIR / filename

    content_parts = [
        f"# Bruto: {bruto_type.upper()} - {target_site}",
        f"Gerado em: {datetime.now().isoformat()}",
        "",
        "## Erro que motivou este bruto",
        f"```\n{error[:1500]}\n```",
        "",
        "## Análise do Constructor",
        "",
    ]

    if analysis:
        content_parts.append(f"- Shadow DOM: {analysis.get('shadow_dom', '?')}")
        content_parts.append(f"- React Fiber: {analysis.get('react_fiber', '?')}")
        content_parts.append(f"- Densidade iframes: {analysis.get('iframe_density', '?')}")
        content_parts.append("")

    content_parts.extend([
        "## Snippet do DOM (momento do erro)",
        "",
        "```html",
        (dom_snippet[:6000] if dom_snippet else "(vazio)"),
        "```",
    ])

    try:
        path.write_text("\n".join(content_parts), encoding="utf-8")
        return path
    except Exception:
        return None


def generate_gaps_report(gaps: list[str] | None = None) -> str:
    """
    Emite o Relatório de Necessidades (Gaps) ao final da rodada.

    Formato:
    "Comandante, para cruzar esta masmorra em menos de 10 segundos,
    me faltam estas N armas: [lista]"
    """
    g = gaps if gaps is not None else get_gaps()
    if not g:
        return "Comandante, nenhum gap registrado nesta rodada. A masmorra foi cruzada ou não houve erros mapeados."

    lines = [
        "Comandante, para cruzar esta masmorra em menos de 10 segundos, me faltam estas armas:",
        "",
    ]
    for i, gap in enumerate(g, 1):
        lines.append(f"{i}. {gap}")

    return "\n".join(lines)
