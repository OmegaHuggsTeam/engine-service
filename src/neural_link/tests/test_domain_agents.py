"""
Tests for Domain Agent Wrappers — Marketing, Social Media, AI Engineer.

All external dependencies (LLM, ChromaDB, Neo4j) are mocked.
"""

from unittest.mock import MagicMock, patch

from src.neural_link.agents.domain_agents import (
    AiEngineerDomainAgent,
    MarketingDomainAgent,
    SocialMediaDomainAgent,
)
from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY

# ==================================================================
# TestMarketingDomainAgent
# ==================================================================


class TestMarketingDomainAgent:
    """Test MarketingDomainAgent initialization and execution."""

    def test_init(self):
        """Test agent initialization with correct domain and capabilities."""
        agent = MarketingDomainAgent()
        assert agent._domain == "marketing"
        assert "marketing" in agent._categories
        assert "campaigns" in agent._categories
        assert "email" in agent._categories
        assert "copywriting" in agent._categories

    def test_capabilities(self):
        """Test agent capabilities property."""
        agent = MarketingDomainAgent()
        caps = agent.capabilities
        assert "copywriting" in caps
        assert "campaign_strategy" in caps
        assert "a_b_testing" in caps
        assert "audience_targeting" in caps
        assert "email_marketing" in caps
        assert "content_creation" in caps

    @patch("src.utils.llm_client.chat_completion")
    @patch("src.utils.vector_db.search_with_scores")
    def test_execute_with_mocked_llm(self, mock_search, mock_chat):
        """Test execute method with mocked LLM and vector search."""
        # Mock vector search to return empty results
        mock_search.return_value = []

        # Mock LLM response
        mock_chat.return_value = "Campaign strategy: Focus on email marketing with A/B testing"

        agent = MarketingDomainAgent()
        result = agent.execute("Create a campaign strategy for product launch")

        assert result == "Campaign strategy: Focus on email marketing with A/B testing"
        assert mock_chat.called
        assert mock_search.called

    @patch("src.utils.llm_client.chat_completion")
    @patch("src.utils.vector_db.search_with_scores")
    def test_execute_with_context(self, mock_search, mock_chat):
        """Test execute with context from vector search."""
        # Mock vector search with relevant results
        mock_search.return_value = [
            {
                "content": "Marketing best practices for campaigns",
                "score": 0.8,
                "metadata": {"category": "marketing", "source_file": "marketing_guide.md"},
            }
        ]

        mock_chat.return_value = "Strategy based on best practices"

        agent = MarketingDomainAgent()
        result = agent.execute("Develop email campaign")

        assert result == "Strategy based on best practices"
        assert mock_chat.called


# ==================================================================
# TestSocialMediaDomainAgent
# ==================================================================


class TestSocialMediaDomainAgent:
    """Test SocialMediaDomainAgent initialization and execution."""

    def test_init(self):
        """Test agent initialization with correct domain and capabilities."""
        agent = SocialMediaDomainAgent()
        assert agent._domain == "social_media"
        assert "social_media" in agent._categories
        assert "engagement" in agent._categories
        assert "content" in agent._categories

    def test_capabilities(self):
        """Test agent capabilities property."""
        agent = SocialMediaDomainAgent()
        caps = agent.capabilities
        assert "social_posting" in caps
        assert "engagement_analysis" in caps
        assert "content_calendar" in caps
        assert "hashtag_strategy" in caps
        assert "audience_growth" in caps
        assert "analytics" in caps

    @patch("src.utils.llm_client.chat_completion")
    @patch("src.utils.vector_db.search_with_scores")
    def test_execute_with_mocked_llm(self, mock_search, mock_chat):
        """Test execute method with mocked LLM and vector search."""
        mock_search.return_value = []
        mock_chat.return_value = "Social media calendar created with optimal posting times"

        agent = SocialMediaDomainAgent()
        result = agent.execute("Create a social media content calendar")

        assert result == "Social media calendar created with optimal posting times"
        assert mock_chat.called

    @patch("src.utils.llm_client.chat_completion")
    @patch("src.utils.vector_db.search_with_scores")
    def test_execute_engagement_analysis(self, mock_search, mock_chat):
        """Test execute for engagement analysis task."""
        mock_search.return_value = [
            {
                "content": "Engagement metrics: likes, shares, comments",
                "score": 0.75,
                "metadata": {"category": "social_media"},
            }
        ]

        mock_chat.return_value = "Engagement analysis: High performance on visual content"

        agent = SocialMediaDomainAgent()
        result = agent.execute("Analyze engagement metrics")

        assert "Engagement analysis" in result


