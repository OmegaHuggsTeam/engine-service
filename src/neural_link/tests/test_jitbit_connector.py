"""
Testes unitários para JitbitConnector (Task 2 e Task 4).

Task 2.3: JitbitConnector initialization, log file, emoji, timestamp.
Task 4.4: Command conversion edge cases.
"""

import json
import re
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.telemetry.jitbit_connector import (
    JitbitConnector,
    EMOJI_INFO,
    EMOJI_SUCCESS,
    EMOJI_COMPLETE,
    EMOJI_WARNING,
    EMOJI_ERROR,
)


@pytest.fixture
def log_dir(tmp_path):
    """Diretório temporário para logs."""
    return tmp_path / "logs"


@pytest.fixture
def macros_dir(tmp_path):
    """Diretório temporário para macros."""
    return tmp_path / "macros"


@pytest.fixture
def connector(log_dir, macros_dir):
    """JitbitConnector com paths temporários (sem JitbitWrapper)."""
    return JitbitConnector(
        jitbit_wrapper=None,
        log_file=log_dir / "mission_zero.log",
        macros_dir=macros_dir,
        verbose=False,
    )


# ============================================================
# Task 2.3: JitbitConnector Initialization
# ============================================================


class TestJitbitConnectorInit:
    """Testes de inicialização do JitbitConnector."""

    def test_log_file_creation(self, connector, log_dir):
        """Log file é criado no path especificado."""
        connector.log("Teste de criação")
        assert (log_dir / "mission_zero.log").exists()
        content = (log_dir / "mission_zero.log").read_text(encoding="utf-8")
        assert "Teste de criação" in content

    def test_emoji_formatting(self, connector, log_dir):
        """Logs usam emojis corretos."""
        connector.log("Info", emoji=EMOJI_INFO)
        connector.log("Success", emoji=EMOJI_SUCCESS)
        connector.log("Complete", emoji=EMOJI_COMPLETE)
        connector.log("Warning", emoji=EMOJI_WARNING)
        connector.log("Error", emoji=EMOJI_ERROR)
        content = (log_dir / "mission_zero.log").read_text(encoding="utf-8")
        assert EMOJI_INFO in content
        assert EMOJI_SUCCESS in content
        assert EMOJI_COMPLETE in content
        assert EMOJI_WARNING in content
        assert EMOJI_ERROR in content

    def test_timestamp_format(self, connector, log_dir):
        """Timestamp segue formato Mission Zero [YYYY-MM-DD HH:MM:SS.mmm]."""
        connector.log("Mensagem com timestamp")
        content = (log_dir / "mission_zero.log").read_text(encoding="utf-8")
        assert re.match(r"\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d{3}\]", content)


# ============================================================
# Task 4: Action to Jitbit Command Conversion
# ============================================================


class TestConvertToJitbitCommands:
    """Testes de conversão de ações para comandos Jitbit."""

    def test_move_conversion(self, connector):
        """Move (Bézier target) -> MouseMove x y."""
        actions = [{"type": "move", "params": {"x": 960, "y": 540}}]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert cmds == ["MouseMove 960 540"]

    def test_click_conversion(self, connector):
        """Click -> MouseClick x y button clicks."""
        actions = [
            {"type": "click", "params": {"x": 100, "y": 200, "button": "left", "clicks": 1}}
        ]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert cmds == ["MouseClick 100 200 left 1"]

    def test_type_conversion(self, connector):
        """Type -> KeyboardType "text"."""
        actions = [{"type": "type", "params": {"text": "Hello World", "interval": 0.05}}]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert 'KeyboardType "Hello World"' in cmds[0]

    def test_special_characters_keyboard(self, connector):
        """Caracteres especiais em texto são escapados."""
        actions = [{"type": "type", "params": {"text": 'Say "hello"', "interval": 0.05}}]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert "KeyboardType" in cmds[0]
        assert '"' in cmds[0]

    def test_boundary_coordinates(self, connector):
        """Coordenadas de boundary (0,0 e valores altos)."""
        actions = [
            {"type": "move", "params": {"x": 0, "y": 0}},
            {"type": "click", "params": {"x": 1920, "y": 1080, "button": "left", "clicks": 1}},
        ]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert "MouseMove 0 0" in cmds
        assert "MouseClick 1920 1080 left 1" in cmds

    def test_window_handle_inclusion(self, connector):
        """WindowActivate é o primeiro comando quando window_handle fornecido."""
        actions = [{"type": "move", "params": {"x": 100, "y": 100}}]
        cmds = connector.convert_to_jitbit_commands(actions, window_handle=12345)
        assert cmds[0] == "WindowActivate 12345"
        assert cmds[1] == "MouseMove 100 100"

    def test_invalid_action_type_ignored(self, connector):
        """Tipos de ação inválidos são ignorados (não quebram)."""
        actions = [
            {"type": "move", "params": {"x": 50, "y": 50}},
            {"type": "unknown_type", "params": {}},
            {"type": "click", "params": {"x": 60, "y": 60, "button": "left", "clicks": 1}},
        ]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert len(cmds) == 2  # move + click, unknown ignorado
        assert "MouseMove 50 50" in cmds
        assert "MouseClick 60 60 left 1" in cmds

    def test_wait_conversion(self, connector):
        """Wait -> Wait milliseconds."""
        actions = [{"type": "wait", "params": {"duration": 1.5}}]
        cmds = connector.convert_to_jitbit_commands(actions)
        assert cmds == ["Wait 1500"]


