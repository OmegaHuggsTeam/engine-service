"""
Tests for ResearchAgent — multi-source content research collector.

TDD: These tests are written FIRST. All external HTTP calls are mocked.
"""

import textwrap
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import ResearchDigest, ResearchItem
from src.neural_link.agents.content.research_agent import ResearchAgent


# ============================================================
# Sample API responses (fixtures)
# ============================================================

ARXIV_XML_RESPONSE = textwrap.dedent("""\
<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <entry>
    <title>AI Sales Agent: Conversational Commerce with LLMs</title>
    <summary>We present a framework for AI-powered sales agents that leverage
    large language models to automate customer engagement and conversion.</summary>
    <link href="http://arxiv.org/abs/2401.00001"/>
    <published>2024-01-15T00:00:00Z</published>
  </entry>
  <entry>
    <title>Theoretical Bounds on Transformer Benchmark Performance</title>
    <summary>This paper establishes theoretical lower bounds on benchmark
    performance for transformer architectures in abstract settings.</summary>
    <link href="http://arxiv.org/abs/2401.00002"/>
    <published>2024-01-14T00:00:00Z</published>
  </entry>
</feed>
""")

HUGGINGFACE_JSON_RESPONSE = [
    {
        "id": "salesforce/xgen-sales",
        "modelId": "salesforce/xgen-sales",
        "likes": 150,
        "downloads": 5000,
        "tags": ["sales", "customer", "agent"],
    },
    {
        "id": "meta/llama-3-bench",
        "modelId": "meta/llama-3-bench",
        "likes": 300,
        "downloads": 20000,
        "tags": ["benchmark", "theory"],
    },
]

GITHUB_TRENDING_JSON_RESPONSE = {
    "items": [
        {
            "full_name": "whatsapp-ai/sales-bot",
            "html_url": "https://github.com/whatsapp-ai/sales-bot",
            "description": "WhatsApp AI sales chatbot for automated customer conversion",
            "stargazers_count": 1200,
            "language": "Python",
        },
        {
            "full_name": "benchmark-suite/llm-eval",
            "html_url": "https://github.com/benchmark-suite/llm-eval",
            "description": "Benchmark evaluation suite for LLMs",
            "stargazers_count": 800,
            "language": "Python",
        },
    ]
}


# ============================================================
# Helpers
# ============================================================

def _mock_httpx_response(data, status_code=200, is_text=False):
    """Create a mock httpx.Response."""
    mock = MagicMock()
    mock.status_code = status_code
    mock.raise_for_status = MagicMock()
    if is_text:
        mock.text = data
    else:
        mock.json.return_value = data
        mock.text = str(data)
    return mock


# ============================================================
# TestCapabilities
# ============================================================

class TestCapabilities:
    def test_research_agent_has_correct_capabilities(self):
        agent = ResearchAgent()
        assert agent.capabilities == {"research", "papers", "trends", "curation"}

    def test_research_agent_inherits_base_agent(self):
        agent = ResearchAgent()
        assert isinstance(agent, BaseAgent)


# ============================================================
# TestFetchers
# ============================================================

class TestFetchers:
    @patch("src.neural_link.agents.content.research_agent.httpx.get")
    def test_fetch_arxiv_parses_xml(self, mock_get):
        """Arxiv returns Atom XML — agent must parse entries into ResearchItems."""
        mock_get.return_value = _mock_httpx_response(ARXIV_XML_RESPONSE, is_text=True)

        agent = ResearchAgent()
        items = agent._fetch_arxiv(query="AI sales agent")

        assert len(items) == 2
        assert all(isinstance(item, ResearchItem) for item in items)
        assert items[0].source == "arxiv"
        assert "Sales Agent" in items[0].title
        assert items[0].url == "http://arxiv.org/abs/2401.00001"
        mock_get.assert_called_once()

    @patch("src.neural_link.agents.content.research_agent.httpx.get")
    def test_fetch_huggingface_parses_json(self, mock_get):
        """HuggingFace returns JSON array of models."""
        mock_get.return_value = _mock_httpx_response(HUGGINGFACE_JSON_RESPONSE)

        agent = ResearchAgent()
        items = agent._fetch_huggingface()

        assert len(items) == 2
        assert all(isinstance(item, ResearchItem) for item in items)
        assert items[0].source == "huggingface"
        assert "salesforce/xgen-sales" in items[0].title
        mock_get.assert_called_once()

    @patch("src.neural_link.agents.content.research_agent.httpx.get")
    def test_fetch_github_trending_parses_json(self, mock_get):
        """GitHub trending returns search API JSON with items array."""
        mock_get.return_value = _mock_httpx_response(GITHUB_TRENDING_JSON_RESPONSE)

        agent = ResearchAgent()
        items = agent._fetch_github_trending()

        assert len(items) == 2
        assert all(isinstance(item, ResearchItem) for item in items)
        assert items[0].source == "github"
        assert "whatsapp-ai/sales-bot" in items[0].title
        assert items[0].url == "https://github.com/whatsapp-ai/sales-bot"
        mock_get.assert_called_once()

    @patch("src.neural_link.agents.content.research_agent.httpx.get")
    def test_fetch_arxiv_handles_failure_gracefully(self, mock_get):
        """Network failures should return empty list, not crash."""
        mock_get.side_effect = Exception("Connection timeout")

        agent = ResearchAgent()
        items = agent._fetch_arxiv(query="test")

        assert items == []

    @patch("src.neural_link.agents.content.research_agent.httpx.get")
    def test_fetch_huggingface_handles_failure_gracefully(self, mock_get):
        """Network failures should return empty list, not crash."""
        mock_get.side_effect = Exception("Connection refused")

        agent = ResearchAgent()
        items = agent._fetch_huggingface()

        assert items == []


