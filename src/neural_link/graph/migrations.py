"""
Migracao de dados existentes para o grafo Neo4j.
- Chunks do ChromaDB -> nodes Chunk com relationships NEXT_CHUNK e SAME_SOURCE
- Agentes de dominio e operadores -> nodes Agent
"""

import logging
from collections import defaultdict
from datetime import datetime

from .manager import GraphManager
from . import queries

logger = logging.getLogger(__name__)


def migrate_chromadb(graph: GraphManager | None = None) -> dict:
    """
    Migra todos os chunks do ChromaDB para nodes no Neo4j.
    Cria relationships NEXT_CHUNK (por chunk_index) e SAME_SOURCE.

    Returns:
        dict com chunks_migrated, relationships_created, errors
    """
    from src.utils.vector_db import get_all

    if graph is None:
        graph = GraphManager.from_env()

    chunks = get_all()
    if not chunks:
        logger.warning("ChromaDB vazio - nada para migrar")
        return {"chunks_migrated": 0, "relationships_created": 0, "errors": []}

    logger.info(f"Migrando {len(chunks)} chunks do ChromaDB para Neo4j...")

    chunks_migrated = 0
    errors = []

    # Agrupar chunks por source_file para criar relationships
    by_source = defaultdict(list)

    for chunk in chunks:
        source_file = str(chunk.get("source_file", "unknown"))
        chunk_index = chunk.get("chunk_index", "0")
        try:
            chunk_index = int(chunk_index)
        except (ValueError, TypeError):
            chunk_index = 0

        chunk_id = f"{source_file}_{chunk_index}"

        params = {
            "id": chunk_id,
            "content": str(chunk.get("content", ""))[:5000],  # Limita tamanho
            "source_file": source_file,
            "chunk_index": chunk_index,
            "category": str(chunk.get("category", "")),
            "agent_specialty": str(chunk.get("agent_specialty", "")),
            "created_at": datetime.now().isoformat(),
        }

        try:
            graph.execute_write(queries.UPSERT_CHUNK, params)
            chunks_migrated += 1
            by_source[source_file].append((chunk_id, chunk_index))
        except Exception as e:
            errors.append(f"Chunk {chunk_id}: {e}")
            logger.error(f"Erro ao migrar chunk {chunk_id}: {e}")

    # Criar relationships NEXT_CHUNK e SAME_SOURCE
    relationships_created = 0
    for source_file, chunk_list in by_source.items():
        # Ordenar por chunk_index
        chunk_list.sort(key=lambda x: x[1])

        for i in range(len(chunk_list)):
            # NEXT_CHUNK: encadeia sequencialmente
            if i < len(chunk_list) - 1:
                try:
                    graph.execute_write(queries.CREATE_CHUNK_NEXT, {
                        "chunk_id_1": chunk_list[i][0],
                        "chunk_id_2": chunk_list[i + 1][0],
                    })
                    relationships_created += 1
                except Exception as e:
                    errors.append(f"NEXT_CHUNK {chunk_list[i][0]} -> {chunk_list[i+1][0]}: {e}")

            # SAME_SOURCE: conecta todos do mesmo source ao primeiro
            if i > 0:
                try:
                    graph.execute_write(queries.CREATE_CHUNK_SAME_SOURCE, {
                        "chunk_id_1": chunk_list[0][0],
                        "chunk_id_2": chunk_list[i][0],
                    })
                    relationships_created += 1
                except Exception as e:
                    errors.append(f"SAME_SOURCE: {e}")

    result = {
        "chunks_migrated": chunks_migrated,
        "relationships_created": relationships_created,
        "errors": errors,
    }
    logger.info(
        f"Migracao concluida: {chunks_migrated} chunks, "
        f"{relationships_created} relationships, {len(errors)} errors"
    )
    return result


