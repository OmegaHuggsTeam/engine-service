"""
Tests for ObsidianBridge - Obsidian vault generation from Neural Link data.

All Neo4j calls are mocked; tests run without a live database.
"""

import os
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.neural_link.telemetry.obsidian_bridge import (
    ObsidianBridge,
    SourceWatcher,
    validate_environment,
)
from src.neural_link.telemetry.provider import (
    TelemetryHub,
    TelemetryProvider,
    TelemetryEvent,
    EventType,
    JitbitConnector,
)
from src.neural_link.telemetry.ifttt_bridge import IFTTTBridge
from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY


@pytest.fixture
def vault_dir(tmp_path):
    """Temporary vault directory."""
    return tmp_path / "vault"


@pytest.fixture
def mock_graph():
    """GraphManager mock with canned responses."""
    gm = MagicMock()
    gm.execute_read.return_value = []
    gm.verify_connectivity.return_value = True
    return gm


@pytest.fixture
def bridge(vault_dir, mock_graph):
    """ObsidianBridge with mocked graph manager."""
    return ObsidianBridge(vault_path=vault_dir, graph_manager=mock_graph)


@pytest.fixture
def bridge_no_graph(vault_dir):
    """ObsidianBridge without graph manager (static fallback)."""
    return ObsidianBridge(vault_path=vault_dir, graph_manager=None)


# ============================================================
# TestSyncAgents
# ============================================================

class TestSyncAgents:
    """Tests for sync_agents()."""

    def test_generates_all_agent_notes(self, bridge):
        """One .md file per agent in the registry."""
        written = bridge.sync_agents()
        assert len(written) == len(AGENT_REGISTRY)

    def test_agent_files_exist(self, bridge, vault_dir):
        """Each agent gets a file in vault/Agents/."""
        bridge.sync_agents()
        agents_dir = vault_dir / "Agents"
        for agent_id in AGENT_REGISTRY:
            assert (agents_dir / f"{agent_id}.md").exists()

    def test_frontmatter_valid_yaml(self, bridge, vault_dir):
        """Each agent note has valid YAML frontmatter."""
        bridge.sync_agents()
        agents_dir = vault_dir / "Agents"
        for agent_id in AGENT_REGISTRY:
            content = (agents_dir / f"{agent_id}.md").read_text(encoding="utf-8")
            assert content.startswith("---\n")
            fm_block = content.split("---\n")[1]
            fm = yaml.safe_load(fm_block)
            assert fm["agent_id"] == agent_id
            assert fm["name"] == AGENT_REGISTRY[agent_id]["name"]
            assert fm["type"] == AGENT_REGISTRY[agent_id]["type"]
            assert isinstance(fm["capabilities"], list)
            assert len(fm["capabilities"]) > 0

    def test_capabilities_present_in_body(self, bridge, vault_dir):
        """Agent body lists capabilities as bullets."""
        bridge.sync_agents()
        content = (vault_dir / "Agents" / "devops_agent.md").read_text(encoding="utf-8")
        assert "- monitoring" in content
        assert "- health_check" in content

    def test_no_api_keys_in_output(self, bridge, vault_dir):
        """No secrets leak into vault files."""
        bridge.sync_agents()
        agents_dir = vault_dir / "Agents"
        for agent_id in AGENT_REGISTRY:
            content = (agents_dir / f"{agent_id}.md").read_text(encoding="utf-8")
            lower = content.lower()
            assert "api_key" not in lower
            assert "password" not in lower
            assert "secret" not in lower

    def test_wikilinks_in_body(self, bridge, vault_dir):
        """Agent notes link to spec pages."""
        bridge.sync_agents()
        content = (vault_dir / "Agents" / "groq_operator.md").read_text(encoding="utf-8")
        assert "[[AgentSelector]]" in content
        assert "[[TaskExecutor]]" in content
        assert "[[TaskEvaluator]]" in content

    def test_neo4j_enrichment(self, bridge, mock_graph, vault_dir):
        """When Neo4j returns data, success_rate is enriched."""
        mock_graph.execute_read.return_value = [
            {"id": "devops_agent", "name": "DevOps Agent", "type": "specialist",
             "success_rate": 0.92, "status": "active"},
        ]
        bridge.sync_agents()
        content = (vault_dir / "Agents" / "devops_agent.md").read_text(encoding="utf-8")
        fm_block = content.split("---\n")[1]
        fm = yaml.safe_load(fm_block)
        assert fm["success_rate"] == 0.92


# ============================================================
# TestSyncDashboard
# ============================================================

class TestSyncDashboard:
    """Tests for sync_dashboard()."""

    def test_dashboard_created(self, bridge, vault_dir):
        """Dashboard.md is written to vault root."""
        bridge.sync_dashboard()
        assert (vault_dir / "Dashboard.md").exists()

    def test_dataview_codeblocks(self, bridge, vault_dir):
        """Dashboard contains dataview queries."""
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert "```dataview" in content
        assert 'FROM "Agents"' in content
        assert 'FROM "Missions"' in content

    def test_dataview_agent_type_grouping(self, bridge, vault_dir):
        """Dashboard has GROUP BY type query for agent breakdown."""
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert "GROUP BY type" in content

    def test_dataview_active_agents(self, bridge, vault_dir):
        """Dashboard has active agents list query."""
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert 'status = "active"' in content

    def test_dataview_capability_coverage(self, bridge, vault_dir):
        """Dashboard has capability coverage query."""
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert "Capability Coverage" in content
        assert "capabilities" in content.lower()

    def test_dataview_recent_missions(self, bridge, vault_dir):
        """Dashboard has recent missions limited query."""
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert "LIMIT 10" in content

    def test_dataview_wastage_overview(self, bridge, vault_dir):
        """Dashboard links to Telemetry folder."""
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert 'FROM "Telemetry"' in content

    def test_graph_stats_with_data(self, bridge, mock_graph, vault_dir):
        """Graph stats table rendered when Neo4j returns data."""
        mock_graph.execute_read.return_value = [
            {"label": "Agent", "count": 19},
            {"label": "Task", "count": 42},
        ]
        bridge.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert "| Agent | 19 |" in content
        assert "| Task | 42 |" in content

    def test_graph_stats_fallback(self, bridge_no_graph, vault_dir):
        """Graceful message when Neo4j unavailable."""
        bridge_no_graph.sync_dashboard()
        content = (vault_dir / "Dashboard.md").read_text(encoding="utf-8")
        assert "stats unavailable" in content


# ============================================================
# TestSyncMissions
# ============================================================

