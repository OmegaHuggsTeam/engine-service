"""
Stress Mission 001 - Energy Infrastructure Audit

End-to-end orchestration demo exercising:
  AgentSelector -> TaskExecutor -> TaskEvaluator

Decomposes an infrastructure audit into 2 tasks:
  1. Generate energy monitoring code  (devops_agent)
  2. Generate tests for the monitor   (testing_agent)

Task 2 receives Task 1 output as context (inter-agent communication).
Both outputs scored via TaskEvaluator with formatted Scoreboard.
"""

import sys
import uuid
from datetime import datetime

from ..orchestrator.models import Task, TaskType
from ..orchestrator.agent_selector import AgentSelector
from ..orchestrator.task_executor import TaskExecutor
from ..graph.evaluator import TaskEvaluator, EvaluationResult

# ANSI colors (matches maestro_service.py)
_C_CYAN = "\033[96m"
_C_GREEN = "\033[92m"
_C_YELLOW = "\033[93m"
_C_RED = "\033[91m"
_C_BOLD = "\033[1m"
_C_RESET = "\033[0m"

PASS_THRESHOLD = 7.0


def _safe_print(msg: str):
    """Windows-safe print that handles encoding issues."""
    safe = msg.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(
        sys.stdout.encoding or "utf-8", errors="replace"
    )
    sys.stdout.write(safe + "\n")
    sys.stdout.flush()


