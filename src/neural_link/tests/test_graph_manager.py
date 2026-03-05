"""
Tests para o Neural Link Graph Manager e componentes relacionados.

Tests que nao requerem Neo4j:
- QueryRouter
- ResultMerger
- ConceptExtractor (rule-based)
- TaskDecomposer (simples)
- AgentSelector (registry)
- Models

Tests que requerem Neo4j (skipados se indisponivel):
- GraphManager
- Schema creation
- Migration
"""

import pytest
import uuid
from unittest.mock import MagicMock, patch

# ============================================================
# Tests sem dependencia de Neo4j
# ============================================================


class TestQueryRouter:
    """Tests para o QueryRouter."""

    def test_default_weights(self):
        from src.neural_link.rag.query_router import QueryRouter

        router = QueryRouter()
        result = router.route("pergunta generica qualquer")

        assert "chroma" in result
        assert "neo4j" in result
        assert "tfidf" in result
        total = result["chroma"] + result["neo4j"] + result["tfidf"]
        assert abs(total - 1.0) < 0.01

    def test_relational_query_boosts_neo4j(self):
        from src.neural_link.rag.query_router import QueryRouter

        router = QueryRouter()
        result = router.route("Como RAG se relaciona com ChromaDB?")

        assert result["neo4j"] > result["chroma"]
        assert result["query_type"] == "relational"

    def test_error_query_boosts_neo4j(self):
        from src.neural_link.rag.query_router import QueryRouter

        router = QueryRouter()
        result = router.route("Como corrigir o erro de conexao?")

        assert result["neo4j"] >= result["tfidf"]
        assert result["query_type"] == "error_resolution"

    def test_documentation_query_boosts_tfidf(self):
        from src.neural_link.rag.query_router import QueryRouter

        router = QueryRouter()
        result = router.route("Como configurar Selenium passo a passo?")

        assert result["tfidf"] > result["neo4j"]
        assert result["query_type"] == "documentation"

    def test_conceptual_query_boosts_chroma(self):
        from src.neural_link.rag.query_router import QueryRouter

        router = QueryRouter()
        result = router.route("O que e RAG e como funciona?")

        assert result["chroma"] > result["neo4j"]
        assert result["query_type"] == "conceptual"


class TestResultMerger:
    """Tests para o ResultMerger."""

    def test_merge_empty(self):
        from src.neural_link.rag.result_merger import ResultMerger

        merger = ResultMerger()
        result = merger.merge({}, {"chroma": 0.4, "neo4j": 0.3, "tfidf": 0.3})
        assert result == []

    def test_merge_single_engine(self):
        from src.neural_link.rag.result_merger import ResultMerger

        merger = ResultMerger()
        results = {
            "chroma": [
                {"content": "Hello world", "source_file": "test.md", "score": 0.9},
                {"content": "Foo bar", "source_file": "test2.md", "score": 0.5},
            ]
        }
        merged = merger.merge(results, {"chroma": 1.0}, top_k=5)

        assert len(merged) == 2
        assert merged[0]["score"] >= merged[1]["score"]

    def test_cross_engine_boost(self):
        from src.neural_link.rag.result_merger import ResultMerger

        merger = ResultMerger()
        results = {
            "chroma": [
                {"content": "shared content", "source_file": "test.md", "score": 0.8},
            ],
            "tfidf": [
                {"content": "shared content", "source_file": "test.md", "score": 0.7},
            ],
        }
        merged = merger.merge(
            results, {"chroma": 0.5, "tfidf": 0.5}, top_k=5
        )

        assert len(merged) == 1
        assert merged[0]["engine_count"] == 2
        # Score should be boosted by 15%
        assert merged[0]["score"] > 0.5

    def test_deduplication(self):
        from src.neural_link.rag.result_merger import ResultMerger

        merger = ResultMerger()
        results = {
            "chroma": [
                {"content": "same content here", "source_file": "a.md", "score": 0.9},
            ],
            "neo4j": [
                {"content": "same content here", "source_file": "a.md", "score": 0.8},
            ],
        }
        merged = merger.merge(
            results, {"chroma": 0.5, "neo4j": 0.5}, top_k=5
        )

        assert len(merged) == 1


class TestConceptExtractor:
    """Tests para o ConceptExtractor (rule-based only)."""

    def test_extracts_known_concepts(self):
        from src.neural_link.rag.concept_extractor import extract_concepts_rule_based

        known = ["Python", "RAG", "ChromaDB"]
        concepts = extract_concepts_rule_based(
            "Python tem boa integracao com ChromaDB para RAG",
            known_concepts=known,
        )

        names = [c["name"] for c in concepts]
        assert "Python" in names or "python" in names
        assert "ChromaDB" in names or "chromadb" in names

    def test_extracts_tech_patterns(self):
        from src.neural_link.rag.concept_extractor import extract_concepts_rule_based

        concepts = extract_concepts_rule_based(
            "Usando selenium com docker e fastapi"
        )

        names = [c["name"].lower() for c in concepts]
        assert "selenium" in names
        assert "docker" in names
        assert "fastapi" in names

    def test_empty_text(self):
        from src.neural_link.rag.concept_extractor import extract_concepts

        concepts = extract_concepts("", use_cache=False)
        assert concepts == []


