"""
Criacao de constraints, indexes e fulltext indexes no Neo4j.
Executar uma vez na inicializacao ou apos reset do DB.
"""

import logging

from .manager import GraphManager
from . import queries

logger = logging.getLogger(__name__)

# Todas as queries de schema em ordem
SCHEMA_QUERIES = [
    # Constraints (uniqueness)
    ("chunk_id constraint", queries.CREATE_CHUNK_CONSTRAINT),
    ("concept_id constraint", queries.CREATE_CONCEPT_CONSTRAINT),
    ("agent_id constraint", queries.CREATE_AGENT_CONSTRAINT),
    ("skill_id constraint", queries.CREATE_SKILL_CONSTRAINT),
    ("task_id constraint", queries.CREATE_TASK_CONSTRAINT),
    ("error_id constraint", queries.CREATE_ERROR_CONSTRAINT),
    ("session_id constraint", queries.CREATE_SESSION_CONSTRAINT),
    # Indexes
    ("chunk_source index", queries.CREATE_CHUNK_SOURCE_INDEX),
    ("concept_name index", queries.CREATE_CONCEPT_NAME_INDEX),
    ("concept_domain index", queries.CREATE_CONCEPT_DOMAIN_INDEX),
    ("agent_type index", queries.CREATE_AGENT_TYPE_INDEX),
    ("task_status index", queries.CREATE_TASK_STATUS_INDEX),
    ("error_type index", queries.CREATE_ERROR_TYPE_INDEX),
    # Fulltext indexes
    ("chunk_content fulltext", queries.CREATE_CHUNK_FULLTEXT),
    ("concept_search fulltext", queries.CREATE_CONCEPT_FULLTEXT),
    # GraphSynergy: Service / N8nNode
    ("service_id constraint", queries.CREATE_SERVICE_CONSTRAINT),
    ("n8n_node_id constraint", queries.CREATE_N8N_NODE_CONSTRAINT),
    ("service_name index", queries.CREATE_SERVICE_NAME_INDEX),
    ("n8n_node_type index", queries.CREATE_N8N_NODE_TYPE_INDEX),
    ("n8n_node_workflow index", queries.CREATE_N8N_NODE_WORKFLOW_INDEX),
    # CRM: Lead / Flow / Interaction
    ("lead_id constraint", queries.CREATE_LEAD_CONSTRAINT),
    ("flow_id constraint", queries.CREATE_FLOW_CONSTRAINT),
    ("interaction_id constraint", queries.CREATE_INTERACTION_CONSTRAINT),
    ("lead_name index", queries.CREATE_LEAD_NAME_INDEX),
    ("lead_email index", queries.CREATE_LEAD_EMAIL_INDEX),
    ("lead_source index", queries.CREATE_LEAD_SOURCE_INDEX),
    ("flow_status index", queries.CREATE_FLOW_STATUS_INDEX),
    ("interaction_timestamp index", queries.CREATE_INTERACTION_TIMESTAMP_INDEX),
    ("lead_search fulltext", queries.CREATE_LEAD_FULLTEXT),
    # CRM Use Cases: Module / UseCase
    ("module_id constraint", queries.CREATE_MODULE_CONSTRAINT),
    ("usecase_id constraint", queries.CREATE_USECASE_CONSTRAINT),
    ("module_repo index", queries.CREATE_MODULE_REPO_INDEX),
    ("module_domain index", queries.CREATE_MODULE_DOMAIN_INDEX),
    ("usecase_domain index", queries.CREATE_USECASE_DOMAIN_INDEX),
    ("usecase_status index", queries.CREATE_USECASE_STATUS_INDEX),
    ("usecase_search fulltext", queries.CREATE_USECASE_FULLTEXT),
    # KPI Metrics Intelligence
    ("model_metric_id constraint", queries.CREATE_MODEL_METRIC_CONSTRAINT),
    ("tool_review_id constraint", queries.CREATE_TOOL_REVIEW_CONSTRAINT),
    ("request_metric_id constraint", queries.CREATE_REQUEST_METRIC_CONSTRAINT),
    ("daily_aggregate_id constraint", queries.CREATE_DAILY_AGGREGATE_CONSTRAINT),
    ("model_metric_date index", queries.CREATE_MODEL_METRIC_DATE_INDEX),
    ("tool_review_tool index", queries.CREATE_TOOL_REVIEW_TOOL_INDEX),
    ("request_metric_session index", queries.CREATE_REQUEST_METRIC_SESSION_INDEX),
    ("daily_aggregate_date index", queries.CREATE_DAILY_AGGREGATE_DATE_INDEX),
    # Audit: AuditResult (UC-AUDIT-001)
    ("audit_result_id constraint", queries.CREATE_AUDIT_RESULT_CONSTRAINT),
    ("audit_result_target index", queries.CREATE_AUDIT_RESULT_TARGET_INDEX),
    ("audit_result_type index", queries.CREATE_AUDIT_RESULT_TYPE_INDEX),
]


def create_schema(graph: GraphManager | None = None) -> dict:
    """
    Cria todo o schema do Neural Link no Neo4j.

    Returns:
        dict com created (list) e errors (list)
    """
    if graph is None:
        graph = GraphManager.from_env()

    created = []
    errors = []

    for name, query in SCHEMA_QUERIES:
        try:
            graph.run_cypher(query)
            created.append(name)
            logger.info(f"[Schema] Created: {name}")
        except Exception as e:
            err_msg = str(e)
            # "equivalent" constraints/indexes already exist - not an error
            if "already exists" in err_msg.lower() or "equivalent" in err_msg.lower():
                created.append(f"{name} (already exists)")
                logger.debug(f"[Schema] Already exists: {name}")
            else:
                errors.append(f"{name}: {err_msg}")
                logger.error(f"[Schema] Error creating {name}: {err_msg}")

    result = {"created": created, "errors": errors}
    logger.info(f"[Schema] Done: {len(created)} created, {len(errors)} errors")
    return result