class TestSyncMissions:
    """Tests for sync_missions()."""

    def _make_mission_result(self, passed=True):
        mock_eval = MagicMock()
        mock_eval.quality_score = 8.5
        return {
            "mission_name": "Stress_Mission_001",
            "mission_id": "stress_001",
            "mission_passed": passed,
            "agents_used": ["devops_agent", "testing_agent"],
            "eval1": mock_eval,
            "eval2": mock_eval,
        }

    def test_mission_note_created(self, bridge, vault_dir):
        """Mission .md file is written."""
        bridge.sync_missions(self._make_mission_result())
        assert (vault_dir / "Missions" / "Stress_Mission_001.md").exists()

    def test_mission_agent_wikilinks(self, bridge, vault_dir):
        """Mission note has WikiLinks to agents."""
        bridge.sync_missions(self._make_mission_result())
        content = (vault_dir / "Missions" / "Stress_Mission_001.md").read_text(encoding="utf-8")
        assert "[[devops_agent]]" in content
        assert "[[testing_agent]]" in content

    def test_mission_frontmatter(self, bridge, vault_dir):
        """Mission frontmatter has correct fields."""
        bridge.sync_missions(self._make_mission_result(passed=False))
        content = (vault_dir / "Missions" / "Stress_Mission_001.md").read_text(encoding="utf-8")
        fm_block = content.split("---\n")[1]
        fm = yaml.safe_load(fm_block)
        assert fm["mission_id"] == "stress_001"
        assert fm["status"] == "failed"
        assert "devops_agent" in fm["agents_used"]

    def test_mission_scores_in_body(self, bridge, vault_dir):
        """Scores section present when evals have quality_score."""
        bridge.sync_missions(self._make_mission_result())
        content = (vault_dir / "Missions" / "Stress_Mission_001.md").read_text(encoding="utf-8")
        assert "8.5" in content


# ============================================================
# TestSyncWastage
# ============================================================

SAMPLE_TASK_ROWS = [
    {"agent_id": "devops_agent", "agent_name": "DevOps Agent",
     "task_id": "t1", "description": "Monitor", "type": "analysis",
     "quality_score": 8.0, "feedback": "Good", "status": "completed",
     "created_at": "2026-03-03"},
    {"agent_id": "devops_agent", "agent_name": "DevOps Agent",
     "task_id": "t2", "description": "Deploy", "type": "automation",
     "quality_score": 7.5, "feedback": None, "status": "completed",
     "created_at": "2026-03-03"},
    {"agent_id": "testing_agent", "agent_name": "Testing Agent",
     "task_id": "t3", "description": "Test", "type": "analysis",
     "quality_score": 9.0, "feedback": "Excellent", "status": "completed",
     "created_at": "2026-03-03"},
]


class TestSyncWastage:
    """Tests for sync_wastage()."""

    def test_wastage_created(self, bridge, vault_dir):
        """Wastage_Report.md is written."""
        bridge.sync_wastage()
        assert (vault_dir / "Telemetry" / "Wastage_Report.md").exists()

    def test_wastage_with_agent_data(self, bridge, mock_graph, vault_dir):
        """Per-agent sections when task data available."""
        mock_graph.execute_read.side_effect = [list(SAMPLE_TASK_ROWS)]
        bridge.sync_wastage()
        content = (vault_dir / "Telemetry" / "Wastage_Report.md").read_text(encoding="utf-8")
        assert "[[devops_agent]]" in content
        assert "[[testing_agent]]" in content
        assert "Tasks assigned" in content
        assert "7.75" in content  # avg of 8.0 and 7.5

    def test_wastage_no_data_fallback(self, bridge_no_graph, vault_dir):
        """Graceful message without Neo4j."""
        bridge_no_graph.sync_wastage()
        content = (vault_dir / "Telemetry" / "Wastage_Report.md").read_text(encoding="utf-8")
        assert "No task-agent data" in content

    def test_wastage_mermaid_chart(self, bridge, mock_graph, vault_dir):
        """Wastage report contains a mermaid pie chart when data exists."""
        mock_graph.execute_read.side_effect = [list(SAMPLE_TASK_ROWS)]
        bridge.sync_wastage()
        content = (vault_dir / "Telemetry" / "Wastage_Report.md").read_text(encoding="utf-8")
        assert "```mermaid" in content
        assert "pie title" in content
        assert "Token Usage by Agent" in content
        assert '"devops_agent"' in content
        assert '"testing_agent"' in content

    def test_wastage_mermaid_has_total(self, bridge, mock_graph, vault_dir):
        """Mermaid section reports total estimated tokens."""
        mock_graph.execute_read.side_effect = [list(SAMPLE_TASK_ROWS)]
        bridge.sync_wastage()
        content = (vault_dir / "Telemetry" / "Wastage_Report.md").read_text(encoding="utf-8")
        assert "Total estimated tokens" in content

    def test_wastage_token_estimate_per_agent(self, bridge, mock_graph, vault_dir):
        """Each agent section includes a token estimate line."""
        mock_graph.execute_read.side_effect = [list(SAMPLE_TASK_ROWS)]
        bridge.sync_wastage()
        content = (vault_dir / "Telemetry" / "Wastage_Report.md").read_text(encoding="utf-8")
        assert "Est. tokens consumed" in content

    def test_wastage_no_mermaid_without_data(self, bridge_no_graph, vault_dir):
        """No mermaid block when there's no task data."""
        bridge_no_graph.sync_wastage()
        content = (vault_dir / "Telemetry" / "Wastage_Report.md").read_text(encoding="utf-8")
        assert "```mermaid" not in content


# ============================================================
# TestEnvironmentValidation
# ============================================================

class TestEnvironmentValidation:
    """Tests for validate_environment()."""

    def test_valid_environment(self, tmp_path):
        """No warnings when vault is writable and NEO4J_URI set."""
        vault = tmp_path / "vault"
        with patch.dict(os.environ, {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_USER": "neo4j",
                                      "NEO4J_PASSWORD": "test123"}):
            status = validate_environment(vault)
        assert status.vault_writable is True
        assert status.neo4j_configured is True
        assert len(status.warnings) == 0
        assert status.ok is True

    def test_missing_neo4j_uri(self, tmp_path):
        """Warns when NEO4J_URI is not set."""
        vault = tmp_path / "vault"
        with patch.dict(os.environ, {}, clear=True):
            # Ensure key absent
            os.environ.pop("NEO4J_URI", None)
            os.environ.pop("NEO4J_USER", None)
            os.environ.pop("NEO4J_PASSWORD", None)
            status = validate_environment(vault)
        assert any("NEO4J_URI" in w for w in status.warnings)
        assert status.neo4j_configured is False
        # vault should still be writable
        assert status.vault_writable is True

    def test_unwritable_vault(self, tmp_path):
        """Warns when vault path is not writable."""
        # Use a path that can't be created (nested under a file)
        blocker = tmp_path / "blocker"
        blocker.write_text("I am a file")
        vault = blocker / "vault" / "nested"
        status = validate_environment(vault)
        assert any("not writable" in w for w in status.warnings)
        assert status.vault_writable is False

    def test_neo4j_connectivity_check(self, tmp_path, mock_graph):
        """Connectivity check integrates with graph_manager."""
        vault = tmp_path / "vault"
        mock_graph.verify_connectivity.return_value = True
        with patch.dict(os.environ, {"NEO4J_URI": "bolt://localhost:7687", "NEO4J_USER": "neo4j",
                                      "NEO4J_PASSWORD": "pass"}):
            status = validate_environment(vault, check_neo4j_connection=True, graph_manager=mock_graph)
        mock_graph.verify_connectivity.assert_called_once()
        assert status.ok is True

    def test_neo4j_connectivity_failure(self, tmp_path, mock_graph):
        """Warns when connectivity check fails."""
        vault = tmp_path / "vault"
        mock_graph.verify_connectivity.return_value = False
        with patch.dict(os.environ, {"NEO4J_URI": "bolt://remote:7687", "NEO4J_USER": "neo4j",
                                      "NEO4J_PASSWORD": "pass"}):
            status = validate_environment(vault, check_neo4j_connection=True, graph_manager=mock_graph)
        assert any("connectivity" in w.lower() for w in status.warnings)

    def test_never_crashes(self, tmp_path, mock_graph):
        """validate_environment never raises, even on bizarre errors."""
        vault = tmp_path / "vault"
        mock_graph.verify_connectivity.side_effect = RuntimeError("driver exploded")
        with patch.dict(os.environ, {"NEO4J_URI": "bolt://x:7687", "NEO4J_USER": "u",
                                      "NEO4J_PASSWORD": "p"}):
            status = validate_environment(vault, check_neo4j_connection=True, graph_manager=mock_graph)
        # Should have a warning, not an exception
        assert any("error" in w.lower() for w in status.warnings)


