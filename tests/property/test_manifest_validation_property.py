"""
Property-based tests for ManifestLoader.

Tests universal properties that should hold across all valid and invalid manifests.
Uses hypothesis to generate random but structured test data.
"""

from hypothesis import given, strategies as st, assume
import pytest
from src.neural_link.k8s_monitoring.manifest_loader import ManifestLoader


# Strategy for generating valid event types
valid_event_types = st.sampled_from(["ADDED", "MODIFIED", "DELETED"])

# Strategy for generating invalid event types
invalid_event_types = st.text(min_size=1).filter(
    lambda x: x not in ["ADDED", "MODIFIED", "DELETED"]
)

# Strategy for generating valid resource types
valid_resource_types = st.sampled_from([
    "Pod", "Service", "Deployment", "StatefulSet", "DaemonSet",
    "ConfigMap", "Secret", "Namespace", "Node", "PersistentVolume"
])

# Strategy for generating valid handler names
valid_handlers = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=50
).filter(lambda x: x[0].isalpha())

# Strategy for generating valid namespace strings
valid_namespaces = st.one_of(
    st.just("*"),
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        min_size=1,
        max_size=63
    ).filter(lambda x: x[0].isalnum() and x[-1].isalnum())
)

# Strategy for generating valid filters (dict with string keys and values)
valid_filters = st.dictionaries(
    keys=st.text(min_size=1, max_size=50),
    values=st.one_of(
        st.text(min_size=1, max_size=100),
        st.integers(),
        st.booleans()
    ),
    min_size=0,
    max_size=5
)

# Strategy for generating a valid hook
@st.composite
def valid_hook_strategy(draw):
    """Generate a valid on_k8s_event hook."""
    hook = {
        "resource_type": draw(valid_resource_types),
        "event_types": draw(st.lists(valid_event_types, min_size=1, max_size=3, unique=True)),
        "handler": draw(valid_handlers),
    }
    
    # Optionally add namespace
    if draw(st.booleans()):
        hook["namespace"] = draw(valid_namespaces)
    
    # Optionally add filters
    if draw(st.booleans()):
        hook["filters"] = draw(valid_filters)
    
    return hook

# Strategy for generating a valid manifest with on_k8s_event hooks
@st.composite
def valid_manifest_strategy(draw):
    """Generate a valid manifest with on_k8s_event hooks."""
    hooks = draw(st.lists(valid_hook_strategy(), min_size=1, max_size=5))
    
    manifest = {
        "name": draw(st.text(min_size=1, max_size=50)),
        "version": draw(st.text(min_size=1, max_size=20)),
        "hooks": {
            "on_k8s_event": hooks
        }
    }
    
    return manifest

# Strategy for generating invalid hooks (missing required fields)
@st.composite
def invalid_hook_missing_fields_strategy(draw):
    """Generate an invalid hook missing one or more required fields."""
    # Start with a valid hook
    hook = {
        "resource_type": draw(valid_resource_types),
        "event_types": draw(st.lists(valid_event_types, min_size=1, max_size=3, unique=True)),
        "handler": draw(valid_handlers),
    }
    
    # Remove at least one required field
    fields_to_remove = draw(st.lists(
        st.sampled_from(["resource_type", "event_types", "handler"]),
        min_size=1,
        max_size=3,
        unique=True
    ))
    
    for field in fields_to_remove:
        del hook[field]
    
    return hook

