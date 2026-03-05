"""
Validação de API Keys.

Valida formato (regex) e conectividade (request de teste) antes de salvar.
"""

import re
from typing import Literal

from src.utils.logger import get_logger
from src.utils.retry import retry

logger = get_logger(__name__)

# Padrões de API keys por plataforma
API_KEY_PATTERNS = {
    "groq": re.compile(r"gsk_[a-zA-Z0-9]{20,}"),
    "openai": re.compile(r"sk-proj-[a-zA-Z0-9_-]+|sk-[a-zA-Z0-9]{48,}"),
    "anthropic": re.compile(r"sk-ant-[a-zA-Z0-9_-]+"),
    "generic": re.compile(r"[a-zA-Z0-9_-]{20,}"),
}

PlatformType = Literal["groq", "openai", "anthropic", "generic"]


class ValidationError(Exception):
    """Erro de validação de API key."""
    pass


def validate_format(key: str, platform: PlatformType = "generic") -> bool:
    """
    Valida formato da API key usando regex.

    Args:
        key: API key a validar
        platform: Plataforma (groq, openai, anthropic, generic)

    Returns:
        True se formato válido

    Raises:
        ValidationError: Se formato inválido
    """
    pattern = API_KEY_PATTERNS.get(platform, API_KEY_PATTERNS["generic"])

    if not pattern.match(key):
        raise ValidationError(
            f"Formato inválido para plataforma '{platform}'. "
            f"Esperado: {pattern.pattern}"
        )

    logger.info(f"Formato válido para plataforma '{platform}'")
    return True


@retry(
    max_attempts=2,
    backoff_factor=2,
    retriable_exceptions=(ConnectionError, TimeoutError),
)
def validate_connectivity_groq(key: str) -> dict:
    """
    Testa conectividade com API Groq.

    Args:
        key: API key Groq

    Returns:
        Dict com informações da validação

    Raises:
        ValidationError: Se chave inválida ou sem permissões
    """
    try:
        from groq import Groq

        client = Groq(api_key=key)

        # Request de teste: listar modelos disponíveis
        models = client.models.list()

        if not models.data:
            raise ValidationError("Chave válida mas sem acesso a modelos")

        logger.info(f"Conectividade Groq OK. Modelos disponíveis: {len(models.data)}")

        return {
            "valid": True,
            "platform": "groq",
            "models_count": len(models.data),
            "models": [m.id for m in models.data[:5]],  # Primeiros 5
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "401" in error_msg or "unauthorized" in error_msg:
            raise ValidationError("Chave inválida ou expirada") from e
        elif "403" in error_msg or "forbidden" in error_msg:
            raise ValidationError("Chave sem permissões necessárias") from e
        elif "429" in error_msg or "rate limit" in error_msg:
            raise ValidationError("Rate limit excedido. Tente novamente mais tarde") from e
        else:
            raise ValidationError(f"Erro ao validar conectividade: {e}") from e


@retry(
    max_attempts=2,
    backoff_factor=2,
    retriable_exceptions=(ConnectionError, TimeoutError),
)
def validate_connectivity_openai(key: str) -> dict:
    """
    Testa conectividade com API OpenAI.

    Args:
        key: API key OpenAI

    Returns:
        Dict com informações da validação

    Raises:
        ValidationError: Se chave inválida ou sem permissões
    """
    try:
        from openai import OpenAI

        client = OpenAI(api_key=key)

        # Request de teste: listar modelos disponíveis
        models = client.models.list()

        if not models.data:
            raise ValidationError("Chave válida mas sem acesso a modelos")

        logger.info(f"Conectividade OpenAI OK. Modelos disponíveis: {len(models.data)}")

        return {
            "valid": True,
            "platform": "openai",
            "models_count": len(models.data),
            "models": [m.id for m in models.data[:5]],  # Primeiros 5
        }

    except Exception as e:
        error_msg = str(e).lower()
        if "401" in error_msg or "unauthorized" in error_msg:
            raise ValidationError("Chave inválida ou expirada") from e
        elif "403" in error_msg or "forbidden" in error_msg:
            raise ValidationError("Chave sem permissões necessárias") from e
        elif "429" in error_msg or "rate limit" in error_msg:
            raise ValidationError("Rate limit excedido. Tente novamente mais tarde") from e
        else:
            raise ValidationError(f"Erro ao validar conectividade: {e}") from e


def validate_api_key(key: str, platform: PlatformType = "groq") -> dict:
    """
    Valida API key: formato + conectividade.

    Args:
        key: API key a validar
        platform: Plataforma (groq, openai, anthropic)

    Returns:
        Dict com resultado da validação

    Raises:
        ValidationError: Se validação falhar
    """
    logger.info(f"Validando API key para plataforma '{platform}'...")

    # Etapa 1: Validar formato
    validate_format(key, platform)

    # Etapa 2: Validar conectividade
    if platform == "groq":
        result = validate_connectivity_groq(key)
    elif platform == "openai":
        result = validate_connectivity_openai(key)
    else:
        # Plataformas sem validação de conectividade
        logger.warning(f"Validação de conectividade não implementada para '{platform}'")
        result = {
            "valid": True,
            "platform": platform,
            "connectivity_tested": False,
        }

    logger.info(f"Validação completa para '{platform}': {result}")
    return result


def main():
    """Ponto de entrada via linha de comando."""
    import argparse

    parser = argparse.ArgumentParser(description="Valida API Key")
    parser.add_argument("--key", required=True, help="API key a validar")
    parser.add_argument(
        "--platform",
        choices=["groq", "openai", "anthropic", "generic"],
        default="groq",
        help="Plataforma da API key",
    )
    args = parser.parse_args()

    try:
        result = validate_api_key(args.key, args.platform)
        print(f"✅ Validação bem-sucedida: {result}")
    except ValidationError as e:
        print(f"❌ Validação falhou: {e}")
        exit(1)


if __name__ == "__main__":
    main()
