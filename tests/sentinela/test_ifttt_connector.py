"""
Unit tests for IFTTTConnector.

Tests health checks, retry logic, and offline isolation detection.
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import urllib.error

from src.sentinela.ifttt_connector import (
    IFTTTConnector,
    Alert,
    AlertStatus,
    ConnectivityStatus,
    RetryConfig
)


class TestRetryConfig:
    """Test RetryConfig functionality."""
    
    def test_default_delays(self):
        """Test default retry delays."""
        config = RetryConfig()
        
        assert config.delays_seconds == [30, 60, 300]
        assert config.max_attempts == 3
    
    def test_custom_delays(self):
        """Test custom retry delays."""
        config = RetryConfig(
            delays_seconds=[10, 20, 30],
            max_attempts=3
        )
        
        assert config.delays_seconds == [10, 20, 30]
        assert config.max_attempts == 3
    
    def test_get_delay(self):
        """Test getting delay for attempt."""
        config = RetryConfig(delays_seconds=[10, 20, 30])
        
        assert config.get_delay(0) == 10
        assert config.get_delay(1) == 20
        assert config.get_delay(2) == 30
        assert config.get_delay(3) is None  # Exceeded


class TestAlert:
    """Test Alert data class."""
    
    def test_alert_creation(self):
        """Test alert creation."""
        alert = Alert(
            alert_id="test_123",
            event_name="telegram_alert",
            value1="Test message"
        )
        
        assert alert.alert_id == "test_123"
        assert alert.event_name == "telegram_alert"
        assert alert.value1 == "Test message"
        assert alert.status == AlertStatus.PENDING
        assert len(alert.attempts) == 0
    
    def test_add_attempt(self):
        """Test adding attempt to alert."""
        alert = Alert(
            alert_id="test_123",
            event_name="telegram_alert",
            value1="Test message"
        )
        
        alert.add_attempt(
            attempt_number=0,
            status=AlertStatus.SENDING,
            http_code=200
        )
        
        assert len(alert.attempts) == 1
        assert alert.attempts[0].attempt_number == 0
        assert alert.attempts[0].status == AlertStatus.SENDING
        assert alert.attempts[0].http_code == 200
        assert alert.status == AlertStatus.SENDING


class TestIFTTTConnector:
    """Test IFTTTConnector functionality."""
    
    def test_initialization(self):
        """Test connector initialization."""
        connector = IFTTTConnector(webhook_key="test_key_123")
        
        assert connector.webhook_key == "test_key_123"
        assert connector.connectivity_status == ConnectivityStatus.UNKNOWN
        assert connector.total_alerts_sent == 0
        assert connector.total_alerts_failed == 0
        assert len(connector.pending_alerts) == 0
    
    def test_initialization_with_custom_retry(self):
        """Test connector with custom retry config."""
        retry_config = RetryConfig(
            delays_seconds=[5, 10, 15],
            max_attempts=3
        )
        
        connector = IFTTTConnector(
            webhook_key="test_key",
            retry_config=retry_config
        )
        
        assert connector.retry_config.delays_seconds == [5, 10, 15]
        assert connector.retry_config.max_attempts == 3
    
    @patch('urllib.request.urlopen')
    def test_health_check_success(self, mock_urlopen):
        """Test successful health check."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        is_healthy, status, message = connector.health_check()
        
        assert is_healthy
        assert status == ConnectivityStatus.ONLINE
        assert "OK" in message
        assert connector.connectivity_status == ConnectivityStatus.ONLINE
    
    @patch('urllib.request.urlopen')
    def test_health_check_http_403(self, mock_urlopen):
        """Test health check with 403 error."""
        # Mock 403 error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://maker.ifttt.com",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None
        )
        
        connector = IFTTTConnector(webhook_key="invalid_key")
        
        is_healthy, status, message = connector.health_check()
        
        assert not is_healthy
        assert status == ConnectivityStatus.OFFLINE
        assert "403" in message
        assert connector.connectivity_status == ConnectivityStatus.OFFLINE
        assert connector.offline_events == 1
    
    @patch('urllib.request.urlopen')
    def test_health_check_http_404(self, mock_urlopen):
        """Test health check with 404 error."""
        # Mock 404 error
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://maker.ifttt.com",
            code=404,
            msg="Not Found",
            hdrs={},
            fp=None
        )
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        is_healthy, status, message = connector.health_check()
        
        assert not is_healthy
        assert status == ConnectivityStatus.OFFLINE
        assert "404" in message
        assert connector.offline_events == 1
    
    @patch('urllib.request.urlopen')
    def test_health_check_network_error(self, mock_urlopen):
        """Test health check with network error."""
        # Mock network error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        is_healthy, status, message = connector.health_check()
        
        assert not is_healthy
        assert status == ConnectivityStatus.OFFLINE
        assert "Network" in message
        assert connector.offline_events == 1
    
    @patch('urllib.request.urlopen')
    def test_send_alert_success(self, mock_urlopen):
        """Test successful alert sending."""
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        success, message = connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        assert success
        assert "successfully" in message
        assert connector.total_alerts_sent == 1
        assert "test_123" not in connector.pending_alerts
    
    @patch('urllib.request.urlopen')
    def test_send_alert_with_health_check(self, mock_urlopen):
        """Test sending critical alert with health check."""
        # Mock successful responses for both health check and alert
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.read.return_value = b'{"status": "ok"}'
        mock_response.__enter__ = Mock(return_value=mock_response)
        mock_response.__exit__ = Mock(return_value=False)
        mock_urlopen.return_value = mock_response
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        success, message = connector.send_alert(
            event_name="telegram_alert",
            value1="Critical message",
            critical=True
        )
        
        assert success
        assert connector.total_alerts_sent == 1
    
    @patch('urllib.request.urlopen')
    def test_send_alert_failure_schedules_retry(self, mock_urlopen):
        """Test failed alert schedules retry."""
        # Mock network error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        success, message = connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        assert not success
        assert "Network" in message
        assert "test_123" in connector.pending_alerts
        
        alert = connector.pending_alerts["test_123"]
        assert alert.status == AlertStatus.RETRYING
        assert alert.next_retry_at is not None
    
    @patch('urllib.request.urlopen')
    def test_retry_logic_exponential_delays(self, mock_urlopen):
        """Test exponential retry delays."""
        # Mock network error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        retry_config = RetryConfig(delays_seconds=[10, 20, 30])
        connector = IFTTTConnector(
            webhook_key="test_key",
            retry_config=retry_config
        )
        
        # Send alert (will fail)
        connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        alert = connector.pending_alerts["test_123"]
        
        # Check first retry is scheduled for 10s
        first_retry = alert.next_retry_at
        assert first_retry is not None
        
        # Simulate time passing and retry
        alert.next_retry_at = datetime.now() - timedelta(seconds=1)
        connector.process_retries()
        
        # Check second retry is scheduled for 20s
        assert alert.status == AlertStatus.RETRYING
        assert len(alert.attempts) == 2
    
    @patch('urllib.request.urlopen')
    def test_max_retries_marks_as_failed(self, mock_urlopen):
        """Test alert marked as failed after max retries."""
        # Mock network error
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        retry_config = RetryConfig(delays_seconds=[1, 2], max_attempts=2)
        connector = IFTTTConnector(
            webhook_key="test_key",
            retry_config=retry_config
        )
        
        # Send alert (will fail)
        connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        # Process first retry
        alert = connector.pending_alerts["test_123"]
        alert.next_retry_at = datetime.now() - timedelta(seconds=1)
        connector.process_retries()
        
        # Process second retry (should fail definitively)
        alert.next_retry_at = datetime.now() - timedelta(seconds=1)
        connector.process_retries()
        
        # Alert should be removed from pending and marked as failed
        assert "test_123" not in connector.pending_alerts
        assert connector.total_alerts_failed == 1
    
    def test_process_retries_no_pending(self):
        """Test process_retries with no pending alerts."""
        connector = IFTTTConnector(webhook_key="test_key")
        
        retries_processed = connector.process_retries()
        
        assert retries_processed == 0
    
    @patch('urllib.request.urlopen')
    def test_process_retries_not_ready(self, mock_urlopen):
        """Test process_retries with alerts not ready for retry."""
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        connector = IFTTTConnector(webhook_key="test_key")
        
        # Send alert (will fail and schedule retry)
        connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        # Try to process retries immediately (not ready yet)
        retries_processed = connector.process_retries()
        
        assert retries_processed == 0
        assert "test_123" in connector.pending_alerts
    
    def test_get_statistics(self):
        """Test statistics retrieval."""
        connector = IFTTTConnector(webhook_key="test_key")
        
        stats = connector.get_statistics()
        
        assert "connectivity_status" in stats
        assert "total_alerts_sent" in stats
        assert "total_alerts_failed" in stats
        assert "total_retries" in stats
        assert "offline_events" in stats
        assert "pending_alerts" in stats
        assert "retry_config" in stats
    
    def test_get_pending_alerts(self):
        """Test getting pending alerts list."""
        connector = IFTTTConnector(webhook_key="test_key")
        
        # Create a pending alert manually
        alert = Alert(
            alert_id="test_123",
            event_name="telegram_alert",
            value1="Test message",
            status=AlertStatus.RETRYING
        )
        connector.pending_alerts["test_123"] = alert
        
        pending = connector.get_pending_alerts()
        
        assert len(pending) == 1
        assert pending[0]["alert_id"] == "test_123"
        assert pending[0]["status"] == "retrying"
    
    @patch('urllib.request.urlopen')
    def test_offline_isolation_reported_to_telemetry(self, mock_urlopen):
        """Test OFFLINE_ISOLATION event reported to TelemetryHub."""
        mock_urlopen.side_effect = urllib.error.HTTPError(
            url="https://maker.ifttt.com",
            code=403,
            msg="Forbidden",
            hdrs={},
            fp=None
        )
        
        # Mock TelemetryHub
        mock_telemetry = Mock()
        mock_telemetry._event_log = []
        
        connector = IFTTTConnector(
            webhook_key="test_key",
            telemetry_hub=mock_telemetry
        )
        
        # Trigger health check (will fail with 403)
        connector.health_check()
        
        # Verify event was logged
        assert len(mock_telemetry._event_log) == 1
        event = mock_telemetry._event_log[0]
        assert "OFFLINE_ISOLATION" in event.message
        assert event.data["reason"] == "HTTP 403"
    
    @patch('urllib.request.urlopen')
    def test_definitive_failure_logged_to_obsidian(self, mock_urlopen):
        """Test definitive failure logged to Obsidian."""
        mock_urlopen.side_effect = urllib.error.URLError("Network unreachable")
        
        # Mock Obsidian logger
        mock_obsidian = Mock()
        mock_obsidian.log_failure = Mock()
        
        retry_config = RetryConfig(delays_seconds=[1], max_attempts=1)
        connector = IFTTTConnector(
            webhook_key="test_key",
            retry_config=retry_config,
            obsidian_logger=mock_obsidian
        )
        
        # Send alert (will fail definitively after 1 attempt)
        connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        # Verify Obsidian logger was called
        assert mock_obsidian.log_failure.called
        log_entry = mock_obsidian.log_failure.call_args[0][0]
        assert "test_123" in log_entry
        assert "Alert Failure" in log_entry