class TestModels:
    """Tests para os Pydantic models."""

    def test_task_creation(self):
        from src.neural_link.orchestrator.models import Task, TaskType, TaskStatus

        task = Task(
            id="test_1",
            description="Test task",
            type=TaskType.QUERY,
            priority=5,
        )

        assert task.id == "test_1"
        assert task.status == TaskStatus.PENDING
        assert task.type == TaskType.QUERY

    def test_task_result(self):
        from src.neural_link.orchestrator.models import TaskResult

        result = TaskResult(
            task_id="test_1",
            success=True,
            output="Hello",
            agent_used="groq_operator",
            execution_time_ms=100.5,
        )

        assert result.success
        assert result.output == "Hello"

    def test_orchestrator_response(self):
        from src.neural_link.orchestrator.models import OrchestratorResponse

        response = OrchestratorResponse(
            answer="Test answer",
            session_id="sess_123",
            processing_time_ms=500.0,
        )

        assert response.answer == "Test answer"
        assert response.tasks == []
        assert response.results == []


class TestTaskDecomposer:
    """Tests para o TaskDecomposer (sem LLM)."""

    def test_simple_request(self):
        from src.neural_link.orchestrator.task_decomposer import TaskDecomposer

        decomposer = TaskDecomposer()
        tasks = decomposer.decompose("O que e RAG?")

        assert len(tasks) == 1
        assert tasks[0].description == "O que e RAG?"

    def test_infer_task_type_error(self):
        from src.neural_link.orchestrator.task_decomposer import TaskDecomposer

        decomposer = TaskDecomposer()
        tasks = decomposer.decompose("Corrigir o erro de conexao do Selenium")

        assert len(tasks) == 1
        assert tasks[0].type.value == "repair"

    def test_infer_task_type_generation(self):
        from src.neural_link.orchestrator.task_decomposer import TaskDecomposer

        decomposer = TaskDecomposer()
        tasks = decomposer.decompose("Crie um post para Instagram")

        assert len(tasks) == 1
        assert tasks[0].type.value == "generation"


class TestAgentSelector:
    """Tests para o AgentSelector (sem Neo4j)."""

    def test_select_marketing(self):
        from src.neural_link.orchestrator.agent_selector import AgentSelector
        from src.neural_link.orchestrator.models import Task

        selector = AgentSelector()
        task = Task(
            id="t1",
            description="Criar campanha",
            required_capabilities=["marketing", "copywriting"],
        )

        agent = selector.select(task)
        assert agent == "marketing_agent"

    def test_select_analytics(self):
        from src.neural_link.orchestrator.agent_selector import AgentSelector
        from src.neural_link.orchestrator.models import Task

        selector = AgentSelector()
        task = Task(
            id="t2",
            description="Analisar metricas",
            required_capabilities=["analytics", "data_analysis"],
        )

        agent = selector.select(task)
        assert agent == "analytics_agent"

    def test_select_default(self):
        from src.neural_link.orchestrator.agent_selector import AgentSelector
        from src.neural_link.orchestrator.models import Task

        selector = AgentSelector()
        task = Task(id="t3", description="Algo generico")

        agent = selector.select(task)
        assert agent == "groq_operator"

    def test_select_ai_engineer(self):
        from src.neural_link.orchestrator.agent_selector import AgentSelector
        from src.neural_link.orchestrator.models import Task

        selector = AgentSelector()
        task = Task(
            id="t4",
            description="Treinar modelo",
            required_capabilities=["ai", "embeddings"],
        )

        agent = selector.select(task)
        assert agent == "ai_engineer_agent"


class TestUnifiedInterface:
    """Tests para UnifiedInterface (sem dependencias externas)."""

    def test_health_without_neo4j(self):
        from src.neural_link.api.interface import UnifiedInterface

        interface = UnifiedInterface()
        health = interface.health()

        assert health["status"] == "ok"
        assert "neo4j" in health


# ============================================================
# Tests que requerem Neo4j (skipados se indisponivel)
# ============================================================

def _neo4j_available():
    """Checa se Neo4j esta acessivel."""
    try:
        from src.neural_link.graph.manager import GraphManager
        gm = GraphManager.from_env()
        return gm.verify_connectivity()
    except Exception:
        return False


@pytest.mark.skipif(not _neo4j_available(), reason="Neo4j not available")
class TestGraphManager:
    """Tests que requerem Neo4j rodando."""

    def test_connectivity(self):
        from src.neural_link.graph.manager import GraphManager
        gm = GraphManager.from_env()
        assert gm.verify_connectivity()

    def test_execute_read(self):
        from src.neural_link.graph.manager import GraphManager
        gm = GraphManager.from_env()
        result = gm.execute_read("RETURN 1 AS num")
        assert result[0]["num"] == 1

    def test_create_and_read_node(self):
        from src.neural_link.graph.manager import GraphManager
        gm = GraphManager.from_env()

        test_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create
        gm.execute_write(
            "CREATE (n:TestNode {id: $id, name: $name})",
            {"id": test_id, "name": "test_node"},
        )

        # Read
        result = gm.execute_read(
            "MATCH (n:TestNode {id: $id}) RETURN n.name AS name",
            {"id": test_id},
        )
        assert result[0]["name"] == "test_node"

        # Cleanup
        gm.execute_write(
            "MATCH (n:TestNode {id: $id}) DELETE n",
            {"id": test_id},
        )

    def test_schema_creation(self):
        from src.neural_link.graph.schema import create_schema
        from src.neural_link.graph.manager import GraphManager

        gm = GraphManager.from_env()
        result = create_schema(gm)

        assert len(result["created"]) > 0
        assert isinstance(result["errors"], list)