# ============================================================
# TestSourceWatcher
# ============================================================

class TestSourceWatcher:
    """Tests for the SourceWatcher polling logic."""

    def test_no_changes_initially(self, tmp_path):
        """First call to has_changes after init returns False."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hi')")
        watcher = SourceWatcher(src)
        assert watcher.has_changes() is False

    def test_detects_file_change(self, tmp_path):
        """Detects when a .py file is modified."""
        src = tmp_path / "src"
        src.mkdir()
        f = src / "main.py"
        f.write_text("v1")
        watcher = SourceWatcher(src)
        assert watcher.has_changes() is False

        # Bump mtime forward
        time.sleep(0.05)
        f.write_text("v2")
        assert watcher.has_changes() is True
        # Second call: no new change
        assert watcher.has_changes() is False

    def test_detects_new_file(self, tmp_path):
        """Detects when a new .py file appears."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("a")
        watcher = SourceWatcher(src)
        assert watcher.has_changes() is False

        time.sleep(0.05)
        (src / "b.py").write_text("b")
        assert watcher.has_changes() is True

    def test_nonexistent_src(self, tmp_path):
        """Handles missing src directory gracefully."""
        watcher = SourceWatcher(tmp_path / "nonexistent")
        assert watcher.has_changes() is False

    def test_neo4j_task_count_change(self):
        """Detects Neo4j task count changes."""
        gm = MagicMock()
        gm.execute_read.return_value = [{"cnt": 5}]
        watcher = SourceWatcher(Path("/fake"), graph_manager=gm)

        # No change
        gm.execute_read.return_value = [{"cnt": 5}]
        assert watcher.has_changes() is False

        # Task count changed
        gm.execute_read.return_value = [{"cnt": 8}]
        assert watcher.has_changes() is True

    def test_neo4j_error_handled(self):
        """Neo4j errors don't crash the watcher."""
        gm = MagicMock()
        gm.execute_read.side_effect = Exception("down")
        watcher = SourceWatcher(Path("/fake"), graph_manager=gm)
        # Should not raise
        assert watcher.has_changes() is False


# ============================================================
# TestWatchLoop
# ============================================================

class TestWatchLoop:
    """Tests for the ObsidianBridge.watch() method."""

    def test_watch_max_cycles(self, bridge, tmp_path):
        """watch() respects _max_cycles and stops."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "a.py").write_text("a")
        # Should complete without blocking
        bridge.watch(src_path=src, interval=0.01, _max_cycles=2)

    def test_watch_syncs_on_change(self, bridge, mock_graph, tmp_path):
        """watch() triggers full_sync when watcher detects changes."""
        src = tmp_path / "src"
        src.mkdir()
        (src / "main.py").write_text("v1")

        sync_count = {"n": 0}
        original_full_sync = bridge.full_sync

        def counting_sync(*a, **kw):
            sync_count["n"] += 1
            return original_full_sync(*a, **kw)

        bridge.full_sync = counting_sync

        # Patch has_changes to return True on first cycle
        with patch.object(SourceWatcher, "has_changes", return_value=True):
            bridge.watch(src_path=src, interval=0.01, _max_cycles=1)

        assert sync_count["n"] >= 1


# ============================================================
# TestGracefulFallback
# ============================================================

class TestGracefulFallback:
    """Tests that all syncs work without Neo4j."""

    def test_sync_agents_static(self, bridge_no_graph, vault_dir):
        """sync_agents works with static registry only."""
        written = bridge_no_graph.sync_agents()
        assert len(written) == len(AGENT_REGISTRY)

        # success_rate should default to N/A
        content = (vault_dir / "Agents" / "devops_agent.md").read_text(encoding="utf-8")
        fm_block = content.split("---\n")[1]
        fm = yaml.safe_load(fm_block)
        assert fm["success_rate"] == "N/A"

    def test_full_sync_no_graph(self, bridge_no_graph):
        """full_sync completes without errors when no graph."""
        results = bridge_no_graph.full_sync()
        assert "agents" in results
        assert "dashboard" in results
        assert "wastage" in results
        assert len(results["agents"]) == len(AGENT_REGISTRY)

    def test_full_sync_with_mission(self, bridge_no_graph):
        """full_sync includes mission when result provided."""
        mock_eval = MagicMock()
        mock_eval.quality_score = 7.0
        mission = {
            "mission_name": "test_mission",
            "mission_passed": True,
            "agents_used": ["groq_operator"],
            "eval1": mock_eval,
        }
        results = bridge_no_graph.full_sync(mission_result=mission)
        assert results["mission"] == "test_mission.md"

    def test_neo4j_exception_handled(self, bridge, mock_graph, vault_dir):
        """Neo4j exceptions don't crash syncs."""
        mock_graph.execute_read.side_effect = Exception("Connection refused")
        # Should not raise
        written = bridge.sync_agents()
        assert len(written) == len(AGENT_REGISTRY)


# ============================================================
# TestTelemetryHub
# ============================================================

