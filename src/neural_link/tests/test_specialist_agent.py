"""
Tests for SpecialistAgent - Knowledge-Powered Agent.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.specialist_agent import (
    SpecialistAgent,
    _adapt_workflow_json,
    _build_context_block,
    _credential_to_env_var,
    _extract_expressions,
    _search_chunks,
)

# ---------------------------------------------------------------------------
# Fixtures & helpers for explain_and_adapt tests
# ---------------------------------------------------------------------------

WORKFLOW_WITH_CREDS = {
    "name": "Test Automation",
    "nodes": [
        {
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 1,
            "parameters": {"path": "incoming"},
            "credentials": {},
        },
        {
            "name": "Google Sheets",
            "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4,
            "parameters": {
                "operation": "append",
                "sheetName": "Sheet1",
                "values": "={{ $('Webhook').item.json.email }}",
            },
            "credentials": {
                "googleSheetsOAuth2Api": {"id": "abc123", "name": "My Sheets"},
            },
        },
        {
            "name": "Groq Chat",
            "type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "typeVersion": 1,
            "parameters": {
                "prompt": '={{ $node["Google Sheets"].json["status"] }}',
            },
            "credentials": {
                "groqApi": {"id": "xyz789", "name": "Groq Prod"},
            },
        },
    ],
    "connections": {
        "Webhook": {"main": [[{"node": "Google Sheets", "type": "main", "index": 0}]]},
        "Google Sheets": {"main": [[{"node": "Groq Chat", "type": "main", "index": 0}]]},
    },
}


def _mock_httpx_response(json_str: str):
    """Returns a mock that replaces httpx.Client as a context manager."""
    mock_response = MagicMock()
    mock_response.text = json_str
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.get.return_value = mock_response
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)

    return mock_client


class TestBaseAgent:
    """BaseAgent interface."""

    def test_base_agent_is_abstract(self):
        """BaseAgent cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseAgent()


class TestSpecialistAgent:
    """SpecialistAgent behavior."""

    def test_inherits_base_agent(self):
        """SpecialistAgent herda de BaseAgent."""
        agent = SpecialistAgent()
        assert isinstance(agent, BaseAgent)

    def test_load_knowledge_returns_list(self, tmp_path):
        """load_knowledge retorna lista de chunks."""
        (tmp_path / "test.json").write_text(
            '[{"content": "chunk 1", "category": "n8n_templates"}]',
            encoding="utf-8",
        )
        agent = SpecialistAgent(chunks_dir=tmp_path)
        chunks = agent.load_knowledge("n8n_templates")
        assert isinstance(chunks, list)
        assert len(chunks) == 1
        assert chunks[0]["content"] == "chunk 1"

    def test_load_knowledge_empty_for_unknown_category(self, tmp_path):
        """load_knowledge retorna vazio para categoria inexistente."""
        (tmp_path / "test.json").write_text(
            '[{"content": "x", "category": "other"}]',
            encoding="utf-8",
        )
        agent = SpecialistAgent(chunks_dir=tmp_path)
        chunks = agent.load_knowledge("n8n_templates")
        assert chunks == []

    def test_decorate_prompt_injects_context(self):
        """Prompt Decorator injeta Contexto de Referência."""
        agent = SpecialistAgent()
        agent._knowledge = [
            {"content": "Conteúdo A", "source_file": "fonte1"},
            {"content": "Conteúdo B", "source_file": "fonte2"},
        ]
        decorated = agent._decorate_prompt("Responda X")
        assert "Contexto de Referência" in decorated
        assert "Conteúdo A" in decorated
        assert "Tarefa" in decorated
        assert "Responda X" in decorated

    def test_creative_synthesis_requires_chunks(self):
        """creative_synthesis retorna mensagem se chunk_a ou chunk_b ausente."""
        agent = SpecialistAgent()
        result = agent.execute("x", mode="creative_synthesis")
        assert "chunk_a" in result.lower() or "chunk_b" in result.lower()

    def test_creative_synthesis_with_chunks(self):
        """creative_synthesis com chunk_a e chunk_b invoca LLM."""
        agent = SpecialistAgent()
        chunk_a = {"content": "Trigger: webhook recebe evento", "source_file": "A"}
        chunk_b = {"content": "Action: enviar email", "source_file": "B"}
        from unittest.mock import patch

        with patch.object(agent, "_invoke_llm", return_value="Conexão: webhook -> email"):
            result = agent.execute(
                "propor fluxo",
                mode="creative_synthesis",
                chunk_a=chunk_a,
                chunk_b=chunk_b,
            )
        assert "Conexão" in result or "webhook" in result


