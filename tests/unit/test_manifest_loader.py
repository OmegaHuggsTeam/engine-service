"""
Unit tests for ManifestLoader.

Tests specific examples, edge cases, and error conditions for manifest loading and validation.
"""

import json
import pytest
from pathlib import Path
from src.neural_link.k8s_monitoring.manifest_loader import ManifestLoader


@pytest.fixture
def manifest_loader():
    """Create a ManifestLoader instance."""
    return ManifestLoader()


@pytest.fixture
def valid_manifest():
    """Create a valid manifest dictionary."""
    return {
        "name": "test-manifest",
        "version": "1.0.0",
        "hooks": {
            "on_k8s_event": [
                {
                    "resource_type": "Pod",
                    "namespace": "*",
                    "event_types": ["MODIFIED"],
                    "filters": {
                        "status.phase": "Failed"
                    },
                    "handler": "handle_pod_crash"
                }
            ]
        }
    }


@pytest.fixture
def temp_manifest_file(tmp_path, valid_manifest):
    """Create a temporary manifest file."""
    manifest_path = tmp_path / "manifest.json"
    with open(manifest_path, "w") as f:
        json.dump(valid_manifest, f)
    return str(manifest_path)


class TestLoadManifest:
    """Tests for load_manifest method."""

    def test_load_valid_manifest(self, manifest_loader, temp_manifest_file, valid_manifest):
        """Test loading a valid manifest file."""
        result = manifest_loader.load_manifest(temp_manifest_file)
        assert result == valid_manifest

    def test_load_nonexistent_file(self, manifest_loader):
        """Test loading a file that doesn't exist."""
        with pytest.raises(FileNotFoundError):
            manifest_loader.load_manifest("/nonexistent/path/manifest.json")

    def test_load_invalid_json(self, manifest_loader, tmp_path):
        """Test loading a file with invalid JSON."""
        invalid_file = tmp_path / "invalid.json"
        with open(invalid_file, "w") as f:
            f.write("{ invalid json }")
        
        with pytest.raises(json.JSONDecodeError):
            manifest_loader.load_manifest(str(invalid_file))

    def test_load_empty_file(self, manifest_loader, tmp_path):
        """Test loading an empty file."""
        empty_file = tmp_path / "empty.json"
        with open(empty_file, "w") as f:
            f.write("")
        
        with pytest.raises(json.JSONDecodeError):
            manifest_loader.load_manifest(str(empty_file))