class StressMission001:
    """Stress Mission 001: Energy Infrastructure Audit orchestration."""

    def __init__(self, graph_manager=None):
        self._graph = graph_manager
        self._selector = AgentSelector(graph_manager=graph_manager)
        self._executor = TaskExecutor(graph_manager=graph_manager)
        self._evaluator = TaskEvaluator(graph_manager=graph_manager, threshold=PASS_THRESHOLD)

    def run(self) -> dict:
        """
        Execute the full orchestration pipeline.

        Returns:
            dict with keys: task1_agent, task2_agent, eval1, eval2,
                           task1_result, task2_result, mission_passed
        """
        self._print_banner()

        # === Phase 1: Task Decomposition ===
        _safe_print(f"\n{_C_BOLD}{_C_CYAN}[ Phase 1 ] Task Decomposition{_C_RESET}")
        _safe_print("=" * 60)

        task1 = Task(
            id=f"stress001-t1-{uuid.uuid4().hex[:8]}",
            description=(
                "Generate energy infrastructure monitoring code. "
                "The module should read voltage, current, and power from multiple sources, "
                "detect anomalies using configurable thresholds, and produce an audit report "
                "with total power, average voltage, critical count, and efficiency percentage."
            ),
            type=TaskType.GENERATION,
            priority=8,
            required_capabilities=["monitoring", "infrastructure"],
            input_data={"domain": "energy", "sources": ["grid_main", "solar_array", "backup_gen", "battery_bank"]},
        )

        task2 = Task(
            id=f"stress001-t2-{uuid.uuid4().hex[:8]}",
            description=(
                "Generate a comprehensive test suite for the energy monitor module. "
                "Cover: model validation, sensor reading ranges, audit aggregation, "
                "threshold detection for voltage and power anomalies, and edge cases."
            ),
            type=TaskType.GENERATION,
            priority=7,
            required_capabilities=["testing", "unit_testing"],
            depends_on=[task1.id],
        )

        _safe_print(f"  Task 1: {task1.description[:60]}...")
        _safe_print(f"    ID: {task1.id}")
        _safe_print(f"    Capabilities: {task1.required_capabilities}")
        _safe_print(f"  Task 2: {task2.description[:60]}...")
        _safe_print(f"    ID: {task2.id}")
        _safe_print(f"    Capabilities: {task2.required_capabilities}")
        _safe_print(f"    Depends on: {task2.depends_on}")

        # === Phase 2: Agent Selection & Execution ===
        _safe_print(f"\n{_C_BOLD}{_C_CYAN}[ Phase 2 ] Agent Selection & Execution{_C_RESET}")
        _safe_print("=" * 60)

        # Task 1
        agent1 = self._selector.select(task1)
        _safe_print(f"  Task 1 -> Agent: {_C_GREEN}{agent1}{_C_RESET}")
        _safe_print(f"  Executing Task 1...")
        result1 = self._executor.execute(task1, agent1)
        status1 = f"{_C_GREEN}OK{_C_RESET}" if result1.success else f"{_C_RED}FAIL{_C_RESET}"
        _safe_print(f"  Task 1 result: {status1} ({result1.execution_time_ms:.0f}ms)")

        # Inter-agent communication: pass Task 1 output to Task 2
        task2.input_data = {
            "upstream_task_id": task1.id,
            "upstream_agent": agent1,
            "upstream_output": str(result1.output)[:2000] if result1.output else "",
        }
        _safe_print(f"  {_C_YELLOW}>> Inter-agent data: Task 1 output -> Task 2 input{_C_RESET}")

        # Task 2
        agent2 = self._selector.select(task2)
        _safe_print(f"  Task 2 -> Agent: {_C_GREEN}{agent2}{_C_RESET}")
        _safe_print(f"  Executing Task 2...")
        result2 = self._executor.execute(task2, agent2)
        status2 = f"{_C_GREEN}OK{_C_RESET}" if result2.success else f"{_C_RED}FAIL{_C_RESET}"
        _safe_print(f"  Task 2 result: {status2} ({result2.execution_time_ms:.0f}ms)")

        # === Phase 3: Evaluation Scoreboard ===
        _safe_print(f"\n{_C_BOLD}{_C_CYAN}[ Phase 3 ] TaskEvaluator Scoreboard{_C_RESET}")
        _safe_print("=" * 60)

        eval1 = self._evaluator.evaluate(task1, result1)
        eval2 = self._evaluator.evaluate(task2, result2)

        scoreboard_data = [
            (agent1, "Monitor Code", eval1),
            (agent2, "Test Generation", eval2),
        ]
        self._print_scoreboard(scoreboard_data)

        # === Phase 4: Summary ===
        mission_passed = eval1.passed and eval2.passed
        _safe_print(f"\n{_C_BOLD}{_C_CYAN}[ Phase 4 ] Mission Summary{_C_RESET}")
        _safe_print("=" * 60)

        if mission_passed:
            _safe_print(f"  {_C_GREEN}{_C_BOLD}MISSION PASSED{_C_RESET}")
        else:
            _safe_print(f"  {_C_RED}{_C_BOLD}MISSION FAILED{_C_RESET}")
            if not eval1.passed:
                _safe_print(f"    Task 1 score {eval1.quality_score:.1f} below threshold {PASS_THRESHOLD}")
            if not eval2.passed:
                _safe_print(f"    Task 2 score {eval2.quality_score:.1f} below threshold {PASS_THRESHOLD}")

        _safe_print(f"  Timestamp: {datetime.now().isoformat()}")
        _safe_print("")

        return {
            "task1_agent": agent1,
            "task2_agent": agent2,
            "eval1": eval1,
            "eval2": eval2,
            "task1_result": result1,
            "task2_result": result2,
            "mission_passed": mission_passed,
        }

    def _print_banner(self):
        """Print mission startup banner."""
        banner = (
            f"\n{_C_BOLD}{_C_CYAN}"
            "  +------------------------------------------------------+\n"
            "  |        STRESS MISSION 001 - Energy Audit             |\n"
            "  |   AgentSelector | TaskExecutor | TaskEvaluator       |\n"
            "  +------------------------------------------------------+\n"
            f"{_C_RESET}"
        )
        _safe_print(banner)

    @staticmethod
    def _print_scoreboard(evals: list[tuple[str, str, EvaluationResult]]):
        """Print formatted ASCII scoreboard table."""
        _safe_print("")
        _safe_print(f"  {_C_BOLD}+==============================================================+{_C_RESET}")
        _safe_print(f"  {_C_BOLD}|              SCOREBOARD - Stress Mission 001                  |{_C_RESET}")
        _safe_print(f"  {_C_BOLD}+==============================================================+{_C_RESET}")
        _safe_print(f"  {_C_BOLD}| Agent            | Task               | Score | Status        |{_C_RESET}")
        _safe_print(f"  {_C_BOLD}+------------------+--------------------+-------+---------------+{_C_RESET}")

        for agent_id, task_label, ev in evals:
            score_str = f"{ev.quality_score:5.1f}"
            if ev.passed:
                status_str = f"{_C_GREEN}[PASS]{_C_RESET}"
            else:
                status_str = f"{_C_RED}[FAIL]{_C_RESET}"
            _safe_print(
                f"  | {agent_id:<16} | {task_label:<18} | {score_str} | {status_str:<22} |"
            )

        _safe_print(f"  {_C_BOLD}+------------------+--------------------+-------+---------------+{_C_RESET}")

        # Summary rows
        if evals:
            scores = [ev.quality_score for _, _, ev in evals]
            all_passed = all(ev.passed for _, _, ev in evals)
            mission_status = f"{_C_GREEN}PASS{_C_RESET}" if all_passed else f"{_C_RED}FAIL{_C_RESET}"

            for agent_id, task_label, ev in evals:
                label = task_label.replace(" ", " ")
                _safe_print(f"  | {label + ':':<37} {ev.quality_score:5.1f}/10           |")

            _safe_print(f"  | {'Mission Status:':<37} {mission_status:<22} |")

        _safe_print(f"  {_C_BOLD}+==============================================================+{_C_RESET}")
        _safe_print("")


if __name__ == "__main__":
    mission = StressMission001()
    results = mission.run()

    if results["mission_passed"]:
        sys.exit(0)
    else:
        sys.exit(1)
