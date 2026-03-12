"""
AudioAgent -- TTS audio generation with ElevenLabs primary + OpenAI fallback.

Generates MP3 audio files from text/SSML scripts using:
- Primary: ElevenLabs TTS API (high-quality voices)
- Fallback: OpenAI TTS API (reliable, lower cost)

Saves output to configurable directory (default: data/audio).
"""

import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any

import httpx

from src.neural_link.agents.base_agent import BaseAgent
from src.neural_link.agents.content.models import AudioAsset

logger = logging.getLogger(__name__)

TTS_TIMEOUT = 120  # seconds — TTS generation can be slow for long scripts


class AudioAgent(BaseAgent):
    """
    Agent that converts text scripts into MP3 audio via TTS APIs.

    Inherits from BaseAgent with capabilities: {"tts", "audio", "elevenlabs"}.

    Uses ElevenLabs as primary TTS provider with automatic fallback to OpenAI
    when ElevenLabs is unavailable or fails.
    """

    def __init__(self, output_dir: str = "data/audio") -> None:
        self._output_dir = Path(output_dir)
        self._output_dir.mkdir(parents=True, exist_ok=True)

    @property
    def capabilities(self) -> set[str]:
        return {"tts", "audio", "elevenlabs"}

    def execute(self, task: Any, **kwargs: Any) -> dict:
        """
        Execute a TTS audio generation task.

        Args:
            task: Either a dict with a "script" key containing
                  {"text": str, "voice": str, "episode_id": str},
                  or a string description (uses kwargs for script data).
            **kwargs: Optional overrides (text, voice, episode_id).

        Returns:
            dict: AudioAsset.model_dump() with file path, duration, metadata.
        """
        # Extract script data from task dict or kwargs
        if isinstance(task, dict) and "script" in task:
            script = task["script"]
            text = script.get("text", "")
            voice = script.get("voice", "default")
            episode_id = script.get("episode_id", str(uuid.uuid4())[:8])
        else:
            text = kwargs.get("text", str(task) if task else "")
            voice = kwargs.get("voice", "default")
            episode_id = kwargs.get("episode_id", str(uuid.uuid4())[:8])

        # Generate audio via TTS
        audio_bytes = self._call_tts(text, voice)

        # Save MP3 file
        filename = f"{episode_id}_{uuid.uuid4().hex[:8]}.mp3"
        file_path = self._output_dir / filename
        file_path.write_bytes(audio_bytes)

        # Estimate duration: raw MP3 at ~16kBps (128kbps / 8)
        size_bytes = len(audio_bytes)
        duration_seconds = size_bytes / 16000.0

        asset = AudioAsset(
            file_path=str(file_path),
            duration_seconds=duration_seconds,
            size_bytes=size_bytes,
            voice_id=voice,
            transcript=text,
            metadata={"episode_id": episode_id},
        )

        return asset.model_dump()

    # ------------------------------------------------------------------
    # TTS orchestration
    # ------------------------------------------------------------------

    def _call_tts(self, text: str, voice: str) -> bytes:
        """
        Generate audio bytes from text using TTS.

        Tries ElevenLabs first; falls back to OpenAI on any failure.

        Args:
            text: The text (or SSML) to synthesize.
            voice: Voice identifier.

        Returns:
            bytes: Raw MP3 audio data.
        """
        try:
            return self._tts_elevenlabs(text, voice)
        except Exception as exc:
            logger.warning(
                "ElevenLabs TTS failed, falling back to OpenAI: %s", exc
            )
            return self._tts_openai(text, voice)

    # ------------------------------------------------------------------
    # Provider implementations
    # ------------------------------------------------------------------

    def _tts_elevenlabs(self, text: str, voice: str) -> bytes:
        """
        Generate audio via ElevenLabs TTS API.

        Env vars required:
            ELEVENLABS_API_KEY: API key for authentication.
            ELEVENLABS_VOICE_ID: Default voice ID (overridden by voice param
                                 if it looks like an ElevenLabs voice ID).
        """
        api_key = os.environ.get("ELEVENLABS_API_KEY", "")
        voice_id = voice if len(voice) > 10 else os.environ.get("ELEVENLABS_VOICE_ID", voice)

        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75,
            },
        }

        resp = httpx.post(url, json=payload, headers=headers, timeout=TTS_TIMEOUT)
        resp.raise_for_status()
        return resp.content

    def _tts_openai(self, text: str, voice: str) -> bytes:
        """
        Generate audio via OpenAI TTS API (fallback).

        Strips SSML tags since OpenAI TTS does not support SSML.

        Env vars required:
            OPENAI_API_KEY: API key for authentication.
        """
        api_key = os.environ.get("OPENAI_API_KEY", "")

        # Strip SSML tags -- OpenAI TTS only accepts plain text
        plain_text = re.sub(r"<[^>]+>", "", text).strip()

        url = "https://api.openai.com/v1/audio/speech"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": "tts-1",
            "input": plain_text,
            "voice": "alloy",  # default OpenAI voice
            "response_format": "mp3",
        }

        resp = httpx.post(url, json=payload, headers=headers, timeout=TTS_TIMEOUT)
        resp.raise_for_status()
        return resp.content
