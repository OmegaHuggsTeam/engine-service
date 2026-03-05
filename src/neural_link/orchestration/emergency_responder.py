"""
Emergency Responder - Workflow de Intervenção para Anomalias Críticas.

Inscreve-se no TelemetryHub para ouvir eventos CRITICAL_ANOMALY.
Ao receber uma anomalia, dispara mission_zero com --execute-macro
para executar macro de Refresh/Recalibrate no Dashboard.

Trava de Segurança (Cooldown): máximo 1 macro a cada 5 minutos
por agente, evitando desperdício de tokens e loops de interface.

Visual Evidence: em CRITICAL_ANOMALY, captura screenshot e anexa
URL da evidência em value3 para IFTTT (Evidence Server).
"""

import logging
import os
import subprocess
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

from ..telemetry.provider import (
    EventType,
    TelemetryEvent,
    TelemetryHub,
    JitbitConnector as TelemetryJitbitConnector,
)
from ..telemetry.ifttt_connector import IFTTTConnector

logger = logging.getLogger(__name__)

RECOVERY_WAIT_SECONDS = 10

# Cooldown: 5 minutos por agente
COOLDOWN_SECONDS = 300
DEFAULT_REFRESH_MACRO = Path("macros/refresh_recalibrate.json")
DEFAULT_EVIDENCE_DIR = Path("temp/evidence")


def _capture_and_save_evidence(evidence_dir: Path) -> bool:
    """
    Captura screenshot e salva em evidence_dir/last_fail.png.
    Retorna True se salvou com sucesso.
    """
    try:
        from PIL import ImageGrab
        evidence_dir.mkdir(parents=True, exist_ok=True)
        path = evidence_dir / "last_fail.png"
        img = ImageGrab.grab()
        img.save(str(path))
        logger.debug("Evidence saved to %s", path)
        return True
    except Exception as e:
        logger.warning("Could not capture evidence screenshot: %s", e)
        return False


def _get_evidence_url() -> str:
    """URL da evidência para value3 (Evidence Server)."""
    try:
        from ..services.evidence_server import get_evidence_url
        return get_evidence_url()
    except ImportError:
        return ""


