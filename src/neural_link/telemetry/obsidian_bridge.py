"""
ObsidianBridge - Syncs Neural Link state into an Obsidian-compatible vault.

Reads AGENT_REGISTRY + optional Neo4j data and writes Markdown files
with YAML frontmatter and WikiLinks for Obsidian Dataview.

Features:
  --watch   Persistent monitor: polls src/ mtimes + Neo4j for changes
  Env validation: warns on missing creds / bad vault path (never crashes)
  Dataview boilerplate: full query set ready for Obsidian plugin
  Mermaid charts: token wastage pie chart in Wastage_Report.md
"""

import argparse
import logging
import os
import tempfile
import shutil
import time
from datetime import date
from pathlib import Path
from typing import Any

import yaml

from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY
from src.neural_link.graph import queries

logger = logging.getLogger(__name__)

# Rough token estimate: ~1.3 tokens per word, ~5 words per line of output
TOKENS_PER_TASK_ESTIMATE = 150


# ==================================================================
# Environment Validation
# ==================================================================

class EnvironmentStatus:
    """Result of environment validation."""

    def __init__(self):
        self.warnings: list[str] = []
        self.neo4j_configured = False
        self.vault_writable = False

    @property
    def ok(self) -> bool:
        return len(self.warnings) == 0


def validate_environment(vault_path: Path, check_neo4j_connection: bool = False,
                         graph_manager=None) -> EnvironmentStatus:
    """
    Validate that Neo4j creds and vault path are sane.
    Warns but never raises. Returns EnvironmentStatus.
    """
    status = EnvironmentStatus()

    # --- Neo4j credentials ---
    neo4j_uri = os.getenv("NEO4J_URI", "")
    neo4j_user = os.getenv("NEO4J_USER", "")
    neo4j_password = os.getenv("NEO4J_PASSWORD", "")

    if not neo4j_uri:
        status.warnings.append("NEO4J_URI not set; bridge will use static registry only")
    elif neo4j_uri == "bolt://localhost:7687" and not neo4j_password:
        status.warnings.append("NEO4J_URI is default localhost and NEO4J_PASSWORD is empty")

    if neo4j_uri and neo4j_user:
        status.neo4j_configured = True

    if check_neo4j_connection and graph_manager:
        try:
            if not graph_manager.verify_connectivity():
                status.warnings.append("Neo4j configured but connectivity check failed")
        except Exception as e:
            status.warnings.append(f"Neo4j connectivity test error: {e}")

    # --- Vault path ---
    vault = Path(vault_path)
    try:
        vault.mkdir(parents=True, exist_ok=True)
        test_file = vault / ".bridge_write_test"
        test_file.write_text("ok", encoding="utf-8")
        test_file.unlink()
        status.vault_writable = True
    except OSError as e:
        status.warnings.append(f"Vault path not writable ({vault}): {e}")

    # --- Log all warnings ---
    for w in status.warnings:
        logger.warning("[env-check] %s", w)

    if not status.warnings:
        logger.info("[env-check] Environment OK (neo4j_configured=%s, vault=%s)",
                     status.neo4j_configured, vault)

    return status


# ==================================================================
# File Watcher (zero-dependency polling)
# ==================================================================

class SourceWatcher:
    """Polls src/ directory mtimes and Neo4j task count to detect changes."""

    def __init__(self, src_path: Path, graph_manager=None):
        self._src = Path(src_path)
        self._graph = graph_manager
        self._last_mtime = self._scan_max_mtime()
        self._last_task_count = self._poll_task_count()

    def has_changes(self) -> bool:
        """Return True if src/ files changed or Neo4j has new tasks."""
        changed = False

        new_mtime = self._scan_max_mtime()
        if new_mtime > self._last_mtime:
            logger.info("[watch] src/ change detected (mtime %s -> %s)", self._last_mtime, new_mtime)
            self._last_mtime = new_mtime
            changed = True

        new_count = self._poll_task_count()
        if new_count != self._last_task_count:
            logger.info("[watch] Neo4j task count changed (%s -> %s)", self._last_task_count, new_count)
            self._last_task_count = new_count
            changed = True

        return changed

    def _scan_max_mtime(self) -> float:
        """Walk src/ and return the most recent mtime."""
        max_mt = 0.0
        if not self._src.exists():
            return max_mt
        try:
            for p in self._src.rglob("*.py"):
                try:
                    mt = p.stat().st_mtime
                    if mt > max_mt:
                        max_mt = mt
                except OSError:
                    continue
        except OSError:
            pass
        return max_mt

    def _poll_task_count(self) -> int:
        """Query Neo4j for total task count. Returns -1 if unavailable."""
        if not self._graph:
            return -1
        try:
            rows = self._graph.execute_read(
                "MATCH (t:Task) RETURN count(t) AS cnt"
            )
            return rows[0]["cnt"] if rows else 0
        except Exception:
            return -1


# ==================================================================
# ObsidianBridge
# ==================================================================

