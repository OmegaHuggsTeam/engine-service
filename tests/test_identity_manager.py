"""
Testes unitarios para o Identity Manager.
Testa IdentityManager, models, checksum validation e SecretVault (KeyManager).
"""

import hashlib
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.services.models import (
    IdentityConfig,
    ProviderConfig,
    ProviderType,
    ProvisioningStep,
    ProvisioningTask,
    StepConfig,
)
from src.services.identity_manager import IdentityManager, PROVIDER_ORDER
from src.utils.llm_client import KeyManager


# ============================================================
# Fixtures
# ============================================================

CONFIG_PATH = Path(__file__).parent.parent / "src" / "services" / "identity_config.json"


@pytest.fixture
def sample_config_data():
    """Retorna dados de config validos."""
    return {
        "version": "1.0",
        "identity_name": "test_identity",
        "providers": [
            {
                "provider": "google",
                "enabled": True,
                "base_url": "http://localhost:9090/mock/google",
                "form_fields": {"email": "test@test.com", "display_name": "Test"},
                "steps": [
                    {"step": "navigate", "selector": "#login-form", "timeout_ms": 5000},
                    {"step": "fill_form", "selector": "#email-input", "value_field": "email"},
                    {"step": "submit", "selector": "#submit-btn"},
                    {"step": "verify", "selector": ".success-msg"},
                ],
            },
            {
                "provider": "github",
                "enabled": True,
                "base_url": "http://localhost:9090/mock/github",
                "form_fields": {"username": "testuser", "email": "test@test.com"},
                "steps": [
                    {"step": "navigate", "selector": "#signup-form", "timeout_ms": 5000},
                    {"step": "fill_form", "selector": "#username-input", "value_field": "username"},
                    {"step": "submit", "selector": "#create-account-btn"},
                    {"step": "verify", "selector": ".welcome-msg"},
                ],
            },
            {
                "provider": "groq",
                "enabled": True,
                "base_url": "http://localhost:9090/mock/groq",
                "form_fields": {"api_key_name": "test-key"},
                "steps": [
                    {"step": "navigate", "selector": "#api-keys", "timeout_ms": 5000},
                    {"step": "extract_key", "selector": "#new-key-value"},
                    {"step": "store_key", "selector": None, "value_field": "api_key"},
                ],
            },
        ],
    }


@pytest.fixture
def config_file(sample_config_data, tmp_path):
    """Cria arquivo de config temporario."""
    config_path = tmp_path / "identity_config.json"
    config_path.write_text(json.dumps(sample_config_data), encoding="utf-8")
    return str(config_path)


@pytest.fixture
def mock_graph_manager():
    """GraphManager mockado."""
    gm = MagicMock()
    gm.execute_write = MagicMock(return_value=[])
    gm.execute_read = MagicMock(return_value=[])
    return gm


@pytest.fixture
def identity_manager(mock_graph_manager):
    """IdentityManager com GraphManager mockado."""
    return IdentityManager(graph_manager=mock_graph_manager)


@pytest.fixture
def identity_manager_no_graph():
    """IdentityManager sem GraphManager."""
    return IdentityManager()


# ============================================================
# Pydantic Models Tests
# ============================================================

class TestModels:
    def test_provider_type_enum(self):
        assert ProviderType.GOOGLE.value == "google"
        assert ProviderType.GITHUB.value == "github"
        assert ProviderType.GROQ.value == "groq"

    def test_provisioning_step_enum(self):
        assert ProvisioningStep.NAVIGATE.value == "navigate"
        assert ProvisioningStep.FILL_FORM.value == "fill_form"
        assert ProvisioningStep.STORE_KEY.value == "store_key"

    def test_step_config_defaults(self):
        step = StepConfig(step=ProvisioningStep.NAVIGATE)
        assert step.timeout_ms == 5000
        assert step.selector is None
        assert step.value_field is None

    def test_provider_config(self):
        config = ProviderConfig(
            provider=ProviderType.GOOGLE,
            base_url="http://localhost:9090",
        )
        assert config.enabled is True
        assert config.steps == []
        assert config.form_fields == {}

    def test_identity_config(self):
        config = IdentityConfig(identity_name="test")
        assert config.version == "1.0"
        assert config.providers == []
        assert config.created_at  # auto-generated

    def test_provisioning_task_checksum(self):
        task = ProvisioningTask(
            id="test_google_00_navigate",
            provider=ProviderType.GOOGLE,
            step=ProvisioningStep.NAVIGATE,
        )
        checksum = task.compute_checksum()
        expected = hashlib.sha256(b"test_google_00_navigate:google:navigate").hexdigest()
        assert checksum == expected

    def test_provisioning_task_defaults(self):
        task = ProvisioningTask(
            id="t1",
            provider=ProviderType.GITHUB,
            step=ProvisioningStep.SUBMIT,
        )
        assert task.status == "pending"
        assert task.depends_on == []
        assert task.input_data == {}
        assert task.created_at  # auto-generated