@pytest.mark.integration
class TestIFTTTConnectorIntegration:
    """Integration tests for IFTTTConnector."""
    
    @patch('urllib.request.urlopen')
    def test_full_retry_workflow(self, mock_urlopen):
        """Test complete retry workflow from failure to success."""
        # First two attempts fail, third succeeds
        call_count = [0]
        
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] <= 2:
                raise urllib.error.URLError("Network unreachable")
            else:
                # Success on third attempt
                mock_response = MagicMock()
                mock_response.status = 200
                mock_response.read.return_value = b'{"status": "ok"}'
                mock_response.__enter__ = Mock(return_value=mock_response)
                mock_response.__exit__ = Mock(return_value=False)
                return mock_response
        
        mock_urlopen.side_effect = side_effect
        
        retry_config = RetryConfig(delays_seconds=[1, 2, 3])
        connector = IFTTTConnector(
            webhook_key="test_key",
            retry_config=retry_config
        )
        
        # Send alert (will fail initially)
        success, _ = connector.send_alert(
            event_name="telegram_alert",
            value1="Test message",
            alert_id="test_123"
        )
        
        assert not success
        assert "test_123" in connector.pending_alerts
        
        # Process first retry (will fail)
        alert = connector.pending_alerts["test_123"]
        alert.next_retry_at = datetime.now() - timedelta(seconds=1)
        connector.process_retries()
        
        assert "test_123" in connector.pending_alerts
        
        # Process second retry (will succeed)
        alert.next_retry_at = datetime.now() - timedelta(seconds=1)
        connector.process_retries()
        
        # Alert should be removed (success)
        assert "test_123" not in connector.pending_alerts
        assert connector.total_alerts_sent == 1
        assert connector.total_retries == 2
