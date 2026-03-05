"""
AgentSelector - Seleciona o melhor agente para uma task baseado no grafo.

Criterios:
1. Capabilities match com required_capabilities da task
2. Success rate historico (rolling average)
3. Especializacao em conceitos relevantes
"""

import logging
from typing import Optional

from .models import Task

logger = logging.getLogger(__name__)

# Registry estatico dos agentes (fallback se Neo4j nao disponivel)
AGENT_REGISTRY = {
    "marketing_agent": {
        "name": "Marketing Agent",
        "type": "domain",
        "agent_class": "MarketingDomainAgent",
        "module_path": "src.neural_link.agents.domain_agents",
        "invoke": "execute",
        "capabilities": {"copywriting", "campaign_strategy", "a_b_testing",
                         "audience_targeting", "email_marketing", "content_creation"},
    },
    "social_media_agent": {
        "name": "Social Media Agent",
        "type": "domain",
        "agent_class": "SocialMediaDomainAgent",
        "module_path": "src.neural_link.agents.domain_agents",
        "invoke": "execute",
        "capabilities": {"social_posting", "engagement_analysis", "content_calendar",
                         "hashtag_strategy", "audience_growth", "analytics"},
    },
    "analytics_agent": {
        "name": "Analytics Agent",
        "type": "specialist",
        "module_path": "src.neural_link.agents.crm_domain_agent",
        "capabilities": {"analytics", "data_analysis", "clickhouse", "weekly_kpis",
                          "real_time_analytics", "card_analytics", "acquisition_analytics",
                          "ai_recommendations", "cohort_analysis", "campaign_analytics"},
        "invoke": "execute",
        "agent_class": "AnalyticsAgent",
    },
    "ai_engineer_agent": {
        "name": "AI Engineer Agent",
        "type": "domain",
        "agent_class": "AiEngineerDomainAgent",
        "module_path": "src.neural_link.agents.domain_agents",
        "invoke": "execute",
        "capabilities": {"model_evaluation", "pipeline_design", "data_engineering",
                         "embedding_optimization", "rag_architecture", "fine_tuning",
                         "ai", "machine_learning", "llm", "rag", "embeddings"},
    },
    "groq_operator": {
        "name": "Groq Operator",
        "type": "operator",
        "module_path": "automation_hub.agents.groq_operator",
        "capabilities": {"llm_inference", "function_calling", "automation"},
        "invoke": "process_command",
    },
    "gemini_operator": {
        "name": "Gemini Operator",
        "type": "operator",
        "module_path": "automation_hub.agents.gemini_operator",
        "capabilities": {"llm_inference", "multimodal", "long_context"},
        "invoke": "process_command",
    },
    "claude_operator": {
        "name": "Claude Operator",
        "type": "operator",
        "module_path": "automation_hub.agents.claude_operator",
        "capabilities": {"llm_inference", "reasoning", "code_generation"},
        "invoke": "process_command",
    },
    "divine_inspiration": {
        "name": "Divine Inspiration Engine",
        "type": "specialist",
        "module_path": "src.divine_inspiration.divine_inspiration_engine",
        "capabilities": {"auto_repair", "skill_generation", "error_detection"},
        "knowledge_categories": ["auto_repair", "skill_generation", "error_detection"],
        "invoke": "handle_exception",
    },
    "evolutionary_orchestrator": {
        "name": "Evolutionary Orchestrator",
        "type": "specialist",
        "module_path": "src.utils.evolutionary_orchestrator",
        "capabilities": {"evolution", "self_improvement", "adaptation"},
        "knowledge_categories": ["evolution", "self_improvement", "adaptation"],
        "invoke": "evolve",
    },
    "devops_agent": {
        "name": "DevOps Agent",
        "type": "specialist",
        "module_path": "src.agents.devops_agent",
        "capabilities": {"monitoring", "data_pipeline", "observability", "maintenance", "health_check"},
        "knowledge_categories": ["kubernetes", "docker", "ci_cd", "monitoring"],
        "invoke": "ask_agent",
    },
    "computer_use_agent": {
        "name": "Computer Use Agent",
        "type": "specialist",
        "module_path": "src.agents.computer_use_agent",
        "capabilities": {"computer_use", "ui_automation", "screenshot", "typing", "mouse_control",
                          "dual_monitor", "window_management", "spatial_awareness", "smart_clipboard"},
        "knowledge_categories": ["computer_use", "ui_automation", "window_management"],
        "invoke": "ask_agent",
    },
    # === Ouroboros Expansion: 9 new specialists ===
    "cloud_provisioning_agent": {
        "name": "Cloud Provisioning Agent",
        "type": "specialist",
        "module_path": "src.agents.cloud_provisioning_agent",
        "capabilities": {"cloud", "infrastructure", "provisioning", "terraform", "kubernetes"},
        "knowledge_categories": ["cloud", "infrastructure", "terraform", "kubernetes"],
        "invoke": "ask_agent",
    },
    "security_audit_agent": {
        "name": "Security Audit Agent",
        "type": "specialist",
        "module_path": "src.agents.security_audit_agent",
        "capabilities": {"security", "auditing", "vulnerability", "compliance", "penetration_testing"},
        "knowledge_categories": ["security", "vulnerability", "compliance", "penetration_testing"],
        "invoke": "ask_agent",
    },
    "testing_agent": {
        "name": "Testing Agent",
        "type": "specialist",
        "module_path": "src.agents.testing_agent",
        "capabilities": {"testing", "unit_testing", "integration_testing", "qa", "test_automation"},
        "knowledge_categories": ["testing", "unit_testing", "integration_testing", "qa"],
        "invoke": "ask_agent",
    },
    "documentation_agent": {
        "name": "Documentation Agent",
        "type": "specialist",
        "module_path": "src.agents.documentation_agent",
        "capabilities": {"documentation", "technical_writing", "api_docs", "changelog"},
        "knowledge_categories": ["documentation", "technical_writing", "api_docs"],
        "invoke": "ask_agent",
    },
    "data_engineering_agent": {
        "name": "Data Engineering Agent",
        "type": "specialist",
        "module_path": "src.agents.data_engineering_agent",
        "capabilities": {"data_engineering", "etl", "data_pipeline_advanced", "spark", "airflow"},
        "knowledge_categories": ["data_engineering", "etl", "spark", "airflow"],
        "invoke": "ask_agent",
    },
    "frontend_agent": {
        "name": "Frontend Agent",
        "type": "specialist",
        "module_path": "src.agents.frontend_agent",
        "capabilities": {"frontend", "ui_design", "react", "css", "accessibility"},
        "knowledge_categories": ["frontend", "react", "ui_design", "css", "accessibility"],
        "invoke": "ask_agent",
    },
    "api_gateway_agent": {
        "name": "API Gateway Agent",
        "type": "specialist",
        "module_path": "src.agents.api_gateway_agent",
        "capabilities": {"api_gateway", "rate_limiting", "authentication", "api_versioning"},
        "knowledge_categories": ["api_gateway", "rate_limiting", "authentication", "api_versioning"],
        "invoke": "ask_agent",
    },
    "workflow_agent": {
        "name": "Workflow Agent",
        "type": "specialist",
        "module_path": "src.agents.workflow_agent",
        "capabilities": {"workflow", "task_scheduling", "cron", "event_driven"},
        "knowledge_categories": ["workflow", "task_scheduling", "cron", "event_driven"],
        "invoke": "ask_agent",
    },
    "nlp_agent": {
        "name": "NLP Agent",
        "type": "specialist",
        "module_path": "src.agents.nlp_agent",
        "capabilities": {"nlp", "text_classification", "sentiment_analysis", "entity_extraction"},
        "knowledge_categories": ["nlp", "text_classification", "sentiment_analysis", "entity_extraction"],
        "invoke": "ask_agent",
    },
    "specialist_agent": {
        "name": "Knowledge-Powered Specialist",
        "type": "specialist",
        "module_path": "src.neural_link.agents.specialist_agent",
        "capabilities": {"knowledge", "chunks", "creative_synthesis", "n8n_templates", "automation"},
        "knowledge_categories": ["knowledge", "chunks", "creative_synthesis", "n8n_templates"],
        "invoke": "execute",
    },
    # === CRM Domain Agents ===
    "crm_backend_agent": {
        "name": "CRM Backend Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.crm_domain_agent",
        "capabilities": {"crm_backend", "campaigns", "journeys", "contacts", "ontology",
                          "kafka", "mongodb", "express", "templates", "journey_engine",
                          "campaign_scheduler", "contact_import", "tag_rules", "webhooks"},
        "invoke": "execute",
        "agent_class": "CrmBackendAgent",
    },
    "crm_frontend_agent": {
        "name": "CRM Frontend Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.crm_domain_agent",
        "capabilities": {"crm_frontend", "react", "react_flow", "tailwind", "shadcn",
                          "journey_builder", "segment_dashboard", "campaign_dashboard",
                          "real_time_dashboard", "card_analytics_ui", "cohort_heatmap",
                          "funnel_charts", "ai_recommendations_ui", "d3_visualizations"},
        "invoke": "execute",
        "agent_class": "CrmFrontendAgent",
    },
    "crm_data_agent": {
        "name": "CRM Data Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.crm_domain_agent",
        "capabilities": {"crm_data", "segmentation", "clickhouse", "kafka_workers",
                          "behavioral_analysis", "ingestion", "profiling", "dynamic_fields",
                          "weekly_stats", "ml_scoring", "feature_buckets",
                          "audience_queries", "peerdb_cdc"},
        "invoke": "execute",
        "agent_class": "CrmDataAgent",
    },
    "crm_integration_agent": {
        "name": "CRM Integration Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.crm_domain_agent",
        "capabilities": {"crm_integration", "event_collection", "fingerprinting",
                          "rules_engine", "smart_modals", "minigames", "buyer_agent",
                          "websocket", "form_capture", "tracker_sdk", "sms", "email"},
        "invoke": "execute",
        "agent_class": "CrmIntegrationAgent",
    },
    # === SendSpeed Platform Agents ===
    "sendspeed_sms_agent": {
        "name": "SendSpeed SMS Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.sendspeed_agent",
        "capabilities": {"sms_delivery", "supplier_routing", "campaign_execution",
                          "credit_management", "rabbitmq", "webhook_processing",
                          "status_normalization", "batch_processing", "deduplication",
                          "multi_supplier", "rate_limiting"},
        "invoke": "execute",
        "agent_class": "SendSpeedSmsAgent",
    },
    "sendspeed_admin_agent": {
        "name": "SendSpeed Admin Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.sendspeed_agent",
        "capabilities": {"supplier_management", "campaign_management", "billing",
                          "client_management", "pricing", "lost_list",
                          "blacklist_management", "fraud_detection", "phone_maturation",
                          "alerting", "admin_panel", "approval_workflow", "scheduling"},
        "invoke": "execute",
        "agent_class": "SendSpeedAdminAgent",
    },
    "sendspeed_pipeline_agent": {
        "name": "SendSpeed Pipeline Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.sendspeed_agent",
        "capabilities": {"message_delivery", "rabbitmq_consumer", "circuit_breaker",
                          "dlq", "retry_patterns", "kafka_processing",
                          "redis_caching", "production_sync", "smartico_crm",
                          "status_queue", "batch_buffering"},
        "invoke": "execute",
        "agent_class": "SendSpeedPipelineAgent",
    },
    "sendspeed_api_agent": {
        "name": "SendSpeed API Agent",
        "type": "domain",
        "module_path": "src.neural_link.agents.sendspeed_agent",
        "capabilities": {"rest_api", "multi_tenant", "authentication",
                          "rate_limiting_api", "contact_management", "template_engine",
                          "api_logging", "ip_whitelist", "ddd_architecture",
                          "variable_interpolation"},
        "invoke": "execute",
        "agent_class": "SendSpeedApiAgent",
    },
}


