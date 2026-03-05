"""
DecisionTree - Deterministic query classification for pipeline optimization.

Maps incoming queries to optimal resolution layer without LLM calls.
Used for cost estimation and routing decisions.
"""

import re
from dataclasses import dataclass


@dataclass
class LayerDecision:
    """Result of classifying a query into a resolution layer."""

    layer: int  # 0=cache/shortcut, 1=triage, 2=domain, 3=full pipeline
    reason: str
    estimated_cost: float  # USD
    requires_llm: bool


# Cost estimates per layer (USD)
_LAYER_COSTS = {
    0: 0.0,   # Cache or graph shortcut - no LLM
    1: 0.0001,  # Single LLM call (8b)
    2: 0.0003,  # Domain agent with context
    3: 0.005,   # Full decomposition + execution
}


class DecisionTree:
    """Maps incoming queries to optimal resolution layer."""

    # Layer 0: exact cache, graph shortcut, FAQ, status queries
    _LAYER_0_PATTERNS = [
        # Status queries - Neo4j direct
        (r"\b(what is the )?status (of )?(UC-|usecase-)[A-Z0-9-]+\b", "Status query - Neo4j direct"),
        (r"\bstatus\s+(of\s+)?(UC-[A-Z]+-\d+)\b", "Status query - Neo4j direct"),
        (r"\b(status|estado)\s+(de|of)\s+(UC-|usecase-)[A-Z0-9-]+\b", "Status query - Neo4j direct"),
        # Agent listing / capabilities - GRAPH_SHORTCUTS
        (r"\b(agents?|agentes?)\s+(list|available|registered|disponiveis|todos)\b", "Agent listing - graph shortcut"),
        (r"\b(list|show|listar|mostrar)\s+(agents?|agentes?)\b", "Agent listing - graph shortcut"),
        (r"\b(what can|capabilities of)\s+(\w+_agent)\b", "Agent capabilities - graph shortcut"),
        (r"\b(roadmap|usecases?|use\s*cases?)\b", "Roadmap - graph shortcut"),
        (r"\b(coverage|cobertura)\s*(de\s*agentes?)?\b", "Coverage - graph shortcut"),
        (r"\b(stats?|estatisticas?|status)\s*(do\s*)?(sistema|system|crm)\b", "System stats - graph shortcut"),
        # FAQ definitions (incl. PT-BR)
        (r"\b(what is|o que e)\s+(a |an |uma? )?(rag|campaign|campanha|segment|segmento|journey|jornada|lead|flow)\b", "FAQ definition - graph shortcut"),
    ]

    # Layer 1: simple single-intent (skip decomposition)
    _LAYER_1_PATTERNS = [
        (r"^(what|how|why|when|where|who|which|explain|describe|list|show|get|tell)\b", "Simple question - single agent"),
        (r"^(o que|como|por que|quando|onde|quem|qual|explique|descreva|liste|mostre|me\s+(diga|fale|conte))\b", "Simple question - single agent"),
        (r"\b(what is|o que e)\s+(a |an |uma? )?(rag|campaign|segment|journey)\??\s*$", "Simple domain definition"),
    ]

    # Layer 2: domain-specific tasks (deterministic routing)
    _LAYER_2_PATTERNS = [
        (r"\b(create|crie|create)\s+(a |uma? )?(segment|segmento)\s+(for |para )?(active|ativos?|users?|usuarios?)\b", "Segment creation - segment agent"),
        (r"\b(create|crie|build)\s+(a |uma? )?(campaign|campanha)\b", "Campaign creation - CRM agent"),
        (r"\b(create|crie)\s+(a |uma? )?(flow|jornada|journey)\b", "Journey creation - CRM agent"),
        (r"\b(segment|segmento|segmenta[cç]ao)\b", "Segment-related - deterministic routing"),
        (r"\b(campaign|campanha)\s+(analytics|metrics|metricas)\b", "Campaign analytics - domain agent"),
        (r"\banalyze\s+(sms|SMS)\s+delivery\b", "SMS analytics - domain agent"),
    ]

    # Layer 3: complex multi-step (full pipeline)
    _LAYER_3_PATTERNS = [
        (r"\b(redesign|refactor|rearchitect)\b", "Complex redesign - full decomposition"),
        (r"\b(first|primeiro)\b.*\b(then|depois)\b", "Multi-step - full decomposition"),
        (r"\b\d+\)\s", "Numbered list - multi-step"),
        (r"\b(analyze|analise)\b.*\b(and|e)\b.*\b(then|depois)\b", "Composite analysis - full pipeline"),
        (r"\b(engine|arquitetura|architecture)\s+(redesign|refactor)\b", "Engine redesign - full pipeline"),
    ]

    def classify(self, query: str) -> LayerDecision:
        """
        Returns which layer should handle this query and why.

        Args:
            query: User query string

        Returns:
            LayerDecision with layer, reason, estimated_cost, requires_llm
        """
        q = query.strip().lower()

        # Layer 0: cache hit, graph shortcut, FAQ, status
        for pattern, reason in self._LAYER_0_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return LayerDecision(
                    layer=0,
                    reason=reason,
                    estimated_cost=_LAYER_COSTS[0],
                    requires_llm=False,
                )

        # Layer 3: complex multi-step (check before Layer 1/2)
        for pattern, reason in self._LAYER_3_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return LayerDecision(
                    layer=3,
                    reason=reason,
                    estimated_cost=_LAYER_COSTS[3],
                    requires_llm=True,
                )

        # Layer 2: domain-specific tasks
        for pattern, reason in self._LAYER_2_PATTERNS:
            if re.search(pattern, q, re.IGNORECASE):
                return LayerDecision(
                    layer=2,
                    reason=reason,
                    estimated_cost=_LAYER_COSTS[2],
                    requires_llm=True,
                )

        # Layer 1: simple single-intent
        for pattern, reason in self._LAYER_1_PATTERNS:
            if re.match(pattern, q, re.IGNORECASE):
                return LayerDecision(
                    layer=1,
                    reason=reason,
                    estimated_cost=_LAYER_COSTS[1],
                    requires_llm=True,
                )

        # Default: Layer 3 (full pipeline)
        return LayerDecision(
            layer=3,
            reason="Unclassified - full pipeline",
            estimated_cost=_LAYER_COSTS[3],
            requires_llm=True,
        )
