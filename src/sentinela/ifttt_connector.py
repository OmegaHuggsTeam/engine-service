"""
IFTTT Connector - Connectivity watchdog and exponential retry for external alerts.

Task 7: Connectivity Watchdog

Features:
- Health check for IFTTT Maker Webhook connectivity
- Offline isolation detection (403/404/network errors)
- Exponential retry logic (30s, 1min, 5min)
- TelemetryHub integration for OFFLINE_ISOLATION events
- Obsidian logging for definitive failures
"""

import json
import logging
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class AlertStatus(Enum):
    """Status of alert delivery."""

    PENDING = "pending"
    SENDING = "sending"
    SUCCESS = "success"
    RETRYING = "retrying"
    FAILED = "failed"
    OFFLINE = "offline"


class ConnectivityStatus(Enum):
    """Connectivity status with IFTTT."""

    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class RetryConfig:
    """Configuration for exponential retry logic."""

    delays_seconds: List[int] = field(default_factory=lambda: [30, 60, 300])  # 30s, 1min, 5min
    max_attempts: int = 3

    def get_delay(self, attempt: int) -> Optional[int]:
        """
        Get delay for retry attempt.

        Args:
            attempt: Retry attempt number (0-indexed)

        Returns:
            Delay in seconds, or None if max attempts exceeded
        """
        if attempt >= len(self.delays_seconds):
            return None
        return self.delays_seconds[attempt]


@dataclass
class AlertAttempt:
    """Record of an alert delivery attempt."""

    timestamp: datetime
    attempt_number: int
    status: AlertStatus
    http_code: Optional[int] = None
    error_message: Optional[str] = None
    response_data: Optional[str] = None


@dataclass
class Alert:
    """Alert to be sent via IFTTT."""

    alert_id: str
    event_name: str
    value1: str
    value2: Optional[str] = None
    value3: Optional[str] = None
    status: AlertStatus = AlertStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    attempts: List[AlertAttempt] = field(default_factory=list)
    next_retry_at: Optional[datetime] = None

    def add_attempt(
        self,
        attempt_number: int,
        status: AlertStatus,
        http_code: Optional[int] = None,
        error_message: Optional[str] = None,
        response_data: Optional[str] = None,
    ) -> None:
        """Record an attempt to send this alert."""
        attempt = AlertAttempt(
            timestamp=datetime.now(),
            attempt_number=attempt_number,
            status=status,
            http_code=http_code,
            error_message=error_message,
            response_data=response_data,
        )
        self.attempts.append(attempt)
        self.status = status


