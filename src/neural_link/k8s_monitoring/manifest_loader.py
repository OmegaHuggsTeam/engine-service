"""
ManifestLoader for n8n-k8s-monitoring.

This module provides functionality to load, validate, and extract
Kubernetes event hooks from the manifest.json configuration file.
"""

import json
from pathlib import Path
from typing import Any


class ManifestLoader:
    """Loads and validates manifest.json configuration."""

    # JSON schema for on_k8s_event hook validation
    HOOK_SCHEMA = {
        "required_fields": ["resource_type", "event_types", "handler"],
        "optional_fields": ["namespace", "filters"],
        "valid_event_types": ["ADDED", "MODIFIED", "DELETED"],
    }

    def load_manifest(self, path: str) -> dict[str, Any]:
        """
        Load manifest from file path.

        Args:
            path: Path to manifest.json file

        Returns:
            Parsed manifest dictionary

        Raises:
            FileNotFoundError: If manifest file doesn't exist
            json.JSONDecodeError: If manifest is not valid JSON
        """
        manifest_path = Path(path)

        if not manifest_path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        return manifest

    def validate_hooks(self, manifest: dict[str, Any]) -> bool:
        """
        Validate on_k8s_event hook structure.

        Args:
            manifest: Manifest dictionary to validate

        Returns:
            True if all hooks are valid

        Raises:
            ValueError: If validation fails with details about the error
        """
        if "hooks" not in manifest:
            raise ValueError("Manifest missing 'hooks' section")

        hooks = manifest.get("hooks", {})

        if "on_k8s_event" not in hooks:
            raise ValueError("Manifest missing 'on_k8s_event' hooks")

        k8s_hooks = hooks.get("on_k8s_event", [])

        if not isinstance(k8s_hooks, list):
            raise ValueError("'on_k8s_event' must be a list")

        if len(k8s_hooks) == 0:
            raise ValueError("'on_k8s_event' list is empty")

        # Validate each hook
        for idx, hook in enumerate(k8s_hooks):
            self._validate_single_hook(hook, idx)

        return True

    def _validate_single_hook(self, hook: dict[str, Any], index: int) -> None:
        """
        Validate a single hook configuration.

        Args:
            hook: Hook configuration dictionary
            index: Index of hook in list (for error messages)

        Raises:
            ValueError: If hook is invalid
        """
        if not isinstance(hook, dict):
            raise ValueError(f"Hook at index {index} must be a dictionary")

        # Check required fields
        for field in self.HOOK_SCHEMA["required_fields"]:
            if field not in hook:
                raise ValueError(f"Hook at index {index} missing required field: {field}")

        # Validate resource_type
        resource_type = hook.get("resource_type")
        if not isinstance(resource_type, str) or not resource_type:
            raise ValueError(
                f"Hook at index {index} has invalid resource_type: must be non-empty string"
            )

        # Validate event_types
        event_types = hook.get("event_types")
        if not isinstance(event_types, list) or len(event_types) == 0:
            raise ValueError(
                f"Hook at index {index} has invalid event_types: must be non-empty list"
            )

        for event_type in event_types:
            if event_type not in self.HOOK_SCHEMA["valid_event_types"]:
                raise ValueError(
                    f"Hook at index {index} has invalid event_type '{event_type}'. "
                    f"Valid types: {self.HOOK_SCHEMA['valid_event_types']}"
                )

        # Validate handler
        handler = hook.get("handler")
        if not isinstance(handler, str) or not handler:
            raise ValueError(f"Hook at index {index} has invalid handler: must be non-empty string")

        # Validate optional namespace field
        if "namespace" in hook:
            namespace = hook.get("namespace")
            if not isinstance(namespace, str) or not namespace:
                raise ValueError(
                    f"Hook at index {index} has invalid namespace: must be non-empty string"
                )

        # Validate optional filters field
        if "filters" in hook:
            filters = hook.get("filters")
            if not isinstance(filters, dict):
                raise ValueError(f"Hook at index {index} has invalid filters: must be a dictionary")

    def get_k8s_hooks(self, manifest: dict[str, Any]) -> list[dict[str, Any]]:
        """
        Extract all on_k8s_event hooks from manifest.

        Args:
            manifest: Manifest dictionary

        Returns:
            List of hook configuration dictionaries

        Raises:
            ValueError: If manifest structure is invalid
        """
        if "hooks" not in manifest:
            raise ValueError("Manifest missing 'hooks' section")

        hooks = manifest.get("hooks", {})

        if "on_k8s_event" not in hooks:
            raise ValueError("Manifest missing 'on_k8s_event' hooks")

        k8s_hooks = hooks.get("on_k8s_event", [])

        if not isinstance(k8s_hooks, list):
            raise ValueError("'on_k8s_event' must be a list")

        return k8s_hooks
