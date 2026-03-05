"""
QueryRouter - Classifica query e define pesos para cada motor de busca.

Pesos default: chroma=0.4, neo4j=0.3, tfidf=0.3
O router ajusta baseado em sinais da query.
"""

import re
import logging

logger = logging.getLogger(__name__)

# Pesos default
DEFAULT_WEIGHTS = {
    "chroma": 0.4,
    "neo4j": 0.3,
    "tfidf": 0.3,
}

# Sinais que indicam busca relacional (boost neo4j)
RELATIONAL_SIGNALS = [
    r'\bcomo\s+\w+\s+se\s+relaciona\b',
    r'\brelac[iã]o\s+entre\b',
    r'\bconex[aã]o\s+entre\b',
    r'\brelationship\s+between\b',
    r'\bhow\s+\w+\s+relates?\s+to\b',
    r'\bdepend[eê]ncia\b',
    r'\bimpact[oa]\b',
]

# Sinais de erro (boost neo4j para error resolution)
ERROR_SIGNALS = [
    r'\berro\b',
    r'\berror\b',
    r'\bexception\b',
    r'\btraceback\b',
    r'\bfix\b',
    r'\bcorrigir\b',
    r'\bresolver\b',
    r'\bbug\b',
    r'\bfalh[aou]\b',
]

# Sinais de lookup de documentacao (boost tfidf)
DOC_SIGNALS = [
    r'\bcomo\s+configurar\b',
    r'\bhow\s+to\b',
    r'\bstep\s+by\s+step\b',
    r'\bpasso\s+a\s+passo\b',
    r'\bdocument[aç][çã]o\b',
    r'\bdocumentation\b',
    r'\bprocedimento\b',
    r'\bsetup\b',
    r'\binstall\b',
    r'\bconfigurar\b',
]

# Sinais conceituais (boost chroma embeddings)
CONCEPTUAL_SIGNALS = [
    r'\bo\s+que\s+[eé]\b',
    r'\bwhat\s+is\b',
    r'\bexplique?\b',
    r'\bexplain\b',
    r'\bconceito\b',
    r'\bconcept\b',
    r'\bdiferença\s+entre\b',
    r'\bdifference\s+between\b',
]


class QueryRouter:
    """Classifica queries e calcula pesos otimos para cada motor de busca."""

    def __init__(self, default_weights: dict | None = None):
        self._default = default_weights or DEFAULT_WEIGHTS.copy()

    def route(self, query: str) -> dict:
        """
        Analisa a query e retorna pesos otimos para cada motor.

        Returns:
            dict com chroma, neo4j, tfidf (weights somam ~1.0),
            query_type, e signals detectados
        """
        query_lower = query.lower().strip()
        weights = self._default.copy()
        signals = []
        query_type = "general"

        # Detectar sinais relacionais -> boost neo4j
        for pattern in RELATIONAL_SIGNALS:
            if re.search(pattern, query_lower):
                signals.append("relational")
                query_type = "relational"
                break

        # Detectar sinais de erro -> boost neo4j
        for pattern in ERROR_SIGNALS:
            if re.search(pattern, query_lower):
                signals.append("error")
                query_type = "error_resolution"
                break

        # Detectar sinais de documentacao -> boost tfidf
        for pattern in DOC_SIGNALS:
            if re.search(pattern, query_lower):
                signals.append("documentation")
                query_type = "documentation"
                break

        # Detectar sinais conceituais -> boost chroma
        for pattern in CONCEPTUAL_SIGNALS:
            if re.search(pattern, query_lower):
                signals.append("conceptual")
                query_type = "conceptual"
                break

        # Ajustar pesos baseado nos sinais
        if "relational" in signals or "error" in signals:
            weights["neo4j"] = 0.5
            weights["chroma"] = 0.3
            weights["tfidf"] = 0.2
        elif "documentation" in signals:
            weights["tfidf"] = 0.5
            weights["chroma"] = 0.3
            weights["neo4j"] = 0.2
        elif "conceptual" in signals:
            weights["chroma"] = 0.55
            weights["neo4j"] = 0.25
            weights["tfidf"] = 0.2

        # Normalizar pesos para somar 1.0
        total = sum(weights.values())
        if total > 0:
            weights = {k: v / total for k, v in weights.items()}

        return {
            **weights,
            "query_type": query_type,
            "signals": signals,
        }
