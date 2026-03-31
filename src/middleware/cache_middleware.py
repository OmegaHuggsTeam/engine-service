"""
Cache Middleware — Intercepta requests antes do pipeline AI.

Uso no gateway:
    from src.middleware.cache_middleware import CacheMiddleware

    cache_mw = CacheMiddleware()

    # No endpoint:
    cached = cache_mw.check(query, company_id)
    if cached:
        return cached
    # ... pipeline normal ...
    cache_mw.store(query, company_id, response, domain)
"""

import logging
import os
import time

from src.cache.cache_layer import CacheLayer

log = logging.getLogger(__name__)


class CacheMiddleware:
    """Middleware que checa cache antes de encaminhar pro pipeline."""

    def __init__(self, redis_url: str = None):
        self.cache = CacheLayer(redis_url=redis_url)
        log.info("[CACHE MW] Cache middleware inicializado")

    def check(self, query: str, company_id: str = "default") -> dict | None:
        """
        Verifica se a query esta no cache (exato ou semantico).

        Args:
            query: pergunta do usuario
            company_id: ID do tenant (padrao "default" se nao multi-tenant)

        Returns:
            Resposta cacheada com metadados ou None
        """
        start = time.monotonic()
        result = self.cache.lookup(query, company_id)
        elapsed_ms = (time.monotonic() - start) * 1000

        if result:
            log.info(f"[CACHE MW] HIT | {elapsed_ms:.1f}ms | company={company_id}")
            # Adicionar metadados de cache na resposta
            if isinstance(result, dict):
                result["_cache"] = {
                    "hit": True,
                    "latency_ms": round(elapsed_ms, 2),
                    "source": "cache_layer_0"
                }
            return result

        log.debug(f"[CACHE MW] MISS | {elapsed_ms:.1f}ms | company={company_id}")
        return None

    def store(self, query: str, company_id: str, response: dict, domain: str = "default", ttl: int = None) -> None:
        """
        Grava resposta no cache apos o pipeline processar.

        Args:
            query: pergunta original
            company_id: ID do tenant
            response: resposta do pipeline
            domain: dominio da query (define TTL)
            ttl: TTL custom em segundos (opcional)
        """
        # Nao cachear respostas de erro
        if isinstance(response, dict) and response.get("error"):
            log.debug(f"[CACHE MW] SKIP (erro) | company={company_id}")
            return

        self.cache.set(query, company_id, response, domain=domain, ttl=ttl)

    def health(self) -> dict:
        """Status do cache."""
        redis_ok = self.cache.health()
        metrics = self.cache.hit_rate()
        return {
            "redis_connected": redis_ok,
            **metrics
        }

    def invalidate_query(self, query: str, company_id: str) -> bool:
        """Invalida cache de uma query especifica."""
        return self.cache.invalidate(query, company_id)

    def invalidate_tenant(self, company_id: str) -> int:
        """Invalida todo o cache de um tenant."""
        return self.cache.invalidate_tenant(company_id)