class TestHelpers:
    """Helpers de busca e contexto."""

    def test_build_context_block_empty(self):
        """build_context_block vazio retorna string vazia."""
        assert _build_context_block([]) == ""

    def test_build_context_block_with_chunks(self):
        """build_context_block monta bloco formatado."""
        chunks = [
            {"content": "C1", "source_file": "f1"},
            {"content": "C2", "source_file": "f2"},
        ]
        block = _build_context_block(chunks)
        assert "Referência 1" in block
        assert "C1" in block
        assert "C2" in block

    def test_search_chunks_keyword_fallback(self):
        """_search_chunks usa keyword quando TF-IDF indisponível."""
        chunks = [
            {"content": "n8n workflow automation"},
            {"content": "python scripts"},
        ]
        result = _search_chunks(chunks, "n8n workflow", top_k=2)
        assert len(result) >= 1
        assert "n8n" in result[0]["content"].lower()


# ---------------------------------------------------------------------------
# Tests for _credential_to_env_var
# ---------------------------------------------------------------------------


class TestCredentialToEnvVar:
    """_credential_to_env_var conversion."""

    def test_simple_camel(self):
        assert _credential_to_env_var("groqApi") == "GROQ_API"

    def test_long_camel(self):
        assert _credential_to_env_var("googleSheetsOAuth2Api") == "GOOGLE_SHEETS_O_AUTH2_API"

    def test_single_word(self):
        assert _credential_to_env_var("slack") == "SLACK"

    def test_already_upper(self):
        assert _credential_to_env_var("HTTP") == "HTTP"


# ---------------------------------------------------------------------------
# Tests for _extract_expressions
# ---------------------------------------------------------------------------


class TestExtractExpressions:
    """_extract_expressions regex scanning."""

    def test_modern_pattern(self):
        raw = """{"value": "={{ $('Webhook').item.json.email }}"}"""
        result = _extract_expressions(raw)
        assert len(result) == 1
        assert result[0] == {"node": "Webhook", "field": "email"}

    def test_legacy_pattern(self):
        raw = '{"value": "={{ $node[\\"Sheets\\"].json[\\"status\\"] }}"}'
        result = _extract_expressions(raw)
        assert len(result) == 1
        assert result[0] == {"node": "Sheets", "field": "status"}

    def test_no_expressions(self):
        raw = '{"value": "plain text"}'
        assert _extract_expressions(raw) == []

    def test_dedup(self):
        raw = """{"a": "={{ $('X').item.json.f1 }}", """ """"b": "={{ $('X').item.json.f1 }}"}"""
        result = _extract_expressions(raw)
        assert len(result) == 1

    def test_multiple_different(self):
        raw = """{"a": "={{ $('A').item.json.name }}", """ """"b": "={{ $('B').item.json.age }}"}"""
        result = _extract_expressions(raw)
        assert len(result) == 2
        nodes = {r["node"] for r in result}
        assert nodes == {"A", "B"}


# ---------------------------------------------------------------------------
# Tests for _adapt_workflow_json
# ---------------------------------------------------------------------------


class TestAdaptWorkflowJson:
    """_adapt_workflow_json credential replacement."""

    def test_credentials_replaced(self):
        adapted_str, env_lines = _adapt_workflow_json(WORKFLOW_WITH_CREDS)
        adapted = json.loads(adapted_str)
        groq_creds = adapted["nodes"][2]["credentials"]["groqApi"]
        assert "$env." in groq_creds["id"]
        assert "$env." in groq_creds["name"]

    def test_env_lines_generated(self):
        _, env_lines = _adapt_workflow_json(WORKFLOW_WITH_CREDS)
        assert len(env_lines) >= 2
        assert any("GROQ_API" in line for line in env_lines)
        assert any("GOOGLE_SHEETS" in line for line in env_lines)

    def test_no_creds_passthrough(self):
        wf = {"nodes": [{"name": "X", "type": "t", "parameters": {}}], "connections": {}}
        adapted_str, env_lines = _adapt_workflow_json(wf)
        assert env_lines == []
        assert "X" in adapted_str

    def test_original_unchanged(self):
        original_id = WORKFLOW_WITH_CREDS["nodes"][2]["credentials"]["groqApi"]["id"]
        _adapt_workflow_json(WORKFLOW_WITH_CREDS)
        assert WORKFLOW_WITH_CREDS["nodes"][2]["credentials"]["groqApi"]["id"] == original_id


# ---------------------------------------------------------------------------
# Tests for explain_and_adapt
# ---------------------------------------------------------------------------


