"""
Testes unitarios para o Maestro Service.
Testa WindowArranger, TaskWatcher, VisualHeartbeat e InstrumentedRunner.
"""

import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

import pytest

from src.automation.maestro_service import (
    MonitorInfo,
    WindowArranger,
    TaskWatcher,
    VisualHeartbeat,
    InstrumentedRunner,
    MaestroService,
    detect_monitors,
    _get_element_coords,
)


# ============================================================
# MonitorInfo Tests
# ============================================================

class TestMonitorInfo:
    def test_creation(self):
        m = MonitorInfo(1, 0, 0, 1920, 1080)
        assert m.index == 1
        assert m.width == 1920
        assert m.height == 1080
        assert m.left == 0
        assert m.top == 0

    def test_repr(self):
        m = MonitorInfo(2, 1920, 130, 3456, 994)
        assert "Monitor(2:" in repr(m)
        assert "1536x864" in repr(m)

    def test_secondary_monitor(self):
        m = MonitorInfo(1, 1920, 130, 3456, 994)
        assert m.left == 1920
        assert m.width == 1536
        assert m.height == 864


# ============================================================
# WindowArranger Tests
# ============================================================

class TestWindowArranger:
    def test_detect_monitors_returns_list(self):
        monitors = detect_monitors()
        assert isinstance(monitors, list)
        # At least 1 monitor on any machine running tests
        assert len(monitors) >= 1

    def test_get_monitor_valid(self):
        arranger = WindowArranger()
        m1 = arranger.get_monitor(1)
        assert m1 is not None
        assert m1.width > 0

    def test_get_monitor_invalid(self):
        arranger = WindowArranger()
        assert arranger.get_monitor(99) is None

    def test_arrange_with_mocked_monitors(self):
        arranger = WindowArranger()
        # Force 2 monitors for test
        arranger.monitors = [
            MonitorInfo(1, 1920, 130, 3456, 994),  # right (Cursor)
            MonitorInfo(2, 0, 0, 1920, 1080),       # left (Browser)
        ]
        with patch("src.automation.maestro_service._find_window", return_value=None):
            report = arranger.arrange()
        assert report["monitors_detected"] == 2
        assert report["browser_target_monitor"]["left"] == 0

    def test_arrange_single_monitor_skips(self):
        arranger = WindowArranger()
        arranger.monitors = [MonitorInfo(1, 0, 0, 1920, 1080)]
        report = arranger.arrange()
        assert any("skip" in a.lower() for a in report["actions"])

    def test_move_window_calls_methods(self):
        mock_win = MagicMock()
        mock_win.restore = MagicMock()
        mock_win.moveTo = MagicMock()
        mock_win.resizeTo = MagicMock()
        monitor = MonitorInfo(1, 0, 0, 1920, 1080)

        WindowArranger._move_window(mock_win, monitor, "Test")
        mock_win.moveTo.assert_called_once_with(0, 0)
        mock_win.resizeTo.assert_called_once_with(1920, 1080)

    def test_move_browser_to_monitor2_no_dual(self):
        arranger = WindowArranger()
        arranger.monitors = [MonitorInfo(1, 0, 0, 1920, 1080)]
        assert arranger.move_browser_to_monitor2() is False


# ============================================================
# TaskWatcher Tests
# ============================================================

class TestTaskWatcher:
    def test_init_defaults(self):
        tw = TaskWatcher()
        assert tw._poll_interval == 5.0
        assert tw._running is False
        assert tw._seen_task_ids == set()

    def test_poll_once_no_graph(self):
        tw = TaskWatcher(graph_manager=None)
        assert tw._poll_once() == []

    def test_poll_once_with_results(self):
        mock_graph = MagicMock()
        mock_graph.execute_read.return_value = [
            {"t": {"id": "task_1", "status": "pending"}},
            {"t": {"id": "task_2", "status": "pending"}},
        ]
        tw = TaskWatcher(graph_manager=mock_graph)
        new = tw._poll_once()
        assert len(new) == 2
        assert tw._seen_task_ids == {"task_1", "task_2"}

    def test_poll_once_deduplicates(self):
        mock_graph = MagicMock()
        mock_graph.execute_read.return_value = [
            {"t": {"id": "task_1", "status": "pending"}},
        ]
        tw = TaskWatcher(graph_manager=mock_graph)
        first = tw._poll_once()
        second = tw._poll_once()
        assert len(first) == 1
        assert len(second) == 0  # already seen

    def test_poll_once_handles_exception(self):
        mock_graph = MagicMock()
        mock_graph.execute_read.side_effect = Exception("connection refused")
        tw = TaskWatcher(graph_manager=mock_graph)
        assert tw._poll_once() == []

    def test_stop(self):
        tw = TaskWatcher()
        tw._running = True
        tw.stop()
        assert tw._running is False

    def test_start_calls_callback(self):
        mock_graph = MagicMock()
        mock_graph.execute_read.return_value = [
            {"t": {"id": "task_new", "status": "pending"}},
        ]
        callback = AsyncMock()

        tw = TaskWatcher(
            graph_manager=mock_graph,
            poll_interval=0.1,
            on_new_tasks=callback,
        )

        async def _run():
            async def stop_after_delay():
                await asyncio.sleep(0.25)
                tw.stop()
            await asyncio.gather(tw.start(), stop_after_delay())

        asyncio.run(_run())
        callback.assert_called()


