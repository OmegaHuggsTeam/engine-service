"""
Telemetry Provider Layer - Observer pattern for external integrations.

TelemetryProvider is the ABC that connectors implement.
TelemetryHub is the central dispatcher that routes events to subscribers.
JitbitConnector is the first concrete provider (Jitbit helpdesk / automation).
"""

import logging
import threading
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ==================================================================
# Event Model
# ==================================================================

class EventType(str, Enum):
    """Categories of telemetry events."""
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    SYNC_TRIGGERED = "sync_triggered"
    SYNC_COMPLETED = "sync_completed"
    KILL_SWITCH_TRIGGERED = "kill_switch_triggered"
    CRITICAL_ANOMALY = "critical_anomaly"
    RECOVERY_ATTEMPTED = "recovery_attempted"
    LOG = "log"
    METRIC = "metric"
    KPI_ANOMALY_DETECTED = "kpi_anomaly_detected"


@dataclass
class TelemetryEvent:
    """A single telemetry event emitted by a provider."""
    event_type: EventType
    source: str                             # provider id, e.g. "jitbit"
    message: str
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    data: dict[str, Any] = field(default_factory=dict)


# ==================================================================
# Provider ABC
# ==================================================================

class TelemetryProvider(ABC):
    """Abstract base class for telemetry connectors."""

    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for this provider (e.g. 'jitbit')."""
        ...

    @property
    @abstractmethod
    def display_name(self) -> str:
        """Human-readable name shown in vault notes."""
        ...

    @abstractmethod
    def poll(self) -> list[TelemetryEvent]:
        """
        Poll the external system for new events since last call.
        Returns a list of new TelemetryEvent objects (may be empty).
        Must never raise — return [] on failure.
        """
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """Return True if the external system is reachable."""
        ...


# ==================================================================
# Hub (Observer Dispatcher)
# ==================================================================

EventCallback = Callable[[TelemetryEvent], None]


class TelemetryHub:
    """
    Central observer that manages providers and dispatches events.

    Usage:
        hub = TelemetryHub()
        hub.register(JitbitConnector(...))
        hub.subscribe(my_callback)
        events = hub.poll_all()  # polls every provider, dispatches to subscribers
    """

    def __init__(self):
        self._providers: dict[str, TelemetryProvider] = {}
        self._subscribers: list[EventCallback] = []
        self._event_log: list[TelemetryEvent] = []
        self._lock = threading.Lock()

    def register(self, provider: TelemetryProvider) -> None:
        """Register a telemetry provider."""
        with self._lock:
            pid = provider.provider_id
            if pid in self._providers:
                logger.warning("Provider '%s' already registered, replacing", pid)
            self._providers[pid] = provider
            logger.info("Registered telemetry provider: %s (%s)", pid, provider.display_name)

    def unregister(self, provider_id: str) -> bool:
        """Remove a provider by id. Returns True if found."""
        with self._lock:
            if provider_id in self._providers:
                del self._providers[provider_id]
                logger.info("Unregistered telemetry provider: %s", provider_id)
                return True
            return False

    def subscribe(self, callback: EventCallback) -> None:
        """Add a subscriber that receives every event."""
        with self._lock:
            self._subscribers.append(callback)

    def poll_all(self) -> list[TelemetryEvent]:
        """
        Poll every registered provider and dispatch events.
        Returns all collected events.
        """
        all_events: list[TelemetryEvent] = []

        with self._lock:
            providers = list(self._providers.values())

        for provider in providers:
            try:
                events = provider.poll()
                all_events.extend(events)
            except Exception as e:
                logger.warning("Provider '%s' poll failed: %s", provider.provider_id, e)
                all_events.append(TelemetryEvent(
                    event_type=EventType.LOG,
                    source=provider.provider_id,
                    message=f"Poll error: {e}",
                    data={"error": True},
                ))

        # Dispatch to subscribers
        with self._lock:
            subscribers = list(self._subscribers)

        for event in all_events:
            for cb in subscribers:
                try:
                    cb(event)
                except Exception as e:
                    logger.warning("Subscriber callback error: %s", e)

        # Append to internal log
        with self._lock:
            self._event_log.extend(all_events)

        return all_events

    def get_event_log(self) -> list[TelemetryEvent]:
        """Return a copy of all events received so far."""
        with self._lock:
            return list(self._event_log)

    def get_events_by_source(self, source: str) -> list[TelemetryEvent]:
        """Return events filtered by provider source id."""
        with self._lock:
            return [e for e in self._event_log if e.source == source]

    @property
    def provider_ids(self) -> list[str]:
        """List registered provider ids."""
        with self._lock:
            return list(self._providers.keys())

    def health(self) -> dict[str, bool]:
        """Run health_check on all providers. Returns {id: bool}."""
        with self._lock:
            providers = list(self._providers.values())

        results = {}
        for p in providers:
            try:
                results[p.provider_id] = p.health_check()
            except Exception:
                results[p.provider_id] = False
        return results


# ==================================================================
# JitbitConnector
# ==================================================================

class JitbitConnector(TelemetryProvider):
    """
    Connector for Jitbit helpdesk / automation platform.

    In production, this would call the Jitbit REST API.
    Currently implements the provider interface with a local event buffer
    so the rest of the pipeline (Hub -> ObsidianBridge) can be tested
    end-to-end before the Jitbit API is wired.
    """

    def __init__(self, base_url: str = "", api_token: str = ""):
        self._base_url = base_url
        self._api_token = api_token
        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()

    @property
    def provider_id(self) -> str:
        return "jitbit"

    @property
    def display_name(self) -> str:
        return "Jitbit Helpdesk"

    def push_event(self, event_type: EventType, message: str,
                   data: dict[str, Any] | None = None) -> None:
        """
        Push a synthetic event into the buffer.
        Used by the orchestration layer to record Jitbit actions
        before the REST API integration is complete.
        """
        with self._lock:
            self._buffer.append(TelemetryEvent(
                event_type=event_type,
                source=self.provider_id,
                message=message,
                data=data or {},
            ))

    def poll(self) -> list[TelemetryEvent]:
        """Drain the buffer and return all pending events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        """
        Returns True if the connector is operational.
        When base_url is empty (pre-integration), returns True
        so the pipeline doesn't block.
        """
        if not self._base_url:
            return True
        # Future: HTTP HEAD to self._base_url
        return True

    def persist_to_graph(self, graph_manager, events: list[TelemetryEvent] | None = None) -> int:
        """
        Write events to Neo4j as ExternalSync nodes.
        Returns count of persisted events.
        """
        from src.neural_link.graph import queries as q

        target = events if events is not None else self.get_buffered_events()
        if not graph_manager or not target:
            return 0

        batch = []
        for ev in target:
            batch.append((q.UPSERT_EXTERNAL_SYNC, {
                "id": f"jitbit_{ev.timestamp}",
                "source": ev.source,
                "event_type": ev.event_type.value if isinstance(ev.event_type, EventType) else ev.event_type,
                "message": ev.message,
                "data": str(ev.data),
                "created_at": ev.timestamp,
                "phase": ev.data.get("phase", "unknown"),
            }))

        try:
            return graph_manager.execute_write_batch(batch)
        except Exception as e:
            logger.warning("JitbitConnector.persist_to_graph failed: %s", e)
            return 0

    def get_buffered_events(self) -> list[TelemetryEvent]:
        """Peek at buffer without draining."""
        with self._lock:
            return list(self._buffer)