class AgentSelector:
    """Seleciona o melhor agente para uma task."""

    def __init__(self, graph_manager=None):
        self._graph = graph_manager

    def select(self, task: Task) -> Optional[str]:
        """
        Seleciona o melhor agente para a task dada.

        Returns:
            agent_id (str) ou None se nenhum agente adequado
        """
        required = set(task.required_capabilities)

        if not required:
            # Sem capabilities definidas: usa groq_operator como default
            return "groq_operator"

        # Tenta via grafo primeiro
        if self._graph:
            agent_id = self._select_from_graph(required)
            if agent_id:
                return agent_id

        # Fallback: registry estatico
        return self._select_from_registry(required)

    def _select_from_graph(self, required_capabilities: set[str]) -> Optional[str]:
        """Seleciona agente consultando Neo4j."""
        try:
            caps_list = list(required_capabilities)
            results = self._graph.execute_read(
                "MATCH (a:Agent) "
                "WHERE any(cap IN $required_capabilities WHERE cap IN a.capabilities) "
                "RETURN a.id AS id, a.name AS name, a.capabilities AS capabilities, "
                "       a.success_rate AS success_rate "
                "ORDER BY a.success_rate DESC",
                {"required_capabilities": caps_list},
            )

            if not results:
                return None

            # Score: capabilities overlap + success_rate
            best_id = None
            best_score = -1
            for row in results:
                agent_caps = set(row.get("capabilities", []))
                overlap = len(required_capabilities & agent_caps)
                success_rate = float(row.get("success_rate", 0.5))
                score = overlap * 2 + success_rate
                if score > best_score:
                    best_score = score
                    best_id = row["id"]

            return best_id

        except Exception as e:
            logger.warning(f"Graph agent selection failed: {e}")
            return None

    def _select_from_registry(self, required_capabilities: set[str]) -> Optional[str]:
        """Seleciona agente do registry estatico."""
        best_id = None
        best_overlap = 0

        for agent_id, agent_info in AGENT_REGISTRY.items():
            agent_caps = agent_info["capabilities"]
            overlap = len(required_capabilities & agent_caps)
            if overlap > best_overlap:
                best_overlap = overlap
                best_id = agent_id

        # Se nenhum overlap, default para groq_operator (LLM generico)
        return best_id or "groq_operator"

    def get_agent_info(self, agent_id: str) -> Optional[dict]:
        """Retorna info do agente."""
        return AGENT_REGISTRY.get(agent_id)