class TestExplainAndAdapt:
    """SpecialistAgent.explain_and_adapt integration."""

    def _make_agent(self):
        return SpecialistAgent()

    def test_happy_path_contains_sections(self):
        """Happy path returns all expected Markdown sections."""
        agent = self._make_agent()
        raw = json.dumps(WORKFLOW_WITH_CREDS)
        mock_client = _mock_httpx_response(raw)

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://example.com/wf.json")

        assert "*Test Automation*" in result
        assert "Categoria:" in result
        assert "*Objetivo do Fluxo*" in result
        assert "*Servicos Necessarios*" in result
        assert "Cadeia:" in result

    def test_contains_env_block(self):
        """Output includes .env variable block."""
        agent = self._make_agent()
        raw = json.dumps(WORKFLOW_WITH_CREDS)
        mock_client = _mock_httpx_response(raw)

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://example.com/wf.json")

        assert "Variaveis .env necessarias:" in result
        assert "GROQ_API_ID=<seu-id-aqui>" in result

    def test_adapted_json_has_env_refs(self):
        """Adapted JSON section contains $env references."""
        agent = self._make_agent()
        raw = json.dumps(WORKFLOW_WITH_CREDS)
        mock_client = _mock_httpx_response(raw)

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://example.com/wf.json")

        assert "$env." in result
        assert "*JSON Adaptado:*" in result

    def test_download_error(self):
        """Download failure returns error message."""
        agent = self._make_agent()
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("Connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://bad-url.com/wf.json")

        assert "*Erro ao baixar workflow:*" in result

    def test_invalid_json(self):
        """Invalid JSON returns parse error."""
        agent = self._make_agent()
        mock_client = _mock_httpx_response("not valid json {{{")

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://example.com/bad.json")

        assert "*Erro ao parsear JSON:*" in result

    def test_not_n8n_workflow(self):
        """JSON without 'nodes' key returns not-n8n error."""
        agent = self._make_agent()
        mock_client = _mock_httpx_response('{"foo": "bar"}')

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://example.com/other.json")

        assert "*Erro:*" in result
        assert "nodes" in result

    def test_credentials_section_present(self):
        """Credentials section lists cred -> env mapping."""
        agent = self._make_agent()
        raw = json.dumps(WORKFLOW_WITH_CREDS)
        mock_client = _mock_httpx_response(raw)

        with patch(
            "src.neural_link.agents.specialist_agent.httpx.Client", return_value=mock_client
        ):
            result = agent.explain_and_adapt("https://example.com/wf.json")

        assert "*Credenciais*" in result
        assert "`groqApi`" in result
        assert "`GROQ_API`" in result


# ---------------------------------------------------------------------------
# Tests for analyze_pod_logs
# ---------------------------------------------------------------------------


class TestAnalyzePodLogs:
    """SpecialistAgent.analyze_pod_logs Kubernetes log analysis."""

    def test_empty_logs_returns_message(self):
        """Empty logs return helpful message."""
        agent = SpecialistAgent()
        result = agent.analyze_pod_logs("")
        assert "Logs vazios" in result

    def test_whitespace_only_logs_returns_message(self):
        """Whitespace-only logs return helpful message."""
        agent = SpecialistAgent()
        result = agent.analyze_pod_logs("   \n\n  ")
        assert "Logs vazios" in result

    def test_loads_k8s_error_patterns_by_default(self):
        """analyze_pod_logs loads k8s_error_patterns knowledge base by default."""
        agent = SpecialistAgent()
        sample_logs = "Error: connection refused to database:5432"

        with patch.object(
            agent, "execute", return_value="Connection error detected"
        ) as mock_execute:
            agent.analyze_pod_logs(sample_logs, pod_name="test-pod", namespace="default")

            # Verify execute was called with k8s_error_patterns
            mock_execute.assert_called_once()
            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs.get("chunk_type") == "k8s_error_patterns"

    def test_includes_pod_context_in_analysis(self):
        """Pod name and namespace are included in analysis prompt."""
        agent = SpecialistAgent()
        sample_logs = "Fatal error occurred"

        with patch.object(agent, "execute", return_value="Analysis result") as mock_execute:
            agent.analyze_pod_logs(sample_logs, pod_name="neo4j-0", namespace="bunker")

            # Verify the task includes pod context
            call_args = mock_execute.call_args[0]
            task = call_args[0]
            assert "neo4j-0" in task
            assert "bunker" in task

    def test_handles_analysis_exception(self):
        """Exceptions during analysis are caught and returned as error message."""
        agent = SpecialistAgent()
        sample_logs = "Some error logs"

        with patch.object(agent, "execute", side_effect=Exception("LLM timeout")):
            result = agent.analyze_pod_logs(sample_logs)

            assert "Falha na análise" in result
            assert "LLM timeout" in result

    def test_allows_custom_chunk_type(self):
        """Custom chunk_type can be specified for specialized analysis."""
        agent = SpecialistAgent()
        sample_logs = "n8n workflow error"

        with patch.object(agent, "execute", return_value="n8n analysis") as mock_execute:
            agent.analyze_pod_logs(sample_logs, chunk_type="n8n_master_context")

            call_kwargs = mock_execute.call_args[1]
            assert call_kwargs.get("chunk_type") == "n8n_master_context"

    def test_truncates_long_logs(self):
        """Very long logs are truncated to 4000 characters."""
        agent = SpecialistAgent()
        long_logs = "Error line\n" * 1000  # Much longer than 4000 chars

        with patch.object(agent, "execute", return_value="Analysis") as mock_execute:
            agent.analyze_pod_logs(long_logs)

            call_args = mock_execute.call_args[0]
            task = call_args[0]
            # The logs in the task should be truncated
            assert len(task) < len(long_logs) + 1000  # Some overhead for prompt text
