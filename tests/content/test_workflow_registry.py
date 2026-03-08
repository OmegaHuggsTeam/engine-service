"""Tests for the Workflow Registry CRUD API.

TDD RED phase: tests written before implementation.
Each test uses a fresh FastAPI app + TestClient to avoid shared state.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from src.neural_link.api.workflow_registry import router, _workflow_store


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_app() -> FastAPI:
    """Create a fresh FastAPI app with the workflow registry router."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


def _make_client() -> TestClient:
    """Create a TestClient and reset the in-memory store."""
    _workflow_store.clear()
    return TestClient(_make_app())


def _sample_payload(**overrides) -> dict:
    """Return a valid WorkflowCreateRequest payload with optional overrides."""
    base = {
        "id": f"wp-{uuid.uuid4().hex[:8]}",
        "name": "Weekly Podcast",
        "description": "Automated weekly podcast pipeline.",
        "category": "podcast",
        "n8n_workflow_json": {"nodes": []},
        "config": {"voice": "alloy"},
        "schedule": "0 9 * * MON",
        "agents_used": ["researcher", "scriptwriter"],
        "webhook_urls": ["https://hook.example.com/1"],
        "brand_voice_file": "/voices/brand.json",
        "cost_per_run": 0.50,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Test: Create workflow product
# ---------------------------------------------------------------------------


class TestCreateWorkflowProduct:
    def test_create_workflow_product(self):
        """POST /workflows returns 201 and status defaults to 'draft'."""
        client = _make_client()
        payload = _sample_payload(id="wp-001")

        response = client.post("/api/v1/workflows", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["id"] == "wp-001"
        assert data["name"] == "Weekly Podcast"
        assert data["status"] == "draft"
        assert data["category"] == "podcast"
        assert data["cost_per_run"] == 0.50
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_workflow_defaults(self):
        """POST with minimal fields uses correct defaults."""
        client = _make_client()
        payload = {
            "id": "wp-minimal",
            "name": "Minimal",
            "description": "Bare minimum.",
            "category": "general",
            "n8n_workflow_json": {},
        }

        response = client.post("/api/v1/workflows", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["config"] == {}
        assert data["schedule"] is None
        assert data["agents_used"] == []
        assert data["webhook_urls"] == []
        assert data["brand_voice_file"] is None
        assert data["cost_per_run"] == 0.0

    def test_create_duplicate_id_returns_409(self):
        """POST with an existing ID returns 409 Conflict."""
        client = _make_client()
        payload = _sample_payload(id="wp-dup")

        client.post("/api/v1/workflows", json=payload)
        response = client.post("/api/v1/workflows", json=payload)

        assert response.status_code == 409


# ---------------------------------------------------------------------------
# Test: List workflow products
# ---------------------------------------------------------------------------


class TestListWorkflowProducts:
    def test_list_workflow_products(self):
        """GET /workflows returns list of all workflows."""
        client = _make_client()
        client.post("/api/v1/workflows", json=_sample_payload(id="wp-a"))
        client.post("/api/v1/workflows", json=_sample_payload(id="wp-b"))

        response = client.get("/api/v1/workflows")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

    def test_list_empty(self):
        """GET /workflows returns empty list when no workflows exist."""
        client = _make_client()

        response = client.get("/api/v1/workflows")

        assert response.status_code == 200
        assert response.json() == []

    def test_list_with_category_filter(self):
        """GET /workflows?category=podcast filters by category."""
        client = _make_client()
        client.post(
            "/api/v1/workflows",
            json=_sample_payload(id="wp-pod", category="podcast"),
        )
        client.post(
            "/api/v1/workflows",
            json=_sample_payload(id="wp-car", category="carousel"),
        )

        response = client.get("/api/v1/workflows", params={"category": "podcast"})

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == "wp-pod"


# ---------------------------------------------------------------------------
# Test: Get workflow product by ID
# ---------------------------------------------------------------------------


class TestGetWorkflowProduct:
    def test_get_workflow_product(self):
        """GET /workflows/{id} returns the correct workflow."""
        client = _make_client()
        payload = _sample_payload(id="wp-get")
        client.post("/api/v1/workflows", json=payload)

        response = client.get("/api/v1/workflows/wp-get")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "wp-get"
        assert data["name"] == "Weekly Podcast"

    def test_get_nonexistent_returns_404(self):
        """GET /workflows/{id} returns 404 when workflow does not exist."""
        client = _make_client()

        response = client.get("/api/v1/workflows/wp-nope")

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test: Update workflow product
# ---------------------------------------------------------------------------


class TestUpdateWorkflowProduct:
    def test_update_workflow_product(self):
        """PUT /workflows/{id} partial update only changes provided fields."""
        client = _make_client()
        client.post("/api/v1/workflows", json=_sample_payload(id="wp-upd"))

        response = client.put(
            "/api/v1/workflows/wp-upd",
            json={"name": "Updated Name", "schedule": "0 12 * * FRI"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["schedule"] == "0 12 * * FRI"
        # Unchanged fields remain
        assert data["category"] == "podcast"
        assert data["description"] == "Automated weekly podcast pipeline."

    def test_update_nonexistent_returns_404(self):
        """PUT /workflows/{id} returns 404 when workflow does not exist."""
        client = _make_client()

        response = client.put(
            "/api/v1/workflows/wp-nope",
            json={"name": "Ghost"},
        )

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Delete (soft delete) workflow product
# ---------------------------------------------------------------------------


class TestDeleteWorkflowProduct:
    def test_delete_workflow_product(self):
        """DELETE /workflows/{id} soft deletes by setting status='paused'."""
        client = _make_client()
        client.post("/api/v1/workflows", json=_sample_payload(id="wp-del"))

        response = client.delete("/api/v1/workflows/wp-del")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "paused"

        # Verify via GET
        get_resp = client.get("/api/v1/workflows/wp-del")
        assert get_resp.json()["status"] == "paused"

    def test_delete_nonexistent_returns_404(self):
        """DELETE /workflows/{id} returns 404 when workflow does not exist."""
        client = _make_client()

        response = client.delete("/api/v1/workflows/wp-nope")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Search templates
# ---------------------------------------------------------------------------


class TestSearchTemplates:
    def test_search_templates(self):
        """GET /workflows/templates returns a list (empty if RAG unavailable)."""
        client = _make_client()

        response = client.get("/api/v1/workflows/templates")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_search_templates_with_query(self):
        """GET /workflows/templates?q=podcast returns a list."""
        client = _make_client()

        response = client.get(
            "/api/v1/workflows/templates",
            params={"q": "podcast"},
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Test: Deploy workflow (stub)
# ---------------------------------------------------------------------------


class TestDeployWorkflow:
    def test_deploy_workflow(self):
        """POST /workflows/{id}/deploy returns mock deployment response."""
        client = _make_client()
        client.post("/api/v1/workflows", json=_sample_payload(id="wp-dep"))

        response = client.post("/api/v1/workflows/wp-dep/deploy")

        assert response.status_code == 200
        data = response.json()
        assert "n8n_workflow_id" in data
        assert data["status"] == "deployed"

    def test_deploy_nonexistent_returns_404(self):
        """POST /workflows/{id}/deploy returns 404 for unknown workflow."""
        client = _make_client()

        response = client.post("/api/v1/workflows/wp-nope/deploy")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Run workflow (manual trigger)
# ---------------------------------------------------------------------------


class TestRunWorkflow:
    def test_run_workflow(self):
        """POST /workflows/{id}/run creates an Execution record."""
        client = _make_client()
        client.post("/api/v1/workflows", json=_sample_payload(id="wp-run"))

        response = client.post("/api/v1/workflows/wp-run/run")

        assert response.status_code == 200
        data = response.json()
        assert data["workflow_product_id"] == "wp-run"
        assert data["status"] == "running"
        assert "id" in data
        assert "started_at" in data

    def test_run_nonexistent_returns_404(self):
        """POST /workflows/{id}/run returns 404 for unknown workflow."""
        client = _make_client()

        response = client.post("/api/v1/workflows/wp-nope/run")

        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Test: Execute agent by slug
# ---------------------------------------------------------------------------


class TestExecuteAgent:
    def test_execute_unknown_agent_returns_404(self):
        """POST /agents/{slug}/execute returns 404 for unregistered agent."""
        client = _make_client()

        response = client.post(
            "/api/v1/agents/nonexistent-agent/execute",
            json={"input": "test"},
        )

        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()
