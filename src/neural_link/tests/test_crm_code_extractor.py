"""
Tests for CRM Code Extractor — detection and extraction functions.

All file operations use tempfile — no external dependencies required.
Follows test_graph_sync.py conventions.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.crm_code_extractor import (
    is_express_route,
    is_react_component,
    is_typescript_service,
    is_data_model,
    is_kafka_worker,
    extract_express_routes,
    extract_react_components,
    extract_typescript_services,
    extract_data_models,
    extract_kafka_workers,
    detect_and_extract,
    _infer_domain,
    _infer_language,
    _extract_route_info,
    _extract_component_info,
    _extract_model_fields,
    _extract_kafka_info,
    sync_crm_modules_to_graph,
)


# ==================================================================
# Helpers
# ==================================================================


def _write_temp(content: str, suffix: str = ".ts") -> Path:
    """Write content to a temp file and return its Path."""
    f = tempfile.NamedTemporaryFile(
        mode="w", suffix=suffix, delete=False, encoding="utf-8"
    )
    f.write(content)
    f.close()
    return Path(f.name)


EXPRESS_CONTENT = """\
import express from 'express';
const router = express.Router();

router.get('/campaigns', authMiddleware, async (req, res) => {
  const campaigns = await CampaignService.list();
  res.json(campaigns);
});

router.post('/campaigns', async (req, res) => {
  const campaign = await CampaignService.create(req.body);
  res.json(campaign);
});

router.delete('/campaigns/:id', async (req, res) => {
  await CampaignService.remove(req.params.id);
  res.sendStatus(204);
});

