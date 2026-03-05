"""
IFTTT Connector - Notificações externas via Webhooks.

Envia triggers para IFTTT Maker Webhooks com payload JSON
no formato exigido: {"value1": "", "value2": "", "value3": ""}

Documentação: https://ifttt.com/maker_webhooks
"""

import json
import logging
from typing import Optional

import urllib.request
import urllib.error

logger = logging.getLogger(__name__)

IFTTT_MAKER_URL = "https://maker.ifttt.com/trigger/{event}/with/key/{key}"


def _build_payload(value1: str = "", value2: str = "", value3: str = "") -> dict:
    """
    Constrói payload JSON no formato exigido pelo IFTTT.
    Valores são convertidos para string.
    """
    return {
        "value1": str(value1) if value1 is not None else "",
        "value2": str(value2) if value2 is not None else "",
        "value3": str(value3) if value3 is not None else "",
    }


class IFTTTConnector:
    """
    Conector para IFTTT Maker Webhooks.
    Envia triggers via POST com payload JSON padrão.
    """

    def __init__(
        self,
        webhook_key: str,
        event_name: str = "critical_anomaly",
    ):
        """
        Args:
            webhook_key: IFTTT_WEBHOOK_KEY (chave do Maker Webhooks).
            event_name: Nome do evento IFTTT (ex: critical_anomaly, recovery_started).
        """
        self.webhook_key = webhook_key.strip()
        self.event_name = event_name.strip() or "critical_anomaly"

    def send_trigger(
        self,
        value1: str = "",
        value2: str = "",
        value3: str = "",
    ) -> bool:
        """
        Envia POST para IFTTT Maker Webhooks.

        URL: https://maker.ifttt.com/trigger/{event}/with/key/{key}
        Body: {"value1": "...", "value2": "...", "value3": "..."}

        Returns:
            True se request retornou 200, False caso contrário.
        """
        if not self.webhook_key:
            logger.warning("IFTTTConnector: webhook_key vazia, ignorando send_trigger")
            return False

        url = IFTTT_MAKER_URL.format(event=self.event_name, key=self.webhook_key)
        payload = _build_payload(value1, value2, value3)
        body = json.dumps(payload).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                if resp.status == 200:
                    logger.debug("IFTTT trigger enviado: %s", self.event_name)
                    return True
                logger.warning("IFTTT retornou status %d", resp.status)
                return False
        except urllib.error.HTTPError as e:
            logger.warning("IFTTT HTTPError %d: %s", e.code, e.reason)
            return False
        except urllib.error.URLError as e:
            logger.warning("IFTTT URLError: %s", e.reason)
            return False
        except Exception as e:
            logger.exception("IFTTT send_trigger falhou: %s", e)
            return False