class TestValidateHooks:
    """Tests for validate_hooks method."""

    def test_validate_valid_hooks(self, manifest_loader, valid_manifest):
        """Test validating a manifest with valid hooks."""
        assert manifest_loader.validate_hooks(valid_manifest) is True

    def test_validate_missing_hooks_section(self, manifest_loader):
        """Test validating a manifest without hooks section."""
        manifest = {"name": "test"}
        with pytest.raises(ValueError, match="missing 'hooks' section"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_missing_on_k8s_event(self, manifest_loader):
        """Test validating a manifest without on_k8s_event hooks."""
        manifest = {"hooks": {}}
        with pytest.raises(ValueError, match="missing 'on_k8s_event' hooks"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_on_k8s_event_not_list(self, manifest_loader):
        """Test validating when on_k8s_event is not a list."""
        manifest = {"hooks": {"on_k8s_event": "not a list"}}
        with pytest.raises(ValueError, match="must be a list"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_empty_hooks_list(self, manifest_loader):
        """Test validating an empty hooks list."""
        manifest = {"hooks": {"on_k8s_event": []}}
        with pytest.raises(ValueError, match="list is empty"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_hook_not_dict(self, manifest_loader):
        """Test validating when a hook is not a dictionary."""
        manifest = {"hooks": {"on_k8s_event": ["not a dict"]}}
        with pytest.raises(ValueError, match="must be a dictionary"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_missing_resource_type(self, manifest_loader):
        """Test validating a hook missing resource_type."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "event_types": ["MODIFIED"],
                        "handler": "test_handler"
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="missing required field: resource_type"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_missing_event_types(self, manifest_loader):
        """Test validating a hook missing event_types."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "handler": "test_handler"
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="missing required field: event_types"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_missing_handler(self, manifest_loader):
        """Test validating a hook missing handler."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"]
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="missing required field: handler"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_empty_resource_type(self, manifest_loader):
        """Test validating a hook with empty resource_type."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "",
                        "event_types": ["MODIFIED"],
                        "handler": "test_handler"
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="invalid resource_type"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_empty_event_types_list(self, manifest_loader):
        """Test validating a hook with empty event_types list."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": [],
                        "handler": "test_handler"
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="invalid event_types"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_invalid_event_type(self, manifest_loader):
        """Test validating a hook with invalid event_type."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["INVALID_TYPE"],
                        "handler": "test_handler"
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="invalid event_type 'INVALID_TYPE'"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_empty_handler(self, manifest_loader):
        """Test validating a hook with empty handler."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"],
                        "handler": ""
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="invalid handler"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_invalid_namespace(self, manifest_loader):
        """Test validating a hook with invalid namespace."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"],
                        "handler": "test_handler",
                        "namespace": ""
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="invalid namespace"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_invalid_filters(self, manifest_loader):
        """Test validating a hook with invalid filters."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"],
                        "handler": "test_handler",
                        "filters": "not a dict"
                    }
                ]
            }
        }
        with pytest.raises(ValueError, match="invalid filters"):
            manifest_loader.validate_hooks(manifest)

    def test_validate_multiple_valid_hooks(self, manifest_loader):
        """Test validating multiple valid hooks."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"],
                        "handler": "handle_pod"
                    },
                    {
                        "resource_type": "Service",
                        "event_types": ["ADDED", "DELETED"],
                        "handler": "handle_service"
                    }
                ]
            }
        }
        assert manifest_loader.validate_hooks(manifest) is True

    def test_validate_all_event_types(self, manifest_loader):
        """Test validating with all valid event types."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["ADDED", "MODIFIED", "DELETED"],
                        "handler": "handle_all"
                    }
                ]
            }
        }
        assert manifest_loader.validate_hooks(manifest) is True


class TestGetK8sHooks:
    """Tests for get_k8s_hooks method."""

    def test_get_hooks_from_valid_manifest(self, manifest_loader, valid_manifest):
        """Test extracting hooks from a valid manifest."""
        hooks = manifest_loader.get_k8s_hooks(valid_manifest)
        assert len(hooks) == 1
        assert hooks[0]["resource_type"] == "Pod"
        assert hooks[0]["handler"] == "handle_pod_crash"

    def test_get_hooks_missing_hooks_section(self, manifest_loader):
        """Test extracting hooks when hooks section is missing."""
        manifest = {"name": "test"}
        with pytest.raises(ValueError, match="missing 'hooks' section"):
            manifest_loader.get_k8s_hooks(manifest)

    def test_get_hooks_missing_on_k8s_event(self, manifest_loader):
        """Test extracting hooks when on_k8s_event is missing."""
        manifest = {"hooks": {}}
        with pytest.raises(ValueError, match="missing 'on_k8s_event' hooks"):
            manifest_loader.get_k8s_hooks(manifest)

    def test_get_hooks_not_list(self, manifest_loader):
        """Test extracting hooks when on_k8s_event is not a list."""
        manifest = {"hooks": {"on_k8s_event": "not a list"}}
        with pytest.raises(ValueError, match="must be a list"):
            manifest_loader.get_k8s_hooks(manifest)

    def test_get_multiple_hooks(self, manifest_loader):
        """Test extracting multiple hooks."""
        manifest = {
            "hooks": {
                "on_k8s_event": [
                    {
                        "resource_type": "Pod",
                        "event_types": ["MODIFIED"],
                        "handler": "handle_pod"
                    },
                    {
                        "resource_type": "Service",
                        "event_types": ["ADDED"],
                        "handler": "handle_service"
                    }
                ]
            }
        }
        hooks = manifest_loader.get_k8s_hooks(manifest)
        assert len(hooks) == 2
        assert hooks[0]["resource_type"] == "Pod"
        assert hooks[1]["resource_type"] == "Service"

    def test_get_empty_hooks_list(self, manifest_loader):
        """Test extracting from an empty hooks list."""
        manifest = {"hooks": {"on_k8s_event": []}}
        hooks = manifest_loader.get_k8s_hooks(manifest)
        assert hooks == []


class TestIntegration:
    """Integration tests combining multiple methods."""

    def test_load_and_validate_real_manifest(self, manifest_loader):
        """Test loading and validating the actual manifest.json file."""
        manifest_path = "superpowers/n8n/manifest.json"
        
        # Load the manifest
        manifest = manifest_loader.load_manifest(manifest_path)
        
        # Validate it
        assert manifest_loader.validate_hooks(manifest) is True
        
        # Extract hooks
        hooks = manifest_loader.get_k8s_hooks(manifest)
        assert len(hooks) >= 1
        
        # Verify first hook structure
        first_hook = hooks[0]
        assert "resource_type" in first_hook
        assert "event_types" in first_hook
        assert "handler" in first_hook

    def test_full_workflow(self, manifest_loader, temp_manifest_file, valid_manifest):
        """Test the complete workflow: load -> validate -> extract."""
        # Load
        loaded = manifest_loader.load_manifest(temp_manifest_file)
        assert loaded == valid_manifest
        
        # Validate
        assert manifest_loader.validate_hooks(loaded) is True
        
        # Extract
        hooks = manifest_loader.get_k8s_hooks(loaded)
        assert len(hooks) == 1
        assert hooks[0]["resource_type"] == "Pod"
