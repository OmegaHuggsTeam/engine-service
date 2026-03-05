"""
Sistema de retry com backoff exponencial.

Decorator @retry para funções que podem falhar temporariamente.
Configurável por tipo de erro e com logging detalhado.
"""

import functools
import logging
import time
from typing import Callable, Type

logger = logging.getLogger(__name__)


class RetryError(Exception):
    """Erro após esgotar todas as tentativas de retry."""
    pass


def retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    retriable_exceptions: tuple[Type[Exception], ...] = (Exception,),
    non_retriable_exceptions: tuple[Type[Exception], ...] = (),
    on_retry: Callable[[Exception, int, int], None] | None = None,
):
    """
    Decorator para retry automático com backoff exponencial.

    Args:
        max_attempts: Número máximo de tentativas (padrão: 3)
        backoff_factor: Fator de multiplicação do delay (padrão: 2.0)
        retriable_exceptions: Tupla de exceções que devem ser retriadas
        non_retriable_exceptions: Tupla de exceções que NÃO devem ser retriadas
        on_retry: Callback chamado a cada retry (exception, attempt, max_attempts)

    Exemplo:
        @retry(max_attempts=3, backoff_factor=2)
        def fetch_data():
            # Código que pode falhar temporariamente
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except non_retriable_exceptions as e:
                    # Erro não retriável - falha imediatamente
                    logger.error(
                        f"{func.__name__}: Erro não retriável na tentativa {attempt}/{max_attempts}: {e}"
                    )
                    raise
                except retriable_exceptions as e:
                    last_exception = e
                    if attempt == max_attempts:
                        # Última tentativa - falha
                        logger.error(
                            f"{func.__name__}: Falhou após {max_attempts} tentativas: {e}"
                        )
                        raise RetryError(
                            f"Falhou após {max_attempts} tentativas: {e}"
                        ) from e

                    # Calcular delay com backoff exponencial
                    delay = backoff_factor ** (attempt - 1)
                    logger.warning(
                        f"{func.__name__}: Tentativa {attempt}/{max_attempts} falhou: {e}. "
                        f"Retry em {delay:.1f}s..."
                    )

                    # Callback opcional
                    if on_retry:
                        on_retry(e, attempt, max_attempts)

                    time.sleep(delay)

            # Nunca deve chegar aqui, mas por segurança
            raise RetryError(f"Falhou após {max_attempts} tentativas") from last_exception

        return wrapper
    return decorator