# ============================================================
# IdentityManager.load_config Tests
# ============================================================

class TestLoadConfig:
    def test_load_valid_config(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        assert isinstance(config, IdentityConfig)
        assert config.identity_name == "test_identity"
        assert len(config.providers) == 3

    def test_load_config_providers(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        providers = [p.provider for p in config.providers]
        assert ProviderType.GOOGLE in providers
        assert ProviderType.GITHUB in providers
        assert ProviderType.GROQ in providers

    def test_load_config_file_not_found(self, identity_manager):
        with pytest.raises(FileNotFoundError):
            identity_manager.load_config("/nonexistent/path.json")

    def test_load_config_invalid_json(self, identity_manager, tmp_path):
        bad_file = tmp_path / "bad.json"
        bad_file.write_text("{invalid json", encoding="utf-8")
        with pytest.raises(json.JSONDecodeError):
            identity_manager.load_config(str(bad_file))

    def test_load_config_invalid_schema(self, identity_manager, tmp_path):
        bad_file = tmp_path / "bad_schema.json"
        bad_file.write_text(json.dumps({"version": "1.0"}), encoding="utf-8")
        with pytest.raises(Exception):  # Pydantic ValidationError
            identity_manager.load_config(str(bad_file))

    def test_load_real_config(self, identity_manager):
        """Testa que o identity_config.json do projeto e valido."""
        if CONFIG_PATH.exists():
            config = identity_manager.load_config(str(CONFIG_PATH))
            assert config.identity_name == "energy_alias"
            assert len(config.providers) == 3


# ============================================================
# IdentityManager.generate_task_queue Tests
# ============================================================

class TestGenerateTaskQueue:
    def test_generates_tasks_for_all_providers(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)
        # google: 4 steps + github: 4 steps + groq: 3 steps = 11
        assert len(tasks) == 11

    def test_task_ids_are_unique(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)
        ids = [t.id for t in tasks]
        assert len(ids) == len(set(ids))

    def test_provider_ordering(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)
        providers_seen = []
        for t in tasks:
            if t.provider not in providers_seen:
                providers_seen.append(t.provider)
        assert providers_seen == [ProviderType.GOOGLE, ProviderType.GITHUB, ProviderType.GROQ]

    def test_intra_provider_dependencies(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)

        # Google tasks: first has no dep, rest depend on previous
        google_tasks = [t for t in tasks if t.provider == ProviderType.GOOGLE]
        assert google_tasks[0].depends_on == []
        for i in range(1, len(google_tasks)):
            assert google_tasks[i].depends_on == [google_tasks[i - 1].id]

    def test_cross_provider_dependency(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)

        google_tasks = [t for t in tasks if t.provider == ProviderType.GOOGLE]
        github_tasks = [t for t in tasks if t.provider == ProviderType.GITHUB]
        groq_tasks = [t for t in tasks if t.provider == ProviderType.GROQ]

        # First github step depends on last google step
        assert github_tasks[0].depends_on == [google_tasks[-1].id]
        # First groq step depends on last github step
        assert groq_tasks[0].depends_on == [github_tasks[-1].id]

    def test_all_tasks_have_checksums(self, identity_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)
        for task in tasks:
            assert task.checksum
            assert task.checksum == task.compute_checksum()

    def test_disabled_provider_excluded(self, identity_manager, sample_config_data, tmp_path):
        sample_config_data["providers"][1]["enabled"] = False  # disable github
        config_path = tmp_path / "cfg.json"
        config_path.write_text(json.dumps(sample_config_data), encoding="utf-8")
        config = identity_manager.load_config(str(config_path))
        tasks = identity_manager.generate_task_queue(config)
        providers = {t.provider for t in tasks}
        assert ProviderType.GITHUB not in providers

    def test_empty_providers(self, identity_manager):
        config = IdentityConfig(identity_name="empty")
        tasks = identity_manager.generate_task_queue(config)
        assert tasks == []


# ============================================================
# IdentityManager.persist_tasks Tests
# ============================================================

class TestPersistTasks:
    def test_persist_calls_graph(self, identity_manager, mock_graph_manager, config_file):
        config = identity_manager.load_config(config_file)
        tasks = identity_manager.generate_task_queue(config)
        identity_manager.persist_tasks(tasks)
        assert mock_graph_manager.execute_write.call_count == len(tasks)

    def test_persist_without_graph(self, identity_manager_no_graph, config_file):
        im = identity_manager_no_graph
        config = im.load_config(config_file)
        tasks = im.generate_task_queue(config)
        # Should not raise, just log warning
        im.persist_tasks(tasks)


# ============================================================
# IdentityManager.get_pending_tasks Tests
# ============================================================

class TestGetPendingTasks:
    def test_get_pending_with_provider(self, identity_manager, mock_graph_manager):
        identity_manager.get_pending_tasks(provider="google")
        mock_graph_manager.execute_read.assert_called_once()

    def test_get_pending_without_provider(self, identity_manager, mock_graph_manager):
        identity_manager.get_pending_tasks()
        mock_graph_manager.execute_read.assert_called_once()

    def test_get_pending_no_graph(self, identity_manager_no_graph):
        result = identity_manager_no_graph.get_pending_tasks()
        assert result == []


# ============================================================
# IdentityManager.update_task_status Tests
# ============================================================

class TestUpdateTaskStatus:
    def test_update_calls_graph(self, identity_manager, mock_graph_manager):
        identity_manager.update_task_status("task-1", "completed", {"key": "value"})
        mock_graph_manager.execute_write.assert_called_once()

    def test_update_no_graph(self, identity_manager_no_graph):
        # Should not raise
        identity_manager_no_graph.update_task_status("task-1", "completed")


# ============================================================
# IdentityManager.process_config Tests
# ============================================================

class TestProcessConfig:
    def test_full_pipeline(self, identity_manager, mock_graph_manager, config_file):
        tasks = identity_manager.process_config(config_file)
        assert len(tasks) == 11
        assert mock_graph_manager.execute_write.call_count == 11


# ============================================================
# Checksum Validation Tests
# ============================================================

class TestChecksum:
    def test_task_checksum_consistency(self):
        task = ProvisioningTask(
            id="x_google_00_navigate",
            provider=ProviderType.GOOGLE,
            step=ProvisioningStep.NAVIGATE,
        )
        c1 = task.compute_checksum()
        c2 = task.compute_checksum()
        assert c1 == c2

    def test_different_tasks_different_checksums(self):
        t1 = ProvisioningTask(
            id="x_google_00_navigate",
            provider=ProviderType.GOOGLE,
            step=ProvisioningStep.NAVIGATE,
        )
        t2 = ProvisioningTask(
            id="x_github_00_navigate",
            provider=ProviderType.GITHUB,
            step=ProvisioningStep.NAVIGATE,
        )
        assert t1.compute_checksum() != t2.compute_checksum()


# ============================================================
# KeyManager SecretVault Tests
# ============================================================

class TestKeyManagerVault:
    def test_validate_checksum_valid(self):
        key = "gsk_test_key_123"
        checksum = hashlib.sha256(key.encode()).hexdigest()
        assert KeyManager.validate_checksum(key, checksum) is True

    def test_validate_checksum_invalid(self):
        assert KeyManager.validate_checksum("key", "wrong_checksum") is False

    def test_register_key_valid(self):
        km = KeyManager(["existing-key"])
        new_key = "new-groq-key"
        checksum = hashlib.sha256(new_key.encode()).hexdigest()
        assert km.register_key(new_key, checksum, provider="groq") is True
        assert len(km._keys) == 2

    def test_register_key_invalid_checksum(self):
        km = KeyManager(["existing-key"])
        assert km.register_key("bad-key", "wrong_checksum") is False
        assert len(km._keys) == 1

    def test_register_key_duplicate(self):
        km = KeyManager(["existing-key"])
        checksum = hashlib.sha256("existing-key".encode()).hexdigest()
        assert km.register_key("existing-key", checksum) is True
        assert len(km._keys) == 1  # no duplicate

    def test_get_vault_status(self):
        km = KeyManager(["key1", "key2"])
        status = km.get_vault_status()
        assert status["total_keys"] == 2
        assert status["active_keys"] == 2
        assert status["in_cooldown"] == 0

    def test_vault_status_with_cooldown(self):
        km = KeyManager(["key1", "key2"])
        km.mark_429("key1")
        status = km.get_vault_status()
        assert status["total_keys"] == 2
        assert status["active_keys"] == 1
        assert status["in_cooldown"] == 1

    def test_register_key_updates_providers(self):
        km = KeyManager([])
        key = "new-key"
        checksum = hashlib.sha256(key.encode()).hexdigest()
        km.register_key(key, checksum, provider="github")
        status = km.get_vault_status()
        assert "github" in status["providers"]

    def test_vault_status_empty(self):
        km = KeyManager([])
        status = km.get_vault_status()
        assert status["total_keys"] == 0
        assert status["active_keys"] == 0


# ============================================================
# IdentityManager Router Integration Tests
# ============================================================

class TestIdentityManagerRouter:
    def test_init_with_router(self):
        mock_router = MagicMock()
        im = IdentityManager(router=mock_router)
        assert im._router is mock_router

    def test_init_without_router(self):
        im = IdentityManager()
        assert im._router is None
