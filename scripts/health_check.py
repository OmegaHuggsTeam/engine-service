"""
Health Check - Relatorio rapido de validacoes de API.

Executa validacoes (Groq, OpenAI, Telegram, Selenium) e gera
resumo em Markdown pronto para copiar e colar.
"""

import io
import logging
import os
import sys
from contextlib import redirect_stderr, redirect_stdout
from datetime import datetime
from pathlib import Path

# Adiciona projeto ao path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Silencia logs durante checks (modo quiet)
logging.disable(logging.CRITICAL)

# Carrega .env
from dotenv import load_dotenv

load_dotenv(PROJECT_ROOT / ".env")

OK = "[OK]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"


def _run_quiet(func, *args, **kwargs):
    """Executa funcao capturando stdout/stderr (modo quiet)."""
    out = io.StringIO()
    err = io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            return func(*args, **kwargs)
    except Exception as e:
        return None, str(e)[:80]  # Limita tamanho do erro


def check_groq() -> tuple[str, str]:
    """Valida chave Groq (conectividade)."""
    key = os.getenv("GROQ_API_KEY", "").strip()
    if not key:
        return SKIP, "GROQ_API_KEY nao configurada"

    try:
        from src.extractors.validators import validate_api_key, ValidationError

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = validate_api_key(key, "groq")
        models = result.get("models_count", "?")
        return OK, f"Conectividade OK ({models} modelos)"
    except ValidationError as e:
        return FAIL, str(e)[:60]
    except Exception as e:
        return FAIL, str(e)[:60]


def check_openai() -> tuple[str, str]:
    """Valida chave OpenAI (conectividade)."""
    key = os.getenv("OPENAI_API_KEY", "").strip()
    if not key:
        return SKIP, "OPENAI_API_KEY nao configurada"

    try:
        from src.extractors.validators import validate_api_key, ValidationError

        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = validate_api_key(key, "openai")
        models = result.get("models_count", "?")
        return OK, f"Conectividade OK ({models} modelos)"
    except ValidationError as e:
        return FAIL, str(e)[:60]
    except Exception as e:
        return FAIL, str(e)[:60]


def check_telegram() -> tuple[str, str]:
    """Valida token do Telegram Bot (getMe)."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        return SKIP, "TELEGRAM_BOT_TOKEN nao configurada"

    try:
        import urllib.request

        url = f"https://api.telegram.org/bot{token}/getMe"
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode()
        if '"ok":true' in data and '"username"' in data:
            return OK, "Bot valido"
        return FAIL, "Resposta inesperada"
    except Exception as e:
        err = str(e)[:60]
        if "401" in err or "Unauthorized" in err:
            return FAIL, "Token invalido"
        return FAIL, err


def check_selenium() -> tuple[str, str]:
    """Valida imports do Selenium e web_extractor."""
    try:
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            from selenium import webdriver
            from webdriver_manager.chrome import ChromeDriverManager
            from src.extractors.web_extractor import extract_api_key, ExtractionError
        return OK, "Selenium + web_extractor OK"
    except ImportError as e:
        return FAIL, str(e)[:60]
    except Exception as e:
        return FAIL, str(e)[:60]


def check_env_keys() -> tuple[str, str]:
    """Verifica presenca de chaves no .env."""
    keys = [
        ("GROQ_API_KEY", "Groq"),
        ("OPENAI_API_KEY", "OpenAI"),
        ("TELEGRAM_BOT_TOKEN", "Telegram"),
    ]
    found = [name for var, name in keys if os.getenv(var, "").strip()]
    if not found:
        return FAIL, "Nenhuma chave configurada"
    return OK, ", ".join(found)


def run_all_checks() -> list[tuple[str, str, str]]:
    """Executa todas as validacoes e retorna lista (nome, status, motivo)."""
    checks = [
        ("Chaves no .env", check_env_keys),
        ("Groq (conectividade)", check_groq),
        ("OpenAI (conectividade)", check_openai),
        ("Telegram Bot", check_telegram),
        ("Selenium / Web Extractor", check_selenium),
    ]

    results = []
    for name, check_func in checks:
        try:
            status, reason = check_func()
            results.append((name, status, reason))
        except Exception as e:
            results.append((name, FAIL, str(e)[:60]))

    return results


def format_markdown(results: list[tuple[str, str, str]]) -> str:
    """Formata resultados como Markdown (tabela + lista)."""
    lines = [
        "# Health Check - Chunk Generator",
        "",
        f"**Data:** {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "",
        "## Resumo",
        "",
        "| Check | Status | Detalhe |",
        "|-------|--------|---------|",
    ]

    for name, status, reason in results:
        lines.append(f"| {name} | {status} | {reason} |")

    lines.extend([
        "",
        "## Detalhes",
        "",
    ])

    for name, status, reason in results:
        lines.append(f"- **{name}**: {status} - {reason}")

    passed = sum(1 for _, s, _ in results if s == OK)
    total = len(results)
    lines.extend([
        "",
        f"**Total:** {passed}/{total} checks OK",
        "",
    ])

    return "\n".join(lines)


def main():
    """Executa health check e imprime Markdown."""
    results = run_all_checks()
    logging.disable(logging.NOTSET)  # Restaura logging
    md = format_markdown(results)
    print(md)
    # Exit 0 se todos OK ou SKIP; 1 se algum FAIL
    return 0 if not any(s == FAIL for _, s, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
