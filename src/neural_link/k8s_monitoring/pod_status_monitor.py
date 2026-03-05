"""
PodStatusMonitor - Monitors Pod events and detects CrashLoopBackOff.

Task 5.x: Pod status monitoring for neo4j and chromadb.
When a pod enters CrashLoopBackOff, dispatches PodFailureEvent for SpecialistAgent.
Envia payload para webhook n8n para feedback loop (botão Aprovar Correção no Telegram).
"""

import logging
import os
from collections import deque
from dataclasses import dataclass, field
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Webhook n8n para feedback loop (K8sEventMonitor -> n8n -> Telegram)
N8N_WEBHOOK_URL = os.environ.get("N8N_WEBHOOK_URL", "")

# Pod labels/names we care about (neo4j, chromadb)
MONITORED_POD_PATTERNS = ("neo4j", "chromadb", "chroma")


@dataclass
class PodFailureEvent:
    """Event emitted when a Pod enters CrashLoopBackOff."""

    pod_name: str
    namespace: str
    container_name: Optional[str] = None
    reason: str = "CrashLoopBackOff"
    message: Optional[str] = None
    restart_count: int = 0
    last_state: Optional[dict] = None
    timestamp: Optional[str] = None
    is_neo4j: bool = False
    is_chromadb: bool = False


