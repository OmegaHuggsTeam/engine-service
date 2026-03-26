"""
Layer 0 — Cache Deterministico (Redis + TF-IDF)
Intercepta queries frequentes sem chamar LLM.

Fluxo:
    Pergunta -> cache exato (SHA-256) -> cache semantico (TF-IDF) -> pipeline

Isolamento: toda chave inclui company_id (multi-tenant).
"""

import hashlib
import json
import logging
import os

import redis
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

log = logging.getLogger(__name__)

# TTL padrao por dominio (em segundos)
DEFAULT_TTL = {
    "audience": 1800,      # 30 min (contatos mudam frequentemente)
    "identity": 3600,      # 1 hora
    "capture": 1800,       # 30 min
    "scoring": 21600,      # 6 horas (scores recalculam 1x/dia)
    "journey": 3600,       # 1 hora
    "integrations": 3600,  # 1 hora
    "platform": 7200,      # 2 horas
    "default": 3600,       # 1 hora (fallback)
}

SEMANTIC_THRESHOLD = 0.85


class CacheLayer:
    """Cache Layer 0 do pipeline AI. Redis + TF-IDF."""

    def __init__(self, redis_url: str = None):
        url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.redis = redis.from_url(url, decode_responses=True)
        self.hits = 0
        self.misses = 0
        log.info(f"[CACHE] Conectado ao Redis: {url}")

    # =========================================================================
    # CHAVE DE CACHE
    # =========================================================================

    def _make_key(self, query: str, company_id: str) -> str:
        """Gera chave unica: cache:{company_id}:{sha256(query)}"""
        query_normalized = query.strip().lower()
        query_hash = hashlib.sha256(query_normalized.encode()).hexdigest()
        return f"cache:{company_id}:{query_hash}"

    def _semantic_index_key(self, company_id: str) -> str:
        """Chave do indice semantico por tenant."""
        return f"cache_index:{company_id}"

    # =========================================================================
    # CACHE EXATO (SHA-256)
    # =========================================================================

    def get_exact(self, query: str, company_id: str) -> dict | None:
        """Busca cache exato por hash. Retorna resposta cacheada ou None."""
        key = self._make_key(query, company_id)
        cached = self.redis.get(key)

        if cached:
            self.hits += 1
            log.info(f"[CACHE] HIT exato | company={company_id} | key={key[:30]}...")
            return json.loads(cached)

        return None

    # =========================================================================
    # CACHE SEMANTICO (TF-IDF + Cosine Similarity)
    # =========================================================================

    def get_semantic(self, query: str, company_id: str, threshold: float = None) -> dict | None:
        """
        Busca cache semantico por similaridade TF-IDF.
        Compara a query nova com queries cacheadas do mesmo tenant.
        Se cosine similarity > threshold, retorna a resposta mais similar.
        """
        if threshold is None:
            threshold = SEMANTIC_THRESHOLD

        index_key = self._semantic_index_key(company_id)
        cached_queries = self.redis.hgetall(index_key)

        if not cached_queries:
            return None

        queries_list = list(cached_queries.keys())
        query_normalized = query.strip().lower()

        if query_normalized in queries_list:
            return None

        all_queries = queries_list + [query_normalized]

        vectorizer = TfidfVectorizer()
        tfidf_matrix = vectorizer.fit_transform(all_queries)

        query_vector = tfidf_matrix[-1]
        cached_vectors = tfidf_matrix[:-1]
        similarities = cosine_similarity(query_vector, cached_vectors).flatten()

        best_idx = similarities.argmax()
        best_score = similarities[best_idx]

        if best_score >= threshold:
            best_query = queries_list[best_idx]
            cache_key = cached_queries[best_query]
            cached = self.redis.get(cache_key)

            if cached:
                self.hits += 1
                log.info(f"[CACHE] HIT semantico | score={best_score:.3f} | company={company_id}")
                return json.loads(cached)

        return None

    # =========================================================================
    # GRAVAR NO CACHE
    # =========================================================================

    def set(self, query: str, company_id: str, response: dict, domain: str = "default", ttl: int = None) -> None:
        """Grava pergunta + resposta no cache com TTL por dominio."""
        key = self._make_key(query, company_id)
        query_normalized = query.strip().lower()

        if ttl is None:
            ttl = DEFAULT_TTL.get(domain, DEFAULT_TTL["default"])

        self.redis.setex(key, ttl, json.dumps(response, ensure_ascii=False))

        index_key = self._semantic_index_key(company_id)
        self.redis.hset(index_key, query_normalized, key)

        log.info(f"[CACHE] SET | company={company_id} | domain={domain} | ttl={ttl}s")

    # =========================================================================
    # INVALIDACAO
    # =========================================================================

    def invalidate(self, query: str, company_id: str) -> bool:
        """Remove uma entrada especifica do cache."""
        key = self._make_key(query, company_id)
        query_normalized = query.strip().lower()
        index_key = self._semantic_index_key(company_id)

        self.redis.delete(key)
        self.redis.hdel(index_key, query_normalized)
        log.info(f"[CACHE] INVALIDATE | company={company_id}")
        return True

    def invalidate_tenant(self, company_id: str) -> int:
        """Remove todo o cache de um tenant."""
        pattern = f"cache:{company_id}:*"
        keys = list(self.redis.scan_iter(match=pattern))
        index_key = self._semantic_index_key(company_id)

        count = 0
        if keys:
            count = self.redis.delete(*keys)
        self.redis.delete(index_key)

        log.info(f"[CACHE] INVALIDATE TENANT | company={company_id} | {count} chaves removidas")
        return count

    # =========================================================================
    # METRICAS
    # =========================================================================

    def hit_rate(self) -> dict:
        """Retorna metricas de cache."""
        total = self.hits + self.misses
        rate = (self.hits / total * 100) if total > 0 else 0.0
        return {
            "hits": self.hits,
            "misses": self.misses,
            "total": total,
            "hit_rate_pct": round(rate, 2)
        }

    def record_miss(self):
        """Registra um cache miss."""
        self.misses += 1

    # =========================================================================
    # LOOKUP COMPLETO (exato + semantico)
    # =========================================================================

    def lookup(self, query: str, company_id: str) -> dict | None:
        """
        Busca completa: tenta exato primeiro, depois semantico.
        Se nenhum resolver, retorna None e registra miss.
        """
        result = self.get_exact(query, company_id)
        if result:
            return result

        result = self.get_semantic(query, company_id)
        if result:
            return result

        self.record_miss()
        return None

    def health(self) -> bool:
        """Verifica se o Redis esta acessivel."""
        try:
            return self.redis.ping()
        except Exception:
            return False
