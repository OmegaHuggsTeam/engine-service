"""
Testes unitários para KillSwitchMonitor (Task 8).

Task 8.4: trigger zone, thread lifecycle, reset.
"""

import time
from unittest.mock import patch

import pytest

from src.neural_link.telemetry.kill_switch import KillSwitchMonitor, _get_mouse_position


class TestKillSwitchTriggerZone:
    """Testes de detecção da zona de trigger."""

    def test_in_trigger_zone_default(self):
        """Mouse em (0,0) e (9,9) está na zona de trigger padrão."""
        monitor = KillSwitchMonitor(trigger_zone=(10, 10))
        assert monitor._in_trigger_zone(0, 0) is True
        assert monitor._in_trigger_zone(9, 9) is True

    def test_outside_trigger_zone(self):
        """Mouse em (10,10) ou acima está fora da zona."""
        monitor = KillSwitchMonitor(trigger_zone=(10, 10))
        assert monitor._in_trigger_zone(10, 10) is False
        assert monitor._in_trigger_zone(10, 0) is False
        assert monitor._in_trigger_zone(0, 10) is False
        assert monitor._in_trigger_zone(100, 100) is False


class TestKillSwitchLifecycle:
    """Testes de ciclo de vida do monitor."""

    def test_start_stop(self):
        """Start inicia thread, stop encerra."""
        monitor = KillSwitchMonitor(check_interval=0.05)
        monitor.start()
        assert monitor._thread is not None
        assert monitor._thread.is_alive()
        monitor.stop()
        time.sleep(0.15)
        assert monitor._thread is None or not monitor._thread.is_alive()

    def test_reset_clears_triggered(self):
        """Reset limpa o estado triggered."""
        monitor = KillSwitchMonitor(trigger_zone=(10, 10))
        with patch(
            "src.neural_link.telemetry.kill_switch._get_mouse_position",
            return_value=(0, 0),
        ):
            monitor.start()
            time.sleep(0.15)  # Dar tempo para detectar
            assert monitor.is_triggered() is True
            monitor.reset()
            assert monitor.is_triggered() is False
        monitor.stop()