class PodStatusMonitor:
    """
    Handles Pod events from K8sEventMonitor.
    Detects CrashLoopBackOff and dispatches internal events for SpecialistAgent.
    """

    def __init__(
        self,
        log_analyzer: Optional[object] = None,
        specialist_agent: Optional[object] = None,
        notifier: Optional[object] = None,
        max_queue_size: int = 50,
    ):
        """
        Initialize PodStatusMonitor.

        Args:
            log_analyzer: KubectlLogAnalyzer for fetching pod logs
            specialist_agent: SpecialistAgent for log analysis
            notifier: TelegramNotifier for alerts
            max_queue_size: Max failures in FIFO queue (priority for Neo4j)
        """
        self._log_analyzer = log_analyzer
        self._specialist_agent = specialist_agent
        self._notifier = notifier
        self._failure_queue: deque[PodFailureEvent] = deque(maxlen=max_queue_size)
        self._handlers: list[Callable[[PodFailureEvent], None]] = []

    def handle_pod_event(self, event: dict, hook: dict) -> None:
        """
        Process Pod event from K8sEventMonitor.
        Called when event matches hook (e.g. CrashLoopBackOff filter).

        Args:
            event: Kubernetes event dict with 'type' and 'object'
            hook: Hook configuration
        """
        obj = event.get("object")
        if not obj:
            return

        if not self._is_crash_loop_backoff(obj):
            return

        failure_info = self._extract_failure_info(obj)
        if not failure_info:
            return

        logger.info(
            "Pod failure detected: %s/%s (reason=%s)",
            failure_info.namespace,
            failure_info.pod_name,
            failure_info.reason,
        )

        # Add to queue (FIFO, Neo4j gets priority when processing)
        self._failure_queue.append(failure_info)

        # Dispatch to internal handlers
        for handler in self._handlers:
            try:
                handler(failure_info)
            except Exception as e:
                logger.error("Handler error for PodFailureEvent: %s", e, exc_info=True)

        # Orchestrate analysis pipeline
        self._analyze_failure(failure_info)

    def _is_crash_loop_backoff(self, obj: object) -> bool:
        """Check if Pod is in CrashLoopBackOff state."""
        if not hasattr(obj, "status") or obj.status is None:
            return False

        status = obj.status
        if not hasattr(status, "containerStatuses") or not status.containerStatuses:
            return False

        for cs in status.containerStatuses:
            if not hasattr(cs, "state") or cs.state is None:
                continue
            waiting = getattr(cs.state, "waiting", None)
            if waiting and getattr(waiting, "reason", None) == "CrashLoopBackOff":
                return True

        return False

    def _extract_failure_info(self, obj: object) -> Optional[PodFailureEvent]:
        """Extract PodFailureEvent from Pod object."""
        if not hasattr(obj, "metadata") or obj.metadata is None:
            return None

        name = getattr(obj.metadata, "name", None) or "unknown"
        namespace = getattr(obj.metadata, "namespace", None) or "default"

        container_name = None
        message = None
        restart_count = 0
        last_state = None

        if hasattr(obj, "status") and obj.status and hasattr(obj.status, "containerStatuses"):
            for cs in obj.status.containerStatuses:
                waiting = getattr(getattr(cs, "state", None), "waiting", None)
                if waiting and getattr(waiting, "reason", None) == "CrashLoopBackOff":
                    container_name = getattr(cs, "name", None)
                    message = getattr(waiting, "message", None)
                    restart_count = getattr(cs, "restartCount", 0)
                    
                    # Extract last terminated state
                    last_terminated = getattr(cs, "lastState", None)
                    if last_terminated:
                        terminated = getattr(last_terminated, "terminated", None)
                        if terminated:
                            last_state = {
                                "exit_code": getattr(terminated, "exitCode", None),
                                "reason": getattr(terminated, "reason", None),
                                "message": getattr(terminated, "message", None),
                                "finished_at": str(getattr(terminated, "finishedAt", "")),
                            }
                    break

        # Get timestamp from metadata
        timestamp = None
        if hasattr(obj.metadata, "creationTimestamp"):
            timestamp = str(obj.metadata.creationTimestamp)

        pod_lower = name.lower()
        is_neo4j = "neo4j" in pod_lower
        is_chromadb = "chroma" in pod_lower

        return PodFailureEvent(
            pod_name=name,
            namespace=namespace,
            container_name=container_name,
            reason="CrashLoopBackOff",
            message=message,
            restart_count=restart_count,
            last_state=last_state,
            timestamp=timestamp,
            is_neo4j=is_neo4j,
            is_chromadb=is_chromadb,
        )

    def _analyze_failure(self, failure: PodFailureEvent) -> None:
        """
        Orchestrate failure analysis: logs -> SpecialistAgent -> Notifier.
        Neo4j pods get priority.
        """
        try:
            logs = ""
            if self._log_analyzer and hasattr(self._log_analyzer, "get_pod_logs"):
                logs = self._log_analyzer.get_pod_logs(
                    failure.pod_name,
                    failure.namespace,
                    tail_lines=50,
                    container=failure.container_name,
                ) or ""

            suggestion = ""
            if self._specialist_agent and hasattr(self._specialist_agent, "analyze_pod_logs"):
                suggestion = self._specialist_agent.analyze_pod_logs(
                    logs,
                    pod_name=failure.pod_name,
                    namespace=failure.namespace,
                ) or ""

            if self._notifier and hasattr(self._notifier, "send_pod_failure_alert"):
                self._notifier.send_pod_failure_alert(
                    status=failure,
                    logs=logs[:2000] if logs else "",
                    suggestion=suggestion,
                )

            # Feedback loop: POST para webhook n8n -> workflow envia "Aprovar Correção" no Telegram
            self._post_to_n8n_webhook(failure, logs, suggestion)
        except Exception as e:
            logger.error("Failure analysis error: %s", e, exc_info=True)

    def _post_to_n8n_webhook(
        self,
        failure: "PodFailureEvent",
        logs: str,
        suggestion: str,
    ) -> None:
        """Envia payload para webhook n8n para processar e enviar botão Aprovar Correção."""
        url = os.environ.get("N8N_WEBHOOK_URL") or N8N_WEBHOOK_URL
        if not url:
            logger.debug("N8N_WEBHOOK_URL não configurado, pulando POST para n8n")
            return
        try:
            import httpx
            payload = {
                "pod_name": failure.pod_name,
                "namespace": failure.namespace,
                "reason": failure.reason,
                "container_name": failure.container_name,
                "message": failure.message,
                "is_neo4j": failure.is_neo4j,
                "is_chromadb": failure.is_chromadb,
                "logs": logs[:1500] if logs else "",
                "suggestion": suggestion,
                "restart_count": failure.restart_count,
            }
            with httpx.Client(timeout=10) as client:
                r = client.post(url, json=payload)
            if r.status_code in (200, 201, 204):
                logger.info("Payload enviado para n8n webhook com sucesso")
            else:
                logger.warning("n8n webhook retornou %s: %s", r.status_code, r.text[:200])
        except Exception as e:
            logger.warning("Falha ao POST para n8n webhook: %s", e)

    def register_handler(self, handler: Callable[[PodFailureEvent], None]) -> None:
        """Register handler for PodFailureEvent."""
        self._handlers.append(handler)

    @property
    def failure_queue(self) -> deque:
        """Expose failure queue for tests."""
        return self._failure_queue
