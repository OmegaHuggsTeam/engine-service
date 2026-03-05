"""
Shared pytest fixtures - Bunker Intelligence.
Autouse: sets safe test env vars before any test runs.
"""

import os
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _env_defaults(monkeypatch):
    """
    Set safe test environment variables for all tests.
    Prevents real API calls and DB connections during CI.
    """
    safe_vars = {
        "GROQ_API_KEY": "test-key-do-not-use",
        "GROQ_KEY_1": "test-key-do-not-use",
        "LLM_PROVIDER": "groq",
        "NEO4J_URI": "bolt://localhost:7687",
        "NEO4J_USER": "neo4j",
        "NEO4J_PASSWORD": "test-password",
        "CHROMA_PERSIST_DIR": ".chroma_test",
        "KUBERNETES_SERVICE_HOST": "",
        "TELEGRAM_BOT_TOKEN": "",
        "TELEGRAM_CHAT_ID": "",
    }
    for k, v in safe_vars.items():
        monkeypatch.setenv(k, v, prepend=False)
    yield


@pytest.fixture
def mock_graph_manager():
    """Mock GraphManager for tests that need graph without Neo4j."""
    mock = MagicMock()
    mock.verify_connectivity.return_value = True
    mock.execute_write_batch.return_value = 0
    mock.session.return_value.__enter__ = MagicMock(return_value=MagicMock())
    mock.session.return_value.__exit__ = MagicMock(return_value=False)
    return mock


@pytest.fixture
def mock_llm_client():
    """Mock LLMClient for tests that need LLM without API calls."""
    mock = MagicMock()
    mock.chat.return_value = "Mocked response"
    mock.generate.return_value = "Mocked generation"
    return mock
