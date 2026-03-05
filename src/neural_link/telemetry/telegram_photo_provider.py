"""
TelegramPhotoProvider - Envia screenshots de Anchoring Errors via Telegram Bot API.

Provedor secundario no TelemetryHub, disparado exclusivamente quando
um CRITICAL_ANOMALY possui detection_status == "NOT_DETECTED" e um
screenshot_path valido. Usa requests para POST multipart ao sendPhoto.

Filtro de privacidade:
  - Arquivo deve existir no disco
  - Tamanho maximo: 10 MB (limite Telegram para fotos)
"""

import logging
import threading
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

from src.neural_link.telemetry.provider import (
    EventType,
    TelemetryEvent,
    TelemetryProvider,
)

logger = logging.getLogger(__name__)

MAX_PHOTO_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
TELEGRAM_API_URL = "https://api.telegram.org/bot{token}/sendPhoto"


def _build_caption(
    agent_id: str,
    quality_score: float | str,
    vault_name: str,
    note_path: str,
) -> str:
    """
    Monta a legenda da foto com dados da anomalia e deep-link Obsidian.

    Formato:
        ALERTA VISUAL - Anchoring Error
        Agente: <agent_id>
        Score: <quality_score>/10
        Nota: obsidian://open?vault=...&file=...
    """
    encoded_vault = quote(vault_name, safe="")
    encoded_file = quote(note_path, safe="/")
    obsidian_link = f"obsidian://open?vault={encoded_vault}&file={encoded_file}"
    return (
        "ALERTA VISUAL - Anchoring Error\n"
        f"Agente: {agent_id}\n"
        f"Score: {quality_score}/10\n"
        f"Nota: {obsidian_link}"
    )


def _validate_photo(photo_path: str) -> str | None:
    """
    Filtro de privacidade. Retorna None se o arquivo e valido,
    ou uma string de erro descrevendo o problema.
    """
    p = Path(photo_path)
    if not p.exists():
        return f"Arquivo nao encontrado: {photo_path}"
    if not p.is_file():
        return f"Caminho nao e um arquivo: {photo_path}"
    size = p.stat().st_size
    if size > MAX_PHOTO_SIZE_BYTES:
        mb = size / (1024 * 1024)
        return f"Arquivo excede 10 MB ({mb:.1f} MB): {photo_path}"
    return None


class TelegramPhotoProvider(TelemetryProvider):
    """
    Provedor de telemetria que envia screenshots via Telegram Bot API.

    Dispara apenas em Anchoring Errors:
      - event_type == CRITICAL_ANOMALY
      - data["detection_status"] == "NOT_DETECTED"
      - data["screenshot_path"] presente e valido
    """

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        vault_name: str = "vault",
        timeout: int = 15,
    ):
        self._bot_token = bot_token.strip()
        self._chat_id = chat_id.strip()
        self._vault_name = vault_name
        self._timeout = timeout
        self._buffer: list[TelemetryEvent] = []
        self._lock = threading.Lock()
        self._last_send_ok: bool | None = None
        self._last_send_ts: str | None = None
        self._photos_sent: int = 0
        self._photos_rejected: int = 0

    # ------------------------------------------------------------------
    # TelemetryProvider ABC
    # ------------------------------------------------------------------

    @property
    def provider_id(self) -> str:
        return "telegram_photo"

    @property
    def display_name(self) -> str:
        return "Telegram Photo (Bot API)"

    def poll(self) -> list[TelemetryEvent]:
        """Drain the buffer and return all pending events."""
        with self._lock:
            events = list(self._buffer)
            self._buffer.clear()
        return events

    def health_check(self) -> bool:
        """Pre-first-use = healthy; after that, reflects last send result."""
        if self._last_send_ok is None:
            return True
        return self._last_send_ok

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def send_photo(self, photo_path: str, caption: str) -> bool:
        """
        Envia uma foto ao Telegram via Bot API sendPhoto.

        Aplica filtro de privacidade antes do envio.
        Returns True se a API retornou 200 e result.ok == true.
        """
        if not self._bot_token or not self._chat_id:
            logger.warning("TelegramPhoto: bot_token ou chat_id vazio, ignorando")
            return False

        # --- Filtro de privacidade ---
        rejection = _validate_photo(photo_path)
        if rejection:
            logger.warning("TelegramPhoto filtro: %s", rejection)
            self._photos_rejected += 1
            return False

        url = TELEGRAM_API_URL.format(token=self._bot_token)

        try:
            with open(photo_path, "rb") as f:
                resp = requests.post(
                    url,
                    data={"chat_id": self._chat_id, "caption": caption},
                    files={"photo": (Path(photo_path).name, f, "image/png")},
                    timeout=self._timeout,
                )
            if resp.status_code == 200:
                body = resp.json()
                if body.get("ok"):
                    logger.debug("TelegramPhoto enviado: %s", photo_path)
                    self._photos_sent += 1
                    return True
            logger.warning("TelegramPhoto HTTP %d: %s", resp.status_code, resp.text[:200])
            return False
        except requests.RequestException as e:
            logger.warning("TelegramPhoto falhou: %s", e)
            return False
        except Exception as e:
            logger.exception("TelegramPhoto erro inesperado: %s", e)
            return False

    def dispatch(self, event: TelemetryEvent) -> bool:
        """
        Processa um evento de telemetria.

        Apenas eventos de Anchoring Error sao enviados:
          - CRITICAL_ANOMALY + detection_status == "NOT_DETECTED" + screenshot_path

        Outros eventos sao ignorados silenciosamente (retorna False).
        """
        if not self._is_anchoring_error(event):
            return False

        data = event.data
        photo_path = data.get("screenshot_path", "")
        agent_id = data.get("agent_name", event.source)
        score = data.get("quality_score", "?")
        task_id = data.get("task_id", "unknown")

        note_path = f"Agents/{agent_id}"
        caption = _build_caption(agent_id, score, self._vault_name, note_path)

        ok = self.send_photo(photo_path, caption)

        now = datetime.now().isoformat()
        self._last_send_ok = ok
        if ok:
            self._last_send_ts = now

        sync_event = TelemetryEvent(
            event_type=EventType.SYNC_COMPLETED if ok else EventType.SYNC_TRIGGERED,
            source=self.provider_id,
            message=f"Telegram photo {'sent' if ok else 'failed'}: {agent_id} task {task_id}",
            timestamp=now,
            data={
                "agent_name": agent_id,
                "task_id": task_id,
                "quality_score": score,
                "screenshot_path": photo_path,
                "success": ok,
            },
        )
        with self._lock:
            self._buffer.append(sync_event)

        return ok

    def ping_status(self) -> dict:
        """Status dict for Obsidian Connected Services."""
        active = self._last_send_ok if self._last_send_ok is not None else True
        return {
            "active": active,
            "last_ping": self._last_send_ts,
            "photos_sent": self._photos_sent,
            "photos_rejected": self._photos_rejected,
        }

    # ------------------------------------------------------------------
    # Private
    # ------------------------------------------------------------------

    @staticmethod
    def _is_anchoring_error(event: TelemetryEvent) -> bool:
        """Retorna True se o evento e um Anchoring Error com screenshot."""
        etype = event.event_type
        if hasattr(etype, "value"):
            etype_val = etype.value
        else:
            etype_val = str(etype)

        if etype_val != "critical_anomaly":
            return False

        data = event.data if isinstance(event.data, dict) else {}
        if data.get("detection_status") != "NOT_DETECTED":
            return False
        if not data.get("screenshot_path"):
            return False

        return True