def seed_agents(graph: GraphManager | None = None) -> dict:
    """
    Semeia Agent nodes para os agentes de dominio e operadores existentes.

    Returns:
        dict com agents_created (list of names) e errors
    """
    if graph is None:
        graph = GraphManager.from_env()

    agents = [
        {
            "id": "marketing_agent",
            "name": "Marketing Agent",
            "type": "domain",
            "module_path": "src.agents.marketing_agent",
            "capabilities": ["marketing", "copywriting", "branding", "funnel"],
            "status": "active",
        },
        {
            "id": "social_media_agent",
            "name": "Social Media Agent",
            "type": "domain",
            "module_path": "src.agents.social_media_agent",
            "capabilities": ["social_media", "content_creation", "engagement", "scheduling"],
            "status": "active",
        },
        {
            "id": "analytics_agent",
            "name": "Analytics Agent",
            "type": "domain",
            "module_path": "src.agents.analytics_agent",
            "capabilities": ["analytics", "metrics", "reporting", "data_analysis"],
            "status": "active",
        },
        {
            "id": "ai_engineer_agent",
            "name": "AI Engineer Agent",
            "type": "domain",
            "module_path": "src.agents.ai_engineer_agent",
            "capabilities": ["ai", "machine_learning", "llm", "rag", "embeddings"],
            "status": "active",
        },
        {
            "id": "groq_operator",
            "name": "Groq Operator",
            "type": "operator",
            "module_path": "automation_hub.agents.groq_operator",
            "capabilities": ["llm_inference", "function_calling", "automation"],
            "status": "active",
        },
        {
            "id": "gemini_operator",
            "name": "Gemini Operator",
            "type": "operator",
            "module_path": "automation_hub.agents.gemini_operator",
            "capabilities": ["llm_inference", "multimodal", "long_context"],
            "status": "active",
        },
        {
            "id": "claude_operator",
            "name": "Claude Operator",
            "type": "operator",
            "module_path": "automation_hub.agents.claude_operator",
            "capabilities": ["llm_inference", "reasoning", "code_generation"],
            "status": "active",
        },
        {
            "id": "divine_inspiration",
            "name": "Divine Inspiration Engine",
            "type": "specialist",
            "module_path": "src.divine_inspiration.divine_inspiration_engine",
            "capabilities": ["auto_repair", "skill_generation", "error_detection"],
            "status": "active",
        },
        {
            "id": "evolutionary_orchestrator",
            "name": "Evolutionary Orchestrator",
            "type": "specialist",
            "module_path": "src.utils.evolutionary_orchestrator",
            "capabilities": ["evolution", "self_improvement", "adaptation"],
            "status": "active",
        },
        {
            "id": "devops_agent",
            "name": "DevOps Agent",
            "type": "specialist",
            "module_path": "src.agents.devops_agent",
            "capabilities": ["monitoring", "data_pipeline", "observability", "maintenance", "health_check"],
            "status": "active",
        },
        {
            "id": "computer_use_agent",
            "name": "Computer Use Agent",
            "type": "specialist",
            "module_path": "src.agents.computer_use_agent",
            "capabilities": ["computer_use", "ui_automation", "screenshot", "typing", "mouse_control",
                             "dual_monitor", "window_management", "spatial_awareness", "smart_clipboard"],
            "status": "active",
        },
        # === Ouroboros Expansion ===
        {
            "id": "cloud_provisioning_agent",
            "name": "Cloud Provisioning Agent",
            "type": "specialist",
            "module_path": "src.agents.cloud_provisioning_agent",
            "capabilities": ["cloud", "infrastructure", "provisioning", "terraform", "kubernetes"],
            "status": "active",
        },
        {
            "id": "security_audit_agent",
            "name": "Security Audit Agent",
            "type": "specialist",
            "module_path": "src.agents.security_audit_agent",
            "capabilities": ["security", "auditing", "vulnerability", "compliance", "penetration_testing"],
            "status": "active",
        },
        {
            "id": "testing_agent",
            "name": "Testing Agent",
            "type": "specialist",
            "module_path": "src.agents.testing_agent",
            "capabilities": ["testing", "unit_testing", "integration_testing", "qa", "test_automation"],
            "status": "active",
        },
        {
            "id": "documentation_agent",
            "name": "Documentation Agent",
            "type": "specialist",
            "module_path": "src.agents.documentation_agent",
            "capabilities": ["documentation", "technical_writing", "api_docs", "changelog"],
            "status": "active",
        },
        {
            "id": "data_engineering_agent",
            "name": "Data Engineering Agent",
            "type": "specialist",
            "module_path": "src.agents.data_engineering_agent",
            "capabilities": ["data_engineering", "etl", "data_pipeline_advanced", "spark", "airflow"],
            "status": "active",
        },
        {
            "id": "frontend_agent",
            "name": "Frontend Agent",
            "type": "specialist",
            "module_path": "src.agents.frontend_agent",
            "capabilities": ["frontend", "ui_design", "react", "css", "accessibility"],
            "status": "active",
        },
        {
            "id": "api_gateway_agent",
            "name": "API Gateway Agent",
            "type": "specialist",
            "module_path": "src.agents.api_gateway_agent",
            "capabilities": ["api_gateway", "rate_limiting", "authentication", "api_versioning"],
            "status": "active",
        },
        {
            "id": "workflow_agent",
            "name": "Workflow Agent",
            "type": "specialist",
            "module_path": "src.agents.workflow_agent",
            "capabilities": ["workflow", "task_scheduling", "cron", "event_driven"],
            "status": "active",
        },
        {
            "id": "nlp_agent",
            "name": "NLP Agent",
            "type": "specialist",
            "module_path": "src.agents.nlp_agent",
            "capabilities": ["nlp", "text_classification", "sentiment_analysis", "entity_extraction"],
            "status": "active",
        },
    ]

    created = []
    errors = []

    for agent in agents:
        try:
            graph.execute_write(queries.UPSERT_AGENT, agent)
            created.append(agent["name"])
            logger.info(f"[Seed] Agent created: {agent['name']}")
        except Exception as e:
            errors.append(f"{agent['name']}: {e}")
            logger.error(f"[Seed] Error creating agent {agent['name']}: {e}")

    result = {"agents_created": created, "errors": errors}
    logger.info(f"[Seed] Done: {len(created)} agents created, {len(errors)} errors")
    return result


def run_full_migration(graph: GraphManager | None = None) -> dict:
    """Executa migracao completa: chunks + agents."""
    if graph is None:
        graph = GraphManager.from_env()

    from .schema import create_schema

    schema_result = create_schema(graph)
    chunk_result = migrate_chromadb(graph)
    agent_result = seed_agents(graph)

    return {
        "schema": schema_result,
        "chunks": chunk_result,
        "agents": agent_result,
    }
