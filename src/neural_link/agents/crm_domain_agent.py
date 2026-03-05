"""
CRM Domain Agent - Agente especializado para tarefas CRM.

Diferencial: 3-layer context injection para precisao 100%:
1. UseCase specs (acceptance criteria = limite de verdade)
2. Code chunks (codigo real = fundamentacao factual)
3. Graph context (relacionamentos Neo4j = completude)

4 subclasses thin: backend, frontend, data, integration.
"""

import logging
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class CrmDomainAgent(BaseAgent):
    """
    Base class para agentes CRM especializados.

    Ao contrario do SpecialistAgent que carrega chunks por categoria,
    este agente monta um prompt de 3 camadas:
    - Layer 1: UseCase spec com acceptance criteria
    - Layer 2: Code chunks do repositorio real
    - Layer 3: Relacionamentos do grafo Neo4j
    """

    def __init__(
        self,
        domain: str,
        categories: list[str],
        agent_capabilities: set[str],
    ):
        self._domain = domain
        self._categories = categories
        self._capabilities = agent_capabilities
        self._usecase_context: list[dict] = []
        self._code_context: list[dict] = []
        self._graph_context: str = ""

    @property
    def capabilities(self) -> set[str]:
        return self._capabilities

    def execute(self, task: str, **kwargs: Any) -> Any:
        """
        Executa task CRM com 3-layer context injection.

        Args:
            task: Descricao da tarefa.
            **kwargs: Pode conter usecase_id, lead_id, domain override, etc.

        Returns:
            Resposta do LLM fundamentada no contexto.
        """
        # 1. Load UseCase context (Layer 1)
        usecase_text = self._load_usecase_context(task, kwargs.get("usecase_id"))

        # 2. Load Code context (Layer 2)
        code_text = self._load_code_context(task)

        # 3. Load Graph context (Layer 3)
        graph_text = self._load_graph_context(kwargs)

        # 4. Build composite prompt
        prompt = self._build_prompt(task, usecase_text, code_text, graph_text)

        # 5. Invoke LLM
        return self._invoke_llm(prompt, task)

    def _load_usecase_context(self, task: str, usecase_id: str | None = None) -> str:
        """Layer 1: Busca UseCase specs relevantes via HybridRAG."""
        try:
            from src.utils.vector_db import search_with_scores

            # Search for relevant use cases
            query = f"usecase {self._domain} {task[:100]}"
            results = search_with_scores(query, top_k=3)

            # Score threshold: filter low-relevance noise
            results = [r for r in results if r.get("score", 0) >= 0.35]

            # Filter for usecase category
            usecase_results = [
                r for r in results
                if r.get("metadata", {}).get("category") == "usecase"
            ]

            if not usecase_results:
                usecase_results = results[:2]

            if usecase_results:
                self._usecase_context = usecase_results
                parts = []
                for r in usecase_results:
                    content = r.get("content", r.get("document", ""))
                    # Adaptive truncation: higher score = more content
                    score = r.get("score", 0.5)
                    max_chars = max(100, int(500 * score))
                    parts.append(content[:max_chars])
                return "\n---\n".join(parts)

        except Exception as e:
            logger.debug("UseCase context load failed: %s", e)

        return ""

    def _load_code_context(self, task: str) -> str:
        """Layer 2: Busca code chunks relevantes via ChromaDB."""
        try:
            from src.utils.vector_db import search_with_scores

            results = search_with_scores(task, top_k=5)

            # Score threshold: filter low-relevance noise
            results = [r for r in results if r.get("score", 0) >= 0.35]

            # Filter for CRM code categories
            code_results = [
                r for r in results
                if r.get("metadata", {}).get("category", "").startswith("crm_")
            ]

            if not code_results:
                code_results = results[:3]

            if code_results:
                self._code_context = code_results
                parts = []
                for r in code_results:
                    content = r.get("content", r.get("document", ""))
                    source = r.get("metadata", {}).get("source_file", "unknown")
                    # Adaptive truncation: higher score = more content
                    score = r.get("score", 0.5)
                    max_chars = max(100, int(400 * score))
                    parts.append(f"[{source}]\n{content[:max_chars]}")
                return "\n---\n".join(parts)

        except Exception as e:
            logger.debug("Code context load failed: %s", e)

        return ""

    def _load_graph_context(self, kwargs: dict) -> str:
        """Layer 3: Busca relacionamentos do grafo Neo4j."""
        try:
            from src.neural_link.graph.manager import GraphManager
            from src.neural_link.graph import queries

            graph = GraphManager.from_env()
            if not graph.verify_connectivity():
                return "(Graph unavailable)"

            # Get modules for this domain
            results = graph.execute_read(
                queries.GET_MODULES_BY_DOMAIN,
                {"domain": self._domain},
            )

            if results:
                parts = []
                for r in results[:5]:  # Limit to 5 results, 1-hop depth
                    parts.append(f"Module: {r.get('name', '?')} ({r.get('type', '?')}) - {r.get('file_path', '')}")
                self._graph_context = "\n".join(parts)
                return self._graph_context

        except Exception as e:
            logger.debug("Graph context load failed: %s", e)

        return ""

    def _build_prompt(
        self,
        task: str,
        usecase_text: str,
        code_text: str,
        graph_text: str,
    ) -> str:
        """Constroi prompt de 3 camadas para precisao."""
        return (
            f"You are a CRM {self._domain} specialist agent. "
            f"Answer ONLY based on the provided context. "
            f"If the context doesn't contain enough information, say so explicitly.\n\n"
            f"## USE CASE SPECS (acceptance criteria = truth boundary)\n"
            f"{usecase_text}\n\n"
            f"## CODE CONTEXT (implementation reality)\n"
            f"{code_text}\n\n"
            f"## GRAPH CONTEXT (module relationships)\n"
            f"{graph_text}\n\n"
            f"## TASK\n"
            f"{task}"
        )

    def _invoke_llm(self, system_prompt: str, user_task: str) -> str:
        """Invoca LLM com o prompt construido."""
        from src.utils.llm_client import chat_completion

        response = chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_task},
        ])

        return response