# ==================================================================
# TestAiEngineerDomainAgent
# ==================================================================


class TestAiEngineerDomainAgent:
    """Test AiEngineerDomainAgent initialization and execution."""

    def test_init(self):
        """Test agent initialization with correct domain and capabilities."""
        agent = AiEngineerDomainAgent()
        assert agent._domain == "ai_engineering"
        assert "ml" in agent._categories
        assert "ai" in agent._categories
        assert "pipeline" in agent._categories
        assert "model" in agent._categories

    def test_capabilities(self):
        """Test agent capabilities property."""
        agent = AiEngineerDomainAgent()
        caps = agent.capabilities
        assert "model_evaluation" in caps
        assert "pipeline_design" in caps
        assert "data_engineering" in caps
        assert "embedding_optimization" in caps
        assert "rag_architecture" in caps
        assert "fine_tuning" in caps
        assert "ai" in caps
        assert "machine_learning" in caps
        assert "llm" in caps
        assert "rag" in caps
        assert "embeddings" in caps

    @patch("src.utils.llm_client.chat_completion")
    @patch("src.utils.vector_db.search_with_scores")
    def test_execute_with_mocked_llm(self, mock_search, mock_chat):
        """Test execute method with mocked LLM and vector search."""
        mock_search.return_value = []
        mock_chat.return_value = "ML pipeline designed with evaluation stages"

        agent = AiEngineerDomainAgent()
        result = agent.execute("Design an ML evaluation pipeline")

        assert result == "ML pipeline designed with evaluation stages"
        assert mock_chat.called

    @patch("src.utils.llm_client.chat_completion")
    @patch("src.utils.vector_db.search_with_scores")
    def test_execute_rag_architecture(self, mock_search, mock_chat):
        """Test execute for RAG architecture task."""
        mock_search.return_value = [
            {
                "content": "RAG architecture: embeddings, vector store, retrieval",
                "score": 0.85,
                "metadata": {"category": "ai", "source_file": "rag_guide.md"},
            }
        ]

        mock_chat.return_value = "RAG system designed with ChromaDB and optimized retrieval"

        agent = AiEngineerDomainAgent()
        result = agent.execute("Design a RAG architecture")

        assert "RAG" in result


# ==================================================================
# TestAgentRegistryCompleteness
# ==================================================================


class TestAgentRegistryCompleteness:
    """Test that all domain agents are properly registered."""

    def test_marketing_agent_registry(self):
        """Test marketing_agent has required fields in registry."""
        agent_info = AGENT_REGISTRY.get("marketing_agent")
        assert agent_info is not None
        assert agent_info["agent_class"] == "MarketingDomainAgent"
        assert agent_info["module_path"] == "src.neural_link.agents.domain_agents"
        assert agent_info["type"] == "domain"
        assert agent_info["invoke"] == "execute"
        assert "copywriting" in agent_info["capabilities"]

    def test_social_media_agent_registry(self):
        """Test social_media_agent has required fields in registry."""
        agent_info = AGENT_REGISTRY.get("social_media_agent")
        assert agent_info is not None
        assert agent_info["agent_class"] == "SocialMediaDomainAgent"
        assert agent_info["module_path"] == "src.neural_link.agents.domain_agents"
        assert agent_info["type"] == "domain"
        assert agent_info["invoke"] == "execute"
        assert "social_posting" in agent_info["capabilities"]

    def test_ai_engineer_agent_registry(self):
        """Test ai_engineer_agent has required fields in registry."""
        agent_info = AGENT_REGISTRY.get("ai_engineer_agent")
        assert agent_info is not None
        assert agent_info["agent_class"] == "AiEngineerDomainAgent"
        assert agent_info["module_path"] == "src.neural_link.agents.domain_agents"
        assert agent_info["type"] == "domain"
        assert agent_info["invoke"] == "execute"
        assert "model_evaluation" in agent_info["capabilities"]

    def test_specialist_agents_have_knowledge_categories(self):
        """Test top specialist agents have knowledge_categories field."""
        specialists = [
            "devops_agent",
            "security_audit_agent",
            "testing_agent",
            "documentation_agent",
            "frontend_agent",
        ]

        for agent_id in specialists:
            agent_info = AGENT_REGISTRY.get(agent_id)
            assert agent_info is not None, f"{agent_id} not found in registry"
            assert "knowledge_categories" in agent_info, f"{agent_id} missing knowledge_categories"
            assert isinstance(agent_info["knowledge_categories"], list)
            assert len(agent_info["knowledge_categories"]) > 0