class TestTelemetryHub:
    """Tests for TelemetryHub observer dispatcher."""

    def test_register_provider(self):
        """Registering a provider makes it available."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        hub.register(jc)
        assert "jitbit" in hub.provider_ids

    def test_unregister_provider(self):
        """Unregistering removes the provider."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        hub.register(jc)
        assert hub.unregister("jitbit") is True
        assert "jitbit" not in hub.provider_ids

    def test_unregister_nonexistent(self):
        """Unregistering unknown id returns False."""
        hub = TelemetryHub()
        assert hub.unregister("ghost") is False

    def test_poll_all_collects_events(self):
        """poll_all drains events from all providers."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.TASK_STARTED, "ticket #42 opened")
        jc.push_event(EventType.TASK_COMPLETED, "ticket #42 resolved")
        hub.register(jc)

        events = hub.poll_all()
        assert len(events) == 2
        assert events[0].message == "ticket #42 opened"
        assert events[1].source == "jitbit"

    def test_subscriber_called(self):
        """Subscribers receive dispatched events."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.LOG, "hello")
        hub.register(jc)

        received = []
        hub.subscribe(lambda ev: received.append(ev))

        hub.poll_all()
        assert len(received) == 1
        assert received[0].message == "hello"

    def test_event_log_persisted(self):
        """get_event_log returns all historical events."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.LOG, "a")
        hub.register(jc)
        hub.poll_all()

        jc.push_event(EventType.LOG, "b")
        hub.poll_all()

        log = hub.get_event_log()
        assert len(log) == 2

    def test_events_by_source(self):
        """get_events_by_source filters correctly."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.LOG, "jitbit event")
        hub.register(jc)
        hub.poll_all()

        assert len(hub.get_events_by_source("jitbit")) == 1
        assert len(hub.get_events_by_source("other")) == 0

    def test_health_check(self):
        """health() reports per-provider status."""
        hub = TelemetryHub()
        hub.register(JitbitConnector())
        h = hub.health()
        assert h["jitbit"] is True

    def test_provider_poll_error_handled(self):
        """A failing provider doesn't crash poll_all."""
        hub = TelemetryHub()
        bad = MagicMock(spec=TelemetryProvider)
        bad.provider_id = "broken"
        bad.display_name = "Broken"
        bad.poll.side_effect = RuntimeError("boom")
        hub.register(bad)

        events = hub.poll_all()
        # Should have one error event
        assert len(events) == 1
        assert "error" in events[0].data


# ============================================================
# TestJitbitConnector
# ============================================================

class TestJitbitConnector:
    """Tests for JitbitConnector provider."""

    def test_provider_id(self):
        assert JitbitConnector().provider_id == "jitbit"

    def test_display_name(self):
        assert JitbitConnector().display_name == "Jitbit Helpdesk"

    def test_push_and_poll(self):
        """push_event + poll drains the buffer."""
        jc = JitbitConnector()
        jc.push_event(EventType.TASK_STARTED, "ticket opened", {"ticket_id": 42})
        events = jc.poll()
        assert len(events) == 1
        assert events[0].event_type == EventType.TASK_STARTED
        assert events[0].data["ticket_id"] == 42
        # Buffer drained
        assert jc.poll() == []

    def test_health_check_no_url(self):
        """Health returns True when no base_url (pre-integration)."""
        assert JitbitConnector().health_check() is True

    def test_health_check_with_url(self):
        """Health returns True with a base_url set."""
        assert JitbitConnector(base_url="http://jitbit.local").health_check() is True

    def test_persist_to_graph(self):
        """Events are batched to graph_manager."""
        gm = MagicMock()
        gm.execute_write_batch.return_value = 2
        jc = JitbitConnector()
        events = [
            TelemetryEvent(EventType.TASK_STARTED, "jitbit", "ev1", data={"phase": "phase_6"}),
            TelemetryEvent(EventType.TASK_COMPLETED, "jitbit", "ev2"),
        ]
        count = jc.persist_to_graph(gm, events)
        assert count == 2
        gm.execute_write_batch.assert_called_once()

    def test_persist_no_graph(self):
        """persist_to_graph returns 0 without graph_manager."""
        jc = JitbitConnector()
        assert jc.persist_to_graph(None) == 0

    def test_persist_graph_error(self):
        """persist_to_graph handles errors gracefully."""
        gm = MagicMock()
        gm.execute_write_batch.side_effect = Exception("neo4j down")
        jc = JitbitConnector()
        events = [TelemetryEvent(EventType.LOG, "jitbit", "test")]
        assert jc.persist_to_graph(gm, events) == 0

    def test_get_buffered_events(self):
        """get_buffered_events peeks without draining."""
        jc = JitbitConnector()
        jc.push_event(EventType.LOG, "peek")
        assert len(jc.get_buffered_events()) == 1
        # Still there
        assert len(jc.get_buffered_events()) == 1


# ============================================================
# TestSyncExternalOrchestration
# ============================================================

