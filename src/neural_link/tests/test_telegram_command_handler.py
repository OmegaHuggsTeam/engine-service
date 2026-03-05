"""
Tests for Telegram Command Handler.
"""

import time
from unittest.mock import patch, MagicMock

import pytest

from src.neural_link.telemetry.telegram_command_handler import (
    _is_github_repo_url,
    _is_json_url,
    _ingest_url,
    _handle_command,
    TelegramCommandHandler,
)


class TestUrlDetection:
    """Detecção de URLs."""

    def test_github_repo_url(self):
        assert _is_github_repo_url("https://github.com/zie619/zie619.github.io") is True
        assert _is_github_repo_url("https://github.com/owner/repo") is True

    def test_github_repo_rejects_blob(self):
        assert _is_github_repo_url("https://github.com/o/r/blob/main/file.json") is False

    def test_github_repo_rejects_raw(self):
        assert _is_github_repo_url("https://raw.githubusercontent.com/o/r/b/f.json") is False

    def test_json_url(self):
        assert _is_json_url("https://example.com/workflow.json") is True
        assert _is_json_url("https://raw.githubusercontent.com/o/r/b/f.json") is True


class TestTelegramCommandHandler:
    """Handler."""

    def test_handler_init_without_token(self):
        h = TelegramCommandHandler(bot_token="")
        h.start()
        assert h._thread is None

    def test_handler_init_with_token(self):
        with patch("src.neural_link.telemetry.telegram_command_handler._get_updates") as mock:
            mock.return_value = ([], 0)
            h = TelegramCommandHandler(bot_token="fake_token_123")
            h.start()
            time.sleep(0.2)
            h.stop()
        assert h._thread is not None
