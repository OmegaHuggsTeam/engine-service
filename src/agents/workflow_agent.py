"""
WorkflowAgent - Specialist for task scheduling and automation workflows.

Capabilities: workflow, task_scheduling, cron, event_driven
Commands: tasks, schedule, triggers, status, create
"""

import json
import logging
import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class WorkflowAgent:
    """Specialist agent for task scheduling and automation workflows."""

    def __init__(self):
        self.capabilities = ["workflow", "task_scheduling", "cron", "event_driven"]
        self.commands = ["tasks", "schedule", "triggers", "status", "create"]
        self.project_root = PROJECT_ROOT

    def execute(self, command: str) -> dict:
        """Dispatch to sub-methods based on command text."""
        command_lower = command.strip().lower()

        if command_lower.startswith("tasks"):
            return self._list_tasks()
        elif command_lower.startswith("schedule"):
            return self._show_schedule()
        elif command_lower.startswith("triggers"):
            return self._list_triggers()
        elif command_lower.startswith("status"):
            return self._check_status()
        elif command_lower.startswith("create"):
            description = command_lower.replace("create", "", 1).strip()
            return self._create_workflow(description)
        else:
            return {
                "status": "error",
                "message": f"Unknown command: {command}",
                "available_commands": self.commands,
            }

    def _list_tasks(self) -> dict:
        """Lists all pending/running tasks from Neo4j if available, else returns static info."""
        tasks = []

        # Try to get tasks from Neo4j
        try:
            from neo4j import GraphDatabase

            uri = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
            user = os.environ.get("NEO4J_USER", "neo4j")
            password = os.environ.get("NEO4J_PASSWORD", "password")

            driver = GraphDatabase.driver(uri, auth=(user, password))
            with driver.session() as session:
                result = session.run(
                    "MATCH (t:Task) WHERE t.status IN ['pending', 'running'] "
                    "RETURN t.name AS name, t.status AS status, t.created AS created, "
                    "t.priority AS priority ORDER BY t.created DESC LIMIT 50"
                )
                for record in result:
                    tasks.append({
                        "name": record["name"],
                        "status": record["status"],
                        "created": str(record["created"]) if record["created"] else None,
                        "priority": record["priority"],
                        "source": "neo4j",
                    })
            driver.close()

        except ImportError:
            logger.info("Neo4j driver not available, returning static task info")
            tasks = [
                {
                    "name": "chunk_processing",
                    "status": "available",
                    "description": "Processes text into semantic chunks",
                    "source": "static",
                },
                {
                    "name": "webhook_listener",
                    "status": "available",
                    "description": "Listens for incoming webhook events",
                    "source": "static",
                },
                {
                    "name": "knowledge_graph_update",
                    "status": "available",
                    "description": "Updates Neo4j knowledge graph from chunks",
                    "source": "static",
                },
                {
                    "name": "agent_orchestration",
                    "status": "available",
                    "description": "Routes queries to specialized agents",
                    "source": "static",
                },
            ]
        except Exception as e:
            logger.warning(f"Error connecting to Neo4j: {e}")
            tasks = [{"error": str(e), "source": "neo4j_error"}]

        return {
            "status": "success",
            "command": "tasks",
            "total_tasks": len(tasks),
            "tasks": tasks,
            "timestamp": datetime.now().isoformat(),
        }

    def _show_schedule(self) -> dict:
        """Shows scheduling capabilities with cron syntax helper."""
        cron_reference = {
            "format": "minute hour day_of_month month day_of_week",
            "fields": {
                "minute": "0-59",
                "hour": "0-23",
                "day_of_month": "1-31",
                "month": "1-12",
                "day_of_week": "0-7 (0 and 7 are Sunday)",
            },
            "special_characters": {
                "*": "any value",
                ",": "value list separator",
                "-": "range of values",
                "/": "step values",
            },
            "common_patterns": {
                "every_minute": "* * * * *",
                "every_5_minutes": "*/5 * * * *",
                "every_hour": "0 * * * *",
                "every_day_midnight": "0 0 * * *",
                "every_day_6am": "0 6 * * *",
                "every_monday_9am": "0 9 * * 1",
                "every_weekday_9am": "0 9 * * 1-5",
                "first_of_month": "0 0 1 * *",
                "every_15_minutes": "*/15 * * * *",
                "twice_daily": "0 0,12 * * *",
            },
        }

        # Check for any scheduling config files in the project
        schedule_files = []
        schedule_patterns = ["crontab", "schedule.py", "celery*.py", "tasks.py", "scheduler*.py"]
        for pattern in schedule_patterns:
            for f in self.project_root.rglob(pattern):
                parts = f.parts
                if any(p.startswith(".") or p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
                    continue
                schedule_files.append(str(f.relative_to(self.project_root)))

        return {
            "status": "success",
            "command": "schedule",
            "cron_reference": cron_reference,
            "project_schedule_files": schedule_files,
            "supported_schedulers": [
                "cron (system)",
                "APScheduler (Python)",
                "Celery Beat (distributed)",
                "asyncio scheduled tasks",
            ],
            "timestamp": datetime.now().isoformat(),
        }

    def _list_triggers(self) -> dict:
        """Lists event triggers in the system (webhook endpoints, file watchers)."""
        triggers = []

        # Scan for webhook endpoints
        webhook_patterns = [
            re.compile(r'@app\.(post|put)\s*\(\s*["\']([^"\']*(?:webhook|hook|callback|event)[^"\']*)["\']', re.IGNORECASE),
            re.compile(r'webhook[_\s]*(?:url|endpoint|listener)', re.IGNORECASE),
        ]

        # Scan for file watcher patterns
        filewatcher_patterns = [
            re.compile(r'watchdog|FileSystemEventHandler|Observer', re.IGNORECASE),
            re.compile(r'inotify|watchfiles|file.?watch', re.IGNORECASE),
        ]

        # Scan for event-driven patterns
        event_patterns = [
            re.compile(r'on_event|event_handler|EventHandler|@event', re.IGNORECASE),
            re.compile(r'signal\.connect|pubsub|subscribe|on_message', re.IGNORECASE),
        ]

        for py_file in self.project_root.rglob("*.py"):
            parts = py_file.parts
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(self.project_root))

                # Check webhook patterns
                for pattern in webhook_patterns:
                    matches = pattern.findall(content)
                    if matches:
                        triggers.append({
                            "type": "webhook",
                            "file": rel_path,
                            "details": [m if isinstance(m, str) else list(m) for m in matches],
                        })

                # Check file watcher patterns
                for pattern in filewatcher_patterns:
                    if pattern.search(content):
                        triggers.append({
                            "type": "file_watcher",
                            "file": rel_path,
                            "pattern_matched": pattern.pattern,
                        })
                        break

                # Check event-driven patterns
                for pattern in event_patterns:
                    if pattern.search(content):
                        triggers.append({
                            "type": "event_driven",
                            "file": rel_path,
                            "pattern_matched": pattern.pattern,
                        })
                        break

            except Exception as e:
                logger.warning(f"Error reading {py_file}: {e}")

        return {
            "status": "success",
            "command": "triggers",
            "total_triggers": len(triggers),
            "triggers": triggers,
            "timestamp": datetime.now().isoformat(),
        }

    def _check_status(self) -> dict:
        """Shows running background processes (checks for streamlit, docker, neo4j via subprocess)."""
        processes = {}

        # Define processes to check
        process_checks = {
            "streamlit": {
                "cmd_windows": ["tasklist", "/FI", "IMAGENAME eq streamlit.exe"],
                "cmd_unix": ["pgrep", "-f", "streamlit"],
                "search_term": "streamlit",
            },
            "docker": {
                "cmd_windows": ["docker", "ps", "--format", "{{.Names}}"],
                "cmd_unix": ["docker", "ps", "--format", "{{.Names}}"],
                "search_term": None,
            },
            "neo4j": {
                "cmd_windows": ["tasklist", "/FI", "IMAGENAME eq neo4j.exe"],
                "cmd_unix": ["pgrep", "-f", "neo4j"],
                "search_term": "neo4j",
            },
            "python": {
                "cmd_windows": ["tasklist", "/FI", "IMAGENAME eq python.exe"],
                "cmd_unix": ["pgrep", "-f", "python"],
                "search_term": "python",
            },
            "uvicorn": {
                "cmd_windows": ["tasklist"],
                "cmd_unix": ["pgrep", "-f", "uvicorn"],
                "search_term": "uvicorn",
            },
        }

        is_windows = os.name == "nt"

        for proc_name, config in process_checks.items():
            try:
                cmd = config["cmd_windows"] if is_windows else config["cmd_unix"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                output = result.stdout.strip()

                if proc_name == "docker":
                    if result.returncode == 0 and output:
                        containers = [c.strip() for c in output.split("\n") if c.strip()]
                        processes[proc_name] = {
                            "status": "running",
                            "containers": containers,
                            "count": len(containers),
                        }
                    else:
                        processes[proc_name] = {
                            "status": "not_running" if result.returncode == 0 else "not_installed",
                        }
                else:
                    search = config["search_term"]
                    if search and search.lower() in output.lower():
                        processes[proc_name] = {"status": "running"}
                    elif not search and result.returncode == 0 and output:
                        processes[proc_name] = {"status": "running"}
                    else:
                        processes[proc_name] = {"status": "not_detected"}

            except FileNotFoundError:
                processes[proc_name] = {"status": "check_unavailable", "reason": "command not found"}
            except subprocess.TimeoutExpired:
                processes[proc_name] = {"status": "check_timeout"}
            except Exception as e:
                processes[proc_name] = {"status": "error", "error": str(e)}

        return {
            "status": "success",
            "command": "status",
            "platform": "windows" if is_windows else "unix",
            "processes": processes,
            "timestamp": datetime.now().isoformat(),
        }

    def _create_workflow(self, description: str) -> dict:
        """Describes how to create a new automated workflow."""
        workflow_template = {
            "steps_to_create": [
                "1. Define the workflow trigger (webhook, cron schedule, or event)",
                "2. Create a workflow configuration file (YAML or Python)",
                "3. Define the task sequence with dependencies",
                "4. Set up error handling and retry logic",
                "5. Configure notifications (success/failure)",
                "6. Register the workflow with the orchestrator",
                "7. Test with a dry run before enabling",
            ],
            "workflow_template": {
                "name": description if description else "new_workflow",
                "trigger": {
                    "type": "cron|webhook|event",
                    "config": {},
                },
                "tasks": [
                    {
                        "name": "step_1",
                        "action": "describe_action_here",
                        "timeout": "300s",
                        "retry": {"max_attempts": 3, "backoff": "exponential"},
                    },
                    {
                        "name": "step_2",
                        "action": "describe_action_here",
                        "depends_on": ["step_1"],
                        "timeout": "600s",
                    },
                ],
                "on_success": "notify",
                "on_failure": "alert",
                "enabled": False,
            },
            "example_python": (
                "from apscheduler.schedulers.asyncio import AsyncIOScheduler\n"
                "\n"
                "scheduler = AsyncIOScheduler()\n"
                "\n"
                "@scheduler.scheduled_job('cron', hour=6, minute=0)\n"
                "async def daily_workflow():\n"
                "    # Step 1: Collect data\n"
                "    data = await collect_data()\n"
                "    # Step 2: Process\n"
                "    results = await process_data(data)\n"
                "    # Step 3: Store\n"
                "    await store_results(results)\n"
                "\n"
                "scheduler.start()\n"
            ),
            "available_actions": [
                "run_agent(agent_name, query)",
                "process_chunks(input_path)",
                "update_knowledge_graph()",
                "send_notification(channel, message)",
                "execute_script(script_path)",
                "http_request(method, url, payload)",
            ],
        }

        return {
            "status": "success",
            "command": "create",
            "description": description if description else "generic workflow",
            "workflow_guide": workflow_template,
            "timestamp": datetime.now().isoformat(),
        }


def ask_agent(query: str) -> str:
    """Entry point for the WorkflowAgent. Creates instance, executes query, returns JSON."""
    agent = WorkflowAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "status"
    print(ask_agent(query))
