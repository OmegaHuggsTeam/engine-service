"""
Tests for n8n Workflow Extractor, Knowledge Synthesizer, and Flow Validator.

Uses synthetic n8n workflow JSONs in tmp_path fixtures.
No real n8n instance or API calls needed.
"""

import json
from pathlib import Path

import pytest
import yaml

from src.extractors.n8n_extractor import (
    is_n8n_workflow,
    extract_operation_modules,
    extract_all_workflows,
    get_integration_pairs,
    get_node_type_pairs,
    build_reference_index,
    _extract_service_name,
    _get_node_connections,
)
from src.processors.n8n_knowledge import (
    synthesize_capabilities,
    generate_capabilities_md,
    classify_workflow,
    generate_recipes_md,
    generate_master_context,
)
from src.processors.n8n_validator import (
    N8nFlowValidator,
    ValidationResult,
)


# ==================================================================
# Fixtures
# ==================================================================


MINIMAL_WORKFLOW = {
    "nodes": [
        {
            "name": "Webhook",
            "type": "n8n-nodes-base.webhook",
            "typeVersion": 2.1,
            "parameters": {"path": "hook", "httpMethod": "POST"},
            "position": [0, 0],
            "id": "aaa",
        },
        {
            "name": "Google Sheets",
            "type": "n8n-nodes-base.googleSheets",
            "typeVersion": 4.7,
            "parameters": {"operation": "appendOrUpdate", "documentId": "doc123"},
            "position": [200, 0],
            "id": "bbb",
            "credentials": {"googleSheetsOAuth2Api": {"id": "x", "name": "GSheets"}},
        },
    ],
    "connections": {
        "Webhook": {
            "main": [[{"node": "Google Sheets", "type": "main", "index": 0}]]
        }
    },
}

AI_WORKFLOW = {
    "name": "AI Agent Flow",
    "nodes": [
        {
            "name": "Chat Trigger",
            "type": "@n8n/n8n-nodes-langchain.chatTrigger",
            "typeVersion": 1.3,
            "parameters": {"options": {}},
            "position": [0, 0],
            "id": "c1",
        },
        {
            "name": "AI Agent",
            "type": "@n8n/n8n-nodes-langchain.agent",
            "typeVersion": 2.2,
            "parameters": {"promptType": "define", "text": "hello"},
            "position": [200, 0],
            "id": "c2",
        },
        {
            "name": "Groq Model",
            "type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "typeVersion": 1,
            "parameters": {"model": "llama-3.3-70b-versatile"},
            "position": [200, 200],
            "id": "c3",
            "credentials": {"groqApi": {"id": "g1", "name": "Groq"}},
        },
        {
            "name": "Sticky Note",
            "type": "n8n-nodes-base.stickyNote",
            "typeVersion": 1,
            "parameters": {"content": "nota"},
            "position": [0, 200],
            "id": "c4",
        },
    ],
    "connections": {
        "Chat Trigger": {
            "main": [[{"node": "AI Agent", "type": "main", "index": 0}]]
        },
        "Groq Model": {
            "ai_languageModel": [[{"node": "AI Agent", "type": "ai_languageModel", "index": 0}]]
        },
    },
}


@pytest.fixture
def workflow_file(tmp_path):
    """Write minimal n8n workflow to a temp file."""
    p = tmp_path / "test_flow.json"
    p.write_text(json.dumps(MINIMAL_WORKFLOW), encoding="utf-8")
    return p


@pytest.fixture
def ai_workflow_file(tmp_path):
    """Write AI agent workflow to a temp file."""
    p = tmp_path / "ai_flow.json"
    p.write_text(json.dumps(AI_WORKFLOW), encoding="utf-8")
    return p


@pytest.fixture
def workflows_dir(tmp_path):
    """Directory with multiple workflow files."""
    (tmp_path / "flow1.json").write_text(json.dumps(MINIMAL_WORKFLOW), encoding="utf-8")
    (tmp_path / "flow2.json").write_text(json.dumps(AI_WORKFLOW), encoding="utf-8")
    # A non-workflow JSON that should be skipped
    (tmp_path / "config.json").write_text(json.dumps({"key": "value"}), encoding="utf-8")
    # A macOS resource fork that should be skipped
    (tmp_path / "._hidden.json").write_text(json.dumps(MINIMAL_WORKFLOW), encoding="utf-8")
    return tmp_path


