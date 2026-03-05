"""
Sistema de logging estruturado para o projeto.

Configura logging com níveis, formatação e saída para arquivo + console.
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "api_key_extractor",
    level: str = "INFO",
    log_file: Path | None = None,
    format_json: bool = False,
) -> logging.Logger:
    """
    Configura e retorna um logger estruturado.

    Args:
        name: Nome do logger
        level: Nível de log (DEBUG, INFO, WARNING, ERROR)
        log_file: Caminho para arquivo de log (opcional)
        format_json: Se True, formata logs como JSON

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))

    # Remove handlers existentes para evitar duplicação
    logger.handlers.clear()

    # Formato de log
    if format_json:
        # TODO: Implementar formatação JSON com python-json-logger
        fmt = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    else:
        fmt = "%(asctime)s | %(levelname)-8s | %(name)s:%(funcName)s:%(lineno)d | %(message)s"

    formatter = logging.Formatter(fmt, datefmt="%Y-%m-%d %H:%M:%S")

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Handler para arquivo (se especificado)
    if log_file:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def get_logger(name: str = "api_key_extractor") -> logging.Logger:
    """
    Retorna um logger existente ou cria um novo com configuração padrão.

    Args:
        name: Nome do logger

    Returns:
        Logger configurado
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        # Configuração padrão se logger não foi configurado
        setup_logger(name)
    return logger