# Strategy for generating invalid hooks (invalid field values)
@st.composite
def invalid_hook_bad_values_strategy(draw):
    """Generate an invalid hook with invalid field values."""
    invalid_type = draw(st.sampled_from([
        "empty_resource_type",
        "empty_event_types",
        "invalid_event_type",
        "empty_handler",
        "empty_namespace",
        "invalid_filters"
    ]))
    
    hook = {
        "resource_type": draw(valid_resource_types),
        "event_types": draw(st.lists(valid_event_types, min_size=1, max_size=3, unique=True)),
        "handler": draw(valid_handlers),
    }
    
    if invalid_type == "empty_resource_type":
        hook["resource_type"] = ""
    elif invalid_type == "empty_event_types":
        hook["event_types"] = []
    elif invalid_type == "invalid_event_type":
        hook["event_types"] = [draw(invalid_event_types)]
    elif invalid_type == "empty_handler":
        hook["handler"] = ""
    elif invalid_type == "empty_namespace":
        hook["namespace"] = ""
    elif invalid_type == "invalid_filters":
        hook["filters"] = "not a dict"
    
    return hook


class TestManifestHookValidationProperty:
    """
    Property 1: Manifest Hook Validation
    
    **Validates: Requirements 1.2, 1.3, 1.4, 1.5**
    
    For any manifest file loaded by the system, if it contains on_k8s_event hooks,
    then each hook must have valid structure including resource_type, event_types,
    and handler fields.
    """
    
    @given(manifest=valid_manifest_strategy())
    def test_valid_manifests_always_pass_validation(self, manifest):
        """
        Property: Any manifest with properly structured hooks should validate successfully.
        
        This test generates random valid manifests and verifies that validate_hooks
        always returns True for them.
        """
        loader = ManifestLoader()
        
        # Valid manifests should always pass validation
        assert loader.validate_hooks(manifest) is True
        
        # Should also be able to extract hooks without error
        hooks = loader.get_k8s_hooks(manifest)
        assert len(hooks) > 0
        assert len(hooks) == len(manifest["hooks"]["on_k8s_event"])
    
    @given(manifest=valid_manifest_strategy())
    def test_all_hooks_have_required_fields(self, manifest):
        """
        Property: Every hook in a valid manifest must have resource_type, event_types, and handler.
        
        **Validates: Requirements 1.2, 1.3, 1.5**
        """
        loader = ManifestLoader()
        
        # Validate the manifest
        loader.validate_hooks(manifest)
        
        # Extract hooks
        hooks = loader.get_k8s_hooks(manifest)
        
        # Every hook must have the required fields
        for hook in hooks:
            assert "resource_type" in hook, "Hook missing resource_type"
            assert "event_types" in hook, "Hook missing event_types"
            assert "handler" in hook, "Hook missing handler"
            
            # Verify types
            assert isinstance(hook["resource_type"], str)
            assert isinstance(hook["event_types"], list)
            assert isinstance(hook["handler"], str)
            
            # Verify non-empty
            assert len(hook["resource_type"]) > 0
            assert len(hook["event_types"]) > 0
            assert len(hook["handler"]) > 0
    
    @given(manifest=valid_manifest_strategy())
    def test_event_types_are_valid(self, manifest):
        """
        Property: All event_types in hooks must be from the valid set (ADDED, MODIFIED, DELETED).
        
        **Validates: Requirements 1.4**
        """
        loader = ManifestLoader()
        
        # Validate the manifest
        loader.validate_hooks(manifest)
        
        # Extract hooks
        hooks = loader.get_k8s_hooks(manifest)
        
        valid_types = {"ADDED", "MODIFIED", "DELETED"}
        
        # Every event_type must be valid
        for hook in hooks:
            for event_type in hook["event_types"]:
                assert event_type in valid_types, f"Invalid event_type: {event_type}"
    
    @given(hook=invalid_hook_missing_fields_strategy())
    def test_hooks_missing_required_fields_fail_validation(self, hook):
        """
        Property: Any hook missing required fields should fail validation.
        
        **Validates: Requirements 1.2, 1.3, 1.5**
        """
        loader = ManifestLoader()
        
        manifest = {
            "name": "test",
            "hooks": {
                "on_k8s_event": [hook]
            }
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            loader.validate_hooks(manifest)
    
    @given(hook=invalid_hook_bad_values_strategy())
    def test_hooks_with_invalid_values_fail_validation(self, hook):
        """
        Property: Any hook with invalid field values should fail validation.
        
        **Validates: Requirements 1.2, 1.3, 1.4, 1.5**
        """
        loader = ManifestLoader()
        
        manifest = {
            "name": "test",
            "hooks": {
                "on_k8s_event": [hook]
            }
        }
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            loader.validate_hooks(manifest)
    
    @given(
        valid_hooks=st.lists(valid_hook_strategy(), min_size=1, max_size=3),
        invalid_hook=invalid_hook_missing_fields_strategy()
    )
    def test_one_invalid_hook_fails_entire_validation(self, valid_hooks, invalid_hook):
        """
        Property: If any hook in a manifest is invalid, the entire validation should fail.
        
        This ensures that validation is strict and doesn't allow partially valid manifests.
        """
        loader = ManifestLoader()
        
        # Insert invalid hook at random position
        all_hooks = valid_hooks + [invalid_hook]
        
        manifest = {
            "name": "test",
            "hooks": {
                "on_k8s_event": all_hooks
            }
        }
        
        # Should raise ValueError due to the invalid hook
        with pytest.raises(ValueError):
            loader.validate_hooks(manifest)
    
    @given(manifest=valid_manifest_strategy())
    def test_optional_fields_are_validated_when_present(self, manifest):
        """
        Property: When optional fields (namespace, filters) are present, they must be valid.
        
        **Validates: Requirements 1.3, 1.4**
        """
        loader = ManifestLoader()
        
        # Should validate successfully
        loader.validate_hooks(manifest)
        
        hooks = loader.get_k8s_hooks(manifest)
        
        for hook in hooks:
            # If namespace is present, it must be a non-empty string
            if "namespace" in hook:
                assert isinstance(hook["namespace"], str)
                assert len(hook["namespace"]) > 0
            
            # If filters is present, it must be a dict
            if "filters" in hook:
                assert isinstance(hook["filters"], dict)
    
    @given(
        manifest_structure=st.sampled_from([
            {},  # Empty manifest
            {"name": "test"},  # Missing hooks
            {"hooks": {}},  # Missing on_k8s_event
            {"hooks": {"on_k8s_event": "not a list"}},  # Wrong type
            {"hooks": {"on_k8s_event": []}},  # Empty list
        ])
    )
    def test_invalid_manifest_structure_fails_validation(self, manifest_structure):
        """
        Property: Manifests with invalid structure should fail validation.
        
        **Validates: Requirements 1.2**
        """
        loader = ManifestLoader()
        
        # Should raise ValueError
        with pytest.raises(ValueError):
            loader.validate_hooks(manifest_structure)
    
    @given(manifest=valid_manifest_strategy())
    def test_get_k8s_hooks_returns_all_hooks(self, manifest):
        """
        Property: get_k8s_hooks should return all hooks from the manifest without modification.
        
        **Validates: Requirements 1.2**
        """
        loader = ManifestLoader()
        
        hooks = loader.get_k8s_hooks(manifest)
        expected_hooks = manifest["hooks"]["on_k8s_event"]
        
        # Should return the same number of hooks
        assert len(hooks) == len(expected_hooks)
        
        # Should return the exact same hooks
        assert hooks == expected_hooks
    
    @given(
        manifest=valid_manifest_strategy(),
        extra_data=st.dictionaries(
            keys=st.text(min_size=1, max_size=20),
            values=st.one_of(st.text(), st.integers(), st.booleans()),
            min_size=1,
            max_size=3
        )
    )
    def test_validation_ignores_extra_fields(self, manifest, extra_data):
        """
        Property: Validation should not fail due to extra fields in the manifest.
        
        This ensures forward compatibility - new fields can be added without breaking validation.
        """
        loader = ManifestLoader()
        
        # Add extra fields to manifest
        for key, value in extra_data.items():
            # Don't overwrite existing keys
            if key not in manifest:
                manifest[key] = value
        
        # Should still validate successfully
        assert loader.validate_hooks(manifest) is True
