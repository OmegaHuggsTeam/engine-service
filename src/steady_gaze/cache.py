"""
Sistema de cache para análises Steady Gaze.

Implementa cache com TTL para evitar re-análise de páginas conhecidas.
"""

import hashlib
import time
from typing import Dict, Optional, Tuple

from src.steady_gaze.models import AnalysisReport
from src.utils.logger import get_logger


class AnalysisCache:
    """
    Cache de análises com TTL configurável.

    Evita re-análise de páginas já conhecidas usando hash
    baseado em URL + estrutura DOM.
    """

    def __init__(self, ttl_seconds: int = 3600):
        """
        Inicializa cache com TTL.

        Args:
            ttl_seconds: Tempo de vida do cache em segundos (padrão: 1 hora)
        """
        self._cache: Dict[str, Tuple[AnalysisReport, float]] = {}
        self.ttl = ttl_seconds
        self.logger = get_logger("steady_gaze.cache")

    def get(self, page_hash: str) -> Optional[AnalysisReport]:
        """
        Recupera análise do cache se válida.

        Args:
            page_hash: Hash único da página

        Returns:
            AnalysisReport se cache hit e válido, None caso contrário
        """
        if page_hash not in self._cache:
            self.logger.debug(f"Cache miss: {page_hash[:16]}...")
            return None

        report, timestamp = self._cache[page_hash]
        age = time.time() - timestamp

        if age > self.ttl:
            self.logger.debug(f"Cache expirado (age={age:.1f}s): {page_hash[:16]}...")
            del self._cache[page_hash]
            return None

        self.logger.info(f"Cache hit (age={age:.1f}s): {page_hash[:16]}...")
        return report

    def set(self, page_hash: str, report: AnalysisReport) -> None:
        """
        Armazena análise no cache.

        Args:
            page_hash: Hash único da página
            report: Relatório de análise
        """
        self._cache[page_hash] = (report, time.time())
        self.logger.debug(f"Cache armazenado: {page_hash[:16]}...")

    def clear(self) -> None:
        """Limpa todo o cache."""
        count = len(self._cache)
        self._cache.clear()
        self.logger.info(f"Cache limpo: {count} entradas removidas")

    def cleanup_expired(self) -> int:
        """
        Remove entradas expiradas do cache.

        Returns:
            Número de entradas removidas
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, (_, timestamp) in self._cache.items()
            if current_time - timestamp > self.ttl
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            self.logger.debug(f"Limpeza: {len(expired_keys)} entradas expiradas removidas")

        return len(expired_keys)

    @staticmethod
    def generate_page_hash(url: str, dom_structure: str) -> str:
        """
        Gera hash único da página baseado em URL + estrutura DOM.

        Args:
            url: URL da página
            dom_structure: Estrutura simplificada do DOM (primeiros 1000 chars)

        Returns:
            Hash SHA256 da página
        """
        # Usar apenas primeiros 1000 chars da estrutura DOM para performance
        dom_sample = dom_structure[:1000] if dom_structure else ""
        content = f"{url}:{dom_sample}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def __len__(self) -> int:
        """Retorna número de entradas no cache."""
        return len(self._cache)