@pytest.fixture
def reference_modules(workflows_dir):
    """Extract modules from the test workflows dir."""
    return extract_all_workflows(workflows_dir)


# ==================================================================
# TestIsN8nWorkflow
# ==================================================================


class TestIsN8nWorkflow:
    """Tests for is_n8n_workflow() detection."""

    def test_valid_workflow(self, workflow_file):
        assert is_n8n_workflow(workflow_file) is True

    def test_not_json_extension(self, tmp_path):
        p = tmp_path / "flow.txt"
        p.write_text(json.dumps(MINIMAL_WORKFLOW))
        assert is_n8n_workflow(p) is False

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid json")
        assert is_n8n_workflow(p) is False

    def test_json_without_nodes(self, tmp_path):
        p = tmp_path / "config.json"
        p.write_text(json.dumps({"key": "value"}))
        assert is_n8n_workflow(p) is False

    def test_empty_nodes_list(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text(json.dumps({"nodes": [], "connections": {}}))
        assert is_n8n_workflow(p) is False

    def test_nodes_without_type(self, tmp_path):
        p = tmp_path / "notype.json"
        p.write_text(json.dumps({"nodes": [{"name": "X"}], "connections": {}}))
        assert is_n8n_workflow(p) is False

    def test_nonexistent_file(self, tmp_path):
        assert is_n8n_workflow(tmp_path / "ghost.json") is False


# ==================================================================
# TestExtractServiceName
# ==================================================================


class TestExtractServiceName:
    """Tests for _extract_service_name() helper."""

    def test_google_sheets(self):
        assert _extract_service_name("n8n-nodes-base.googleSheets") == "Google Sheets"

    def test_webhook(self):
        assert _extract_service_name("n8n-nodes-base.webhook") == "Webhook"

    def test_groq_model(self):
        assert _extract_service_name("@n8n/n8n-nodes-langchain.lmChatGroq") == "Groq"

    def test_http_request(self):
        assert _extract_service_name("n8n-nodes-base.httpRequest") == "HTTP Request"

    def test_custom_node(self):
        """Unknown nodes get title-cased."""
        name = _extract_service_name("@custom/plugin.myCustomTool")
        assert isinstance(name, str)
        assert len(name) > 0


# ==================================================================
# TestGetNodeConnections
# ==================================================================


class TestGetNodeConnections:
    """Tests for _get_node_connections() helper."""

    def test_outputs(self):
        conns = _get_node_connections("Webhook", MINIMAL_WORKFLOW["connections"])
        assert "Google Sheets" in conns["outputs"]

    def test_inputs_from(self):
        conns = _get_node_connections("Google Sheets", MINIMAL_WORKFLOW["connections"])
        assert "Webhook" in conns["inputs_from"]

    def test_isolated_node(self):
        conns = _get_node_connections("NonExistent", MINIMAL_WORKFLOW["connections"])
        assert conns["outputs"] == []
        assert conns["inputs_from"] == []

    def test_ai_model_connection(self):
        """ai_languageModel connections are captured."""
        conns = _get_node_connections("Groq Model", AI_WORKFLOW["connections"])
        assert "AI Agent" in conns["outputs"]


# ==================================================================
# TestExtractOperationModules
# ==================================================================


class TestExtractOperationModules:
    """Tests for extract_operation_modules()."""

    def test_returns_modules(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        assert len(modules) == 2  # Webhook + Google Sheets

    def test_module_structure(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        m = modules[0]
        assert "node_name" in m
        assert "node_type" in m
        assert "service" in m
        assert "parameters" in m
        assert "connections" in m
        assert "content" in m
        assert "source_file" in m
        assert m["category"] == "n8n_workflow"
        assert m["agent_specialty"] == "automation"

    def test_skips_sticky_notes(self, ai_workflow_file):
        modules = extract_operation_modules(ai_workflow_file)
        names = [m["node_name"] for m in modules]
        assert "Sticky Note" not in names

    def test_content_is_descriptive(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        webhook_mod = [m for m in modules if m["node_name"] == "Webhook"][0]
        assert "n8n Node: Webhook" in webhook_mod["content"]
        assert "Webhook" in webhook_mod["content"]

    def test_connections_captured(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        webhook_mod = [m for m in modules if m["node_name"] == "Webhook"][0]
        assert "Google Sheets" in webhook_mod["connections"]["outputs"]

    def test_credentials_extracted(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        sheets_mod = [m for m in modules if m["node_name"] == "Google Sheets"][0]
        assert "googleSheetsOAuth2Api" in sheets_mod["credential_types"]

    def test_invalid_file_raises(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text('{"key": "value"}')
        with pytest.raises(ValueError, match="nao e um fluxo n8n"):
            extract_operation_modules(p)

    def test_chunk_index_sequential(self, ai_workflow_file):
        modules = extract_operation_modules(ai_workflow_file)
        indices = [m["chunk_index"] for m in modules]
        assert indices == list(range(len(modules)))


# ==================================================================
# TestExtractAllWorkflows
# ==================================================================


class TestExtractAllWorkflows:
    """Tests for extract_all_workflows() directory scanner."""

    def test_finds_all_valid_workflows(self, workflows_dir):
        modules = extract_all_workflows(workflows_dir)
        # flow1 (2 nodes) + flow2 (3 nodes, sticky excluded) = 5
        assert len(modules) == 5

    def test_skips_non_workflow_json(self, workflows_dir):
        modules = extract_all_workflows(workflows_dir)
        sources = {m["source_file"] for m in modules}
        assert not any("config" in s for s in sources)

    def test_skips_macos_forks(self, workflows_dir):
        modules = extract_all_workflows(workflows_dir)
        sources = {m["source_file"] for m in modules}
        assert not any("._hidden" in s for s in sources)

    def test_empty_dir(self, tmp_path):
        modules = extract_all_workflows(tmp_path)
        assert modules == []


# ==================================================================
# TestGetIntegrationPairs
# ==================================================================


class TestGetIntegrationPairs:
    """Tests for get_integration_pairs()."""

    def test_finds_webhook_to_sheets(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        pairs = get_integration_pairs(modules)
        services_in_pairs = [(a, b) for a, b, _ in pairs]
        assert ("Webhook", "Google Sheets") in services_in_pairs

    def test_no_self_pairs(self, reference_modules):
        pairs = get_integration_pairs(reference_modules)
        for a, b, _ in pairs:
            assert a != b

    def test_deduplicates(self, workflow_file):
        modules = extract_operation_modules(workflow_file)
        # Duplicate the modules
        pairs = get_integration_pairs(modules + modules)
        # Should not have duplicates for same workflow
        assert len(pairs) == len(set((a, b, w) for a, b, w in pairs))


# ==================================================================
# TestBuildReferenceIndex
# ==================================================================


class TestBuildReferenceIndex:
    """Tests for build_reference_index()."""

    def test_index_structure(self, reference_modules):
        index = build_reference_index(reference_modules)
        assert "n8n-nodes-base.webhook" in index
        entry = index["n8n-nodes-base.webhook"]
        assert "parameter_keys" in entry
        assert "type_versions" in entry
        assert "credential_types" in entry

    def test_parameter_keys_collected(self, reference_modules):
        index = build_reference_index(reference_modules)
        webhook_params = index["n8n-nodes-base.webhook"]["parameter_keys"]
        assert "path" in webhook_params

    def test_versions_collected(self, reference_modules):
        index = build_reference_index(reference_modules)
        versions = index["n8n-nodes-base.webhook"]["type_versions"]
        assert 2.1 in versions

    def test_empty_modules(self):
        index = build_reference_index([])
        assert index == {}


# ==================================================================
# TestSynthesizeCapabilities
# ==================================================================


class TestSynthesizeCapabilities:
    """Tests for synthesize_capabilities()."""

    def test_returns_expected_keys(self, reference_modules):
        caps = synthesize_capabilities(reference_modules)
        assert "integrations" in caps
        assert "services" in caps
        assert "node_types" in caps
        assert "credentials" in caps

    def test_services_counted(self, reference_modules):
        caps = synthesize_capabilities(reference_modules)
        assert len(caps["services"]) > 0
        # Webhook should be present
        assert "Webhook" in caps["services"]

    def test_integrations_found(self, reference_modules):
        caps = synthesize_capabilities(reference_modules)
        assert len(caps["integrations"]) > 0

    def test_credentials_mapped(self, reference_modules):
        caps = synthesize_capabilities(reference_modules)
        # Google Sheets cred should be present
        assert "googleSheetsOAuth2Api" in caps["credentials"]


# ==================================================================
# TestGenerateCapabilitiesMd
# ==================================================================


class TestGenerateCapabilitiesMd:
    """Tests for generate_capabilities_md()."""

    def test_file_created(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        result = generate_capabilities_md(reference_modules, vault_path=vault)
        assert Path(result).exists()
        assert result.endswith("n8n_capabilities.md")

    def test_has_frontmatter(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_capabilities_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_capabilities.md").read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_block = content.split("---\n")[1]
        fm = yaml.safe_load(fm_block)
        assert "knowledge" in fm["tags"]
        assert "n8n" in fm["tags"]
        assert fm["total_modules"] == len(reference_modules)

    def test_contains_integration_sentences(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_capabilities_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_capabilities.md").read_text(encoding="utf-8")
        assert "O n8n neste bunker sabe conectar" in content

    def test_contains_services_table(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_capabilities_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_capabilities.md").read_text(encoding="utf-8")
        assert "Servicos Disponiveis" in content
        assert "| Servico |" in content

    def test_contains_node_types(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_capabilities_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_capabilities.md").read_text(encoding="utf-8")
        assert "Node Types de Referencia" in content
        assert "n8n-nodes-base.webhook" in content

    def test_contains_obsidian_links(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_capabilities_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_capabilities.md").read_text(encoding="utf-8")
        assert "[[Dashboard]]" in content


# ==================================================================
# TestN8nFlowValidator
# ==================================================================


class TestN8nFlowValidator:
    """Tests for N8nFlowValidator."""

    def test_from_modules(self, reference_modules):
        v = N8nFlowValidator.from_modules(reference_modules)
        assert "n8n-nodes-base.webhook" in v.known_node_types

    def test_valid_flow(self, reference_modules, workflow_file):
        """A flow using only known nodes/params passes validation."""
        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(workflow_file)
        assert result.valid is True
        assert result.nodes_checked == 2
        assert result.nodes_known == 2
        assert result.nodes_unknown == 0

    def test_unknown_node_type_warning(self, reference_modules, tmp_path):
        """Flow with unknown node type produces a warning."""
        flow = {
            "nodes": [{
                "name": "Slack Post",
                "type": "n8n-nodes-base.slack",
                "typeVersion": 2,
                "parameters": {"channel": "#general"},
            }],
            "connections": {},
        }
        p = tmp_path / "unknown.json"
        p.write_text(json.dumps(flow), encoding="utf-8")

        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(p)
        # Unknown nodes are warnings, not errors
        assert result.valid is True
        assert result.nodes_unknown == 1
        assert len(result.warnings) >= 1
        assert "desconhecido" in result.warnings[0].message

    def test_unknown_parameter_warning(self, reference_modules, tmp_path):
        """Flow with unknown parameter key produces a warning."""
        flow = {
            "nodes": [{
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 2.1,
                "parameters": {"path": "hook", "unknownParam": True},
            }],
            "connections": {},
        }
        p = tmp_path / "badparam.json"
        p.write_text(json.dumps(flow), encoding="utf-8")

        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(p)
        assert any("unknownParam" in w.message for w in result.warnings)

    def test_unknown_version_warning(self, reference_modules, tmp_path):
        """Flow with unseen typeVersion produces a warning."""
        flow = {
            "nodes": [{
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "typeVersion": 99.0,
                "parameters": {"path": "test"},
            }],
            "connections": {},
        }
        p = tmp_path / "newversion.json"
        p.write_text(json.dumps(flow), encoding="utf-8")

        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(p)
        assert any("typeVersion" in w.message for w in result.warnings)

    def test_invalid_file_error(self, reference_modules, tmp_path):
        """Non-workflow file produces an error."""
        p = tmp_path / "bad.json"
        p.write_text('{"key": "value"}')

        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(p)
        assert result.valid is False
        assert len(result.errors) == 1

    def test_summary_output(self, reference_modules, workflow_file):
        """summary() returns human-readable string."""
        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(workflow_file)
        s = result.summary()
        assert "VALIDO" in s
        assert "Nodes:" in s

    def test_validate_json_string(self, reference_modules):
        """validate_json_string() works with raw JSON."""
        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate_json_string(json.dumps(MINIMAL_WORKFLOW))
        assert result.valid is True
        assert result.nodes_checked == 2

    def test_skips_sticky_notes(self, reference_modules, ai_workflow_file):
        """Sticky notes are not counted in validation."""
        v = N8nFlowValidator.from_modules(reference_modules)
        result = v.validate(ai_workflow_file)
        names_checked = [i.node_name for i in result.issues]
        assert "Sticky Note" not in names_checked

    def test_empty_reference_warns_all(self, workflow_file):
        """Validator with empty reference index warns on all nodes."""
        v = N8nFlowValidator(reference_index={})
        result = v.validate(workflow_file)
        assert result.nodes_unknown == 2
        assert len(result.warnings) == 2


# ==================================================================
# TestGetNodeTypePairs
# ==================================================================


class TestGetNodeTypePairs:
    """Tests for get_node_type_pairs()."""

    def test_minimal_workflow_pair(self, workflow_file):
        """Webhook -> GoogleSheets = 1 pair."""
        modules = extract_operation_modules(workflow_file)
        pairs = get_node_type_pairs(modules)
        assert len(pairs) == 1
        src, tgt, count = pairs[0]
        assert src == "n8n-nodes-base.webhook"
        assert tgt == "n8n-nodes-base.googleSheets"
        assert count == 1

    def test_ai_workflow_pairs(self, ai_workflow_file):
        """ChatTrigger->Agent + Groq->Agent = 2 pairs."""
        modules = extract_operation_modules(ai_workflow_file)
        pairs = get_node_type_pairs(modules)
        pair_set = {(s, t) for s, t, _ in pairs}
        assert ("@n8n/n8n-nodes-langchain.chatTrigger", "@n8n/n8n-nodes-langchain.agent") in pair_set
        assert ("@n8n/n8n-nodes-langchain.lmChatGroq", "@n8n/n8n-nodes-langchain.agent") in pair_set
        assert len(pairs) == 2

    def test_count_across_workflows(self, workflows_dir):
        """Same pair in 2 workflows -> count accumulates."""
        # Write the same workflow twice under different names
        wf = json.dumps(MINIMAL_WORKFLOW)
        (workflows_dir / "dup1.json").write_text(wf, encoding="utf-8")
        (workflows_dir / "dup2.json").write_text(wf, encoding="utf-8")
        modules = extract_all_workflows(workflows_dir)
        pairs = get_node_type_pairs(modules)
        webhook_sheets = [
            (s, t, c) for s, t, c in pairs
            if s == "n8n-nodes-base.webhook" and t == "n8n-nodes-base.googleSheets"
        ]
        assert len(webhook_sheets) == 1
        assert webhook_sheets[0][2] >= 2

    def test_empty_modules(self):
        """Returns empty list for no modules."""
        assert get_node_type_pairs([]) == []

    def test_skips_unknown_targets(self, workflow_file):
        """Target not in modules -> skipped gracefully."""
        modules = extract_operation_modules(workflow_file)
        # Inject a fake output target that doesn't exist in modules
        modules[0]["connections"]["outputs"].append("GhostNode")
        pairs = get_node_type_pairs(modules)
        # Should still only find the real pair
        assert all(t != "GhostNode" for _, t, _ in pairs)


# ==================================================================
# TestClassifyWorkflow
# ==================================================================


class TestClassifyWorkflow:
    """Tests for classify_workflow()."""

    def test_ai_llm_category(self):
        """Langchain nodes -> AI / LLM."""
        modules = [
            {"node_type": "@n8n/n8n-nodes-langchain.chatTrigger"},
            {"node_type": "@n8n/n8n-nodes-langchain.agent"},
        ]
        assert classify_workflow(modules) == "AI / LLM"

    def test_communication_category(self):
        """Telegram/WhatsApp -> Communication."""
        modules = [
            {"node_type": "n8n-nodes-base.telegram"},
            {"node_type": "n8n-nodes-base.set"},
        ]
        assert classify_workflow(modules) == "Communication"

    def test_marketing_category(self):
        """GoogleSheets + HTTP -> Marketing."""
        modules = [
            {"node_type": "n8n-nodes-base.googleSheets"},
            {"node_type": "n8n-nodes-base.httpRequest"},
        ]
        assert classify_workflow(modules) == "Marketing"

    def test_devops_category(self):
        """ExecuteCommand/SSH -> DevOps."""
        modules = [
            {"node_type": "n8n-nodes-base.executeCommand"},
            {"node_type": "n8n-nodes-base.set"},
        ]
        assert classify_workflow(modules) == "DevOps"

    def test_default_fallback(self):
        """Unknown nodes -> General Automation."""
        modules = [
            {"node_type": "n8n-nodes-base.set"},
            {"node_type": "n8n-nodes-base.merge"},
        ]
        assert classify_workflow(modules) == "General Automation"

    def test_priority_order(self):
        """AI takes priority over Communication when both present."""
        modules = [
            {"node_type": "@n8n/n8n-nodes-langchain.agent"},
            {"node_type": "n8n-nodes-base.telegram"},
        ]
        assert classify_workflow(modules) == "AI / LLM"


# ==================================================================
# TestGenerateRecipesMd
# ==================================================================


class TestGenerateRecipesMd:
    """Tests for generate_recipes_md()."""

    def test_file_created(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        result = generate_recipes_md(reference_modules, vault_path=vault)
        assert Path(result).exists()
        assert result.endswith("n8n_recipes.md")

    def test_has_frontmatter(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_recipes_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_recipes.md").read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_block = content.split("---\n")[1]
        fm = yaml.safe_load(fm_block)
        assert "recipes" in fm["tags"]
        assert fm["total_workflows"] > 0
        assert isinstance(fm["categories"], list)

    def test_groups_by_category(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_recipes_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_recipes.md").read_text(encoding="utf-8")
        # At least one category heading should exist
        assert "## " in content

    def test_shows_node_chain(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_recipes_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_recipes.md").read_text(encoding="utf-8")
        assert "**Fluxo:**" in content
        assert " -> " in content

    def test_shows_credentials(self, reference_modules, tmp_path):
        vault = tmp_path / "vault"
        generate_recipes_md(reference_modules, vault_path=vault)
        content = (vault / "Knowledge" / "n8n_recipes.md").read_text(encoding="utf-8")
        assert "**Credenciais:**" in content


# ==================================================================
# TestGenerateMasterContext
# ==================================================================


class TestGenerateMasterContext:
    """Tests for generate_master_context()."""

    def test_file_created(self, reference_modules, tmp_path):
        out_dir = tmp_path / "chunks"
        result = generate_master_context(reference_modules, output_dir=out_dir)
        assert Path(result).exists()
        assert result.endswith("n8n_master_context.json")

    def test_valid_json_array(self, reference_modules, tmp_path):
        out_dir = tmp_path / "chunks"
        generate_master_context(reference_modules, output_dir=out_dir)
        data = json.loads((out_dir / "n8n_master_context.json").read_text(encoding="utf-8"))
        assert isinstance(data, list)
        assert len(data) > 0

    def test_chunk_fields(self, reference_modules, tmp_path):
        out_dir = tmp_path / "chunks"
        generate_master_context(reference_modules, output_dir=out_dir)
        data = json.loads((out_dir / "n8n_master_context.json").read_text(encoding="utf-8"))
        for chunk in data:
            assert "content" in chunk
            assert "category" in chunk
            assert "agent_specialty" in chunk
            assert "source_file" in chunk
            assert "chunk_index" in chunk

    def test_category_matches(self, reference_modules, tmp_path):
        out_dir = tmp_path / "chunks"
        generate_master_context(reference_modules, output_dir=out_dir)
        data = json.loads((out_dir / "n8n_master_context.json").read_text(encoding="utf-8"))
        for chunk in data:
            assert chunk["category"] == "n8n_master_context"

    def test_contains_global_patterns(self, reference_modules, tmp_path):
        out_dir = tmp_path / "chunks"
        generate_master_context(reference_modules, output_dir=out_dir)
        data = json.loads((out_dir / "n8n_master_context.json").read_text(encoding="utf-8"))
        last_chunk = data[-1]
        assert "Padroes Globais" in last_chunk["content"]
