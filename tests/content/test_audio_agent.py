"""
Tests for AudioAgent -- ElevenLabs + OpenAI TTS with automatic fallback.

TDD: These tests are written FIRST. All external HTTP/TTS calls are mocked.
"""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import AudioAsset


# ============================================================
# TestCapabilities
# ============================================================


class TestCapabilities:
    def test_audio_agent_has_correct_capabilities(self):
        from src.neural_link.agents.content.audio_agent import AudioAgent

        agent = AudioAgent()
        assert agent.capabilities == {"tts", "audio", "elevenlabs"}

    def test_audio_agent_inherits_base_agent(self):
        from src.neural_link.agents.content.audio_agent import AudioAgent

        agent = AudioAgent()
        assert isinstance(agent, BaseAgent)


# ============================================================
# TestExecute
# ============================================================


class TestExecute:
    def test_execute_calls_tts_and_returns_audio_asset(self, tmp_path):
        """execute() should call _call_tts, save MP3, return AudioAsset dict."""
        from src.neural_link.agents.content.audio_agent import AudioAgent

        agent = AudioAgent(output_dir=str(tmp_path))

        fake_audio = b"\x00" * 32000  # 32000 bytes -> ~2s at 16000 bytes/s

        with patch.object(agent, "_call_tts", return_value=fake_audio) as mock_tts:
            task = {
                "script": {
                    "text": "Hello world, this is a test.",
                    "voice": "test-voice",
                    "episode_id": "ep-001",
                },
            }
            result = agent.execute(task=task)

        # _call_tts should have been called with text and voice
        mock_tts.assert_called_once_with(
            "Hello world, this is a test.", "test-voice"
        )

        # Result should be a dict conforming to AudioAsset
        assert isinstance(result, dict)
        asset = AudioAsset(**result)
        assert asset.size_bytes == 32000
        assert asset.duration_seconds == pytest.approx(2.0)
        assert asset.voice_id == "test-voice"
        assert asset.transcript == "Hello world, this is a test."

        # File should exist on disk
        assert Path(asset.file_path).exists()
        assert Path(asset.file_path).read_bytes() == fake_audio


# ============================================================
# TestTTSFallback
# ============================================================


class TestTTSFallback:
    def test_call_tts_elevenlabs_fallback_to_openai(self):
        """When ElevenLabs fails, _call_tts should fall back to OpenAI."""
        from src.neural_link.agents.content.audio_agent import AudioAgent

        agent = AudioAgent()

        fake_audio = b"\xff\xfb\x90\x00" * 100  # fake MP3 bytes

        with (
            patch.object(
                agent,
                "_tts_elevenlabs",
                side_effect=Exception("ElevenLabs API error"),
            ) as mock_eleven,
            patch.object(
                agent, "_tts_openai", return_value=fake_audio
            ) as mock_openai,
        ):
            result = agent._call_tts("Test text", "voice-123")

        mock_eleven.assert_called_once_with("Test text", "voice-123")
        mock_openai.assert_called_once_with("Test text", "voice-123")
        assert result == fake_audio