class ObsidianBridge:
    """Generates and maintains an Obsidian vault from Neural Link data."""

    def __init__(self, vault_path: Path, graph_manager=None, telemetry_hub=None):
        self.vault_path = Path(vault_path)
        self._graph = graph_manager
        self._hub = telemetry_hub

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def sync_agents(self) -> list[str]:
        """Write one .md per agent to vault/Agents/. Returns list of written filenames."""
        agents_dir = self.vault_path / "Agents"
        agents_dir.mkdir(parents=True, exist_ok=True)

        neo4j_perf = self._fetch_agent_performance()

        written = []
        for agent_id, info in AGENT_REGISTRY.items():
            perf = neo4j_perf.get(agent_id, {})
            capabilities = sorted(info["capabilities"])

            frontmatter = {
                "agent_id": agent_id,
                "name": info["name"],
                "type": info["type"],
                "status": perf.get("status", "active"),
                "success_rate": perf.get("success_rate", "N/A"),
                "capabilities": capabilities,
                "tags": ["agent", info["type"]],
                "last_updated": str(date.today()),
            }

            body_lines = [
                f"# {info['name']}",
                "",
                f"**Module**: `{info['module_path']}`",
                f"**Invoke**: `{info['invoke']}`",
                "",
                "## Capabilities",
                "",
            ]
            for cap in capabilities:
                body_lines.append(f"- {cap}")

            body_lines += [
                "",
                "## Related Specs",
                "",
                "- [[AgentSelector]]",
                "- [[TaskExecutor]]",
                "- [[TaskEvaluator]]",
            ]

            content = self._format_note(frontmatter, "\n".join(body_lines))
            path = agents_dir / f"{agent_id}.md"
            self._safe_write_md(path, content)
            written.append(f"{agent_id}.md")

        logger.info("sync_agents: wrote %d agent notes", len(written))
        return written

    def sync_missions(self, mission_result: dict) -> str:
        """Write a mission note from a mission run result dict. Returns filename."""
        missions_dir = self.vault_path / "Missions"
        missions_dir.mkdir(parents=True, exist_ok=True)

        mission_name = mission_result.get("mission_name", "unnamed_mission")
        mission_id = mission_result.get("mission_id", mission_name)
        status = "passed" if mission_result.get("mission_passed") else "failed"
        agents_used = mission_result.get("agents_used", [])

        scores: dict[str, Any] = {}
        for key, val in mission_result.items():
            if key.startswith("eval") and hasattr(val, "quality_score"):
                scores[key] = val.quality_score

        frontmatter = {
            "mission_id": mission_id,
            "mission_name": mission_name,
            "status": status,
            "agents_used": agents_used,
            "scores": scores if scores else "N/A",
            "timestamp": str(date.today()),
            "tags": ["mission", status],
        }

        body_lines = [
            f"# {mission_name}",
            "",
            f"**Status**: {status}",
            "",
            "## Agents",
            "",
        ]
        for agent_id in agents_used:
            body_lines.append(f"- [[{agent_id}]]")

        if scores:
            body_lines += ["", "## Scores", ""]
            for key, score in scores.items():
                body_lines.append(f"- **{key}**: {score}")

        content = self._format_note(frontmatter, "\n".join(body_lines))
        filename = f"{mission_name}.md"
        self._safe_write_md(missions_dir / filename, content)
        logger.info("sync_missions: wrote %s", filename)
        return filename

    def sync_dashboard(self) -> str:
        """Write vault/Dashboard.md with Dataview queries. Returns filename."""
        graph_stats = self._fetch_graph_stats()

        body_lines = [
            "# Neural Link Dashboard",
            "",
            "## Agent Performance",
            "",
            "```dataview",
            'TABLE success_rate AS "Success Rate", type AS "Type", status AS "Status"',
            'FROM "Agents"',
            "SORT success_rate DESC",
            "```",
            "",
            "## Agents by Type",
            "",
            "```dataview",
            'TABLE length(rows) AS "Count"',
            'FROM "Agents"',
            "GROUP BY type",
            "```",
            "",
            "## Active Agents",
            "",
            "```dataview",
            'LIST',
            'FROM "Agents"',
            'WHERE status = "active"',
            "SORT agent_id ASC",
            "```",
            "",
            "## Mission Results",
            "",
            "```dataview",
            'TABLE status AS "Status", scores AS "Scores", agents_used AS "Agents"',
            'FROM "Missions"',
            "SORT timestamp DESC",
            "```",
            "",
            "## Recent Missions (last 10)",
            "",
            "```dataview",
            'TABLE status AS "Result", timestamp AS "Date"',
            'FROM "Missions"',
            "SORT timestamp DESC",
            "LIMIT 10",
            "```",
            "",
            "## Capability Coverage",
            "",
            "```dataview",
            'TABLE capabilities AS "Capabilities", success_rate AS "Rate"',
            'FROM "Agents"',
            'WHERE success_rate != "N/A"',
            "SORT success_rate DESC",
            "```",
            "",
            "## Wastage Overview",
            "",
            "```dataview",
            'TABLE',
            'FROM "Telemetry"',
            "```",
            "",
            "## Graph Stats",
            "",
        ]

        if graph_stats:
            body_lines.append("| Label | Count |")
            body_lines.append("|-------|-------|")
            for row in graph_stats:
                body_lines.append(f"| {row.get('label', '?')} | {row.get('count', 0)} |")
        else:
            body_lines.append("_No Neo4j connection -- stats unavailable._")

        body_lines += [
            "",
            "## Quick Links",
            "",
            "- [[AgentSelector]]",
            "- [[TaskExecutor]]",
            "- [[TaskEvaluator]]",
        ]

        content = "\n".join(body_lines) + "\n"
        path = self.vault_path / "Dashboard.md"
        self._safe_write_md(path, content)
        logger.info("sync_dashboard: wrote Dashboard.md")
        return "Dashboard.md"

    def sync_wastage(self) -> str:
        """Write vault/Telemetry/Wastage_Report.md with per-agent telemetry + mermaid chart."""
        telemetry_dir = self.vault_path / "Telemetry"
        telemetry_dir.mkdir(parents=True, exist_ok=True)

        task_agent_rows = self._fetch_tasks_with_agents()

        body_lines = [
            "# Wastage Report",
            "",
            f"_Generated: {date.today()}_",
            "",
        ]

        agent_token_map: dict[str, int] = {}

        if task_agent_rows:
            # Group by agent
            agent_tasks: dict[str, list[dict]] = {}
            for row in task_agent_rows:
                aid = row.get("agent_id", "unknown")
                agent_tasks.setdefault(aid, []).append(row)

            for agent_id, tasks in sorted(agent_tasks.items()):
                body_lines.append(f"## [[{agent_id}]]")
                body_lines.append("")
                body_lines.append(f"- **Tasks assigned**: {len(tasks)}")

                scores = [t["quality_score"] for t in tasks if t.get("quality_score") is not None]
                if scores:
                    avg_score = sum(scores) / len(scores)
                    body_lines.append(f"- **Avg quality score**: {avg_score:.2f}")

                refinements = [t for t in tasks if t.get("feedback")]
                body_lines.append(f"- **Refinement count**: {len(refinements)}")

                statuses = [t.get("status", "unknown") for t in tasks]
                completed = statuses.count("completed")
                body_lines.append(f"- **Completed**: {completed}/{len(tasks)}")

                # Token estimate: base per task + extra per refinement
                token_est = len(tasks) * TOKENS_PER_TASK_ESTIMATE + len(refinements) * 80
                agent_token_map[agent_id] = token_est
                body_lines.append(f"- **Est. tokens consumed**: {token_est}")
                body_lines.append("")

            # Mermaid pie chart
            body_lines += self._build_mermaid_chart(agent_token_map)
        else:
            body_lines.append("_No task-agent data available (Neo4j offline or no tasks)._")
            body_lines.append("")

        content = "\n".join(body_lines)
        path = telemetry_dir / "Wastage_Report.md"
        self._safe_write_md(path, content)
        logger.info("sync_wastage: wrote Wastage_Report.md")
        return "Wastage_Report.md"

    def sync_external_orchestration(self) -> str:
        """
        Write vault/Integrations/External_Orchestration.md with
        real-time execution logs from registered telemetry providers.
        Returns filename.
        """
        integrations_dir = self.vault_path / "Integrations"
        integrations_dir.mkdir(parents=True, exist_ok=True)

        body_lines = [
            "# External Orchestration",
            "",
            f"_Last sync: {date.today()}_",
            "",
        ]

        # --- Provider health status ---
        hub_events: list = []
        provider_health: dict[str, bool] = {}

        if self._hub:
            provider_health = self._hub.health()
            hub_events = self._hub.get_event_log()

        if provider_health:
            body_lines += ["## Connected Providers", ""]
            body_lines.append("| Provider | Status |")
            body_lines.append("|----------|--------|")
            for pid, ok in sorted(provider_health.items()):
                status_str = "online" if ok else "offline"
                body_lines.append(f"| [[{pid}]] | {status_str} |")
            body_lines.append("")
        else:
            body_lines += [
                "## Connected Providers",
                "",
                "_No telemetry providers registered._",
                "",
            ]

        # --- Connected Services (IFTTT etc.) ---
        body_lines += self._build_connected_services()

        # --- Neo4j external sync records ---
        neo4j_syncs = self._fetch_external_syncs()

        if neo4j_syncs:
            body_lines += ["## Sync History (Neo4j)", ""]
            body_lines.append("| Source | Event | Phase | Message | Timestamp |")
            body_lines.append("|--------|-------|-------|---------|-----------|")
            for row in neo4j_syncs[:25]:
                body_lines.append(
                    f"| {row.get('source', '?')} "
                    f"| {row.get('event_type', '?')} "
                    f"| {row.get('phase', '?')} "
                    f"| {row.get('message', '')[:60]} "
                    f"| {row.get('created_at', '?')} |"
                )
            body_lines.append("")

        # --- Live event log from hub ---
        if hub_events:
            body_lines += ["## Live Event Log", ""]
            for ev in hub_events[-30:]:
                ts = ev.timestamp if hasattr(ev, "timestamp") else "?"
                src = ev.source if hasattr(ev, "source") else "?"
                etype = ev.event_type
                if hasattr(etype, "value"):
                    etype = etype.value
                msg = ev.message if hasattr(ev, "message") else ""
                body_lines.append(f"- `{ts}` **[{src}]** {etype}: {msg}")
            body_lines.append("")
        else:
            body_lines += [
                "## Live Event Log",
                "",
                "_No events captured yet. Run `--watch` or trigger a mission._",
                "",
            ]

        # --- Phase 6 readiness ---
        body_lines += [
            "## Phase 6: Macro Synchronization",
            "",
        ]

        phase6_ready = self._check_phase6_readiness()
        if phase6_ready["schema_ok"]:
            body_lines.append("Schema: ExternalSync constraint + index **ready**")
        else:
            body_lines.append("Schema: ExternalSync constraint **not yet applied** (run migrations)")

        body_lines.append(f"- ExternalSync nodes: {phase6_ready['sync_count']}")
        body_lines.append(f"- Neo4j reachable: {'yes' if phase6_ready['neo4j_ok'] else 'no'}")
        body_lines.append("")

        # --- Mermaid Gantt chart for mission phase timing ---
        body_lines += self._build_mermaid_gantt(hub_events)

        # --- Sentinel anomaly alerts ---
        sentinel_events = self._get_sentinel_events(hub_events)
        detection_failures = [
            ev for ev in sentinel_events
            if hasattr(ev, "data") and isinstance(ev.data, dict)
            and ev.data.get("detection_status") == "NOT_DETECTED"
        ]

        if detection_failures:
            body_lines += ["## Sentinel Alerts", ""]
            body_lines.append("> [!ERROR] Dashboard Detection Failure")
            body_lines.append("> ")
            for ev in detection_failures:
                agent = ev.data.get("agent_name", "unknown")
                task_id = ev.data.get("task_id", "?")
                score = ev.data.get("quality_score", "?")
                ts = ev.timestamp if hasattr(ev, "timestamp") else "?"
                body_lines.append(
                    f"> **{ts}** -- Agent `{agent}` scored **{score}/10** "
                    f"on task `{task_id}` (Dashboard NOT DETECTED)"
                )
            body_lines += [
                ">",
                f"> **Total detection failures**: {len(detection_failures)}",
                "",
            ]
        elif sentinel_events:
            body_lines += [
                "## Sentinel Alerts",
                "",
                f"_{len(sentinel_events)} anomaly event(s) recorded -- all with successful detection._",
                "",
            ]
        else:
            body_lines += [
                "## Sentinel Alerts",
                "",
                "_No sentinel anomaly events recorded._",
                "",
            ]

        # --- Visual Evidence (screenshot from anchoring failures) ---
        screenshot_entries = self._get_visual_evidence(hub_events)
        if screenshot_entries:
            body_lines += ["## Visual Evidence", ""]
            for entry in screenshot_entries:
                ts = entry["timestamp"]
                path = entry["screenshot_path"]
                agent = entry.get("agent_name", "unknown")
                body_lines.append(f"- **{ts}** -- Agent `{agent}`: `{path}`")
            body_lines.append("")
        else:
            body_lines += [
                "## Visual Evidence",
                "",
                "_No anchoring failure screenshots captured._",
                "",
            ]

        # --- Kill Switch events ---
        kill_events = self._get_kill_switch_events(hub_events)
        if kill_events:
            body_lines += ["## Security Interruptions", ""]
            body_lines.append("| Timestamp | Source | Message | Data |")
            body_lines.append("|-----------|--------|---------|------|")
            for ev in kill_events:
                ts = ev.timestamp if hasattr(ev, "timestamp") else "?"
                src = ev.source if hasattr(ev, "source") else "?"
                msg = ev.message if hasattr(ev, "message") else ""
                data_str = str(ev.data) if hasattr(ev, "data") else ""
                body_lines.append(f"| {ts} | {src} | {msg} | {data_str} |")
            body_lines.append("")
            body_lines.append(f"**Total kill switch events**: {len(kill_events)}")
            body_lines.append("")
        else:
            body_lines += [
                "## Security Interruptions",
                "",
                "_No kill switch events recorded._",
                "",
            ]

        # --- Recovery Operations ---
        recovery_events = self._get_recovery_events(hub_events)
        if recovery_events:
            body_lines += ["## Recovery Operations", ""]
            body_lines.append("| Timestamp | Agent | Task | Success | Message |")
            body_lines.append("|-----------|-------|------|---------|---------|")
            for ev in recovery_events:
                ts = ev.timestamp if hasattr(ev, "timestamp") else "?"
                agent = ev.data.get("agent_name", "?") if hasattr(ev, "data") and isinstance(ev.data, dict) else "?"
                task_id = ev.data.get("task_id", "?") if hasattr(ev, "data") and isinstance(ev.data, dict) else "?"
                success = ev.data.get("success", False) if hasattr(ev, "data") and isinstance(ev.data, dict) else False
                msg = ev.message if hasattr(ev, "message") else ""
                success_str = "YES" if success else "NO"
                body_lines.append(f"| {ts} | {agent} | {task_id} | {success_str} | {msg[:60]} |")
            body_lines.append("")
            body_lines.append(f"**Total recovery attempts**: {len(recovery_events)}")
            body_lines.append("")
        else:
            body_lines += [
                "## Recovery Operations",
                "",
                "_No recovery attempts recorded._",
                "",
            ]

        # --- Healing Efficacy ---
        body_lines += self._build_healing_efficacy(sentinel_events, recovery_events)

        # --- Failure Distribution pie chart ---
        body_lines += self._build_failure_distribution(
            sentinel_events, kill_events
        )

        # --- Links ---
        body_lines += [
            "## Related",
            "",
            "- [[Dashboard]]",
            "- [[AgentSelector]]",
            "- [[TaskExecutor]]",
        ]

        content = "\n".join(body_lines) + "\n"
        path = integrations_dir / "External_Orchestration.md"
        self._safe_write_md(path, content)
        logger.info("sync_external_orchestration: wrote External_Orchestration.md")
        return "External_Orchestration.md"

    def sync_guides(self) -> list[str]:
        """Generate setup guides in vault/Guides/. Returns list of written filenames."""
        guides_dir = self.vault_path / "Guides"
        guides_dir.mkdir(parents=True, exist_ok=True)

        written = []

        # --- IFTTT Telegram Setup Guide ---
        frontmatter = {
            "tags": ["guide", "ifttt", "telegram"],
            "last_updated": str(date.today()),
        }

        body_lines = [
            "# IFTTT Telegram Setup",
            "",
            "Connect your Neural Link bunker to Telegram via IFTTT Maker Webhooks.",
            "",
            "## Step 1: Create IFTTT Account",
            "",
            "Go to [ifttt.com](https://ifttt.com) and create an account or log in.",
            "",
            "## Step 2: Get Your Webhook Key",
            "",
            "1. Go to [Webhooks service](https://ifttt.com/maker_webhooks)",
            "2. Click **Documentation**",
            "3. Copy your webhook key from the top of the page",
            "",
            "## Step 3: Set Environment Variable",
            "",
            "Add to your `.env` file:",
            "",
            "```",
            "IFTTT_WEBHOOK_KEY=your_key_here",
            "```",
            "",
            "## Step 4: Create the Applet (IF)",
            "",
            '1. Go to [Create Applet](https://ifttt.com/create)',
            '2. Click **If This** -> search **Webhooks** -> **Receive a web request**',
            '3. Event name: `bunker_alert`',
            "",
            "## Step 5: Configure Telegram (THEN)",
            "",
            '1. Click **Then That** -> search **Telegram** -> **Send message**',
            "2. Set the message template:",
            "",
            "```",
            "ALERTA DO BUNKER:",
            "Agente: {{Value1}}",
            "Status: {{Value2}}",
            "Acao: {{Value3}}",
            "```",
            "",
            "3. Click **Create action** and **Finish**",
            "",
            "## Step 6: Test",
            "",
            "Run from your terminal:",
            "",
            "```bash",
            'curl -X POST https://maker.ifttt.com/trigger/bunker_alert/with/key/YOUR_KEY \\',
            '  -H "Content-Type: application/json" \\',
            '  -d \'{"value1": "TestAgent", "value2": "OK", "value3": "Manual test"}\'',
            "```",
            "",
            "## Related",
            "",
            "- [[External_Orchestration]]",
            "- [[Dashboard]]",
        ]

        content = self._format_note(frontmatter, "\n".join(body_lines))
        path = guides_dir / "IFTTT_Telegram_Setup.md"
        self._safe_write_md(path, content)
        written.append("IFTTT_Telegram_Setup.md")

        logger.info("sync_guides: wrote %d guide(s)", len(written))
        return written

    def full_sync(self, mission_result: dict | None = None) -> dict[str, Any]:
        """Run all syncs in order. Returns summary dict."""
        results: dict[str, Any] = {}
        results["agents"] = self.sync_agents()
        results["dashboard"] = self.sync_dashboard()
        results["wastage"] = self.sync_wastage()
        results["external"] = self.sync_external_orchestration()
        results["guides"] = self.sync_guides()
        if mission_result:
            results["mission"] = self.sync_missions(mission_result)
        logger.info("full_sync complete: %s", {k: len(v) if isinstance(v, list) else v for k, v in results.items()})
        return results

    def watch(self, src_path: Path, interval: float = 30.0,
              _max_cycles: int = 0) -> None:
        """
        Persistent monitor: poll src/ and Neo4j, re-sync on changes.

        Args:
            src_path: Directory to watch for .py file changes.
            interval: Seconds between polls (default 30).
            _max_cycles: If > 0, stop after N cycles (for testing).
        """
        watcher = SourceWatcher(src_path, graph_manager=self._graph)
        logger.info("[watch] Monitoring %s (interval=%ss)", src_path, interval)
        print(f"[obsidian_bridge] Watching {src_path} (poll every {interval}s) -- Ctrl+C to stop")

        cycle = 0
        try:
            while True:
                cycle += 1
                if watcher.has_changes():
                    print(f"[obsidian_bridge] Change detected, syncing...")
                    self.full_sync()
                    print(f"[obsidian_bridge] Sync complete (cycle {cycle})")

                if _max_cycles and cycle >= _max_cycles:
                    break
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[obsidian_bridge] Watch stopped.")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _build_connected_services(self) -> list[str]:
        """Build Connected Services section from IFTTT (or other) providers."""
        ifttt_status = self._get_ifttt_status()

        if not ifttt_status:
            return [
                "## Connected Services",
                "",
                "_No external messaging services configured._",
                "",
            ]

        lines = [
            "## Connected Services",
            "",
            "| Service | Status | Last Ping | Event |",
            "|---------|--------|-----------|-------|",
        ]

        status_str = "active" if ifttt_status["active"] else "inactive"
        last_ping = ifttt_status["last_ping"] or "never"
        event_name = ifttt_status["event_name"]
        lines.append(f"| IFTTT Webhooks | {status_str} | {last_ping} | {event_name} |")
        lines.append("")
        return lines

    def _get_ifttt_status(self) -> dict | None:
        """Extract ping status from IFTTT provider if registered in hub."""
        if not self._hub:
            return None

        with self._hub._lock:
            providers = list(self._hub._providers.values())

        for provider in providers:
            if provider.provider_id == "ifttt" and hasattr(provider, "ping_status"):
                try:
                    return provider.ping_status()
                except Exception as e:
                    logger.warning("Failed to get IFTTT ping status: %s", e)
                    return None
        return None

    def _fetch_agent_performance(self) -> dict[str, dict]:
        """Query Neo4j for agent performance. Returns {agent_id: {field: value}}."""
        if not self._graph:
            return {}
        try:
            rows = self._graph.execute_read(queries.GET_AGENT_PERFORMANCE)
            return {
                row["id"]: {
                    "success_rate": row.get("success_rate"),
                    "status": row.get("status", "active"),
                }
                for row in rows
                if row.get("id")
            }
        except Exception as e:
            logger.warning("Failed to fetch agent performance: %s", e)
            return {}

    def _fetch_graph_stats(self) -> list[dict]:
        """Query Neo4j for graph stats."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(queries.GET_GRAPH_STATS)
        except Exception as e:
            logger.warning("Failed to fetch graph stats: %s", e)
            return []

    def _fetch_tasks_with_agents(self) -> list[dict]:
        """Query Neo4j for tasks joined with their assigned agents."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(queries.GET_TASKS_WITH_AGENTS, {"limit": 100})
        except Exception as e:
            logger.warning("Failed to fetch tasks with agents: %s", e)
            return []

    def _fetch_external_syncs(self) -> list[dict]:
        """Query Neo4j for ExternalSync records."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(
                queries.GET_EXTERNAL_SYNCS, {"source": "jitbit", "limit": 50}
            )
        except Exception as e:
            logger.warning("Failed to fetch external syncs: %s", e)
            return []

    def _check_phase6_readiness(self) -> dict:
        """Check if Neo4j schema and data are ready for Phase 6."""
        result = {"schema_ok": False, "sync_count": 0, "neo4j_ok": False}
        if not self._graph:
            return result
        try:
            if self._graph.verify_connectivity():
                result["neo4j_ok"] = True
            stats = self._graph.execute_read(queries.GET_EXTERNAL_SYNC_STATS)
            result["sync_count"] = sum(r.get("count", 0) for r in stats)
            # If we can query ExternalSync without error, schema exists
            result["schema_ok"] = True
        except Exception as e:
            logger.warning("Phase 6 readiness check: %s", e)
        return result

    @staticmethod
    def _build_mermaid_gantt(hub_events: list) -> list[str]:
        """Build a Mermaid Gantt chart from hub events showing mission phase timing."""
        from src.neural_link.telemetry.provider import EventType as ET

        if not hub_events:
            return [
                "## Mission Phase Timeline",
                "",
                "_No events available for Gantt chart._",
                "",
            ]

        # Group events by phase (from event.data["phase"])
        phase_times: dict[str, dict[str, str]] = {}  # phase -> {start, end}
        for ev in hub_events:
            phase = None
            if hasattr(ev, "data") and isinstance(ev.data, dict):
                phase = ev.data.get("phase")

            # Auto-derive sentinel_visual phase from CRITICAL_ANOMALY events
            if not phase:
                etype = ev.event_type if hasattr(ev, "event_type") else None
                if etype == ET.CRITICAL_ANOMALY:
                    phase = "sentinel_visual"

            if not phase:
                continue

            ts = ev.timestamp if hasattr(ev, "timestamp") else ""
            if not ts:
                continue

            if phase not in phase_times:
                phase_times[phase] = {"start": ts, "end": ts}
            else:
                if ts < phase_times[phase]["start"]:
                    phase_times[phase]["start"] = ts
                if ts > phase_times[phase]["end"]:
                    phase_times[phase]["end"] = ts

        if not phase_times:
            return [
                "## Mission Phase Timeline",
                "",
                "_No phase data in events for Gantt chart._",
                "",
            ]

        lines = [
            "## Mission Phase Timeline",
            "",
            "```mermaid",
            "gantt",
            "    title Mission Zero - Phase Execution",
            "    dateFormat YYYY-MM-DDTHH:mm:ss",
            "    axisFormat %H:%M",
        ]

        for i, (phase, times) in enumerate(sorted(phase_times.items())):
            section_name = phase.replace("_", " ").title()
            task_id = f"phase_{i}"
            lines.append(f"    section {section_name}")
            lines.append(f"    {phase} :{task_id}, {times['start']}, {times['end']}")

        lines.append("```")
        lines.append("")
        return lines

    @staticmethod
    def _get_sentinel_events(hub_events: list) -> list:
        """Filter hub events for CRITICAL_ANOMALY events from sentinel."""
        from src.neural_link.telemetry.provider import EventType as ET
        result = []
        for ev in hub_events:
            etype = ev.event_type if hasattr(ev, "event_type") else None
            if etype == ET.CRITICAL_ANOMALY:
                result.append(ev)
            elif hasattr(etype, "value") and etype.value == "critical_anomaly":
                result.append(ev)
        return result

    @staticmethod
    def _get_visual_evidence(hub_events: list) -> list[dict]:
        """Extract screenshot paths from anchoring failure events."""
        from src.neural_link.telemetry.provider import EventType as ET
        entries: list[dict] = []
        for ev in hub_events:
            etype = ev.event_type if hasattr(ev, "event_type") else None
            if etype != ET.CRITICAL_ANOMALY:
                if not (hasattr(etype, "value") and etype.value == "critical_anomaly"):
                    continue
            if not (hasattr(ev, "data") and isinstance(ev.data, dict)):
                continue
            spath = ev.data.get("screenshot_path", "")
            if not spath:
                continue
            entries.append({
                "timestamp": ev.timestamp if hasattr(ev, "timestamp") else "?",
                "screenshot_path": spath,
                "agent_name": ev.data.get("agent_name", "unknown"),
            })
        return entries

    @staticmethod
    def _get_kill_switch_events(hub_events: list) -> list:
        """Filter hub events for kill switch triggered events."""
        from src.neural_link.telemetry.provider import EventType as ET
        result = []
        for ev in hub_events:
            etype = ev.event_type if hasattr(ev, "event_type") else None
            if etype == ET.KILL_SWITCH_TRIGGERED:
                result.append(ev)
            elif hasattr(etype, "value") and etype.value == "kill_switch_triggered":
                result.append(ev)
        return result

    @staticmethod
    def _get_recovery_events(hub_events: list) -> list:
        """Filter hub events for RECOVERY_ATTEMPTED events."""
        from src.neural_link.telemetry.provider import EventType as ET
        result = []
        for ev in hub_events:
            etype = ev.event_type if hasattr(ev, "event_type") else None
            if etype == ET.RECOVERY_ATTEMPTED:
                result.append(ev)
            elif hasattr(etype, "value") and etype.value == "recovery_attempted":
                result.append(ev)
        return result

    @staticmethod
    def _build_healing_efficacy(
        sentinel_events: list, recovery_events: list
    ) -> list[str]:
        """
        Build a Healing Efficacy metric section.

        Counts how many CRITICAL_ANOMALY task_ids were followed by a
        successful RECOVERY_ATTEMPTED (data.success=True) for the same task_id.
        """
        total_anomalies = len(sentinel_events)
        if total_anomalies == 0:
            return [
                "## Healing Efficacy",
                "",
                "_No anomalies recorded -- nothing to heal._",
                "",
            ]

        # Collect task_ids that had a successful recovery
        healed_task_ids: set[str] = set()
        for ev in recovery_events:
            if not (hasattr(ev, "data") and isinstance(ev.data, dict)):
                continue
            if ev.data.get("success"):
                tid = ev.data.get("task_id", "")
                if tid:
                    healed_task_ids.add(tid)

        # Collect task_ids from anomalies
        anomaly_task_ids: set[str] = set()
        for ev in sentinel_events:
            if hasattr(ev, "data") and isinstance(ev.data, dict):
                tid = ev.data.get("task_id", "")
                if tid:
                    anomaly_task_ids.add(tid)

        healed = len(anomaly_task_ids & healed_task_ids)
        total_unique = len(anomaly_task_ids) if anomaly_task_ids else total_anomalies
        rate = (healed / total_unique * 100) if total_unique > 0 else 0.0

        lines = [
            "## Healing Efficacy",
            "",
            f"- **Anomalies detected**: {total_anomalies}",
            f"- **Unique tasks affected**: {total_unique}",
            f"- **Successfully recovered**: {healed}",
            f"- **Healing rate**: {rate:.1f}%",
            "",
        ]

        if rate >= 80:
            lines.insert(2, "> [!SUCCESS] Healing rate above 80% -- system self-repair operational.")
            lines.insert(3, "")
        elif rate == 0 and total_unique > 0:
            lines.insert(2, "> [!WARNING] No successful recoveries recorded.")
            lines.insert(3, "")

        return lines

    @staticmethod
    def _build_failure_distribution(
        sentinel_events: list, kill_events: list
    ) -> list[str]:
        """
        Build a Mermaid pie chart showing failure distribution:
        - Score Anomaly: CRITICAL_ANOMALY without detection_status=NOT_DETECTED
        - Anchoring Error: CRITICAL_ANOMALY with detection_status=NOT_DETECTED
        - Hardware Error: KILL_SWITCH_TRIGGERED events
        """
        score_anomaly = 0
        anchoring_error = 0

        for ev in sentinel_events:
            if hasattr(ev, "data") and isinstance(ev.data, dict):
                if ev.data.get("detection_status") == "NOT_DETECTED":
                    anchoring_error += 1
                else:
                    score_anomaly += 1
            else:
                score_anomaly += 1

        hardware_error = len(kill_events)
        total = score_anomaly + anchoring_error + hardware_error

        if total == 0:
            return [
                "## Failure Distribution",
                "",
                "_No failures recorded._",
                "",
            ]

        lines = [
            "## Failure Distribution",
            "",
            "```mermaid",
            "pie title Failure Distribution",
        ]

        if score_anomaly > 0:
            lines.append(f'    "Score Anomaly" : {score_anomaly}')
        if anchoring_error > 0:
            lines.append(f'    "Anchoring Error" : {anchoring_error}')
        if hardware_error > 0:
            lines.append(f'    "Hardware Error" : {hardware_error}')

        lines.append("```")
        lines.append("")
        lines.append(f"**Total failures**: {total}")
        lines.append("")
        return lines

    @staticmethod
    def _build_mermaid_chart(agent_tokens: dict[str, int]) -> list[str]:
        """Build a Mermaid pie chart block for token consumption."""
        if not agent_tokens:
            return []
        total = sum(agent_tokens.values())
        lines = [
            "## Token Consumption",
            "",
            "```mermaid",
            "pie title Token Usage by Agent",
        ]
        for agent_id, tokens in sorted(agent_tokens.items(), key=lambda x: x[1], reverse=True):
            pct = (tokens / total * 100) if total > 0 else 0
            lines.append(f'    "{agent_id}" : {tokens}')
        lines.append("```")
        lines.append("")
        lines.append(f"**Total estimated tokens**: {total}")
        lines.append("")
        return lines

    @staticmethod
    def _format_note(frontmatter: dict, body: str) -> str:
        """Format a note with YAML frontmatter + body."""
        fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)
        return f"---\n{fm_str}---\n\n{body}\n"

    @staticmethod
    def _safe_write_md(path: Path, content: str) -> None:
        """Atomic write with encoding safety."""
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp_fd = tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            suffix=".md.tmp",
            dir=path.parent,
            delete=False,
        )
        try:
            tmp_fd.write(content)
            tmp_fd.close()
            shutil.move(tmp_fd.name, str(path))
        except Exception:
            # Clean up temp file on failure
            tmp_path = Path(tmp_fd.name)
            tmp_fd.close()
            if tmp_path.exists():
                tmp_path.unlink()
            raise


# ------------------------------------------------------------------
# CLI entry point
# ------------------------------------------------------------------

def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="ObsidianBridge - sync Neural Link state to an Obsidian vault"
    )
    parser.add_argument(
        "--watch", action="store_true",
        help="Persistent monitor: poll src/ and Neo4j, re-sync on changes"
    )
    parser.add_argument(
        "--interval", type=float, default=30.0,
        help="Watch poll interval in seconds (default: 30)"
    )
    parser.add_argument(
        "--vault", type=str, default="vault",
        help="Path to the Obsidian vault directory (default: vault)"
    )
    parser.add_argument(
        "--src", type=str, default="src",
        help="Path to the source directory to watch (default: src)"
    )
    return parser


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

    args = _build_cli().parse_args()

    vault = Path(args.vault)
    src = Path(args.src)

    # --- Environment validation ---
    graph = None
    try:
        from src.neural_link.graph.manager import GraphManager
        graph = GraphManager.from_env()
        print("[obsidian_bridge] Connected to Neo4j")
    except Exception as e:
        print(f"[obsidian_bridge] Neo4j unavailable ({e}), using static registry only")

    env_status = validate_environment(vault, check_neo4j_connection=True, graph_manager=graph)
    if env_status.warnings:
        for w in env_status.warnings:
            print(f"[obsidian_bridge] WARNING: {w}")
    else:
        print("[obsidian_bridge] Environment check passed")

    bridge = ObsidianBridge(vault_path=vault, graph_manager=graph)

    if args.watch:
        # Initial sync, then watch
        print("[obsidian_bridge] Initial sync...")
        bridge.full_sync()
        bridge.watch(src_path=src, interval=args.interval)
    else:
        results = bridge.full_sync()
        print("[obsidian_bridge] Sync complete:")
        for key, val in results.items():
            if isinstance(val, list):
                print(f"  {key}: {len(val)} files")
            else:
                print(f"  {key}: {val}")