class TestSyncExternalOrchestration:
    """Tests for sync_external_orchestration() vault note."""

    def test_creates_note(self, vault_dir, mock_graph):
        """External_Orchestration.md is created."""
        mock_graph.verify_connectivity.return_value = True
        bridge = ObsidianBridge(vault_path=vault_dir, graph_manager=mock_graph)
        bridge.sync_external_orchestration()
        assert (vault_dir / "Integrations" / "External_Orchestration.md").exists()

    def test_no_hub_shows_no_providers(self, vault_dir):
        """Without hub, shows 'no providers' message."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "No telemetry providers registered" in content

    def test_hub_shows_provider_status(self, vault_dir):
        """With hub + jitbit, provider table rendered."""
        hub = TelemetryHub()
        hub.register(JitbitConnector())
        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "[[jitbit]]" in content
        assert "online" in content

    def test_hub_events_in_log(self, vault_dir):
        """Hub event log appears in the note."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.TASK_STARTED, "ticket #99 opened")
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "ticket #99 opened" in content
        assert "Live Event Log" in content

    def test_neo4j_sync_history(self, vault_dir, mock_graph):
        """Neo4j ExternalSync records appear in the note."""
        mock_graph.execute_read.return_value = [
            {"id": "jitbit_1", "source": "jitbit", "event_type": "task_completed",
             "message": "macro sync done", "data": "{}", "phase": "phase_6",
             "created_at": "2026-03-03T12:00:00"},
        ]
        mock_graph.verify_connectivity.return_value = True
        bridge = ObsidianBridge(vault_path=vault_dir, graph_manager=mock_graph)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "macro sync done" in content
        assert "Sync History" in content

    def test_phase6_readiness_section(self, vault_dir, mock_graph):
        """Phase 6 readiness section present."""
        mock_graph.execute_read.return_value = []
        mock_graph.verify_connectivity.return_value = True
        bridge = ObsidianBridge(vault_path=vault_dir, graph_manager=mock_graph)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Phase 6" in content
        assert "Macro Synchronization" in content
        assert "Neo4j reachable: yes" in content

    def test_phase6_no_neo4j(self, vault_dir):
        """Phase 6 shows offline without graph."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Neo4j reachable: no" in content

    def test_full_sync_includes_external(self, bridge_no_graph):
        """full_sync now includes external orchestration."""
        results = bridge_no_graph.full_sync()
        assert "external" in results
        assert results["external"] == "External_Orchestration.md"


# ============================================================
# TestPhase6Queries
# ============================================================

class TestPhase6Queries:
    """Tests that Phase 6 Cypher queries are well-formed constants."""

    def test_upsert_external_sync_exists(self):
        from src.neural_link.graph import queries as q
        assert "ExternalSync" in q.UPSERT_EXTERNAL_SYNC
        assert "$id" in q.UPSERT_EXTERNAL_SYNC
        assert "$source" in q.UPSERT_EXTERNAL_SYNC
        assert "$phase" in q.UPSERT_EXTERNAL_SYNC

    def test_get_external_syncs_exists(self):
        from src.neural_link.graph import queries as q
        assert "ExternalSync" in q.GET_EXTERNAL_SYNCS
        assert "$source" in q.GET_EXTERNAL_SYNCS
        assert "$limit" in q.GET_EXTERNAL_SYNCS

    def test_constraint_exists(self):
        from src.neural_link.graph import queries as q
        assert "CREATE CONSTRAINT" in q.CREATE_EXTERNAL_SYNC_CONSTRAINT
        assert "ExternalSync" in q.CREATE_EXTERNAL_SYNC_CONSTRAINT

    def test_index_exists(self):
        from src.neural_link.graph import queries as q
        assert "CREATE INDEX" in q.CREATE_EXTERNAL_SYNC_SOURCE_INDEX

    def test_link_sync_to_task(self):
        from src.neural_link.graph import queries as q
        assert "TRIGGERED" in q.LINK_SYNC_TO_TASK
        assert "$sync_id" in q.LINK_SYNC_TO_TASK
        assert "$task_id" in q.LINK_SYNC_TO_TASK

    def test_sync_stats_query(self):
        from src.neural_link.graph import queries as q
        assert "ExternalSync" in q.GET_EXTERNAL_SYNC_STATS
        assert "count" in q.GET_EXTERNAL_SYNC_STATS


# ============================================================
# TestMermaidGantt
# ============================================================

class TestMermaidGantt:
    """Tests for _build_mermaid_gantt() Gantt chart generation."""

    def test_gantt_no_events(self):
        """Empty events produce fallback message."""
        lines = ObsidianBridge._build_mermaid_gantt([])
        text = "\n".join(lines)
        assert "No events available" in text

    def test_gantt_no_phase_data(self):
        """Events without phase data produce fallback."""
        events = [
            TelemetryEvent(EventType.LOG, "jitbit", "no phase here"),
        ]
        lines = ObsidianBridge._build_mermaid_gantt(events)
        text = "\n".join(lines)
        assert "No phase data" in text

    def test_gantt_with_phases(self):
        """Events with phase data produce a valid Gantt chart."""
        events = [
            TelemetryEvent(
                EventType.TASK_STARTED, "jitbit", "phase start",
                timestamp="2026-03-03T10:00:00",
                data={"phase": "initialization"},
            ),
            TelemetryEvent(
                EventType.TASK_COMPLETED, "jitbit", "phase end",
                timestamp="2026-03-03T10:05:00",
                data={"phase": "initialization"},
            ),
            TelemetryEvent(
                EventType.TASK_STARTED, "jitbit", "exec start",
                timestamp="2026-03-03T10:05:00",
                data={"phase": "execution"},
            ),
            TelemetryEvent(
                EventType.TASK_COMPLETED, "jitbit", "exec end",
                timestamp="2026-03-03T10:15:00",
                data={"phase": "execution"},
            ),
        ]
        lines = ObsidianBridge._build_mermaid_gantt(events)
        text = "\n".join(lines)
        assert "```mermaid" in text
        assert "gantt" in text
        assert "Mission Zero" in text
        assert "initialization" in text
        assert "execution" in text
        assert "2026-03-03T10:00:00" in text
        assert "2026-03-03T10:15:00" in text

    def test_gantt_in_external_orchestration(self, vault_dir):
        """sync_external_orchestration includes Gantt chart section."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.TASK_STARTED, "phase start",
            data={"phase": "deployment"},
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Mission Phase Timeline" in content
        assert "```mermaid" in content
        assert "gantt" in content

    def test_gantt_no_hub_fallback(self, vault_dir):
        """Without hub, shows timeline fallback message."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Mission Phase Timeline" in content
        assert "No events available" in content


# ============================================================
# TestPerformanceAnomalies
# ============================================================

class TestPerformanceAnomalies:
    """Tests for GET_PERFORMANCE_ANOMALIES query constant."""

    def test_query_exists(self):
        from src.neural_link.graph import queries as q
        assert hasattr(q, "GET_PERFORMANCE_ANOMALIES")

    def test_query_has_threshold_param(self):
        from src.neural_link.graph import queries as q
        assert "$quality_threshold" in q.GET_PERFORMANCE_ANOMALIES

    def test_query_has_time_window(self):
        from src.neural_link.graph import queries as q
        assert "$minutes_window" in q.GET_PERFORMANCE_ANOMALIES
        assert "duration" in q.GET_PERFORMANCE_ANOMALIES

    def test_query_joins_task_to_agent(self):
        from src.neural_link.graph import queries as q
        assert "ASSIGNED_TO" in q.GET_PERFORMANCE_ANOMALIES
        assert "Agent" in q.GET_PERFORMANCE_ANOMALIES
        assert "Task" in q.GET_PERFORMANCE_ANOMALIES

    def test_query_returns_expected_fields(self):
        from src.neural_link.graph import queries as q
        assert "agent_id" in q.GET_PERFORMANCE_ANOMALIES
        assert "agent_name" in q.GET_PERFORMANCE_ANOMALIES
        assert "quality_score" in q.GET_PERFORMANCE_ANOMALIES
        assert "evaluated_at" in q.GET_PERFORMANCE_ANOMALIES

    def test_query_orders_by_score(self):
        from src.neural_link.graph import queries as q
        assert "ORDER BY" in q.GET_PERFORMANCE_ANOMALIES
        assert "quality_score ASC" in q.GET_PERFORMANCE_ANOMALIES


# ============================================================
# TestKillSwitchEvents
# ============================================================

class TestKillSwitchEvents:
    """Tests for Kill Switch event capture and Obsidian documentation."""

    def test_kill_switch_event_type_exists(self):
        """KILL_SWITCH_TRIGGERED is in EventType enum."""
        assert hasattr(EventType, "KILL_SWITCH_TRIGGERED")
        assert EventType.KILL_SWITCH_TRIGGERED.value == "kill_switch_triggered"

    def test_hub_captures_kill_switch(self):
        """TelemetryHub correctly captures kill switch events."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.KILL_SWITCH_TRIGGERED,
            "Emergency stop: agent devops_agent exceeded error threshold",
            data={"agent_id": "devops_agent", "reason": "error_threshold"},
        )
        hub.register(jc)
        events = hub.poll_all()

        assert len(events) == 1
        assert events[0].event_type == EventType.KILL_SWITCH_TRIGGERED
        assert "devops_agent" in events[0].message

    def test_kill_switch_in_event_log(self):
        """Kill switch events persist in hub event log."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.KILL_SWITCH_TRIGGERED, "kill test")
        hub.register(jc)
        hub.poll_all()

        log = hub.get_event_log()
        kill_events = [e for e in log if e.event_type == EventType.KILL_SWITCH_TRIGGERED]
        assert len(kill_events) == 1

    def test_kill_switch_subscriber_notified(self):
        """Subscribers receive kill switch events."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.KILL_SWITCH_TRIGGERED, "halt!")
        hub.register(jc)

        received = []
        hub.subscribe(lambda ev: received.append(ev))
        hub.poll_all()

        assert len(received) == 1
        assert received[0].event_type == EventType.KILL_SWITCH_TRIGGERED

    def test_kill_switch_documented_in_obsidian(self, vault_dir):
        """Kill switch events appear in External_Orchestration.md."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.KILL_SWITCH_TRIGGERED,
            "Emergency stop: testing_agent unresponsive",
            data={"agent_id": "testing_agent", "reason": "timeout"},
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Security Interruptions" in content
        assert "testing_agent unresponsive" in content
        assert "Total kill switch events" in content

    def test_no_kill_switch_shows_clean(self, vault_dir):
        """Without kill switch events, shows 'no events' message."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.LOG, "normal event")
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "No kill switch events recorded" in content

    def test_multiple_kill_switches_counted(self, vault_dir):
        """Multiple kill switch events are all documented with count."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.KILL_SWITCH_TRIGGERED, "kill 1")
        jc.push_event(EventType.KILL_SWITCH_TRIGGERED, "kill 2")
        jc.push_event(EventType.KILL_SWITCH_TRIGGERED, "kill 3")
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Total kill switch events**: 3" in content


# ============================================================
# TestSentinelAlerts
# ============================================================


class TestSentinelAlerts:
    """Tests for sentinel anomaly error log in External_Orchestration.md."""

    def test_no_sentinel_events_clean(self, vault_dir):
        """Without sentinel events, shows 'no events' message."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.LOG, "normal event")
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Sentinel Alerts" in content
        assert "No sentinel anomaly events recorded" in content

    def test_detection_failure_red_callout(self, vault_dir):
        """NOT_DETECTED anomaly renders Obsidian error callout."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.CRITICAL_ANOMALY,
            "Agent Reviewer scored 2.0/10 on task t99",
            data={
                "agent_name": "Reviewer",
                "task_id": "t99",
                "quality_score": 2.0,
                "detection_status": "NOT_DETECTED",
            },
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "> [!ERROR] Dashboard Detection Failure" in content
        assert "Reviewer" in content
        assert "t99" in content
        assert "2.0/10" in content
        assert "NOT DETECTED" in content
        assert "Total detection failures**: 1" in content

    def test_multiple_detection_failures_counted(self, vault_dir):
        """Multiple NOT_DETECTED failures are all listed with total count."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        for i, agent in enumerate(["Alpha", "Beta"]):
            jc.push_event(
                EventType.CRITICAL_ANOMALY,
                f"Agent {agent} scored low",
                data={
                    "agent_name": agent,
                    "task_id": f"t{i}",
                    "quality_score": 1.5,
                    "detection_status": "NOT_DETECTED",
                },
            )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Alpha" in content
        assert "Beta" in content
        assert "Total detection failures**: 2" in content

    def test_anomaly_without_not_detected_shows_clean(self, vault_dir):
        """CRITICAL_ANOMALY without NOT_DETECTED shows 'successful detection' summary."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.CRITICAL_ANOMALY,
            "Agent X scored 3.0/10",
            data={"agent_name": "X", "task_id": "t1", "quality_score": 3.0},
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Sentinel Alerts" in content
        assert "1 anomaly event(s) recorded" in content
        assert "successful detection" in content
        assert "[!ERROR]" not in content


# ============================================================
# TestVisualEvidence
# ============================================================


class TestVisualEvidence:
    """Tests for Visual Evidence section with screenshot paths."""

    def test_no_screenshots_fallback(self, vault_dir):
        """Without screenshot data, shows fallback message."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Visual Evidence" in content
        assert "No anchoring failure screenshots captured" in content

    def test_screenshot_path_rendered(self, vault_dir):
        """CRITICAL_ANOMALY with screenshot_path appears in Visual Evidence."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.CRITICAL_ANOMALY,
            "Anchoring failed",
            data={
                "agent_name": "SentinelEye",
                "task_id": "t42",
                "quality_score": 1.0,
                "screenshot_path": "C:/screenshots/anchor_fail_001.png",
                "detection_status": "NOT_DETECTED",
            },
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Visual Evidence" in content
        assert "C:/screenshots/anchor_fail_001.png" in content
        assert "SentinelEye" in content

    def test_multiple_screenshots_listed(self, vault_dir):
        """Multiple screenshot events produce multiple entries."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        for i in range(3):
            jc.push_event(
                EventType.CRITICAL_ANOMALY,
                f"Fail {i}",
                data={
                    "agent_name": f"Agent{i}",
                    "task_id": f"t{i}",
                    "screenshot_path": f"/tmp/fail_{i}.png",
                },
            )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "/tmp/fail_0.png" in content
        assert "/tmp/fail_1.png" in content
        assert "/tmp/fail_2.png" in content

    def test_anomaly_without_screenshot_excluded(self, vault_dir):
        """CRITICAL_ANOMALY without screenshot_path does not appear in Visual Evidence."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.CRITICAL_ANOMALY,
            "No screenshot",
            data={"agent_name": "X", "task_id": "t1", "quality_score": 2.0},
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Visual Evidence" in content
        assert "No anchoring failure screenshots captured" in content


# ============================================================
# TestGanttSentinelVisual
# ============================================================


class TestGanttSentinelVisual:
    """Tests for sentinel_visual phase in Gantt chart."""

    def test_critical_anomaly_creates_sentinel_visual_phase(self):
        """CRITICAL_ANOMALY events (no explicit phase) map to sentinel_visual."""
        events = [
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "Dashboard not detected",
                timestamp="2026-03-03T12:00:00",
                data={"agent_name": "Watcher", "task_id": "t1"},
            ),
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "Still not detected",
                timestamp="2026-03-03T12:00:45",
                data={"agent_name": "Watcher", "task_id": "t2"},
            ),
        ]
        lines = ObsidianBridge._build_mermaid_gantt(events)
        text = "\n".join(lines)
        assert "sentinel_visual" in text
        assert "Sentinel Visual" in text  # section title
        assert "2026-03-03T12:00:00" in text
        assert "2026-03-03T12:00:45" in text

    def test_sentinel_visual_alongside_regular_phases(self):
        """sentinel_visual coexists with regular phase events."""
        events = [
            TelemetryEvent(
                EventType.TASK_STARTED, "jitbit", "init",
                timestamp="2026-03-03T10:00:00",
                data={"phase": "initialization"},
            ),
            TelemetryEvent(
                EventType.TASK_COMPLETED, "jitbit", "init done",
                timestamp="2026-03-03T10:05:00",
                data={"phase": "initialization"},
            ),
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "low score",
                timestamp="2026-03-03T10:06:00",
                data={"agent_name": "X"},
            ),
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "still low",
                timestamp="2026-03-03T10:08:00",
                data={"agent_name": "X"},
            ),
        ]
        lines = ObsidianBridge._build_mermaid_gantt(events)
        text = "\n".join(lines)
        assert "initialization" in text
        assert "sentinel_visual" in text
        assert "```mermaid" in text

    def test_critical_anomaly_with_explicit_phase_uses_that_phase(self):
        """CRITICAL_ANOMALY with explicit phase uses the explicit phase, not sentinel_visual."""
        events = [
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "custom phase",
                timestamp="2026-03-03T10:00:00",
                data={"phase": "custom_check", "agent_name": "Y"},
            ),
        ]
        lines = ObsidianBridge._build_mermaid_gantt(events)
        text = "\n".join(lines)
        assert "custom_check" in text
        assert "sentinel_visual" not in text

    def test_gantt_sentinel_in_external_orchestration(self, vault_dir):
        """sentinel_visual phase appears in External_Orchestration.md Gantt."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.CRITICAL_ANOMALY,
            "Dashboard not found",
            data={"agent_name": "Sentinel", "task_id": "t1"},
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "sentinel_visual" in content
        assert "```mermaid" in content


