"""
ResultMerger - Normaliza scores, merge e aplica cross-engine boost.

1. Normaliza scores de cada motor para [0, 1]
2. Aplica pesos do router
3. Deduplica por ID do chunk
4. Boost de +15% para itens encontrados por multiplos motores
"""

import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

CROSS_ENGINE_BOOST = 0.15
RELEVANCE_THRESHOLD = 0.25  # Minimum score to include in merged results


class ResultMerger:
    """Merge e rerank de resultados de multiplos motores de busca."""

    def merge(
        self,
        results_by_engine: dict[str, list[dict]],
        weights: dict[str, float],
        top_k: int = 10,
    ) -> list[dict]:
        """
        Merge resultados de multiplos motores com pesos e cross-engine boost.

        Args:
            results_by_engine: {"chroma": [...], "neo4j": [...], "tfidf": [...]}
            weights: {"chroma": 0.4, "neo4j": 0.3, "tfidf": 0.3}
            top_k: Numero maximo de resultados finais

        Returns:
            Lista de dicts ordenada por score final, deduplicada
        """
        # Fase 1: Normalizar scores por engine
        normalized = {}
        for engine, results in results_by_engine.items():
            normalized[engine] = self._normalize_scores(results)

        # Fase 2: Agrupar por content hash para deduplicacao
        content_groups = defaultdict(lambda: {"results": [], "engines": set()})

        for engine, results in normalized.items():
            weight = weights.get(engine, 0.3)
            for result in results:
                key = self._dedup_key(result)
                result["weighted_score"] = result.get("score", 0) * weight
                result["source_engine"] = engine
                content_groups[key]["results"].append(result)
                content_groups[key]["engines"].add(engine)

        # Fase 3: Merge + cross-engine boost
        merged = []
        for key, group in content_groups.items():
            # Pega o resultado com maior score como base
            best = max(group["results"], key=lambda x: x["weighted_score"])
            final_score = sum(r["weighted_score"] for r in group["results"])

            # Cross-engine boost: +15% se encontrado por multiplos motores
            engine_count = len(group["engines"])
            if engine_count > 1:
                final_score *= (1.0 + CROSS_ENGINE_BOOST)

            merged_result = {
                "content": best.get("content", ""),
                "source_file": best.get("source_file", ""),
                "category": best.get("category", ""),
                "score": min(1.0, final_score),
                "engines": list(group["engines"]),
                "engine_count": engine_count,
            }

            # Preservar campos extras do melhor resultado
            for field in ["section", "matched_concept", "error_type", "skill_name"]:
                if field in best:
                    merged_result[field] = best[field]

            merged.append(merged_result)

        # Ordenar por score final
        merged.sort(key=lambda x: x["score"], reverse=True)

        # Filter out low-relevance noise
        merged = [r for r in merged if r["score"] >= RELEVANCE_THRESHOLD]

        return merged[:top_k]

    @staticmethod
    def has_high_confidence(results: list[dict], threshold: float = 0.75) -> bool:
        """Check if any result has high confidence score."""
        return any(r.get("score", 0) >= threshold for r in results)

    @staticmethod
    def _normalize_scores(results: list[dict]) -> list[dict]:
        """Normaliza scores para [0, 1] baseado no max do engine."""
        if not results:
            return []

        max_score = max(r.get("score", 0) for r in results)
        if max_score <= 0:
            return results

        for r in results:
            r["score"] = r.get("score", 0) / max_score

        return results

    @staticmethod
    def _dedup_key(result: dict) -> str:
        """Gera chave de deduplicacao baseada no conteudo."""
        content = result.get("content", "")[:200].strip().lower()
        source = result.get("source_file", "")
        return f"{source}::{content}"