class IFTTTConnector:
    """
    IFTTT Maker Webhook connector with health checks and retry logic.

    Features:
    - Health check before sending critical alerts
    - Offline isolation detection
    - Exponential retry with configurable delays
    - TelemetryHub integration
    - Obsidian logging for failures
    """

    def __init__(
        self,
        webhook_key: str,
        retry_config: Optional[RetryConfig] = None,
        telemetry_hub=None,
        obsidian_logger=None,
        health_check_timeout: float = 5.0,
    ):
        """
        Initialize IFTTT connector.

        Args:
            webhook_key: IFTTT Maker Webhook key
            retry_config: Retry configuration (uses default if None)
            telemetry_hub: Optional TelemetryHub for event reporting
            obsidian_logger: Optional Obsidian logger for failure tracking
            health_check_timeout: Timeout for health checks in seconds
        """
        self.webhook_key = webhook_key
        self.retry_config = retry_config or RetryConfig()
        self.telemetry_hub = telemetry_hub
        self.obsidian_logger = obsidian_logger
        self.health_check_timeout = health_check_timeout

        # Connectivity state
        self.connectivity_status = ConnectivityStatus.UNKNOWN
        self.last_health_check: Optional[datetime] = None
        self.last_successful_send: Optional[datetime] = None

        # Alert queue for retry management
        self.pending_alerts: Dict[str, Alert] = {}

        # Statistics
        self.total_alerts_sent = 0
        self.total_alerts_failed = 0
        self.total_retries = 0
        self.offline_events = 0

        logger.info(
            "IFTTTConnector initialized with retry delays: %s", self.retry_config.delays_seconds
        )

    def health_check(self) -> Tuple[bool, ConnectivityStatus, str]:
        """
        Check connectivity with IFTTT Maker Webhook servers.

        Verifies that:
        1. Network is accessible
        2. IFTTT servers are reachable
        3. Webhook key is valid (not 403/404)

        Returns:
            (is_healthy, status, message) tuple
        """
        logger.info("Performing IFTTT health check...")

        try:
            # Use a test event to verify connectivity
            test_url = f"https://maker.ifttt.com/trigger/health_check/with/key/{self.webhook_key}"

            req = urllib.request.Request(
                test_url, method="POST", headers={"Content-Type": "application/json"}
            )

            # Send empty payload
            data = json.dumps({}).encode("utf-8")

            with urllib.request.urlopen(
                req, data=data, timeout=self.health_check_timeout
            ) as response:
                http_code = response.status

                self.last_health_check = datetime.now()

                if http_code == 200:
                    self.connectivity_status = ConnectivityStatus.ONLINE
                    message = "IFTTT connectivity OK"
                    logger.info("✓ Health check passed: %s", message)
                    return True, ConnectivityStatus.ONLINE, message
                else:
                    self.connectivity_status = ConnectivityStatus.DEGRADED
                    message = f"IFTTT responded with HTTP {http_code}"
                    logger.warning("⚠ Health check degraded: %s", message)
                    return False, ConnectivityStatus.DEGRADED, message

        except urllib.error.HTTPError as e:
            self.last_health_check = datetime.now()

            if e.code in [403, 404]:
                # Invalid webhook key or endpoint
                self.connectivity_status = ConnectivityStatus.OFFLINE
                message = f"IFTTT authentication failed: HTTP {e.code}"
                logger.error("✗ Health check failed: %s", message)

                # Report offline isolation
                self._report_offline_isolation(reason=f"HTTP {e.code}", details=str(e))

                return False, ConnectivityStatus.OFFLINE, message
            else:
                self.connectivity_status = ConnectivityStatus.DEGRADED
                message = f"IFTTT HTTP error: {e.code}"
                logger.warning("⚠ Health check degraded: %s", message)
                return False, ConnectivityStatus.DEGRADED, message

        except urllib.error.URLError as e:
            # Network error (no internet, DNS failure, etc)
            self.last_health_check = datetime.now()
            self.connectivity_status = ConnectivityStatus.OFFLINE
            message = f"Network error: {e.reason}"
            logger.error("✗ Health check failed: %s", message)

            # Report offline isolation
            self._report_offline_isolation(reason="Network unreachable", details=str(e))

            return False, ConnectivityStatus.OFFLINE, message

        except Exception as e:
            self.last_health_check = datetime.now()
            self.connectivity_status = ConnectivityStatus.UNKNOWN
            message = f"Health check error: {e}"
            logger.error("✗ Health check error: %s", message)
            return False, ConnectivityStatus.UNKNOWN, message

    def send_alert(
        self,
        event_name: str,
        value1: str,
        value2: Optional[str] = None,
        value3: Optional[str] = None,
        alert_id: Optional[str] = None,
        critical: bool = False,
    ) -> Tuple[bool, str]:
        """
        Send alert to IFTTT with automatic retry on failure.

        Args:
            event_name: IFTTT event name (e.g., "telegram_alert")
            value1: First value (main message)
            value2: Second value (optional)
            value3: Third value (optional)
            alert_id: Unique alert ID (generated if None)
            critical: If True, perform health check before sending

        Returns:
            (success, message) tuple
        """
        # Generate alert ID if not provided
        if alert_id is None:
            alert_id = f"alert_{int(time.time() * 1000)}"

        # Create alert object
        alert = Alert(
            alert_id=alert_id, event_name=event_name, value1=value1, value2=value2, value3=value3
        )

        # Store in pending queue
        self.pending_alerts[alert_id] = alert

        # Perform health check for critical alerts
        if critical:
            is_healthy, status, message = self.health_check()

            if not is_healthy:
                logger.warning("Health check failed for critical alert '%s': %s", alert_id, message)

                # Schedule retry
                self._schedule_retry(alert, attempt=0)

                return False, f"Health check failed: {message}"

        # Attempt to send
        return self._attempt_send(alert, attempt=0)

    def _attempt_send(self, alert: Alert, attempt: int) -> Tuple[bool, str]:
        """
        Attempt to send alert to IFTTT.

        Args:
            alert: Alert to send
            attempt: Attempt number (0-indexed)

        Returns:
            (success, message) tuple
        """
        logger.info(
            "Sending alert '%s' (attempt %d/%d): %s",
            alert.alert_id,
            attempt + 1,
            self.retry_config.max_attempts,
            alert.event_name,
        )

        try:
            # Build webhook URL
            url = f"https://maker.ifttt.com/trigger/{alert.event_name}/with/key/{self.webhook_key}"

            # Build payload
            payload = {
                "value1": alert.value1,
                "value2": alert.value2 or "",
                "value3": alert.value3 or "",
            }

            # Send request
            req = urllib.request.Request(
                url, method="POST", headers={"Content-Type": "application/json"}
            )

            data = json.dumps(payload).encode("utf-8")

            with urllib.request.urlopen(req, data=data, timeout=10.0) as response:
                http_code = response.status
                response_data = response.read().decode("utf-8")

                if http_code == 200:
                    # Success
                    alert.add_attempt(
                        attempt_number=attempt,
                        status=AlertStatus.SUCCESS,
                        http_code=http_code,
                        response_data=response_data,
                    )

                    self.last_successful_send = datetime.now()
                    self.total_alerts_sent += 1

                    # Remove from pending queue
                    self.pending_alerts.pop(alert.alert_id, None)

                    logger.info("✓ Alert '%s' sent successfully", alert.alert_id)

                    return True, "Alert sent successfully"
                else:
                    # Unexpected status code
                    alert.add_attempt(
                        attempt_number=attempt,
                        status=AlertStatus.RETRYING,
                        http_code=http_code,
                        response_data=response_data,
                    )

                    logger.warning("⚠ Alert '%s' returned HTTP %d", alert.alert_id, http_code)

                    # Schedule retry
                    self._schedule_retry(alert, attempt)

                    return False, f"HTTP {http_code}: {response_data}"

        except urllib.error.HTTPError as e:
            # HTTP error (403, 404, 500, etc)
            error_msg = f"HTTP {e.code}: {e.reason}"

            alert.add_attempt(
                attempt_number=attempt,
                status=(
                    AlertStatus.RETRYING
                    if attempt < self.retry_config.max_attempts - 1
                    else AlertStatus.FAILED
                ),
                http_code=e.code,
                error_message=error_msg,
            )

            logger.error("✗ Alert '%s' failed: %s", alert.alert_id, error_msg)

            # Report offline isolation for 403/404
            if e.code in [403, 404]:
                self._report_offline_isolation(
                    reason=f"HTTP {e.code}", details=f"Alert '{alert.alert_id}' failed: {error_msg}"
                )

            # Schedule retry
            self._schedule_retry(alert, attempt)

            return False, error_msg

        except urllib.error.URLError as e:
            # Network error
            error_msg = f"Network error: {e.reason}"

            alert.add_attempt(
                attempt_number=attempt, status=AlertStatus.OFFLINE, error_message=error_msg
            )

            logger.error("✗ Alert '%s' failed: %s", alert.alert_id, error_msg)

            # Report offline isolation
            self._report_offline_isolation(
                reason="Network unreachable",
                details=f"Alert '{alert.alert_id}' failed: {error_msg}",
            )

            # Schedule retry
            self._schedule_retry(alert, attempt)

            return False, error_msg

        except Exception as e:
            # Unexpected error
            error_msg = f"Unexpected error: {e}"

            alert.add_attempt(
                attempt_number=attempt, status=AlertStatus.FAILED, error_message=error_msg
            )

            logger.error("✗ Alert '%s' failed: %s", alert.alert_id, error_msg)

            # Schedule retry
            self._schedule_retry(alert, attempt)

            return False, error_msg

    def _schedule_retry(self, alert: Alert, attempt: int) -> None:
        """
        Schedule retry for failed alert.

        Args:
            alert: Alert to retry
            attempt: Current attempt number (0-indexed)
        """
        next_attempt = attempt + 1

        if next_attempt >= self.retry_config.max_attempts:
            # Max attempts reached - mark as failed
            alert.status = AlertStatus.FAILED
            self.total_alerts_failed += 1

            logger.error(
                "✗ Alert '%s' failed definitively after %d attempts",
                alert.alert_id,
                self.retry_config.max_attempts,
            )

            # Log to Obsidian
            self._log_definitive_failure(alert)

            # Remove from pending queue
            self.pending_alerts.pop(alert.alert_id, None)

            return

        # Get retry delay
        delay = self.retry_config.get_delay(next_attempt)

        if delay is None:
            # No more retries configured
            alert.status = AlertStatus.FAILED
            self.total_alerts_failed += 1

            logger.error(
                "✗ Alert '%s' failed definitively (no more retries configured)", alert.alert_id
            )

            # Log to Obsidian
            self._log_definitive_failure(alert)

            # Remove from pending queue
            self.pending_alerts.pop(alert.alert_id, None)

            return

        # Schedule retry
        alert.next_retry_at = datetime.now()
        alert.next_retry_at = datetime.fromtimestamp(alert.next_retry_at.timestamp() + delay)
        alert.status = AlertStatus.RETRYING
        self.total_retries += 1

        logger.info(
            "⏱ Alert '%s' scheduled for retry in %ds (attempt %d/%d)",
            alert.alert_id,
            delay,
            next_attempt + 1,
            self.retry_config.max_attempts,
        )

    def process_retries(self) -> int:
        """
        Process pending retries.

        Should be called periodically to retry failed alerts.

        Returns:
            Number of retries processed
        """
        now = datetime.now()
        retries_processed = 0

        # Find alerts ready for retry
        alerts_to_retry = [
            alert
            for alert in self.pending_alerts.values()
            if alert.status == AlertStatus.RETRYING
            and alert.next_retry_at is not None
            and alert.next_retry_at <= now
        ]

        for alert in alerts_to_retry:
            # Determine attempt number
            attempt = len(alert.attempts)

            # Attempt send
            self._attempt_send(alert, attempt)

            retries_processed += 1

        return retries_processed

    def _report_offline_isolation(self, reason: str, details: str) -> None:
        """
        Report OFFLINE_ISOLATION event to TelemetryHub.

        Args:
            reason: Reason for offline isolation
            details: Additional details
        """
        self.offline_events += 1

        logger.warning("OFFLINE_ISOLATION detected: %s (total: %d)", reason, self.offline_events)

        if self.telemetry_hub:
            try:
                from src.neural_link.telemetry.provider import EventType, TelemetryEvent

                event = TelemetryEvent(
                    event_type=EventType.LOG,
                    source="sentinela_ifttt",
                    message=f"OFFLINE_ISOLATION: {reason}",
                    data={
                        "reason": reason,
                        "details": details,
                        "connectivity_status": self.connectivity_status.value,
                        "offline_events_count": self.offline_events,
                        "timestamp": datetime.now().isoformat(),
                    },
                )

                self.telemetry_hub._event_log.append(event)

                logger.info("OFFLINE_ISOLATION event reported to TelemetryHub")

            except Exception as e:
                logger.warning("Failed to report to TelemetryHub: %s", e)

    def _log_definitive_failure(self, alert: Alert) -> None:
        """
        Log definitive failure to Obsidian.

        Args:
            alert: Failed alert
        """
        logger.info("Logging definitive failure to Obsidian: %s", alert.alert_id)

        if self.obsidian_logger:
            try:
                # Format failure log
                log_entry = self._format_failure_log(alert)

                # Write to Obsidian
                self.obsidian_logger.log_failure(log_entry)

                logger.info("✓ Failure logged to Obsidian")

            except Exception as e:
                logger.error("Failed to log to Obsidian: %s", e)
        else:
            logger.warning("No Obsidian logger configured - failure not logged")

    def _format_failure_log(self, alert: Alert) -> str:
        """
        Format alert failure for Obsidian logging.

        Args:
            alert: Failed alert

        Returns:
            Formatted log entry
        """
        log = f"# Alert Failure: {alert.alert_id}\n\n"
        log += f"**Event**: {alert.event_name}\n"
        log += f"**Created**: {alert.created_at.isoformat()}\n"
        log += f"**Status**: {alert.status.value}\n"
        log += f"**Attempts**: {len(alert.attempts)}\n\n"

        log += "## Message\n\n"
        log += f"- Value1: {alert.value1}\n"
        if alert.value2:
            log += f"- Value2: {alert.value2}\n"
        if alert.value3:
            log += f"- Value3: {alert.value3}\n"
        log += "\n"

        log += "## Attempt History\n\n"
        for attempt in alert.attempts:
            log += f"### Attempt {attempt.attempt_number + 1}\n"
            log += f"- **Time**: {attempt.timestamp.isoformat()}\n"
            log += f"- **Status**: {attempt.status.value}\n"
            if attempt.http_code:
                log += f"- **HTTP Code**: {attempt.http_code}\n"
            if attempt.error_message:
                log += f"- **Error**: {attempt.error_message}\n"
            if attempt.response_data:
                log += f"- **Response**: {attempt.response_data}\n"
            log += "\n"

        return log

    def get_statistics(self) -> Dict[str, Any]:
        """Get connector statistics."""
        return {
            "connectivity_status": self.connectivity_status.value,
            "last_health_check": (
                self.last_health_check.isoformat() if self.last_health_check else None
            ),
            "last_successful_send": (
                self.last_successful_send.isoformat() if self.last_successful_send else None
            ),
            "total_alerts_sent": self.total_alerts_sent,
            "total_alerts_failed": self.total_alerts_failed,
            "total_retries": self.total_retries,
            "offline_events": self.offline_events,
            "pending_alerts": len(self.pending_alerts),
            "retry_config": {
                "delays_seconds": self.retry_config.delays_seconds,
                "max_attempts": self.retry_config.max_attempts,
            },
        }

    def get_pending_alerts(self) -> List[Dict[str, Any]]:
        """Get list of pending alerts."""
        return [
            {
                "alert_id": alert.alert_id,
                "event_name": alert.event_name,
                "status": alert.status.value,
                "created_at": alert.created_at.isoformat(),
                "attempts": len(alert.attempts),
                "next_retry_at": alert.next_retry_at.isoformat() if alert.next_retry_at else None,
            }
            for alert in self.pending_alerts.values()
        ]