# ============================================================
# TestRecoveryOperations
# ============================================================


class TestRecoveryOperations:
    """Tests for Recovery Operations table in External_Orchestration.md."""

    def test_no_recovery_events_fallback(self, vault_dir):
        """Without recovery events, shows fallback message."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Recovery Operations" in content
        assert "No recovery attempts recorded" in content

    def test_recovery_event_rendered_in_table(self, vault_dir):
        """RECOVERY_ATTEMPTED event appears as a table row."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.RECOVERY_ATTEMPTED,
            "Retried agent Reviewer on task t99",
            data={
                "agent_name": "Reviewer",
                "task_id": "t99",
                "success": True,
            },
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Recovery Operations" in content
        assert "Reviewer" in content
        assert "t99" in content
        assert "YES" in content
        assert "Total recovery attempts**: 1" in content

    def test_failed_recovery_shows_no(self, vault_dir):
        """Recovery with success=False shows NO."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(
            EventType.RECOVERY_ATTEMPTED,
            "Recovery failed for task t50",
            data={"agent_name": "Alpha", "task_id": "t50", "success": False},
        )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "| NO |" in content

    def test_multiple_recovery_events_counted(self, vault_dir):
        """Multiple recovery events produce correct total count."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        for i in range(3):
            jc.push_event(
                EventType.RECOVERY_ATTEMPTED,
                f"Recovery {i}",
                data={"agent_name": f"Agent{i}", "task_id": f"t{i}", "success": i % 2 == 0},
            )
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Total recovery attempts**: 3" in content


