"""
TelegramNotifier - Sends notifications to Telegram with retry logic.

This module implements the notification system for Kubernetes monitoring,
sending formatted alerts for Pod failures and cluster status responses.
"""

import logging
import time
from typing import Optional
from collections import deque
import httpx

from .pod_status_monitor import PodFailureEvent


logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Sends notifications to Telegram with retry logic and message queuing."""

    def __init__(
        self,
        bot_token: str,
        default_chat_id: Optional[int] = None,
        max_retries: int = 3,
        max_queue_size: int = 100,
    ):
        """
        Initialize TelegramNotifier.

        Args:
            bot_token: Telegram bot authentication token
            default_chat_id: Default chat ID for notifications (optional)
            max_retries: Maximum retry attempts for failed sends (default: 3)
            max_queue_size: Maximum size of message queue (default: 100)
        """
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id
        self.max_retries = max_retries
        self.message_queue: deque = deque(maxlen=max_queue_size)
        self.base_url = f"https://api.telegram.org/bot{bot_token}"

        logger.info(
            "TelegramNotifier initialized",
            extra={
                "default_chat_id": default_chat_id,
                "max_retries": max_retries,
                "max_queue_size": max_queue_size,
            },
        )

    def send_pod_failure_alert(
        self,
        status: PodFailureEvent,
        logs: str = "",
        suggestion: str = "",
        chat_id: Optional[int] = None,
    ) -> bool:
        """
        Send Pod failure alert with formatted message.

        Args:
            status: PodFailureEvent object containing failure details
            logs: Pod logs (truncated)
            suggestion: Analysis/suggestion from SpecialistAgent
            chat_id: Target chat ID (uses default if None)

        Returns:
            True if message sent successfully, False otherwise
        """
        target_chat_id = chat_id or self.default_chat_id
        if target_chat_id is None:
            logger.error("No chat_id provided and no default_chat_id configured")
            return False

        # Format the failure alert message
        message = self._format_pod_failure_message(status, suggestion, logs)

        logger.info(
            "Sending Pod failure alert",
            extra={
                "pod_name": status.pod_name,
                "namespace": status.namespace,
                "chat_id": target_chat_id,
            },
        )

        return self._send_with_retry(
            chat_id=target_chat_id,
            text=message,
            parse_mode="Markdown",
        )

    def send_cluster_status(
        self,
        formatted_status: str,
        chat_id: int,
    ) -> bool:
        """
        Send cluster status response.

        Args:
            formatted_status: Pre-formatted status message
            chat_id: Target chat ID

        Returns:
            True if message sent successfully, False otherwise
        """
        logger.info(
            "Sending cluster status",
            extra={"chat_id": chat_id},
        )

        return self._send_with_retry(
            chat_id=chat_id,
            text=formatted_status,
            parse_mode="Markdown",
        )

    def _format_pod_failure_message(
        self,
        failure: PodFailureEvent,
        suggestion: str = "",
        logs: str = "",
    ) -> str:
        """
        Format Pod failure event into a rich Telegram message.

        Args:
            failure: PodFailureEvent object
            suggestion: Suggestion from SpecialistAgent
            logs: Pod logs (truncated)

        Returns:
            Formatted message string with Markdown
        """
        # Status emoji based on failure type
        emoji = "🔴"
        if failure.is_neo4j:
            emoji = "🔴 Neo4j"
        elif failure.is_chromadb:
            emoji = "🔴 ChromaDB"

        # Build message with rich formatting
        lines = [
            f"{emoji} *Pod Failure Detected*",
            "",
            f"*Pod:* `{failure.pod_name}`",
            f"*Namespace:* `{failure.namespace}`",
            f"*Container:* `{failure.container_name}`",
            f"*Reason:* {failure.reason}",
            f"*Restart Count:* {failure.restart_count}",
        ]

        # Add failure message if available
        if failure.message:
            lines.append(f"*Message:* {failure.message}")

        # Add last state information if available
        if failure.last_state:
            lines.append("")
            lines.append("*Last Terminated State:*")
            lines.append(f"  Exit Code: {failure.last_state.get('exit_code', 'N/A')}")
            lines.append(f"  Reason: {failure.last_state.get('reason', 'N/A')}")
            if failure.last_state.get("message"):
                lines.append(f"  Message: {failure.last_state['message']}")

        # Add suggestion section if available
        if suggestion:
            lines.append("")
            lines.append("*Analysis & Suggestion:*")
            lines.append(suggestion)

        # Add logs section if available (truncated)
        if logs:
            lines.append("")
            lines.append("*Recent Logs:*")
            lines.append(f"```\n{logs}\n```")

        # Add timestamp
        lines.append("")
        lines.append(f"_Detected at: {failure.timestamp}_")

        return "\n".join(lines)

    def _send_with_retry(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
        max_retries: Optional[int] = None,
    ) -> bool:
        """
        Send message with exponential backoff retry logic.

        Args:
            chat_id: Target chat ID
            text: Message text
            parse_mode: Telegram parse mode (Markdown or HTML)
            max_retries: Override default max_retries

        Returns:
            True if sent successfully, False otherwise
        """
        retries = max_retries if max_retries is not None else self.max_retries

        # Split message if it exceeds Telegram's 4096 character limit
        messages = self._split_message(text)

        for attempt in range(retries):
            try:
                for msg in messages:
                    success = self._send_message(
                        chat_id=chat_id,
                        text=msg,
                        parse_mode=parse_mode,
                    )
                    if not success:
                        raise Exception("Failed to send message")

                logger.info(
                    "Message sent successfully",
                    extra={
                        "chat_id": chat_id,
                        "attempt": attempt + 1,
                        "message_parts": len(messages),
                    },
                )
                return True

            except Exception as e:
                wait_time = 2**attempt  # Exponential backoff: 1s, 2s, 4s
                logger.warning(
                    f"Failed to send message (attempt {attempt + 1}/{retries})",
                    extra={
                        "chat_id": chat_id,
                        "error": str(e),
                        "wait_time": wait_time,
                    },
                )

                if attempt < retries - 1:
                    time.sleep(wait_time)
                else:
                    # Final attempt failed, queue message
                    self._queue_message(
                        {
                            "chat_id": chat_id,
                            "text": text,
                            "parse_mode": parse_mode,
                        }
                    )
                    logger.error(
                        "All retry attempts failed, message queued",
                        extra={"chat_id": chat_id},
                    )
                    return False

        return False

    def _send_message(
        self,
        chat_id: int,
        text: str,
        parse_mode: str = "Markdown",
    ) -> bool:
        """
        Send a single message to Telegram API.

        Args:
            chat_id: Target chat ID
            text: Message text
            parse_mode: Telegram parse mode

        Returns:
            True if sent successfully, False otherwise
        """
        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.post(url, json=payload)
                response.raise_for_status()
                return True
        except Exception as e:
            logger.error(
                "Failed to send message to Telegram API",
                extra={
                    "chat_id": chat_id,
                    "error": str(e),
                },
            )
            return False

    def _split_message(self, text: str, max_length: int = 4096) -> list[str]:
        """
        Split message into chunks respecting Telegram's character limit.

        Args:
            text: Message text to split
            max_length: Maximum length per message (default: 4096)

        Returns:
            List of message chunks
        """
        if len(text) <= max_length:
            return [text]

        messages = []
        lines = text.split("\n")
        current_message = []
        current_length = 0

        for line in lines:
            line_length = len(line) + 1  # +1 for newline

            if current_length + line_length > max_length:
                # Current message is full, start new one
                if current_message:
                    messages.append("\n".join(current_message))
                    current_message = []
                    current_length = 0

                # If single line exceeds max_length, split it
                if line_length > max_length:
                    for i in range(0, len(line), max_length):
                        messages.append(line[i : i + max_length])
                else:
                    current_message.append(line)
                    current_length = line_length
            else:
                current_message.append(line)
                current_length += line_length

        # Add remaining lines
        if current_message:
            messages.append("\n".join(current_message))

        return messages

    def _queue_message(self, message: dict) -> None:
        """
        Queue message for later delivery when API is unavailable.

        Args:
            message: Message dict with chat_id, text, and parse_mode
        """
        self.message_queue.append(message)
        logger.info(
            "Message queued for later delivery",
            extra={
                "queue_size": len(self.message_queue),
                "chat_id": message.get("chat_id"),
            },
        )

    def process_queue(self) -> int:
        """
        Process queued messages (should be called periodically).

        Returns:
            Number of messages successfully sent
        """
        if not self.message_queue:
            return 0

        sent_count = 0
        failed_messages = []

        logger.info(
            "Processing message queue",
            extra={"queue_size": len(self.message_queue)},
        )

        while self.message_queue:
            message = self.message_queue.popleft()

            success = self._send_with_retry(
                chat_id=message["chat_id"],
                text=message["text"],
                parse_mode=message.get("parse_mode", "Markdown"),
                max_retries=1,  # Only one retry for queued messages
            )

            if success:
                sent_count += 1
            else:
                # Re-queue failed message
                failed_messages.append(message)

        # Re-add failed messages to queue
        for msg in failed_messages:
            self.message_queue.append(msg)

        logger.info(
            "Queue processing complete",
            extra={
                "sent": sent_count,
                "failed": len(failed_messages),
                "remaining": len(self.message_queue),
            },
        )

        return sent_count
