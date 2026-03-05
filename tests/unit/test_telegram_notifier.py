"""
Unit tests for TelegramNotifier.

Tests message formatting, retry logic, message splitting, and queue management.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from collections import deque

from src.neural_link.k8s_monitoring.telegram_notifier import TelegramNotifier
from src.neural_link.k8s_monitoring.pod_status_monitor import PodFailureEvent


class TestTelegramNotifier:
    """Unit tests for TelegramNotifier class."""

    def test_initialization(self):
        """Test TelegramNotifier initializes with correct configuration."""
        notifier = TelegramNotifier(
            bot_token="test_token",
            default_chat_id=12345,
            max_retries=5,
            max_queue_size=200,
        )

        assert notifier.bot_token == "test_token"
        assert notifier.default_chat_id == 12345
        assert notifier.max_retries == 5
        assert isinstance(notifier.message_queue, deque)
        assert notifier.message_queue.maxlen == 200
        assert notifier.base_url == "https://api.telegram.org/bottest_token"

    def test_initialization_without_default_chat_id(self):
        """Test TelegramNotifier can be initialized without default chat ID."""
        notifier = TelegramNotifier(bot_token="test_token")

        assert notifier.default_chat_id is None

    def test_format_pod_failure_message_basic(self):
        """Test _format_pod_failure_message creates properly formatted message."""
        notifier = TelegramNotifier(bot_token="test_token")

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
            container_name="test-container",
            reason="CrashLoopBackOff",
            message="Container failed",
            restart_count=3,
            timestamp="2024-01-01T00:00:00Z",
        )

        message = notifier._format_pod_failure_message(
            failure=failure,
            suggestion="Check database connection",
            logs="Error: Connection refused",
        )

        # Verify message contains all required fields
        assert "test-pod" in message
        assert "default" in message
        assert "test-container" in message
        assert "CrashLoopBackOff" in message
        assert "Container failed" in message
        assert "3" in message
        assert "Check database connection" in message
        assert "Error: Connection refused" in message
        assert "2024-01-01T00:00:00Z" in message

        # Verify Markdown formatting
        assert "*Pod Failure Detected*" in message
        assert "*Pod:*" in message
        assert "*Namespace:*" in message
        assert "*Container:*" in message

    def test_format_pod_failure_message_neo4j(self):
        """Test _format_pod_failure_message uses Neo4j emoji for Neo4j pods."""
        notifier = TelegramNotifier(bot_token="test_token")

        failure = PodFailureEvent(
            pod_name="neo4j-0",
            namespace="bunker",
            container_name="neo4j",
            is_neo4j=True,
        )

        message = notifier._format_pod_failure_message(failure)

        assert "🔴 Neo4j" in message

    def test_format_pod_failure_message_chromadb(self):
        """Test _format_pod_failure_message uses ChromaDB emoji for ChromaDB pods."""
        notifier = TelegramNotifier(bot_token="test_token")

        failure = PodFailureEvent(
            pod_name="chromadb-abc",
            namespace="default",
            container_name="chroma",
            is_chromadb=True,
        )

        message = notifier._format_pod_failure_message(failure)

        assert "🔴 ChromaDB" in message

    def test_format_pod_failure_message_with_last_state(self):
        """Test _format_pod_failure_message includes last terminated state."""
        notifier = TelegramNotifier(bot_token="test_token")

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
            container_name="test",
            last_state={
                "exit_code": 1,
                "reason": "Error",
                "message": "Container crashed",
                "finished_at": "2024-01-01T00:05:00Z",
            },
        )

        message = notifier._format_pod_failure_message(failure)

        assert "Last Terminated State" in message
        assert "Exit Code: 1" in message
        assert "Reason: Error" in message
        assert "Message: Container crashed" in message

    def test_format_pod_failure_message_without_optional_fields(self):
        """Test _format_pod_failure_message handles missing optional fields."""
        notifier = TelegramNotifier(bot_token="test_token")

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
        )

        # Should not raise exception
        message = notifier._format_pod_failure_message(failure)

        assert "test-pod" in message
        assert "default" in message

    def test_split_message_short_message(self):
        """Test _split_message returns single message for short text."""
        notifier = TelegramNotifier(bot_token="test_token")

        text = "Short message"
        messages = notifier._split_message(text)

        assert len(messages) == 1
        assert messages[0] == text

    def test_split_message_long_message(self):
        """Test _split_message splits long messages correctly."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Create message longer than 4096 characters
        text = "Line\n" * 1000  # ~5000 characters
        messages = notifier._split_message(text, max_length=100)

        assert len(messages) > 1
        for msg in messages:
            assert len(msg) <= 100

    def test_split_message_preserves_lines(self):
        """Test _split_message splits on line boundaries."""
        notifier = TelegramNotifier(bot_token="test_token")

        text = "Line 1\nLine 2\nLine 3\nLine 4"
        messages = notifier._split_message(text, max_length=20)

        # Each message should contain complete lines
        for msg in messages:
            assert not msg.endswith("\n")

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_send_message_success(self, mock_client_class):
        """Test _send_message sends message successfully."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = notifier._send_message(
            chat_id=12345,
            text="Test message",
            parse_mode="Markdown",
        )

        assert result is True
        mock_client.__enter__.return_value.post.assert_called_once()

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_send_message_failure(self, mock_client_class):
        """Test _send_message handles API errors."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Mock failed response
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        result = notifier._send_message(
            chat_id=12345,
            text="Test message",
        )

        assert result is False

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    @patch("time.sleep")
    def test_send_with_retry_success_on_first_attempt(self, mock_sleep, mock_client_class):
        """Test _send_with_retry succeeds on first attempt."""
        notifier = TelegramNotifier(bot_token="test_token", max_retries=3)

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = notifier._send_with_retry(
            chat_id=12345,
            text="Test message",
        )

        assert result is True
        mock_sleep.assert_not_called()

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    @patch("time.sleep")
    def test_send_with_retry_exponential_backoff(self, mock_sleep, mock_client_class):
        """Test _send_with_retry uses exponential backoff."""
        notifier = TelegramNotifier(bot_token="test_token", max_retries=3)

        # Mock failed responses then success
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = [
            Exception("Error 1"),
            Exception("Error 2"),
            Mock(raise_for_status=Mock()),
        ]
        mock_client_class.return_value = mock_client

        result = notifier._send_with_retry(
            chat_id=12345,
            text="Test message",
        )

        assert result is True
        # Should sleep 1s, then 2s (exponential backoff: 2^0, 2^1)
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    @patch("time.sleep")
    def test_send_with_retry_all_attempts_fail(self, mock_sleep, mock_client_class):
        """Test _send_with_retry queues message after all retries fail."""
        notifier = TelegramNotifier(bot_token="test_token", max_retries=3)

        # Mock all failed responses
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = Exception("API error")
        mock_client_class.return_value = mock_client

        result = notifier._send_with_retry(
            chat_id=12345,
            text="Test message",
        )

        assert result is False
        # Should have queued the message
        assert len(notifier.message_queue) == 1
        assert notifier.message_queue[0]["chat_id"] == 12345
        assert notifier.message_queue[0]["text"] == "Test message"

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_send_pod_failure_alert_success(self, mock_client_class):
        """Test send_pod_failure_alert sends formatted alert."""
        notifier = TelegramNotifier(
            bot_token="test_token",
            default_chat_id=12345,
        )

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
            container_name="test",
        )

        result = notifier.send_pod_failure_alert(
            status=failure,
            logs="Error logs",
            suggestion="Fix suggestion",
        )

        assert result is True
        mock_client.__enter__.return_value.post.assert_called_once()

    def test_send_pod_failure_alert_no_chat_id(self):
        """Test send_pod_failure_alert fails without chat ID."""
        notifier = TelegramNotifier(bot_token="test_token")

        failure = PodFailureEvent(
            pod_name="test-pod",
            namespace="default",
        )

        result = notifier.send_pod_failure_alert(
            status=failure,
            logs="",
            suggestion="",
        )

        assert result is False

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_send_cluster_status_success(self, mock_client_class):
        """Test send_cluster_status sends formatted status."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        result = notifier.send_cluster_status(
            formatted_status="Cluster status: OK",
            chat_id=12345,
        )

        assert result is True
        mock_client.__enter__.return_value.post.assert_called_once()

    def test_queue_message(self):
        """Test _queue_message adds message to queue."""
        notifier = TelegramNotifier(bot_token="test_token")

        message = {
            "chat_id": 12345,
            "text": "Test message",
            "parse_mode": "Markdown",
        }

        notifier._queue_message(message)

        assert len(notifier.message_queue) == 1
        assert notifier.message_queue[0] == message

    def test_queue_respects_max_size(self):
        """Test message queue respects max_queue_size limit."""
        notifier = TelegramNotifier(
            bot_token="test_token",
            max_queue_size=2,
        )

        # Add 3 messages
        for i in range(3):
            notifier._queue_message(
                {
                    "chat_id": i,
                    "text": f"Message {i}",
                }
            )

        # Queue should only contain last 2 messages
        assert len(notifier.message_queue) == 2
        assert notifier.message_queue[0]["chat_id"] == 1
        assert notifier.message_queue[1]["chat_id"] == 2

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_process_queue_success(self, mock_client_class):
        """Test process_queue sends all queued messages."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Add messages to queue
        notifier._queue_message({"chat_id": 1, "text": "Message 1"})
        notifier._queue_message({"chat_id": 2, "text": "Message 2"})

        sent_count = notifier.process_queue()

        assert sent_count == 2
        assert len(notifier.message_queue) == 0

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_process_queue_partial_failure(self, mock_client_class):
        """Test process_queue re-queues failed messages."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Mock first success, second failure
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.side_effect = [
            Mock(raise_for_status=Mock()),
            Exception("API error"),
            Exception("API error"),  # Retry also fails
        ]
        mock_client_class.return_value = mock_client

        # Add messages to queue
        notifier._queue_message({"chat_id": 1, "text": "Message 1"})
        notifier._queue_message({"chat_id": 2, "text": "Message 2"})

        sent_count = notifier.process_queue()

        assert sent_count == 1
        # Failed message should be re-queued
        assert len(notifier.message_queue) == 1
        assert notifier.message_queue[0]["chat_id"] == 2

    def test_process_queue_empty(self):
        """Test process_queue handles empty queue."""
        notifier = TelegramNotifier(bot_token="test_token")

        sent_count = notifier.process_queue()

        assert sent_count == 0

    @patch("src.neural_link.k8s_monitoring.telegram_notifier.httpx.Client")
    def test_send_with_retry_splits_long_messages(self, mock_client_class):
        """Test _send_with_retry splits messages exceeding 4096 characters."""
        notifier = TelegramNotifier(bot_token="test_token")

        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status = Mock()
        mock_client = MagicMock()
        mock_client.__enter__.return_value.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Create long message
        long_text = "A" * 5000

        result = notifier._send_with_retry(
            chat_id=12345,
            text=long_text,
        )

        assert result is True
        # Should have sent multiple messages
        assert mock_client.__enter__.return_value.post.call_count > 1