# ============================================================
# VisualHeartbeat Tests
# ============================================================

class TestVisualHeartbeat:
    def test_pulse_captures_log(self):
        lines = []
        hb = VisualHeartbeat(output_fn=lines.append)
        hb.pulse("navigate", "google", "#form", 100.0, 200.0, "http://localhost")

        assert len(hb.action_log) == 1
        entry = hb.action_log[0]
        assert entry["step"] == "navigate"
        assert entry["provider"] == "google"
        assert entry["x"] == 100.0
        assert entry["y"] == 200.0
        assert entry["selector"] == "#form"

    def test_pulse_output_contains_coordinates(self):
        lines = []
        hb = VisualHeartbeat(output_fn=lines.append)
        hb.pulse("fill_form", "github", "#input", 350.5, 120.3, "'user'")

        assert len(lines) == 1
        assert "(  350,  120)" in lines[0]  # int-formatted coords

    def test_multiple_pulses_accumulate(self):
        hb = VisualHeartbeat(output_fn=lambda _: None)
        for i in range(5):
            hb.pulse("navigate", "google", f"#el-{i}", float(i * 100), float(i * 50))
        assert len(hb.action_log) == 5

    def test_null_selector(self):
        lines = []
        hb = VisualHeartbeat(output_fn=lines.append)
        hb.pulse("store_key", "groq", None, 0, 0, "vault")
        assert len(lines) == 1
        assert "store_key" in lines[0]


# ============================================================
# _get_element_coords Tests
# ============================================================

class TestGetElementCoords:
    def test_null_selector(self):
        x, y = asyncio.run(_get_element_coords(None, None))
        assert (x, y) == (0.0, 0.0)

    def test_with_mock_page(self):
        mock_element = AsyncMock()
        mock_element.bounding_box.return_value = {
            "x": 100, "y": 200, "width": 50, "height": 30,
        }
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = mock_element

        x, y = asyncio.run(_get_element_coords(mock_page, "#btn"))
        assert x == 125.0  # 100 + 50/2
        assert y == 215.0  # 200 + 30/2

    def test_element_not_found(self):
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = None
        x, y = asyncio.run(_get_element_coords(mock_page, "#missing"))
        assert (x, y) == (0.0, 0.0)

    def test_bounding_box_none(self):
        mock_element = AsyncMock()
        mock_element.bounding_box.return_value = None
        mock_page = AsyncMock()
        mock_page.query_selector.return_value = mock_element

        x, y = asyncio.run(_get_element_coords(mock_page, "#hidden"))
        assert (x, y) == (0.0, 0.0)


# ============================================================
# MaestroService Integration Tests
# ============================================================

class TestMaestroService:
    def test_init_creates_subsystems(self):
        ms = MaestroService()
        assert isinstance(ms.heartbeat, VisualHeartbeat)
        assert isinstance(ms.arranger, WindowArranger)
        assert isinstance(ms.watcher, TaskWatcher)

    def test_init_with_graph(self):
        mock_graph = MagicMock()
        ms = MaestroService(graph_manager=mock_graph)
        assert ms._graph is mock_graph
        assert ms.watcher._graph is mock_graph

    def test_stop(self):
        ms = MaestroService()
        ms._running = True
        ms.stop()
        assert ms._running is False
        assert ms.watcher._running is False

    def test_handle_new_tasks_triggers_e2e(self):
        ms = MaestroService(headless=True)
        ms.run_e2e_now = AsyncMock(return_value={})
        asyncio.run(ms._handle_new_tasks([{"id": "t1"}]))
        ms.run_e2e_now.assert_called_once()

    def test_init_with_router(self):
        mock_router = MagicMock()
        ms = MaestroService(router=mock_router)
        assert ms._router is mock_router

    def test_init_without_router(self):
        ms = MaestroService()
        assert ms._router is None