# ============================================================
# Parse Movement Logs
# ============================================================


class TestParseMovementLogs:
    """Testes de parsing de logs Mission Zero."""

    def test_parse_posicao_alvo(self, connector):
        """Parse 'Posição alvo: (x, y)' -> move."""
        logs = [
            "[2026-03-03 10:15:30.123] [INFO    ] Posição alvo: (960, 980)"
        ]
        actions = connector.parse_movement_logs(logs)
        assert len(actions) == 1
        assert actions[0]["type"] == "move"
        assert actions[0]["params"]["x"] == 960
        assert actions[0]["params"]["y"] == 980

    def test_parse_clicando_em(self, connector):
        """Parse 'Clicando em (x, y)...' -> click."""
        logs = [
            "[2026-03-03 10:15:31.456] [INFO    ] Clicando em (960, 980)..."
        ]
        actions = connector.parse_movement_logs(logs)
        assert len(actions) == 1
        assert actions[0]["type"] == "click"
        assert actions[0]["params"]["x"] == 960
        assert actions[0]["params"]["y"] == 980

    def test_parse_mensagem_type(self, connector):
        """Parse 'Mensagem: \"...\"' -> type."""
        logs = [
            '[2026-03-03 10:15:32.000] [INFO    ]   Mensagem: "Controle de Autonomia"'
        ]
        actions = connector.parse_movement_logs(logs)
        assert len(actions) == 1
        assert actions[0]["type"] == "type"
        assert actions[0]["params"]["text"] == "Controle de Autonomia"


# ============================================================
# Generate Macro File
# ============================================================


class TestGenerateMacroFile:
    """Testes de geração de arquivo de macro."""

    def test_macro_file_created(self, connector, macros_dir):
        """Arquivo de macro é criado no diretório correto."""
        commands = ["MouseMove 100 200", "MouseClick 100 200 left 1"]
        out = macros_dir / "test_macro.json"
        path = connector.generate_macro_file(commands, out)
        assert path.exists()
        assert path.parent == macros_dir

    def test_macro_json_valid(self, connector, macros_dir):
        """Macro gerada é JSON válido."""
        commands = ["MouseMove 100 200"]
        out = macros_dir / "test.json"
        connector.generate_macro_file(commands, out)
        with open(out, encoding="utf-8") as f:
            data = json.load(f)
        assert "metadata" in data
        assert "commands" in data
        assert len(data["commands"]) == 1
        assert data["commands"][0]["command"] == "MouseMove 100 200"


class TestRunMacro:
    """Testes de run_macro e helpers."""

    def test_read_macro_mouse_move_coordinates(self, connector, macros_dir):
        """read_macro_mouse_move_coordinates extrai apenas MouseMove."""
        out = macros_dir / "coord_test.json"
        connector.generate_macro_file(
            ["MouseMove 100 200", "MouseClick 300 400 left 1", "Wait 500"],
            out,
        )
        coords = JitbitConnector.read_macro_mouse_move_coordinates(out)
        assert coords == [(100, 200)]

    def test_run_macro_virtual_driver_json(self, connector, macros_dir):
        """run_macro com JSON usa Virtual Driver."""
        out = macros_dir / "run_test.json"
        connector.generate_macro_file(["MouseMove 50 50", "Wait 10"], out)
        debug_events = []
        def on_debug(i, cmd, start, end, dur):
            debug_events.append((i, cmd[:20], dur))
        ok = connector.run_macro(out, on_command_debug=on_debug)
        assert ok
        assert len(debug_events) == 2
        assert debug_events[0][1].startswith("MouseMove")
