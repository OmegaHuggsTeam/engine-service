"""
Property-based tests for K8sEventMonitor.

Tests universal properties that should hold across all valid event configurations.
Uses hypothesis to generate random but structured test data.
"""

from contextlib import contextmanager
from unittest.mock import patch

from hypothesis import assume, given
from hypothesis import strategies as st
from kubernetes.client import (
    V1ObjectMeta,
    V1Pod,
    V1PodStatus,
)

from src.neural_link.k8s_monitoring.k8s_event_monitor import K8sEventMonitor


@contextmanager
def mock_kubernetes_config():
    """Context manager to mock Kubernetes configuration."""
    with (
        patch("src.neural_link.k8s_monitoring.k8s_event_monitor.config") as mock_config,
        patch("src.neural_link.k8s_monitoring.k8s_event_monitor.client") as mock_client,
    ):
        yield mock_config, mock_client


# Strategy for generating valid event types
valid_event_types = st.sampled_from(["ADDED", "MODIFIED", "DELETED"])

# Strategy for generating valid resource types
valid_resource_types = st.sampled_from(["Pod", "Service", "Deployment", "StatefulSet", "DaemonSet"])

# Strategy for generating valid namespace strings
valid_namespaces = st.one_of(
    st.just("*"),
    st.text(
        alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
        min_size=1,
        max_size=63,
    ).filter(lambda x: x and x[0].isalnum() and x[-1].isalnum()),
)

# Strategy for generating valid handler names
valid_handlers = st.text(
    alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd"), whitelist_characters="_"),
    min_size=1,
    max_size=50,
).filter(lambda x: x[0].isalpha())


# Strategy for generating a valid hook configuration
@st.composite
def hook_config_strategy(draw):
    """Generate a valid hook configuration."""
    hook = {
        "resource_type": draw(valid_resource_types),
        "event_types": draw(st.lists(valid_event_types, min_size=1, max_size=3, unique=True)),
        "handler": draw(valid_handlers),
        "namespace": draw(valid_namespaces),
    }

    # Optionally add filters
    if draw(st.booleans()):
        # Generate simple filters (no array wildcards for now)
        filter_path = draw(st.sampled_from(["status.phase", "metadata.name", "metadata.namespace"]))
        filter_value = draw(st.text(min_size=1, max_size=20))
        hook["filters"] = {filter_path: filter_value}

    return hook


# Strategy for generating Kubernetes Pod objects
@st.composite
def k8s_pod_strategy(draw):
    """Generate a Kubernetes Pod object."""
    name = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
            min_size=1,
            max_size=63,
        ).filter(lambda x: x and x[0].isalnum() and x[-1].isalnum())
    )

    namespace = draw(
        st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
            min_size=1,
            max_size=63,
        ).filter(lambda x: x and x[0].isalnum() and x[-1].isalnum())
    )

    phase = draw(st.sampled_from(["Pending", "Running", "Succeeded", "Failed", "Unknown"]))

    pod = V1Pod(
        kind="Pod",
        metadata=V1ObjectMeta(name=name, namespace=namespace),
        status=V1PodStatus(phase=phase),
    )

    return pod


# Strategy for generating Kubernetes events
@st.composite
def k8s_event_strategy(draw):
    """Generate a Kubernetes event."""
    event_type = draw(valid_event_types)
    pod = draw(k8s_pod_strategy())

    return {"type": event_type, "object": pod}


