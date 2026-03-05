"""
Testes para EmergencyResponder - Workflow de Intervenção.
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.orchestration.emergency_responder import (
    EmergencyResponder,
    COOLDOWN_SECONDS,
)
from src.neural_link.telemetry.provider import (
    EventType,
    TelemetryEvent,
    TelemetryHub,
)


@pytest.fixture
def hub():
    return TelemetryHub()


@pytest.fixture
def tmp_project(tmp_path):
    """Projeto temporário com macro e mission_zero."""
    (tmp_path / "macros").mkdir()
    (tmp_path / "macros" / "refresh_recalibrate.json").write_text(
        '{"metadata":{},"commands":[{"index":0,"command":"Wait 10"}]}'
    )
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "mission_zero_autonomy.py").write_text("# dummy")
    return tmp_path


@pytest.fixture
def responder(hub, tmp_project):
    return EmergencyResponder(
        hub,
        project_root=tmp_project,
        refresh_macro_path=tmp_project / "macros" / "refresh_recalibrate.json",
        cooldown_seconds=1,  # 1s para testes rápidos
    )


class TestEmergencyResponderCooldown:
    """Testes da Trava de Segurança (Cooldown)."""

    def test_ignores_non_critical_anomaly(self, responder, hub):
        """Eventos que não são CRITICAL_ANOMALY são ignorados."""
        received = []
        def capture(ev):
            received.append(ev)
        hub.subscribe(capture)
        responder.start()

        hub._subscribers = [responder._on_event, capture]
        ev = TelemetryEvent(EventType.LOG, "sentinel", "info")
        for cb in hub._subscribers:
            cb(ev)
        assert len([e for e in received if e.event_type == EventType.CRITICAL_ANOMALY]) == 0

    def test_cooldown_blocks_second_trigger(self, responder, hub):
        """Segunda anomalia do mesmo agente dentro do cooldown é bloqueada."""
        triggers = []
        def tracked_dispatch(agent_id, msg):
            triggers.append(agent_id)
            return True
        responder._dispatch_refresh_macro = tracked_dispatch

        responder.start()
        ev1 = TelemetryEvent(
            EventType.CRITICAL_ANOMALY,
            "sentinel",
            "anomaly 1",
            data={"agent_id": "agent_x"},
        )
        ev2 = TelemetryEvent(
            EventType.CRITICAL_ANOMALY,
            "sentinel",
            "anomaly 2",
            data={"agent_id": "agent_x"},
        )
        responder._on_event(ev1)
        responder._on_event(ev2)
        assert len(triggers) == 1

    def test_dispatch_calls_ifttt_when_configured(self, hub, tmp_project):
        """Quando IFTTTConnector configurado, send_trigger é chamado ao iniciar Cura."""
        from unittest.mock import Mock, patch
        ifttt = Mock()
        ifttt.send_trigger = Mock(return_value=True)
        r = EmergencyResponder(
            hub,
            project_root=tmp_project,
            refresh_macro_path=tmp_project / "macros" / "refresh_recalibrate.json",
            cooldown_seconds=1,
            ifttt_connector=ifttt,
        )
        with patch("subprocess.run") as mock_run, patch("time.sleep"), \
             patch("src.neural_link.orchestration.emergency_responder._capture_and_save_evidence", return_value=True):
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="")
            r._dispatch_refresh_macro("agent_1", "erro: quality score baixo")
        ifttt.send_trigger.assert_called_once_with(
            value1="agent_1",
            value2="erro: quality score baixo",
            value3="http://localhost:5000/evidence/last_fail.png",
        )

    def test_dispatch_emits_recovery_attempted(self, responder, hub, tmp_project):
        """Após executar macro, emite RECOVERY_ATTEMPTED com agent_id, macro_path, cooldown."""
        from unittest.mock import patch
        received = []
        hub.subscribe(lambda ev: received.append(ev))

        with patch("subprocess.run") as mock_run, patch("time.sleep"):
            mock_run.return_value = MagicMock(returncode=0, stderr="", stdout="")
            responder._dispatch_refresh_macro("agent_1", "anomaly")

        recovery_events = [e for e in received if e.event_type == EventType.RECOVERY_ATTEMPTED]
        assert len(recovery_events) == 1
        d = recovery_events[0].data
        assert d["agent_id"] == "agent_1"
        assert "refresh_recalibrate" in d["macro_path"]
        assert "cooldown_remaining_seconds" in d
        assert d["success"] is True