# ============================================================
# TestHealingEfficacy
# ============================================================


class TestHealingEfficacy:
    """Tests for Healing Efficacy metric section."""

    def test_no_anomalies_fallback(self):
        """No anomalies -> 'nothing to heal' message."""
        lines = ObsidianBridge._build_healing_efficacy([], [])
        text = "\n".join(lines)
        assert "Healing Efficacy" in text
        assert "nothing to heal" in text

    def test_anomalies_without_recovery_zero_rate(self):
        """Anomalies with no recovery -> 0% healing rate + warning."""
        anomalies = [
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "low score",
                data={"task_id": "t1"},
            ),
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "low score",
                data={"task_id": "t2"},
            ),
        ]
        lines = ObsidianBridge._build_healing_efficacy(anomalies, [])
        text = "\n".join(lines)
        assert "Healing rate**: 0.0%" in text
        assert "Anomalies detected**: 2" in text
        assert "[!WARNING]" in text

    def test_full_recovery_100_percent(self):
        """All anomalies recovered -> 100% rate + success callout."""
        anomalies = [
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "sentinel", "fail",
                data={"task_id": "t1"},
            ),
        ]
        recoveries = [
            TelemetryEvent(
                EventType.RECOVERY_ATTEMPTED, "emergency", "fixed",
                data={"task_id": "t1", "success": True},
            ),
        ]
        lines = ObsidianBridge._build_healing_efficacy(anomalies, recoveries)
        text = "\n".join(lines)
        assert "Healing rate**: 100.0%" in text
        assert "Successfully recovered**: 1" in text
        assert "[!SUCCESS]" in text

    def test_partial_recovery(self):
        """Some anomalies recovered -> correct percentage."""
        anomalies = [
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "a", data={"task_id": "t1"}),
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "b", data={"task_id": "t2"}),
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "c", data={"task_id": "t3"}),
        ]
        recoveries = [
            TelemetryEvent(EventType.RECOVERY_ATTEMPTED, "e", "ok", data={"task_id": "t1", "success": True}),
            TelemetryEvent(EventType.RECOVERY_ATTEMPTED, "e", "fail", data={"task_id": "t2", "success": False}),
        ]
        lines = ObsidianBridge._build_healing_efficacy(anomalies, recoveries)
        text = "\n".join(lines)
        # 1 healed out of 3 unique tasks = 33.3%
        assert "Healing rate**: 33.3%" in text
        assert "Unique tasks affected**: 3" in text
        assert "Successfully recovered**: 1" in text

    def test_recovery_without_matching_anomaly_ignored(self):
        """Recovery for a task_id not in anomalies doesn't inflate the rate."""
        anomalies = [
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "a", data={"task_id": "t1"}),
        ]
        recoveries = [
            TelemetryEvent(EventType.RECOVERY_ATTEMPTED, "e", "ok", data={"task_id": "t999", "success": True}),
        ]
        lines = ObsidianBridge._build_healing_efficacy(anomalies, recoveries)
        text = "\n".join(lines)
        assert "Healing rate**: 0.0%" in text

    def test_healing_efficacy_in_external_orchestration(self, vault_dir):
        """Healing Efficacy section appears in External_Orchestration.md."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.CRITICAL_ANOMALY, "fail", data={"task_id": "t1"})
        jc.push_event(EventType.RECOVERY_ATTEMPTED, "fixed", data={"task_id": "t1", "success": True})
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Healing Efficacy" in content
        assert "Healing rate" in content


# ============================================================
# TestFailureDistribution
# ============================================================


class TestFailureDistribution:
    """Tests for Failure Distribution Mermaid pie chart."""

    def test_no_failures_fallback(self):
        """No failures -> fallback message."""
        lines = ObsidianBridge._build_failure_distribution([], [])
        text = "\n".join(lines)
        assert "Failure Distribution" in text
        assert "No failures recorded" in text

    def test_only_score_anomalies(self):
        """Only score anomalies produce pie chart with single slice."""
        sentinel = [
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "low", data={"task_id": "t1"}),
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "low", data={"task_id": "t2"}),
        ]
        lines = ObsidianBridge._build_failure_distribution(sentinel, [])
        text = "\n".join(lines)
        assert "```mermaid" in text
        assert '"Score Anomaly" : 2' in text
        assert "Anchoring Error" not in text
        assert "Hardware Error" not in text
        assert "Total failures**: 2" in text

    def test_only_anchoring_errors(self):
        """Only NOT_DETECTED anomalies produce anchoring error slice."""
        sentinel = [
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "s", "fail",
                data={"task_id": "t1", "detection_status": "NOT_DETECTED"},
            ),
        ]
        lines = ObsidianBridge._build_failure_distribution(sentinel, [])
        text = "\n".join(lines)
        assert '"Anchoring Error" : 1' in text
        assert "Score Anomaly" not in text

    def test_only_hardware_errors(self):
        """Only kill switch events produce hardware error slice."""
        kills = [
            TelemetryEvent(EventType.KILL_SWITCH_TRIGGERED, "ks", "halt"),
            TelemetryEvent(EventType.KILL_SWITCH_TRIGGERED, "ks", "halt2"),
        ]
        lines = ObsidianBridge._build_failure_distribution([], kills)
        text = "\n".join(lines)
        assert '"Hardware Error" : 2' in text
        assert "Score Anomaly" not in text
        assert "Anchoring Error" not in text

    def test_mixed_failure_types(self):
        """All three failure types produce three slices."""
        sentinel = [
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "score", data={"task_id": "t1"}),
            TelemetryEvent(EventType.CRITICAL_ANOMALY, "s", "score", data={"task_id": "t2"}),
            TelemetryEvent(
                EventType.CRITICAL_ANOMALY, "s", "anchor",
                data={"task_id": "t3", "detection_status": "NOT_DETECTED"},
            ),
        ]
        kills = [
            TelemetryEvent(EventType.KILL_SWITCH_TRIGGERED, "ks", "halt"),
        ]
        lines = ObsidianBridge._build_failure_distribution(sentinel, kills)
        text = "\n".join(lines)
        assert '"Score Anomaly" : 2' in text
        assert '"Anchoring Error" : 1' in text
        assert '"Hardware Error" : 1' in text
        assert "Total failures**: 4" in text
        assert "pie title Failure Distribution" in text

    def test_failure_distribution_in_external_orchestration(self, vault_dir):
        """Failure Distribution section appears in External_Orchestration.md."""
        hub = TelemetryHub()
        jc = JitbitConnector()
        jc.push_event(EventType.CRITICAL_ANOMALY, "score fail", data={"task_id": "t1"})
        jc.push_event(EventType.KILL_SWITCH_TRIGGERED, "hardware halt")
        hub.register(jc)
        hub.poll_all()

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Failure Distribution" in content
        assert "pie title Failure Distribution" in content
        assert "Score Anomaly" in content
        assert "Hardware Error" in content


# ============================================================
# TestConnectedServices
# ============================================================


class TestConnectedServices:
    """Tests for Connected Services section in External_Orchestration.md."""

    def test_no_ifttt_shows_fallback(self, vault_dir):
        """Without IFTTT provider, shows 'no services' fallback."""
        hub = TelemetryHub()
        hub.register(JitbitConnector())
        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Connected Services" in content
        assert "No external messaging services configured" in content

    def test_ifttt_active_renders_table(self, vault_dir):
        """IFTTT provider with successful ping renders table."""
        hub = TelemetryHub()
        ifttt = IFTTTBridge(webhook_key="test_key", event_name="bunker_alert")
        # Simulate a successful ping
        ifttt._last_ping_ok = True
        ifttt._last_ping_ts = "2026-03-03T12:00:00"
        hub.register(ifttt)

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Connected Services" in content
        assert "| IFTTT Webhooks | active |" in content
        assert "2026-03-03T12:00:00" in content
        assert "bunker_alert" in content

    def test_ifttt_inactive_shows_inactive(self, vault_dir):
        """IFTTT provider after failed ping shows inactive."""
        hub = TelemetryHub()
        ifttt = IFTTTBridge(webhook_key="test_key", event_name="bunker_alert")
        ifttt._last_ping_ok = False
        hub.register(ifttt)

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.sync_external_orchestration()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "| IFTTT Webhooks | inactive |" in content

    def test_connected_services_in_full_sync(self, vault_dir):
        """full_sync includes Connected Services when IFTTT registered."""
        hub = TelemetryHub()
        ifttt = IFTTTBridge(webhook_key="test_key", event_name="bunker_alert")
        ifttt._last_ping_ok = True
        ifttt._last_ping_ts = "2026-03-03T14:00:00"
        hub.register(ifttt)

        bridge = ObsidianBridge(vault_path=vault_dir, telemetry_hub=hub)
        bridge.full_sync()
        content = (vault_dir / "Integrations" / "External_Orchestration.md").read_text(encoding="utf-8")
        assert "Connected Services" in content
        assert "IFTTT Webhooks" in content


# ============================================================
# TestSyncGuides
# ============================================================


class TestSyncGuides:
    """Tests for sync_guides() vault guide generation."""

    def test_guide_file_created(self, vault_dir):
        """IFTTT_Telegram_Setup.md is created in vault/Guides/."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        written = bridge.sync_guides()
        assert "IFTTT_Telegram_Setup.md" in written
        assert (vault_dir / "Guides" / "IFTTT_Telegram_Setup.md").exists()

    def test_guide_contains_setup_steps(self, vault_dir):
        """Guide contains step-by-step instructions."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_guides()
        content = (vault_dir / "Guides" / "IFTTT_Telegram_Setup.md").read_text(encoding="utf-8")
        assert "Step 1" in content
        assert "Step 2" in content
        assert "Step 3" in content
        assert "Step 4" in content
        assert "Step 5" in content
        assert "Step 6" in content
        assert "IFTTT_WEBHOOK_KEY" in content

    def test_guide_contains_telegram_template(self, vault_dir):
        """Guide includes the Telegram message template."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_guides()
        content = (vault_dir / "Guides" / "IFTTT_Telegram_Setup.md").read_text(encoding="utf-8")
        assert "ALERTA DO BUNKER" in content
        assert "{{Value1}}" in content
        assert "{{Value2}}" in content
        assert "{{Value3}}" in content

    def test_guide_has_frontmatter(self, vault_dir):
        """Guide has valid YAML frontmatter with tags."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        bridge.sync_guides()
        content = (vault_dir / "Guides" / "IFTTT_Telegram_Setup.md").read_text(encoding="utf-8")
        assert content.startswith("---\n")
        fm_block = content.split("---\n")[1]
        fm = yaml.safe_load(fm_block)
        assert "guide" in fm["tags"]
        assert "ifttt" in fm["tags"]
        assert "telegram" in fm["tags"]

    def test_full_sync_includes_guides(self, vault_dir):
        """full_sync now includes guides in results."""
        bridge = ObsidianBridge(vault_path=vault_dir)
        results = bridge.full_sync()
        assert "guides" in results
        assert "IFTTT_Telegram_Setup.md" in results["guides"]