# ============================================================
# 4 Thin Subclasses
# ============================================================

class CrmBackendAgent(CrmDomainAgent):
    """Agente CRM Backend: campaigns, journeys, contacts, ontology, templates, tag rules."""

    def __init__(self):
        super().__init__(
            domain="campaigns",
            categories=["crm_backend", "crm_service", "crm_model"],
            agent_capabilities={
                "crm_backend", "campaigns", "journeys", "contacts",
                "ontology", "kafka", "mongodb", "express", "templates",
                "journey_engine", "campaign_scheduler", "contact_import",
                "tag_rules", "webhooks",
            },
        )


class CrmFrontendAgent(CrmDomainAgent):
    """Agente CRM Frontend: React components, Journey Canvas, dashboards, analytics UI."""

    def __init__(self):
        super().__init__(
            domain="tracker",
            categories=["crm_frontend"],
            agent_capabilities={
                "crm_frontend", "react", "react_flow", "tailwind",
                "shadcn", "journey_builder", "segment_dashboard",
                "campaign_dashboard", "real_time_dashboard",
                "card_analytics_ui", "cohort_heatmap", "funnel_charts",
                "ai_recommendations_ui", "d3_visualizations",
            },
        )


class CrmDataAgent(CrmDomainAgent):
    """Agente CRM Data: segmentation, ClickHouse, profiling, dynamic fields, ML scoring, audience queries."""

    def __init__(self):
        super().__init__(
            domain="segments",
            categories=["crm_data_pipeline", "crm_service"],
            agent_capabilities={
                "crm_data", "segmentation", "clickhouse",
                "kafka_workers", "behavioral_analysis", "ingestion",
                "profiling", "dynamic_fields", "weekly_stats",
                "ml_scoring", "feature_buckets", "audience_queries",
                "peerdb_cdc",
            },
        )


class CrmIntegrationAgent(CrmDomainAgent):
    """Agente CRM Integration: event collection, fingerprinting, rules engine, smart modals, minigames, buyer agent."""

    def __init__(self):
        super().__init__(
            domain="integrations",
            categories=["crm_service"],
            agent_capabilities={
                "crm_integration", "event_collection", "fingerprinting",
                "rules_engine", "smart_modals", "minigames", "buyer_agent",
                "websocket", "form_capture", "tracker_sdk", "sms", "email",
            },
        )


class AnalyticsAgent(CrmDomainAgent):
    """Agente Analytics: real-time analytics, card analytics, acquisition, AI recommendations, cohort, campaigns."""

    def __init__(self):
        super().__init__(
            domain="analytics",
            categories=["analytics", "crm_data_pipeline", "crm_frontend"],
            agent_capabilities={
                "analytics", "clickhouse", "weekly_kpis",
                "real_time_analytics", "card_analytics",
                "acquisition_analytics", "ai_recommendations",
                "cohort_analysis", "campaign_analytics",
            },
        )

    def _build_prompt(
        self,
        task: str,
        usecase_text: str,
        code_text: str,
        graph_text: str,
    ) -> str:
        """Constroi prompt especializado para analytics cross-repo."""
        return (
            f"You are an Analytics specialist agent covering 3 repos: "
            f"analytics service (real-time, cards, acquisition, AI recommendations), "
            f"segment-engine (weekly KPIs, cohort, ClickHouse), and "
            f"engage-ai-flow (frontend dashboards). "
            f"Answer ONLY based on the provided context. "
            f"If the context doesn't contain enough information, say so explicitly.\n\n"
            f"## USE CASE SPECS (acceptance criteria = truth boundary)\n"
            f"{usecase_text}\n\n"
            f"## CODE CONTEXT (implementation reality)\n"
            f"{code_text}\n\n"
            f"## GRAPH CONTEXT (module relationships)\n"
            f"{graph_text}\n\n"
            f"## TASK\n"
            f"{task}"
        )