module.exports = router;
"""

REACT_CONTENT = """\
import React, { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';

interface CampaignListProps {
  orgId: string;
  limit?: number;
}

export default function CampaignList({ orgId, limit }: CampaignListProps) {
  const [campaigns, setCampaigns] = useState([]);
  useEffect(() => {
    fetch(`/api/campaigns?org=${orgId}`).then(r => r.json()).then(setCampaigns);
  }, [orgId]);

  return <CampaignTable data={campaigns} />;
}
"""

SERVICE_CONTENT = """\
export class CampaignService {
  constructor(private db: Database) {}

  async listCampaigns() {
    return this.db.query('SELECT * FROM campaigns');
  }

  async createCampaign(data: any) {
    return this.db.insert('campaigns', data);
  }
}
"""

MODEL_CONTENT = """\
export interface Campaign {
  id: string;
  name: string;
  status?: string;
  createdAt: Date;
}

export type CampaignInput = {
  name: string;
  template?: string;
}
"""

KAFKA_CONTENT = """\
import { KafkaConsumer } from './kafka';

const consumer = new KafkaConsumer({
  groupId: 'segment-workers',
});

consumer.subscribe({ topic: 'user-events' });
consumer.subscribe({ topic: 'campaign-triggers' });

consumer.on('message', async (msg) => {
  await processEvent(msg);
});
"""


# ==================================================================
# TestFileDetection
# ==================================================================


class TestFileDetection:
    """is_* detection functions."""

    def test_express_route_detected(self):
        p = _write_temp(EXPRESS_CONTENT, suffix=".ts")
        assert is_express_route(p) is True

    def test_express_not_detected_for_tsx(self):
        """Express routes require .js or .ts, not .tsx."""
        p = _write_temp(EXPRESS_CONTENT, suffix=".tsx")
        assert is_express_route(p) is False

    def test_react_component_detected(self):
        p = _write_temp(REACT_CONTENT, suffix=".tsx")
        assert is_react_component(p) is True

    def test_react_not_detected_for_ts(self):
        """React components require .tsx or .jsx."""
        p = _write_temp(REACT_CONTENT, suffix=".ts")
        assert is_react_component(p) is False

    def test_typescript_service_detected(self):
        p = _write_temp(SERVICE_CONTENT, suffix=".ts")
        assert is_typescript_service(p) is True

    def test_data_model_detected(self):
        p = _write_temp(MODEL_CONTENT, suffix=".ts")
        assert is_data_model(p) is True

    def test_kafka_worker_detected(self):
        p = _write_temp(KAFKA_CONTENT, suffix=".ts")
        assert is_kafka_worker(p) is True

    def test_kafka_not_detected_single_pattern(self):
        """Kafka requires >= 2 pattern matches; one match is not enough."""
        p = _write_temp("const kafka = require('kafka');", suffix=".ts")
        # Only _KAFKA_PATTERNS[0] matches "kafka" => 1 match, need >= 2
        assert is_kafka_worker(p) is False

    def test_empty_file_not_detected(self):
        p = _write_temp("", suffix=".ts")
        assert is_express_route(p) is False
        assert is_react_component(p) is False
        assert is_typescript_service(p) is False
        assert is_data_model(p) is False
        assert is_kafka_worker(p) is False

    def test_wrong_extension_rejected(self):
        """Python files are never detected."""
        p = _write_temp(EXPRESS_CONTENT, suffix=".py")
        assert is_express_route(p) is False
        assert is_typescript_service(p) is False
        assert is_data_model(p) is False
        assert is_kafka_worker(p) is False


# ==================================================================
# TestExtraction
# ==================================================================


class TestExtraction:
    """extract_* functions produce correct chunks."""

    def test_extract_express_routes_count(self):
        p = _write_temp(EXPRESS_CONTENT, suffix=".ts")
        chunks = extract_express_routes(p)
        assert len(chunks) == 3  # GET, POST, DELETE

    def test_extract_express_routes_fields(self):
        p = _write_temp(EXPRESS_CONTENT, suffix=".ts")
        chunks = extract_express_routes(p)
        first = chunks[0]
        assert first["category"] == "crm_backend"
        assert first["module_type"] == "route"
        assert first["route_method"] == "GET"
        assert first["route_path"] == "/campaigns"
        assert "content" in first
        assert first["language"] == "typescript"

    def test_extract_react_components_fields(self):
        p = _write_temp(REACT_CONTENT, suffix=".tsx")
        chunks = extract_react_components(p)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk["category"] == "crm_frontend"
        assert chunk["module_type"] == "component"
        assert chunk["component_name"] == "CampaignList"
        assert chunk["language"] == "tsx"

    def test_extract_typescript_services_fields(self):
        p = _write_temp(SERVICE_CONTENT, suffix=".ts")
        chunks = extract_typescript_services(p)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk["category"] == "crm_service"
        assert chunk["module_type"] == "service"
        assert chunk["service_name"] == "CampaignService"

    def test_extract_data_models_fields(self):
        p = _write_temp(MODEL_CONTENT, suffix=".ts")
        chunks = extract_data_models(p)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk["category"] == "crm_model"
        assert chunk["module_type"] == "model"
        assert chunk["agent_specialty"] == "crm_data"
        assert int(chunk["field_count"]) >= 4

    def test_extract_kafka_workers_fields(self):
        p = _write_temp(KAFKA_CONTENT, suffix=".ts")
        chunks = extract_kafka_workers(p)
        assert len(chunks) == 1
        chunk = chunks[0]
        assert chunk["category"] == "crm_data_pipeline"
        assert chunk["module_type"] == "kafka_worker"
        assert chunk["kafka_type"] == "consumer"
        topics = json.loads(chunk["kafka_topics"])
        assert "user-events" in topics
        assert "campaign-triggers" in topics


# ==================================================================
# TestDetectAndExtract
# ==================================================================


class TestDetectAndExtract:
    """detect_and_extract auto-routing."""

    def test_routes_to_kafka(self):
        """Kafka has highest priority in detection order."""
        p = _write_temp(KAFKA_CONTENT, suffix=".ts")
        chunks = detect_and_extract(p)
        assert len(chunks) >= 1
        assert chunks[0]["module_type"] == "kafka_worker"

    def test_routes_to_express(self):
        p = _write_temp(EXPRESS_CONTENT, suffix=".ts")
        chunks = detect_and_extract(p)
        assert len(chunks) >= 1
        assert chunks[0]["module_type"] == "route"

    def test_routes_to_react(self):
        p = _write_temp(REACT_CONTENT, suffix=".tsx")
        chunks = detect_and_extract(p)
        assert len(chunks) == 1
        assert chunks[0]["module_type"] == "component"

    def test_skips_non_code_extensions(self):
        p = _write_temp("some content", suffix=".py")
        assert detect_and_extract(p) == []

    def test_skips_config_files(self):
        """Config files like tsconfig.json are skipped."""
        d = tempfile.mkdtemp()
        config = Path(d) / "tsconfig.json"
        config.write_text('{"compilerOptions": {}}', encoding="utf-8")
        assert detect_and_extract(config) == []

    def test_skips_node_modules(self):
        """Files inside node_modules are skipped."""
        d = tempfile.mkdtemp()
        nm = Path(d) / "node_modules" / "lib"
        nm.mkdir(parents=True)
        f = nm / "index.ts"
        f.write_text(EXPRESS_CONTENT, encoding="utf-8")
        assert detect_and_extract(f) == []


# ==================================================================
# TestInferDomain
# ==================================================================


class TestInferDomain:
    """_infer_domain maps paths and content to CRM domains."""

    def test_campaign_path(self):
        assert _infer_domain("src/campaigns/controller.ts") == "campaigns"

    def test_journey_path(self):
        assert _infer_domain("src/journey-builder/flow.ts") == "journeys"

    def test_segment_path(self):
        assert _infer_domain("services/segment-engine/worker.ts") == "segments"

    def test_tracker_path(self):
        assert _infer_domain("tracker/event-collector.ts") == "tracker"

    def test_integration_path(self):
        assert _infer_domain("adapters/sms-integration.ts") == "integrations"

    def test_analytics_path(self):
        assert _infer_domain("analytics/clickhouse-query.ts") == "analytics"

    def test_auth_path(self):
        assert _infer_domain("auth/jwt-verify.ts") == "auth"

    def test_unknown_path_returns_general(self):
        assert _infer_domain("lib/utils/helpers.ts") == "general"

    def test_content_based_inference(self):
        """When path is generic, content first 500 chars are checked."""
        assert _infer_domain("src/service.ts", "import { CampaignModel }") == "campaigns"


# ==================================================================
# TestInferLanguage
# ==================================================================


class TestInferLanguage:
    """_infer_language returns correct language for file suffix."""

    def test_tsx(self):
        assert _infer_language("file.tsx") == "tsx"

    def test_ts(self):
        assert _infer_language("file.ts") == "typescript"

    def test_jsx(self):
        assert _infer_language("file.jsx") == "jsx"

    def test_js(self):
        assert _infer_language("file.js") == "javascript"

    def test_unknown(self):
        assert _infer_language("file.py") == "unknown"


# ==================================================================
# TestHelperExtractors
# ==================================================================


class TestHelperExtractors:
    """Internal _extract_* helper functions."""

    def test_extract_route_info(self):
        routes = _extract_route_info(EXPRESS_CONTENT)
        assert len(routes) == 3
        methods = [r["method"] for r in routes]
        assert "GET" in methods
        assert "POST" in methods
        assert "DELETE" in methods

    def test_extract_route_info_with_middleware(self):
        routes = _extract_route_info(EXPRESS_CONTENT)
        get_route = [r for r in routes if r["method"] == "GET"][0]
        assert get_route["middleware"] == "authMiddleware"

    def test_extract_component_info_hooks(self):
        info = _extract_component_info(REACT_CONTENT)
        assert "useState" in info["hooks"]
        assert "useEffect" in info["hooks"]

    def test_extract_component_info_props(self):
        info = _extract_component_info(REACT_CONTENT)
        assert "orgId" in info["props"]
        assert "limit" in info["props"]

    def test_extract_model_fields(self):
        fields = _extract_model_fields(MODEL_CONTENT)
        names = [f["name"] for f in fields]
        assert "id" in names
        assert "name" in names
        assert "status" in names
        # status is optional
        optional_fields = [f for f in fields if f["name"] == "status"]
        assert optional_fields[0]["optional"] is True

    def test_extract_kafka_info_topics(self):
        info = _extract_kafka_info(KAFKA_CONTENT)
        assert "user-events" in info["topics"]
        assert "campaign-triggers" in info["topics"]

    def test_extract_kafka_info_type(self):
        info = _extract_kafka_info(KAFKA_CONTENT)
        assert info["type"] == "consumer"

    def test_extract_kafka_info_group_id(self):
        info = _extract_kafka_info(KAFKA_CONTENT)
        assert info["group_id"] == "segment-workers"


# ==================================================================
# TestSyncCrmModulesToGraph
# ==================================================================


class TestSyncCrmModulesToGraph:
    """sync_crm_modules_to_graph with mocked Neo4j."""

    def test_sync_creates_modules(self):
        graph = MagicMock()
        graph.verify_connectivity.return_value = True
        graph.execute_write_batch.return_value = 0

        modules = [
            {
                "source_file": "crm/backend/campaign.ts",
                "module_type": "route",
                "domain": "campaigns",
                "content": "Express Route: GET /campaigns",
                "language": "typescript",
                "service_name": "CampaignController",
            },
        ]
        stats = sync_crm_modules_to_graph(modules, graph=graph)
        assert stats["modules_created"] == 1
        graph.execute_write_batch.assert_called_once()

    def test_sync_empty_list(self):
        graph = MagicMock()
        stats = sync_crm_modules_to_graph([], graph=graph)
        assert stats["modules_created"] == 0
        graph.execute_write_batch.assert_not_called()

    def test_sync_batch_error_captured(self):
        graph = MagicMock()
        graph.verify_connectivity.return_value = True
        graph.execute_write_batch.side_effect = RuntimeError("Neo4j down")

        modules = [
            {
                "source_file": "crm/test.ts",
                "module_type": "service",
                "domain": "general",
                "content": "test",
                "language": "typescript",
            },
        ]
        stats = sync_crm_modules_to_graph(modules, graph=graph)
        assert len(stats["errors"]) == 1
        assert "Neo4j down" in stats["errors"][0]
