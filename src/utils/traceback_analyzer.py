"""
TracebackAnalyzer - Extrai o nome da biblioteca a partir de exceções.
Usado pela AgentFactory para instanciar o Especialista correto.
"""

import traceback
from typing import Optional


def get_lib(exception: BaseException) -> str:
    """
    Analisa o traceback da exceção e retorna o nome da lib principal.
    Ex: selenium.webdriver -> "selenium"
        undetected_chromedriver -> "undetected_chromedriver"
    """
    tb = getattr(exception, "__traceback__", None)
    tb_str = "".join(traceback.format_exception(type(exception), exception, tb))
    err_str = str(exception).lower()

    # Mapeamento de padrões no traceback para lib_name
    patterns = [
        ("selenium", "selenium"),
        ("undetected_chromedriver", "undetected_chromedriver"),
        ("webdriver", "selenium"),
        ("chromedriver", "selenium"),
    ]

    for pattern, lib_name in patterns:
        if pattern in tb_str.lower() or pattern in err_str:
            return lib_name

    # Fallback: exceções conhecidas do Selenium
    exc_name = type(exception).__name__
    if "Timeout" in exc_name or "ElementNotInteractable" in exc_name or "NoSuchElement" in exc_name:
        return "selenium"

    return "unknown"