# ============================================================
# TestRanking
# ============================================================

class TestRanking:
    def test_rank_items_returns_sorted_list(self):
        """Items should be sorted by relevance_score descending."""
        agent = ResearchAgent()

        items = [
            ResearchItem(
                title="Theoretical Bounds on Benchmarks",
                source="arxiv",
                url="http://example.com/1",
                summary="A theory paper on benchmark performance.",
                relevance_score=0.0,
                relevance_reason="",
                category="research",
            ),
            ResearchItem(
                title="AI Sales Agent for WhatsApp",
                source="arxiv",
                url="http://example.com/2",
                summary="An agent for sales conversion on WhatsApp.",
                relevance_score=0.0,
                relevance_reason="",
                category="research",
            ),
        ]

        ranked = agent._rank_items(items)

        assert len(ranked) == 2
        # The sales/whatsapp item should rank higher than the benchmark/theory one
        assert ranked[0].relevance_score >= ranked[1].relevance_score
        assert "sales" in ranked[0].title.lower() or "whatsapp" in ranked[0].title.lower()
        # Scores should be set (no longer 0.0 for sales-related item)
        assert ranked[0].relevance_score > 0.0


# ============================================================
# TestExecute
# ============================================================

class TestExecute:
    @patch.object(ResearchAgent, "_fetch_producthunt", return_value=[])
    @patch.object(ResearchAgent, "_fetch_github_trending", return_value=[])
    @patch.object(ResearchAgent, "_fetch_huggingface", return_value=[])
    @patch.object(ResearchAgent, "_fetch_arxiv")
    def test_execute_returns_research_digest(
        self, mock_arxiv, mock_hf, mock_gh, mock_ph
    ):
        """execute() should return a dict matching ResearchDigest schema."""
        mock_arxiv.return_value = [
            ResearchItem(
                title="AI Sales Automation",
                source="arxiv",
                url="http://arxiv.org/abs/2401.99999",
                summary="Automating sales with AI agents.",
                relevance_score=0.9,
                relevance_reason="Sales + AI + agent keywords",
                category="research",
            ),
        ]

        agent = ResearchAgent()
        result = agent.execute(task="research AI trends")

        # Result should be a dict (model_dump output)
        assert isinstance(result, dict)
        # Validate it conforms to ResearchDigest
        digest = ResearchDigest(**result)
        assert len(digest.items) >= 1
        assert digest.total_collected >= 1
        assert isinstance(digest.sources_status, dict)
        assert "arxiv" in digest.sources_status

    @patch.object(ResearchAgent, "_fetch_producthunt", return_value=[])
    @patch.object(ResearchAgent, "_fetch_github_trending", return_value=[])
    @patch.object(ResearchAgent, "_fetch_huggingface", return_value=[])
    @patch.object(ResearchAgent, "_fetch_arxiv", return_value=[])
    def test_execute_with_no_results(self, mock_arxiv, mock_hf, mock_gh, mock_ph):
        """execute() with no results should still return valid ResearchDigest."""
        agent = ResearchAgent()
        result = agent.execute(task="research AI trends")

        assert isinstance(result, dict)
        digest = ResearchDigest(**result)
        assert len(digest.items) == 0
        assert digest.total_collected == 0

    @patch.object(ResearchAgent, "_fetch_producthunt", return_value=[])
    @patch.object(ResearchAgent, "_fetch_github_trending", return_value=[])
    @patch.object(ResearchAgent, "_fetch_huggingface", return_value=[])
    @patch.object(ResearchAgent, "_fetch_arxiv", return_value=[])
    def test_execute_accepts_dict_task(self, mock_arxiv, mock_hf, mock_gh, mock_ph):
        """execute() should accept a dict task with query and top_n."""
        agent = ResearchAgent()
        result = agent.execute(task="research", query="AI sales", top_n=5)

        assert isinstance(result, dict)
        digest = ResearchDigest(**result)
        assert isinstance(digest.period, str)