# ==================================================================
# K8s Event Buffer (para Sovereign Gateway)
# ==================================================================


class CrmEventProvider(TelemetryProvider):
    """
    Buffer-based CRM event provider.
    CRM endpoints push events here; TelemetryHub polls them so they
    also appear in /ws/telemetry alongside K8s and Jitbit events.
    """

    def __init__(self) -> None:
        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()

    @property
    def provider_id(self) -> str:
        return "crm"

    @property
    def display_name(self) -> str:
        return "CRM Events"

    def push(self, event_type_str: str, message: str,
             data: dict[str, Any] | None = None) -> None:
        """Push a CRM event into the buffer."""
        # Map CRM event strings to EventType
        mapping = {
            "lead_created": EventType.TASK_STARTED,
            "lead_updated": EventType.TASK_COMPLETED,
            "interaction_recorded": EventType.LOG,
            "flow_status_changed": EventType.SYNC_TRIGGERED,
        }
        et = mapping.get(event_type_str, EventType.LOG)
        with self._lock:
            self._buffer.append(TelemetryEvent(
                event_type=et,
                source=self.provider_id,
                message=message,
                data=data or {},
            ))

    def poll(self) -> list[TelemetryEvent]:
        """Drain buffer and return pending events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        return True


class K8sEventBufferProvider(TelemetryProvider):
    """
    Buffer de eventos K8s (CrashLoopBackOff, etc.) para broadcast via WebSocket.
    PodStatusMonitor faz push; TelemetryHub faz poll.
    """

    def __init__(self) -> None:
        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()

    @property
    def provider_id(self) -> str:
        return "k8s-monitor"

    @property
    def display_name(self) -> str:
        return "Kubernetes Monitor"

    def push_pod_failure(self, pod_name: str, namespace: str, reason: str = "CrashLoopBackOff", **kwargs: Any) -> None:
        """Push evento de falha de Pod."""
        with self._lock:
            self._buffer.append(TelemetryEvent(
                event_type=EventType.CRITICAL_ANOMALY,
                source=self.provider_id,
                message=f"Pod {pod_name}/{namespace}: {reason}",
                data={"pod_name": pod_name, "namespace": namespace, "reason": reason, **kwargs},
            ))

    def poll(self) -> list[TelemetryEvent]:
        """Drain buffer e retorna eventos pendentes."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        return True
