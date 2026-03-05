"""
Testing Agent - Specialist for test management and quality assurance.

Capabilities: testing, unit_testing, integration_testing, qa, test_automation

Commands:
    run      - Executes pytest with capture
    discover - Finds all test files via glob patterns
    coverage - Runs pytest --co (collect only) to show test inventory
    generate - Suggests test stubs for a given module
    report   - Summarizes last test run results
"""

import ast
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class TestingAgent:
    """Specialist agent for test management and quality assurance."""

    CAPABILITIES = ["testing", "unit_testing", "integration_testing", "qa", "test_automation"]
    COMMANDS = ["run", "discover", "coverage", "generate", "report"]

    def __init__(self):
        self.name = "TestingAgent"
        self.project_root = PROJECT_ROOT
        self.timestamp = datetime.now().isoformat()

    def execute(self, command: str) -> dict:
        """Execute a testing command.

        Args:
            command: The command string to execute. First word is the command name,
                     rest is arguments.

        Returns:
            dict with results of the command execution.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "run":
            return self._run(args)
        elif cmd == "discover":
            return self._discover(args)
        elif cmd == "coverage":
            return self._coverage(args)
        elif cmd == "generate":
            return self._generate(args)
        elif cmd == "report":
            return self._report(args)
        else:
            return {
                "agent": self.name,
                "status": "error",
                "message": f"Unknown command: '{cmd}'. Available commands: {', '.join(self.COMMANDS)}",
                "timestamp": self.timestamp,
            }

    def _run(self, args: str) -> dict:
        """Execute pytest with capture."""
        pytest_args = ["python", "-m", "pytest"]

        if args.strip():
            pytest_args.extend(args.strip().split())
        else:
            pytest_args.extend(["-v", "--tb=short"])

        try:
            result = subprocess.run(
                pytest_args,
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.project_root),
            )
            return {
                "agent": self.name,
                "command": "run",
                "status": "success" if result.returncode == 0 else "tests_failed",
                "returncode": result.returncode,
                "stdout": result.stdout[-5000:] if result.stdout else "",  # Limit output
                "stderr": result.stderr[-2000:] if result.stderr else "",
                "message": "Tests passed." if result.returncode == 0 else f"Tests completed with exit code {result.returncode}.",
                "timestamp": self.timestamp,
            }
        except FileNotFoundError:
            return {
                "agent": self.name,
                "command": "run",
                "status": "error",
                "message": "pytest not found. Install with: pip install pytest",
                "timestamp": self.timestamp,
            }
        except subprocess.TimeoutExpired:
            return {
                "agent": self.name,
                "command": "run",
                "status": "error",
                "message": "Test execution timed out after 300 seconds.",
                "timestamp": self.timestamp,
            }

    def _discover(self, args: str) -> dict:
        """Find all test files via glob patterns."""
        search_path = Path(args.strip()) if args.strip() else self.project_root

        test_files = []
        patterns = ["**/test_*.py", "**/*_test.py"]

        for pattern in patterns:
            for test_file in search_path.rglob(pattern.replace("**/", "")):
                if any(skip in str(test_file) for skip in ["__pycache__", ".git", "node_modules", ".venv", "venv"]):
                    continue
                rel_path = str(test_file.relative_to(self.project_root))
                if rel_path not in [t["path"] for t in test_files]:
                    try:
                        size = test_file.stat().st_size
                        content = test_file.read_text(encoding="utf-8", errors="ignore")
                        # Count test functions
                        test_count = len([line for line in content.splitlines() if line.strip().startswith("def test_")])
                    except OSError:
                        size = 0
                        test_count = 0

                    test_files.append({
                        "path": rel_path,
                        "size_bytes": size,
                        "test_function_count": test_count,
                    })

        return {
            "agent": self.name,
            "command": "discover",
            "status": "success",
            "test_files_count": len(test_files),
            "test_files": test_files,
            "message": f"Discovered {len(test_files)} test files.",
            "timestamp": self.timestamp,
        }

    def _coverage(self, args: str) -> dict:
        """Run pytest --co (collect only) to show test inventory."""
        pytest_args = ["python", "-m", "pytest", "--co", "-q"]

        if args.strip():
            pytest_args.append(args.strip())

        try:
            result = subprocess.run(
                pytest_args,
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(self.project_root),
            )
            output = result.stdout.strip() if result.stdout else ""
            test_items = [line.strip() for line in output.splitlines() if line.strip() and "::" in line]

            return {
                "agent": self.name,
                "command": "coverage",
                "status": "success" if result.returncode == 0 else "error",
                "total_tests_collected": len(test_items),
                "test_items": test_items[:100],  # Limit output
                "raw_output": output[-3000:] if output else "",
                "message": f"Collected {len(test_items)} test items.",
                "timestamp": self.timestamp,
            }
        except FileNotFoundError:
            return {
                "agent": self.name,
                "command": "coverage",
                "status": "error",
                "message": "pytest not found. Install with: pip install pytest",
                "timestamp": self.timestamp,
            }
        except subprocess.TimeoutExpired:
            return {
                "agent": self.name,
                "command": "coverage",
                "status": "error",
                "message": "Collection timed out after 60 seconds.",
                "timestamp": self.timestamp,
            }

    def _generate(self, module_path: str) -> dict:
        """Suggest test stubs for a given module by extracting function names."""
        if not module_path.strip():
            return {
                "agent": self.name,
                "command": "generate",
                "status": "error",
                "message": "Please provide a module path. Usage: generate <path/to/module.py>",
                "timestamp": self.timestamp,
            }

        target = self.project_root / module_path.strip()
        if not target.exists():
            return {
                "agent": self.name,
                "command": "generate",
                "status": "error",
                "message": f"Module not found: {module_path.strip()}",
                "timestamp": self.timestamp,
            }

        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            functions = []
            classes = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and not node.name.startswith("_"):
                    args_list = [arg.arg for arg in node.args.args if arg.arg != "self"]
                    functions.append({
                        "name": node.name,
                        "args": args_list,
                        "line": node.lineno,
                    })
                elif isinstance(node, ast.ClassDef):
                    methods = []
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef) and not item.name.startswith("_"):
                            methods.append(item.name)
                    classes.append({
                        "name": node.name,
                        "methods": methods,
                        "line": node.lineno,
                    })

            # Generate test stubs
            stubs = []
            stubs.append('"""Tests for {}."""'.format(module_path.strip()))
            stubs.append("")
            stubs.append("import pytest")
            stubs.append("")

            for func in functions:
                args_str = ", ".join(func["args"]) if func["args"] else ""
                stubs.append(f"def test_{func['name']}():")
                stubs.append(f'    """Test {func["name"]} function."""')
                stubs.append(f"    # TODO: Implement test for {func['name']}({args_str})")
                stubs.append(f"    assert True  # Replace with actual assertion")
                stubs.append("")

            for cls in classes:
                stubs.append(f"class Test{cls['name']}:")
                stubs.append(f'    """Tests for {cls["name"]} class."""')
                stubs.append("")
                for method in cls["methods"]:
                    stubs.append(f"    def test_{method}(self):")
                    stubs.append(f'        """Test {cls["name"]}.{method} method."""')
                    stubs.append(f"        # TODO: Implement test for {method}")
                    stubs.append(f"        assert True  # Replace with actual assertion")
                    stubs.append("")

            test_code = "\n".join(stubs)

            return {
                "agent": self.name,
                "command": "generate",
                "status": "success",
                "module": module_path.strip(),
                "functions_found": len(functions),
                "classes_found": len(classes),
                "test_stubs": test_code,
                "message": f"Generated test stubs for {len(functions)} functions and {len(classes)} classes.",
                "timestamp": self.timestamp,
            }

        except SyntaxError as e:
            return {
                "agent": self.name,
                "command": "generate",
                "status": "error",
                "message": f"Syntax error parsing {module_path.strip()}: {e}",
                "timestamp": self.timestamp,
            }
        except OSError as e:
            return {
                "agent": self.name,
                "command": "generate",
                "status": "error",
                "message": f"Could not read module: {e}",
                "timestamp": self.timestamp,
            }

    def _report(self, args: str) -> dict:
        """Summarize last test run results."""
        # Run pytest with short summary to get current state
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "-v", "--tb=line", "-q"],
                capture_output=True,
                text=True,
                timeout=300,
                cwd=str(self.project_root),
            )
            stdout = result.stdout.strip() if result.stdout else ""
            stderr = result.stderr.strip() if result.stderr else ""

            # Parse results from output
            passed = 0
            failed = 0
            errors = 0
            skipped = 0

            for line in stdout.splitlines():
                if "passed" in line:
                    import re
                    match = re.search(r'(\d+)\s+passed', line)
                    if match:
                        passed = int(match.group(1))
                if "failed" in line:
                    import re
                    match = re.search(r'(\d+)\s+failed', line)
                    if match:
                        failed = int(match.group(1))
                if "error" in line:
                    import re
                    match = re.search(r'(\d+)\s+error', line)
                    if match:
                        errors = int(match.group(1))
                if "skipped" in line:
                    import re
                    match = re.search(r'(\d+)\s+skipped', line)
                    if match:
                        skipped = int(match.group(1))

            return {
                "agent": self.name,
                "command": "report",
                "status": "success",
                "test_results": {
                    "passed": passed,
                    "failed": failed,
                    "errors": errors,
                    "skipped": skipped,
                    "total": passed + failed + errors + skipped,
                },
                "returncode": result.returncode,
                "output": stdout[-3000:],
                "message": f"Test report: {passed} passed, {failed} failed, {errors} errors, {skipped} skipped.",
                "timestamp": self.timestamp,
            }
        except FileNotFoundError:
            return {
                "agent": self.name,
                "command": "report",
                "status": "error",
                "message": "pytest not found. Install with: pip install pytest",
                "timestamp": self.timestamp,
            }
        except subprocess.TimeoutExpired:
            return {
                "agent": self.name,
                "command": "report",
                "status": "error",
                "message": "Test execution timed out after 300 seconds.",
                "timestamp": self.timestamp,
            }


def ask_agent(query: str) -> str:
    """Entry point for the Testing Agent.

    Args:
        query: The command string to execute.

    Returns:
        JSON string with the result of the command execution.
    """
    agent = TestingAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)