# ==================================================================
# TestSpecialistAdaptiveTruncation
# ==================================================================


class TestSpecialistAdaptiveTruncation:
    """Test adaptive truncation in specialist agent knowledge loading."""

    @patch("sklearn.metrics.pairwise.cosine_similarity")
    @patch("sklearn.feature_extraction.text.TfidfVectorizer")
    def test_score_filter_applied(self, mock_vectorizer, mock_cosine):
        """Test that score threshold filters low-relevance chunks."""
        import numpy as np

        from src.neural_link.agents.specialist_agent import _search_chunks

        # Mock TF-IDF vectorizer
        mock_vec_instance = MagicMock()
        mock_vectorizer.return_value = mock_vec_instance
        mock_vec_instance.fit_transform.return_value = MagicMock()
        mock_vec_instance.transform.return_value = MagicMock()

        # Mock cosine similarity with scores above and below threshold
        mock_cosine.return_value = np.array([[0.8, 0.3, 0.6, 0.2, 0.9]])  # 0.35 threshold

        chunks = [
            {"content": "High relevance content 1"},
            {"content": "Low relevance content"},
            {"content": "Medium relevance content"},
            {"content": "Very low relevance"},
            {"content": "High relevance content 2"},
        ]

        result = _search_chunks(chunks, "test query", top_k=5)

        # Should filter out chunks with score < 0.35 (indices 1 and 3)
        assert len(result) == 3
        assert all(chunk.get("score", 0) >= 0.35 for chunk in result)

    @patch("sklearn.metrics.pairwise.cosine_similarity")
    @patch("sklearn.feature_extraction.text.TfidfVectorizer")
    def test_adaptive_truncation_applied(self, mock_vectorizer, mock_cosine):
        """Test that adaptive truncation limits content based on score."""
        import numpy as np

        from src.neural_link.agents.specialist_agent import _search_chunks

        # Mock TF-IDF vectorizer
        mock_vec_instance = MagicMock()
        mock_vectorizer.return_value = mock_vec_instance
        mock_vec_instance.fit_transform.return_value = MagicMock()
        mock_vec_instance.transform.return_value = MagicMock()

        # Mock cosine similarity with different scores
        mock_cosine.return_value = np.array([[0.8, 0.5]])

        long_content = "x" * 1000  # 1000 chars
        chunks = [
            {"content": long_content},
            {"content": long_content},
        ]

        result = _search_chunks(chunks, "test query", top_k=2)

        # High score (0.8): max_chars = max(100, int(500 * 0.8)) = 400
        assert len(result[0]["content"]) == 400

        # Medium score (0.5): max_chars = max(100, int(500 * 0.5)) = 250
        assert len(result[1]["content"]) == 250

    def test_fallback_search_no_truncation(self):
        """Test fallback keyword search doesn't break."""
        from src.neural_link.agents.specialist_agent import _search_chunks

        chunks = [
            {"content": "kubernetes deployment configuration"},
            {"content": "docker container setup"},
            {"content": "monitoring and observability"},
        ]

        result = _search_chunks(chunks, "kubernetes monitoring", top_k=2)

        # Should return chunks with matching keywords
        assert len(result) <= 2
        assert len(result) > 0
