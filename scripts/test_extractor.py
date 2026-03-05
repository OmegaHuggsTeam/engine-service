"""
Script de teste para o sistema de extração de API Keys.

Testa componentes individuais sem fazer extração real.
"""

import sys
from pathlib import Path

# Adiciona src ao path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Evita UnicodeEncodeError no Windows (cp1252)
OK = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"


def test_retry_decorator():
    """Testa o decorator de retry."""
    print("\n=== Testando Retry Decorator ===")

    from src.utils.retry import retry, RetryError

    attempt_count = 0

    @retry(max_attempts=3, backoff_factor=1)
    def failing_function():
        nonlocal attempt_count
        attempt_count += 1
        print(f"Tentativa {attempt_count}")
        if attempt_count < 3:
            raise ConnectionError("Falha temporária")
        return "Sucesso!"

    try:
        result = failing_function()
        print(f"{OK} Resultado: {result}")
        print(f"{OK} Tentativas: {attempt_count}")
        assert attempt_count == 3, "Deveria ter tentado 3 vezes"
    except RetryError as e:
        print(f"{FAIL} Falhou apos retries: {e}")
        return False

    return True


def test_logger():
    """Testa o sistema de logging."""
    print("\n=== Testando Logger ===")

    from src.utils.logger import setup_logger

    logger = setup_logger("test_logger", level="DEBUG")

    logger.debug("Mensagem de debug")
    logger.info("Mensagem de info")
    logger.warning("Mensagem de warning")
    logger.error("Mensagem de erro")

    print(f"{OK} Logger configurado e funcionando")
    return True


def test_validators_format():
    """Testa validação de formato de API keys."""
    print("\n=== Testando Validação de Formato ===")

    from src.extractors.validators import validate_format, ValidationError

    # Testes positivos
    test_cases = [
        ("gsk_1234567890123456789012345", "groq", True),
        ("sk-proj-abc123_def456", "openai", True),
        ("sk-1234567890123456789012345678901234567890123456789", "openai", True),
        ("invalid_key", "groq", False),
        ("gsk_short", "groq", False),
    ]

    for key, platform, should_pass in test_cases:
        try:
            validate_format(key, platform)
            if should_pass:
                print(f"{OK} {platform}: {key[:20]}... - Valido")
            else:
                print(f"{FAIL} {platform}: {key[:20]}... - Deveria falhar mas passou")
                return False
        except ValidationError as e:
            if not should_pass:
                print(f"{OK} {platform}: {key[:20]}... - Invalido (esperado)")
            else:
                print(f"{FAIL} {platform}: {key[:20]}... - Deveria passar mas falhou: {e}")
                return False

    return True


def test_supabase_client_init():
    """Testa inicialização do cliente Supabase."""
    print("\n=== Testando Cliente Supabase ===")

    try:
        from src.extractors.supabase_client import SupabaseAPIKeyManager, SupabaseClientError

        # Tenta inicializar (vai falhar se não configurado, mas é esperado)
        try:
            manager = SupabaseAPIKeyManager()
            print(f"{OK} Cliente Supabase inicializado")
            return True
        except SupabaseClientError as e:
            if "Configure SUPABASE_URL" in str(e):
                print(f"{WARN} Supabase nao configurado (esperado se nao tiver .env)")
                return True
            else:
                print(f"{FAIL} Erro inesperado: {e}")
                return False

    except ImportError as e:
        print(f"{WARN} Modulo supabase nao instalado: {e}")
        return True  # Não é erro crítico


def test_groq_key_validation():
    """Testa conectividade real da chave Groq no .env."""
    print("\n=== Testando Validacao de Chave Groq (conectividade) ===")

    import os
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
    key = os.getenv("GROQ_API_KEY", "").strip()

    if not key:
        print(f"{WARN} GROQ_API_KEY nao configurada no .env - pulando teste")
        return True

    try:
        from src.extractors.validators import validate_api_key, ValidationError

        result = validate_api_key(key, "groq")
        print(f"{OK} Chave Groq valida! Modelos: {result.get('models_count', 'N/A')}")
        if result.get("models"):
            print(f"    Exemplos: {result['models'][:3]}")
        return True
    except ValidationError as e:
        print(f"{FAIL} Chave invalida ou expirada: {e}")
        return False
    except Exception as e:
        print(f"{FAIL} Erro ao validar: {e}")
        return False


def test_web_extractor_imports():
    """Testa imports do web_extractor."""
    print("\n=== Testando Imports do Web Extractor ===")

    try:
        from src.extractors.web_extractor import (
            extract_api_key,
            ExtractionError,
            _get_driver,
            _extract_key_from_page,
            _save_api_key,
        )
        print(f"{OK} Todos os imports funcionaram")
        return True
    except ImportError as e:
        print(f"{FAIL} Erro de import: {e}")
        return False


def run_all_tests():
    """Executa todos os testes."""
    print("=" * 60)
    print("TESTES DO SISTEMA DE EXTRAÇÃO DE API KEYS")
    print("=" * 60)

    tests = [
        ("Retry Decorator", test_retry_decorator),
        ("Logger", test_logger),
        ("Validacao de Formato", test_validators_format),
        ("Cliente Supabase", test_supabase_client_init),
        ("Chave Groq (conectividade)", test_groq_key_validation),
        ("Web Extractor Imports", test_web_extractor_imports),
    ]

    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"{FAIL} Erro inesperado em {name}: {e}")
            results.append((name, False))

    # Resumo
    print("\n" + "=" * 60)
    print("RESUMO DOS TESTES")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for name, result in results:
        status = f"{OK} PASSOU" if result else f"{FAIL} FALHOU"
        print(f"{status}: {name}")

    print(f"\nTotal: {passed}/{total} testes passaram")

    if passed == total:
        print("\n>> Todos os testes passaram!")
        return 0
    else:
        print(f"\n>> {total - passed} teste(s) falharam")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
