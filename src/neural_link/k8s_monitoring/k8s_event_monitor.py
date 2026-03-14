"""Kubernetes Event Monitor for observing cluster events."""

import logging
import threading
from typing import Any, Callable, Dict, Optional

from kubernetes import client, config, watch
from kubernetes.client.rest import ApiException

logger = logging.getLogger(__name__)


class K8sEventMonitor:
    """Monitors Kubernetes events using Watch API."""

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize Kubernetes client.

        Args:
            kubeconfig_path: Path to kubeconfig file (None = in-cluster config)
        """
        # Load Kubernetes configuration
        if kubeconfig_path:
            config.load_kube_config(config_file=kubeconfig_path)
            logger.info(f"Loaded kubeconfig from {kubeconfig_path}")
        else:
            try:
                config.load_incluster_config()
                logger.info("Loaded in-cluster Kubernetes configuration")
            except config.ConfigException:
                # Fall back to default kubeconfig location
                config.load_kube_config()
                logger.info("Loaded default kubeconfig")

        self.v1 = client.CoreV1Api()
        self.watcher = watch.Watch()
        self.hooks: list[dict] = []
        self.running = False
        self._watch_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._handlers: Dict[str, Callable] = {}
        self._reconnect_delay = 30  # Initial reconnection delay in seconds
        self._max_reconnect_delay = 300  # Maximum reconnection delay (5 minutes)

    def register_hooks(self, hooks: list[dict]) -> None:
        """
        Register on_k8s_event hooks from manifest.

        Args:
            hooks: List of hook configurations from manifest
        """
        self.hooks = hooks
        logger.info(f"Registered {len(hooks)} Kubernetes event hooks")
        for hook in hooks:
            logger.debug(
                f"Hook: resource_type={hook.get('resource_type')}, "
                f"namespace={hook.get('namespace')}, "
                f"event_types={hook.get('event_types')}, "
                f"handler={hook.get('handler')}"
            )

    def register_handler(self, name: str, handler: Callable) -> None:
        """
        Register a handler function for event callbacks.

        Args:
            name: Handler name (matches 'handler' field in hook config)
            handler: Callable that accepts (event: dict, hook: dict) as arguments
        """
        self._handlers[name] = handler
        logger.info(f"Registered handler: {name}")

    def start(self) -> None:
        """Start watching Kubernetes events in background thread."""
        if self.running:
            logger.warning("K8sEventMonitor is already running")
            return

        if not self.hooks:
            logger.warning("No hooks registered, starting monitor anyway")

        self.running = True
        self._stop_event.clear()
        self._watch_thread = threading.Thread(
            target=self._watch_loop, name="K8sEventMonitor", daemon=True
        )
        self._watch_thread.start()
        logger.info("K8sEventMonitor started")

    def stop(self) -> None:
        """Stop watching events gracefully."""
        if not self.running:
            logger.warning("K8sEventMonitor is not running")
            return

        logger.info("Stopping K8sEventMonitor...")
        self.running = False
        self._stop_event.set()

        # Stop the watcher to unblock the watch stream
        try:
            self.watcher.stop()
        except Exception as e:
            logger.warning(f"Error stopping watcher: {e}")

        # Wait for thread to finish
        if self._watch_thread and self._watch_thread.is_alive():
            self._watch_thread.join(timeout=5.0)
            if self._watch_thread.is_alive():
                logger.warning("Watch thread did not stop within timeout")

        logger.info("K8sEventMonitor stopped")

    def _watch_loop(self) -> None:
        """Main event watching loop with reconnection logic (runs in thread)."""
        logger.info("Starting Kubernetes event watch loop")

        reconnect_delay = self._reconnect_delay
        consecutive_failures = 0

        while self.running and not self._stop_event.is_set():
            try:
                # Determine which resource types to watch based on hooks
                resource_types = self._get_resource_types_from_hooks()

                if not resource_types:
                    logger.warning(
                        "No resource types configured in hooks, watching Pods by default"
                    )
                    resource_types = ["Pod"]

                # Watch events for configured resource types
                # For now, we'll watch Pods (most common use case)
                # TODO: Support watching multiple resource types simultaneously
                logger.info(f"Watching resource types: {resource_types}")

                for event in self.watcher.stream(
                    self.v1.list_pod_for_all_namespaces, timeout_seconds=60
                ):
                    if not self.running or self._stop_event.is_set():
                        break

                    # Process the event
                    self._process_event(event)

                    # Reset reconnection delay on successful event processing
                    if consecutive_failures > 0:
                        consecutive_failures = 0
                        reconnect_delay = self._reconnect_delay
                        logger.info("Connection stable, reset reconnection delay")

            except ApiException as e:
                if self.running:
                    consecutive_failures += 1
                    logger.error(
                        f"Kubernetes API error in watch loop (attempt {consecutive_failures}): "
                        f"{e.status} - {e.reason}"
                    )

                    # Implement exponential backoff with max delay
                    current_delay = min(
                        reconnect_delay * (2 ** (consecutive_failures - 1)),
                        self._max_reconnect_delay,
                    )

                    logger.info(
                        f"Reconnecting in {current_delay} seconds "
                        f"(base delay: {reconnect_delay}s, failures: {consecutive_failures})"
                    )

                    # Wait before retry, but check stop event periodically
                    if self._stop_event.wait(current_delay):
                        break

            except Exception as e:
                if self.running:
                    consecutive_failures += 1
                    logger.error(
                        f"Unexpected error in watch loop (attempt {consecutive_failures}): {e}",
                        exc_info=True,
                    )

                    # Use same exponential backoff for unexpected errors
                    current_delay = min(
                        reconnect_delay * (2 ** (consecutive_failures - 1)),
                        self._max_reconnect_delay,
                    )

                    logger.info(f"Retrying in {current_delay} seconds")

                    if self._stop_event.wait(current_delay):
                        break

        logger.info("Exiting Kubernetes event watch loop")

    def _get_resource_types_from_hooks(self) -> list[str]:
        """
        Extract unique resource types from registered hooks.

        Returns:
            List of unique resource type names
        """
        resource_types = set()
        for hook in self.hooks:
            resource_type = hook.get("resource_type")
            if resource_type:
                resource_types.add(resource_type)
        return list(resource_types)

    def _process_event(self, event: dict) -> None:
        """
        Process a Kubernetes event.

        Args:
            event: Event dict with 'type' and 'object' keys
        """
        event_type = event.get("type")
        obj = event.get("object")

        if not obj:
            logger.warning("Received event without object")
            return

        # Extract basic event information
        resource_type = obj.kind if hasattr(obj, "kind") else "Unknown"
        name = obj.metadata.name if hasattr(obj, "metadata") else "unknown"
        namespace = obj.metadata.namespace if hasattr(obj, "metadata") else "unknown"

        logger.debug(
            f"Received event: type={event_type}, resource={resource_type}, "
            f"name={name}, namespace={namespace}"
        )

        # Match event against registered hooks
        for hook in self.hooks:
            if self._match_event(event, hook):
                self._dispatch_event(event, hook)

    def _match_event(self, event: dict, hook: dict) -> bool:
        """
        Check if event matches hook filters.

        Args:
            event: Kubernetes event dict
            hook: Hook configuration dict

        Returns:
            True if event matches hook criteria
        """
        obj = event.get("object")
        if not obj:
            return False

        event_type = event.get("type")
        resource_type = obj.kind if hasattr(obj, "kind") else None
        namespace = obj.metadata.namespace if hasattr(obj, "metadata") else None

        # Check resource type
        hook_resource_type = hook.get("resource_type")
        if hook_resource_type and resource_type != hook_resource_type:
            return False

        # Check event types
        hook_event_types = hook.get("event_types", [])
        if hook_event_types and event_type not in hook_event_types:
            return False

        # Check namespace
        hook_namespace = hook.get("namespace", "*")
        if hook_namespace != "*" and namespace != hook_namespace:
            return False

        # Evaluate filters (JSONPath-like expressions)
        filters = hook.get("filters", {})
        if filters:
            if not self._evaluate_filters(obj, filters):
                return False

        return True

    def _evaluate_filters(self, obj: Any, filters: dict) -> bool:
        """
        Evaluate filter expressions against a Kubernetes object.

        Supports simple JSONPath-like expressions:
        - "status.phase": "Failed" - checks if status.phase equals "Failed"
        - "status.containerStatuses[*].state.waiting.reason": "CrashLoopBackOff"
          checks if any container has this reason

        Args:
            obj: Kubernetes object to evaluate
            filters: Dict of filter expressions and expected values

        Returns:
            True if all filters match
        """
        for path, expected_value in filters.items():
            actual_value = self._get_nested_value(obj, path)

            # Handle list wildcard matching [*]
            if "[*]" in path:
                # If actual_value is a list, check if any item matches
                if isinstance(actual_value, list):
                    if not any(item == expected_value for item in actual_value):
                        return False
                else:
                    # Not a list, direct comparison
                    if actual_value != expected_value:
                        return False
            else:
                # Direct value comparison
                if actual_value != expected_value:
                    return False

        return True

    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """
        Get nested value from object using dot notation path.

        Supports:
        - Simple paths: "status.phase"
        - Array wildcards: "status.containerStatuses[*].state.waiting.reason"

        Args:
            obj: Object to traverse
            path: Dot-separated path with optional [*] for array wildcard

        Returns:
            Value at path, or None if not found
        """
        parts = path.split(".")
        current = obj

        for part in parts:
            if current is None:
                return None

            # Handle array wildcard [*]
            if "[*]" in part:
                field_name = part.replace("[*]", "")

                # Get the array field
                if hasattr(current, field_name):
                    current = getattr(current, field_name)
                elif isinstance(current, dict):
                    current = current.get(field_name)
                else:
                    return None

                # If it's a list, apply remainder of path to each element
                if isinstance(current, list):
                    remainder_idx = parts.index(part) + 1
                    if remainder_idx < len(parts):
                        remainder = ".".join(parts[remainder_idx:])
                        return [self._get_nested_value(item, remainder) for item in current]
                    return current
                else:
                    return None
            else:
                # Regular field access
                if hasattr(current, part):
                    current = getattr(current, part)
                elif isinstance(current, dict):
                    current = current.get(part)
                else:
                    return None

        return current

    def _dispatch_event(self, event: dict, hook: dict) -> None:
        """
        Dispatch event to registered handler.

        Args:
            event: Kubernetes event dict
            hook: Hook configuration dict
        """
        handler_name = hook.get("handler")
        if not handler_name:
            logger.warning(f"Hook has no handler defined: {hook}")
            return

        logger.info(
            f"Dispatching event to handler '{handler_name}' " f"for {event.get('type')} event"
        )

        # Look up the registered handler
        handler = self._handlers.get(handler_name)

        if handler:
            try:
                # Call the handler with event and hook context
                handler(event, hook)
                logger.debug(f"Successfully called handler: {handler_name}")
            except Exception as e:
                logger.error(f"Error calling handler '{handler_name}': {e}", exc_info=True)
        else:
            logger.warning(
                f"Handler '{handler_name}' not registered. "
                f"Available handlers: {list(self._handlers.keys())}"
            )