class TestEventSubscriptionCompletenessProperty:
    """
    Property 2: Event Subscription Completeness

    **Validates: Requirements 2.2**

    For any set of configured resource types in the manifest, the K8sEventMonitor
    must subscribe to watch events for all of them when started.
    """

    @given(hooks=st.lists(hook_config_strategy(), min_size=1, max_size=5))
    def test_all_configured_resource_types_are_extracted(self, hooks):
        """
        Property: All unique resource types from hooks must be extracted.

        When hooks are registered, the monitor should identify all unique
        resource types that need to be watched.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()
            monitor.register_hooks(hooks)

            # Extract expected resource types
            expected_types = set(hook["resource_type"] for hook in hooks)

            # Get actual resource types from monitor
            actual_types = set(monitor._get_resource_types_from_hooks())

            # All expected types should be present
            assert (
                expected_types == actual_types
            ), f"Expected resource types {expected_types} but got {actual_types}"

    @given(hooks=st.lists(hook_config_strategy(), min_size=1, max_size=5))
    def test_duplicate_resource_types_are_deduplicated(self, hooks):
        """
        Property: Duplicate resource types should be deduplicated.

        If multiple hooks watch the same resource type, it should only appear
        once in the subscription list.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()
            monitor.register_hooks(hooks)

            resource_types = monitor._get_resource_types_from_hooks()

            # No duplicates should exist
            assert len(resource_types) == len(
                set(resource_types)
            ), f"Resource types contain duplicates: {resource_types}"

    @given(hooks=st.lists(hook_config_strategy(), min_size=1, max_size=10))
    def test_all_hooks_are_stored_after_registration(self, hooks):
        """
        Property: All registered hooks must be stored in the monitor.

        After registration, the monitor should have all hooks available
        for event matching.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()
            monitor.register_hooks(hooks)

            # All hooks should be stored
            assert len(monitor.hooks) == len(hooks)
            assert monitor.hooks == hooks


class TestEventFilteringCorrectnessProperty:
    """
    Property 4: Event Filtering Correctness

    **Validates: Requirements 2.4, 2.5**

    For any Kubernetes event and hook configuration, the event should be
    dispatched to the handler if and only if it matches all filters specified
    in the hook.
    """

    @given(event=k8s_event_strategy(), hook=hook_config_strategy())
    def test_event_matches_only_when_all_criteria_match(self, event, hook):
        """
        Property: An event matches a hook if and only if ALL criteria match.

        This tests the fundamental correctness of event filtering:
        - Resource type must match
        - Event type must match
        - Namespace must match (or be wildcard)
        - All filters must match
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            obj = event["object"]
            event_type = event["type"]

            # Determine if event should match based on criteria
            should_match = True

            # Check resource type
            if hook["resource_type"] != obj.kind:
                should_match = False

            # Check event type
            if event_type not in hook["event_types"]:
                should_match = False

            # Check namespace
            hook_namespace = hook.get("namespace", "*")
            if hook_namespace != "*" and hook_namespace != obj.metadata.namespace:
                should_match = False

            # Check filters
            if "filters" in hook and should_match:
                for path, expected_value in hook["filters"].items():
                    actual_value = monitor._get_nested_value(obj, path)
                    if actual_value != expected_value:
                        should_match = False
                        break

            # Test the actual matching
            actual_match = monitor._match_event(event, hook)

            assert actual_match == should_match, (
                f"Event matching failed: expected {should_match} but got {actual_match}\n"
                f"Event: type={event_type}, resource={obj.kind}, "
                f"namespace={obj.metadata.namespace}\n"
                f"Hook: resource_type={hook['resource_type']}, "
                f"event_types={hook['event_types']}, namespace={hook.get('namespace', '*')}, "
                f"filters={hook.get('filters', {})}"
            )

    @given(pod=k8s_pod_strategy(), event_type=valid_event_types)
    def test_matching_resource_type_is_necessary(self, pod, event_type):
        """
        Property: Events with non-matching resource types never match.

        If the hook specifies a resource type, only events of that type
        should match.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            event = {"type": event_type, "object": pod}

            # Hook for a different resource type
            hook = {
                "resource_type": "Service",  # Different from Pod
                "event_types": [event_type],
                "namespace": "*",
                "handler": "test_handler",
            }

            # Should never match
            assert monitor._match_event(event, hook) is False

    @given(
        pod=k8s_pod_strategy(),
        hook_event_types=st.lists(valid_event_types, min_size=1, max_size=2, unique=True),
    )
    def test_matching_event_type_is_necessary(self, pod, hook_event_types):
        """
        Property: Events with non-matching event types never match.

        If the hook specifies event types, only events of those types
        should match.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            # Find an event type not in the hook's list
            all_types = ["ADDED", "MODIFIED", "DELETED"]
            non_matching_type = next(t for t in all_types if t not in hook_event_types)

            event = {"type": non_matching_type, "object": pod}

            hook = {
                "resource_type": "Pod",
                "event_types": hook_event_types,
                "namespace": "*",
                "handler": "test_handler",
            }

            # Should never match
            assert monitor._match_event(event, hook) is False

    @given(
        pod=k8s_pod_strategy(),
        event_type=valid_event_types,
        specific_namespace=st.text(
            alphabet=st.characters(whitelist_categories=("Ll", "Nd"), whitelist_characters="-"),
            min_size=1,
            max_size=63,
        ).filter(lambda x: x and x[0].isalnum() and x[-1].isalnum()),
    )
    def test_namespace_filtering_is_enforced(self, pod, event_type, specific_namespace):
        """
        Property: Namespace filtering must be enforced when not using wildcard.

        If a hook specifies a specific namespace, only events from that
        namespace should match.
        """
        # Ensure pod is in a different namespace
        assume(pod.metadata.namespace != specific_namespace)

        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            event = {"type": event_type, "object": pod}

            hook = {
                "resource_type": "Pod",
                "event_types": [event_type],
                "namespace": specific_namespace,
                "handler": "test_handler",
            }

            # Should not match because namespace is different
            assert monitor._match_event(event, hook) is False

    @given(pod=k8s_pod_strategy(), event_type=valid_event_types)
    def test_wildcard_namespace_matches_all_namespaces(self, pod, event_type):
        """
        Property: Wildcard namespace (*) should match events from any namespace.

        When namespace is "*", events from all namespaces should match
        (assuming other criteria match).
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            event = {"type": event_type, "object": pod}

            hook = {
                "resource_type": "Pod",
                "event_types": [event_type],
                "namespace": "*",
                "handler": "test_handler",
            }

            # Should match regardless of namespace
            assert monitor._match_event(event, hook) is True

    @given(
        event_type=valid_event_types,
        namespace=valid_namespaces.filter(lambda x: x != "*"),
        phase=st.sampled_from(["Pending", "Running", "Succeeded", "Failed", "Unknown"]),
    )
    def test_filter_mismatch_prevents_matching(self, event_type, namespace, phase):
        """
        Property: If any filter doesn't match, the event should not match.

        All filters must match for an event to be dispatched.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            # Create pod with specific phase
            pod = V1Pod(
                kind="Pod",
                metadata=V1ObjectMeta(name="test-pod", namespace=namespace),
                status=V1PodStatus(phase=phase),
            )

            event = {"type": event_type, "object": pod}

            # Hook with filter for a different phase
            different_phases = ["Pending", "Running", "Succeeded", "Failed", "Unknown"]
            different_phases.remove(phase)
            different_phase = different_phases[0]

            hook = {
                "resource_type": "Pod",
                "event_types": [event_type],
                "namespace": "*",
                "filters": {"status.phase": different_phase},
                "handler": "test_handler",
            }

            # Should not match because filter doesn't match
            assert monitor._match_event(event, hook) is False

    @given(
        event_type=valid_event_types,
        namespace=valid_namespaces.filter(lambda x: x != "*"),
        phase=st.sampled_from(["Pending", "Running", "Succeeded", "Failed", "Unknown"]),
    )
    def test_matching_filter_allows_matching(self, event_type, namespace, phase):
        """
        Property: When all filters match, the event should match.

        If all criteria including filters match, the event should be dispatched.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            # Create pod with specific phase
            pod = V1Pod(
                kind="Pod",
                metadata=V1ObjectMeta(name="test-pod", namespace=namespace),
                status=V1PodStatus(phase=phase),
            )

            event = {"type": event_type, "object": pod}

            # Hook with matching filter
            hook = {
                "resource_type": "Pod",
                "event_types": [event_type],
                "namespace": "*",
                "filters": {"status.phase": phase},
                "handler": "test_handler",
            }

            # Should match because all criteria match
            assert monitor._match_event(event, hook) is True

    @given(
        event=k8s_event_strategy(), hooks=st.lists(hook_config_strategy(), min_size=2, max_size=5)
    )
    def test_event_matches_all_applicable_hooks(self, event, hooks):
        """
        Property: An event can match multiple hooks if criteria match.

        A single event should be dispatched to all hooks that match its criteria.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()
            monitor.register_hooks(hooks)

            # Count how many hooks should match
            expected_matches = sum(1 for hook in hooks if monitor._match_event(event, hook))

            # Track actual dispatches
            dispatch_count = 0

            def counting_handler(evt, hk):
                nonlocal dispatch_count
                dispatch_count += 1

            # Register handler for all hooks
            for hook in hooks:
                monitor.register_handler(hook["handler"], counting_handler)

            # Process the event
            monitor._process_event(event)

            # Should dispatch to all matching hooks
            assert (
                dispatch_count == expected_matches
            ), f"Expected {expected_matches} dispatches but got {dispatch_count}"

    def test_event_without_object_never_matches(self):
        """
        Property: Events without an object should never match any hook.

        Malformed events should be safely ignored.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            event = {"type": "MODIFIED", "object": None}

            hook = {
                "resource_type": "Pod",
                "event_types": ["MODIFIED"],
                "namespace": "*",
                "handler": "test_handler",
            }

            # Should never match
            assert monitor._match_event(event, hook) is False

    @given(pod=k8s_pod_strategy(), event_type=valid_event_types)
    def test_hook_without_filters_matches_on_basic_criteria_only(self, pod, event_type):
        """
        Property: Hooks without filters should match based on resource type,
        event type, and namespace only.

        Filters are optional and should not be required for matching.
        """
        with mock_kubernetes_config():
            monitor = K8sEventMonitor()

            event = {"type": event_type, "object": pod}

            hook = {
                "resource_type": "Pod",
                "event_types": [event_type],
                "namespace": "*",
                "handler": "test_handler",
                # No filters
            }

            # Should match based on basic criteria
            assert monitor._match_event(event, hook) is True