class EmergencyResponder:
    """
    Subscriber que reage a CRITICAL_ANOMALY disparando macro de Refresh/Recalibrate.
    Trava de segurança: 1 macro a cada 5 min por agent_id.
    """

    def __init__(
        self,
        hub: TelemetryHub,
        project_root: Path | None = None,
        refresh_macro_path: Path | None = None,
        cooldown_seconds: int = COOLDOWN_SECONDS,
        ifttt_connector: IFTTTConnector | None = None,
    ):
        """
        Args:
            hub: TelemetryHub para subscribe.
            project_root: Raiz do projeto (para encontrar mission_zero).
            refresh_macro_path: Caminho da macro Refresh/Recalibrate.
            cooldown_seconds: Segundos mínimos entre macros por agente.
            ifttt_connector: Opcional. Se IFTTT_WEBHOOK_KEY estiver definida, cria um.
        """
        self._hub = hub
        self._project_root = Path(project_root) if project_root else self._resolve_project_root()
        self._refresh_macro = Path(refresh_macro_path) if refresh_macro_path else DEFAULT_REFRESH_MACRO
        self._cooldown = cooldown_seconds

        self._last_trigger_by_agent: dict[str, datetime] = {}
        self._lock = threading.Lock()

        self._evidence_dir = Path(os.environ.get("EVIDENCE_DIR", str(DEFAULT_EVIDENCE_DIR)))

        self._event_provider = TelemetryJitbitConnector()
        self._hub.register(self._event_provider)

        self._ifttt = ifttt_connector
        if self._ifttt is None and os.environ.get("IFTTT_WEBHOOK_KEY"):
            self._ifttt = IFTTTConnector(
                webhook_key=os.environ["IFTTT_WEBHOOK_KEY"],
                event_name=os.environ.get("IFTTT_EVENT_NAME", "critical_anomaly"),
            )

    def _resolve_project_root(self) -> Path:
        """Resolve raiz do projeto a partir deste arquivo."""
        return Path(__file__).resolve().parent.parent.parent.parent

    def _on_event(self, event: TelemetryEvent) -> None:
        """Callback chamado pelo hub para cada evento."""
        if event.event_type != EventType.CRITICAL_ANOMALY:
            return

        agent_id = event.data.get("agent_id", "") or event.data.get("agent_name", "unknown")
        if not agent_id:
            agent_id = "unknown"

        with self._lock:
            last = self._last_trigger_by_agent.get(agent_id)
            now = datetime.now()
            if last and (now - last).total_seconds() < self._cooldown:
                remaining = self._cooldown - (now - last).total_seconds()
                logger.warning(
                    "EmergencyResponder: Trava de segurança - agente %s em cooldown (%.0fs restantes)",
                    agent_id,
                    remaining,
                )
                return
            self._last_trigger_by_agent[agent_id] = now

        logger.info(
            "EmergencyResponder: CRITICAL_ANOMALY recebida - agente=%s, disparando macro Refresh/Recalibrate",
            agent_id,
        )
        self._dispatch_refresh_macro(agent_id, event.message)

    def _push_and_flush(self, event_type: EventType, message: str, data: dict) -> None:
        """Envia evento ao provider e dispara poll_all para subscribers."""
        self._event_provider.push_event(event_type, message, data)
        self._hub.poll_all()

    def _remaining_cooldown(self, agent_id: str) -> float:
        """Retorna segundos restantes de cooldown para o agente."""
        with self._lock:
            last = self._last_trigger_by_agent.get(agent_id)
            if not last:
                return 0.0
            elapsed = (datetime.now() - last).total_seconds()
            return max(0.0, self._cooldown - elapsed)

    def _dispatch_refresh_macro(self, agent_id: str, anomaly_message: str) -> bool:
        """
        Dispara mission_zero_autonomy.py com --execute-macro.
        Aguarda 10s e dispara RECOVERY_ATTEMPTED para o Hub.
        Em falha (ex: pyautogui/janela perdeu foco), envia WARNING ao Hub.
        Returns True se subprocess retornou 0.
        """
        macro_path = self._project_root / self._refresh_macro
        if not macro_path.exists():
            macro_path = self._project_root / "macros" / "refresh_recalibrate.json"
        if not macro_path.exists():
            logger.error(
                "EmergencyResponder: Macro refresh_recalibrate.json não encontrada em %s",
                self._project_root,
            )
            return False

        mission_script = self._project_root / "tests" / "mission_zero_autonomy.py"
        if not mission_script.exists():
            logger.error(
                "EmergencyResponder: mission_zero_autonomy.py não encontrado em %s",
                mission_script,
            )
            return False

        if self._ifttt:
            # Visual Evidence: captura screenshot e anexa URL em value3
            evidence_url = ""
            if _capture_and_save_evidence(self._evidence_dir):
                evidence_url = _get_evidence_url()
            value3 = evidence_url if evidence_url else str(macro_path)
            self._ifttt.send_trigger(
                value1=agent_id,
                value2=anomaly_message,
                value3=value3,
            )

        cmd = [
            sys.executable,
            str(mission_script),
            "--execute-macro",
            str(macro_path.resolve()),
        ]
        success = False
        error_detail = ""
        try:
            result = subprocess.run(
                cmd,
                cwd=str(self._project_root),
                capture_output=True,
                text=True,
                timeout=120,
            )
            success = result.returncode == 0
            if not success:
                error_detail = (result.stderr or result.stdout or "").strip()[:500]
                logger.warning(
                    "EmergencyResponder: Macro retornou %d - stderr: %s",
                    result.returncode,
                    error_detail,
                )
                self._push_and_flush(
                    EventType.LOG,
                    f"WARNING: Falha ao executar macro Recovery - agente={agent_id}",
                    data={
                        "level": "WARNING",
                        "agent_id": agent_id,
                        "macro_path": str(macro_path),
                        "returncode": result.returncode,
                        "error": error_detail,
                        "context": "Possível janela perdeu foco ou falha pyautogui/hardware",
                    },
                )
            else:
                logger.info(
                    "EmergencyResponder: Macro executada com sucesso (agente=%s)",
                    agent_id,
                )
        except subprocess.TimeoutExpired:
            error_detail = "Timeout ao executar macro"
            logger.error("EmergencyResponder: %s", error_detail)
            self._push_and_flush(
                EventType.LOG,
                f"WARNING: {error_detail} - agente={agent_id}",
                data={
                    "level": "WARNING",
                    "agent_id": agent_id,
                    "macro_path": str(macro_path),
                    "error": error_detail,
                },
            )
        except Exception as e:
            error_detail = str(e)
            logger.exception("EmergencyResponder: Erro ao disparar macro: %s", e)
            self._push_and_flush(
                EventType.LOG,
                f"WARNING: Erro ao disparar macro - {e}",
                data={
                    "level": "WARNING",
                    "agent_id": agent_id,
                    "macro_path": str(macro_path),
                    "error": error_detail,
                },
            )

        time.sleep(RECOVERY_WAIT_SECONDS)
        remaining = self._remaining_cooldown(agent_id)
        self._push_and_flush(
            EventType.RECOVERY_ATTEMPTED,
            f"Recovery executado para agente {agent_id}",
            data={
                "agent_id": agent_id,
                "macro_path": str(macro_path),
                "cooldown_remaining_seconds": round(remaining, 1),
                "success": success,
            },
        )
        return success

    def start(self) -> None:
        """Inscreve no hub e inicia escuta."""
        self._hub.subscribe(self._on_event)
        logger.info(
            "EmergencyResponder iniciado (macro=%s, cooldown=%ds)",
            self._refresh_macro,
            self._cooldown,
        )

    def stop(self) -> None:
        """Remove subscription (hub não tem unsubscribe, manter referência)."""
        logger.info("EmergencyResponder parado")


# ======================================================================
# CLI entry point
# ======================================================================

def _main() -> None:
    import signal

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    hub = TelemetryHub()
    responder = EmergencyResponder(hub, cooldown_seconds=COOLDOWN_SECONDS)
    responder.start()

    # Opcional: registrar SentinelBridge se Neo4j disponível
    sentinel = None
    try:
        from ..graph.manager import GraphManager
        from ..services.sentinel_bridge import SentinelBridge
        gm = GraphManager.from_env()
        if gm.verify_connectivity():
            sentinel = SentinelBridge(gm, hub, interval=60.0)
            sentinel.start()
            print("[emergency_responder] SentinelBridge registrado (Neo4j conectado)")
    except Exception as e:
        logger.debug("SentinelBridge não disponível: %s", e)
        print("[emergency_responder] Executando sem SentinelBridge (sem Neo4j)")

    def _shutdown(sig=None, frame=None):
        print("\n[emergency_responder] Shutting down...")
        if sentinel:
            sentinel.stop()
        responder.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("[emergency_responder] Aguardando CRITICAL_ANOMALY (Ctrl+C para parar)")
    print("[emergency_responder] Cooldown: 5 min por agente")

    while True:
        hub.poll_all()
        time.sleep(2)


if __name__ == "__main__":
    _main()
