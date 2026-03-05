"""
TelegramNotifier - Envia alertas de falha de Pod e status do cluster.

Task 9: Sistema de notificação para diagnóstico completo.
Preparado para receber Status + Log + Sugestão de Fix nos callbacks.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = "https://api.telegram.org/bot{token}/"
MAX_MESSAGE_LENGTH = 4096
MAX_RETRIES = 3
RETRY_DELAY_BASE = 2


@dataclass
class PodFailureStatus:
    """Status de falha de Pod para notificação."""

    pod_name: str
    namespace: str
    reason: str
    container_name: Optional[str] = None
    message: Optional[str] = None
    is_neo4j: bool = False
    is_chromadb: bool = False


class TelegramNotifier:
    """
    Envia notificações para o Telegram.
    Suporta alertas de falha de Pod com diagnóstico completo.
    """

    def __init__(
        self,
        bot_token: Optional[str] = None,
        default_chat_id: Optional[str] = None,
    ):
        """
        Initialize TelegramNotifier.

        Args:
            bot_token: Telegram bot token (ou TELEGRAM_BOT_TOKEN)
            default_chat_id: Chat ID padrão (ou TELEGRAM_CHAT_ID)
        """
        self._token = (bot_token or TELEGRAM_BOT_TOKEN).strip()
        self._chat_id = (
            default_chat_id
            or os.environ.get("TELEGRAM_CHAT_ID")
            or os.environ.get("AUTHORIZED_CHAT_ID", "")
        )
        self._queue: list[dict] = []
        self._queue_lock = threading.Lock()

    def _api_url(self, method: str) -> str:
        return TELEGRAM_API.format(token=self._token) + method

    def send_pod_failure_alert(
        self,
        status: "PodFailureStatus | object",
        logs: str = "",
        suggestion: str = "",
    ) -> bool:
        """
        Envia alerta de falha de Pod com diagnóstico completo.

        Formato preparado para callbacks:
        - Status do Pod
        - Últimas linhas de log (truncado)
        - Sugestão de correção do SpecialistAgent

        Args:
            status: PodFailureEvent ou PodFailureStatus
            logs: Últimas linhas de log
            suggestion: Sugestão de fix do SpecialistAgent

        Returns:
            True se enviado com sucesso
        """
        pod_name = getattr(status, "pod_name", "?")
        namespace = getattr(status, "namespace", "?")
        reason = getattr(status, "reason", "CrashLoopBackOff")
        container = getattr(status, "container_name", None)
        msg_attr = getattr(status, "message", None)
        is_neo4j = getattr(status, "is_neo4j", False)
        is_chromadb = getattr(status, "is_chromadb", False)

        priority = "🔴 Neo4j" if is_neo4j else ("🟠 ChromaDB" if is_chromadb else "⚠️ Pod")

        lines = [
            f"{priority} *CrashLoopBackOff*",
            "",
            f"📦 Pod: `{pod_name}`",
            f"📁 Namespace: `{namespace}`",
            f"📌 Reason: {reason}",
        ]
        if container:
            lines.append(f"📦 Container: `{container}`")
        if msg_attr:
            lines.append(f"💬 Message: {msg_attr[:200]}")

        if logs:
            lines.extend([
                "",
                "--- *Últimas linhas de log* ---",
                f"```\n{logs[:1500]}\n```",
            ])

        if suggestion:
            lines.extend([
                "",
                "--- *Sugestão de correção* ---",
                suggestion[:1500],
            ])

        text = "\n".join(lines)

        # Callback buttons para diagnóstico (Telegram limit: 64 bytes)
        cb_restart = f"pr:{namespace}:{pod_name}"[:64]
        cb_logs = f"pl:{namespace}:{pod_name}"[:64]
        keyboard = {
            "inline_keyboard": [
                [{"text": "🔄 Reiniciar Pod", "callback_data": cb_restart}],
                [{"text": "📋 Ver logs completos", "callback_data": cb_logs}],
                [{"text": "✅ Dismiss", "callback_data": "pod_dismiss"}],
            ]
        }
        return self._send_with_retry(text, reply_markup=keyboard)

    def send_cluster_status(self, status_text: str) -> bool:
        """Envia status do cluster."""
        return self._send_with_retry(status_text[:MAX_MESSAGE_LENGTH])

    def _send_with_retry(
        self,
        text: str,
        chat_id: Optional[str] = None,
        reply_markup: Optional[dict] = None,
    ) -> bool:
        """Envia mensagem com retry e exponential backoff."""
        cid = chat_id or self._chat_id
        if not cid:
            logger.warning("TELEGRAM_CHAT_ID não configurado, notificação não enviada")
            return False

        if not self._token:
            logger.warning("TELEGRAM_BOT_TOKEN não configurado")
            return False

        for attempt in range(MAX_RETRIES):
            try:
                chunks = self._split_message(text)
                for i, chunk in enumerate(chunks):
                    payload: dict = {"chat_id": cid, "text": chunk, "parse_mode": "Markdown"}
                    if reply_markup and i == 0:
                        payload["reply_markup"] = reply_markup
                    with httpx.Client(timeout=15) as client:
                        r = client.post(self._api_url("sendMessage"), json=payload)
                    if r.status_code != 200:
                        raise RuntimeError(f"Telegram API {r.status_code}: {r.text[:200]}")
                return True
            except Exception as e:
                logger.warning("Telegram send attempt %d/%d failed: %s", attempt + 1, MAX_RETRIES, e)
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_DELAY_BASE ** attempt)
                else:
                    self._queue_message({"chat_id": cid, "text": text})
                    return False
        return False

    def _split_message(self, text: str) -> list[str]:
        """Divide mensagem em chunks de até 4096 caracteres."""
        if len(text) <= MAX_MESSAGE_LENGTH:
            return [text]
        chunks = []
        while text:
            chunk = text[:MAX_MESSAGE_LENGTH]
            last_newline = chunk.rfind("\n")
            if last_newline > MAX_MESSAGE_LENGTH // 2:
                chunk = chunk[: last_newline + 1]
            chunks.append(chunk)
            text = text[len(chunk) :]
        return chunks

    def _queue_message(self, msg: dict) -> None:
        """Adiciona mensagem à fila para retry posterior."""
        with self._queue_lock:
            self._queue.append(msg)

    def _process_queue(self) -> int:
        """Processa fila de mensagens pendentes. Retorna quantidade enviada."""
        with self._queue_lock:
            pending = list(self._queue)
            self._queue.clear()

        sent = 0
        for msg in pending:
            if self._send_with_retry(msg.get("text", ""), msg.get("chat_id")):
                sent += 1
        return sent
