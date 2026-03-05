"""
SendSpeed Platform Agents - Agentes especializados para plataforma SendSpeed CPaaS.

Segue mesmo pattern do CrmDomainAgent: 3-layer context injection.
4 subclasses: SMS, Admin, Pipeline, API.
"""

import logging
from typing import Any

from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class SendSpeedDomainAgent(BaseAgent):
    """
    Base class para agentes SendSpeed especializados.

    3-layer context injection:
    - Layer 1: UseCase spec com acceptance criteria
    - Layer 2: Code chunks dos repositorios SendSpeed
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
        """Executa task SendSpeed com 3-layer context injection."""
        usecase_text = self._load_usecase_context(task, kwargs.get("usecase_id"))
        code_text = self._load_code_context(task)
        graph_text = self._load_graph_context(kwargs)
        prompt = self._build_prompt(task, usecase_text, code_text, graph_text)
        return self._invoke_llm(prompt, task)

    def _load_usecase_context(self, task: str, usecase_id: str | None = None) -> str:
        """Layer 1: Busca UseCase specs relevantes."""
        try:
            from src.utils.vector_db import search_with_scores

            query = f"usecase {self._domain} sendspeed {task[:100]}"
            results = search_with_scores(query, top_k=3)

            # Score threshold: filter low-relevance noise
            results = [r for r in results if r.get("score", 0) >= 0.35]

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
        """Layer 2: Busca code chunks dos repos SendSpeed."""
        try:
            from src.utils.vector_db import search_with_scores

            results = search_with_scores(task, top_k=5)

            # Score threshold: filter low-relevance noise
            results = [r for r in results if r.get("score", 0) >= 0.35]

            code_results = [
                r for r in results
                if r.get("metadata", {}).get("category", "").startswith("sendspeed_")
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
            f"You are a SendSpeed {self._domain} specialist agent. "
            f"SendSpeed is a CPaaS platform for multi-channel messaging (SMS, VoIP, WhatsApp, RCS, Email) "
            f"with 15+ suppliers, credit-based billing, and high-throughput delivery pipelines. "
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

class SendSpeedSmsAgent(SendSpeedDomainAgent):
    """SMS Agent: multi-supplier delivery, campaign execution, credit management, dedup."""

    def __init__(self):
        super().__init__(
            domain="sms_delivery",
            categories=["sendspeed_sms", "sendspeed_app", "sendspeed_delivery"],
            agent_capabilities={
                "sms_delivery", "supplier_routing", "campaign_execution",
                "credit_management", "rabbitmq", "webhook_processing",
                "status_normalization", "batch_processing", "deduplication",
                "multi_supplier", "rate_limiting",
            },
        )


class SendSpeedAdminAgent(SendSpeedDomainAgent):
    """Admin Agent: backoffice, supplier mgmt, billing, blacklist, fraud detection."""

    def __init__(self):
        super().__init__(
            domain="administration",
            categories=["sendspeed_admin", "sendspeed_blacklist", "sendspeed_app"],
            agent_capabilities={
                "supplier_management", "campaign_management", "billing",
                "client_management", "pricing", "lost_list",
                "blacklist_management", "fraud_detection", "phone_maturation",
                "alerting", "admin_panel", "approval_workflow", "scheduling",
            },
        )


class SendSpeedPipelineAgent(SendSpeedDomainAgent):
    """Pipeline Agent: RabbitMQ consumers, delivery, circuit breaker, Smartico CRM sync."""

    def __init__(self):
        super().__init__(
            domain="sms_delivery",
            categories=["sendspeed_delivery", "sendspeed_pipeline", "sendspeed_webhook"],
            agent_capabilities={
                "message_delivery", "rabbitmq_consumer", "circuit_breaker",
                "dlq", "retry_patterns", "kafka_processing",
                "redis_caching", "production_sync", "smartico_crm",
                "status_queue", "batch_buffering",
            },
        )


class SendSpeedApiAgent(SendSpeedDomainAgent):
    """API Agent: portal-cliente-api, multi-tenant REST, DDD, contacts, templates."""

    def __init__(self):
        super().__init__(
            domain="api_platform",
            categories=["sendspeed_api"],
            agent_capabilities={
                "rest_api", "multi_tenant", "authentication",
                "rate_limiting_api", "contact_management", "template_engine",
                "api_logging", "ip_whitelist", "ddd_architecture",
                "variable_interpolation",
            },
        )
