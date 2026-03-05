"""
Documentation Agent - Specialist for project documentation.

Capabilities: documentation, technical_writing, api_docs, changelog

Commands:
    index      - Lists all .md files in project with sizes
    missing    - Finds Python modules without docstrings
    changelog  - Reads git log and formats as changelog
    docstrings - Analyzes a module for docstring coverage
    structure  - Generates project directory tree
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


class DocumentationAgent:
    """Specialist agent for project documentation management and analysis."""

    CAPABILITIES = ["documentation", "technical_writing", "api_docs", "changelog"]
    COMMANDS = ["index", "missing", "changelog", "docstrings", "structure"]

    def __init__(self):
        self.name = "DocumentationAgent"
        self.project_root = PROJECT_ROOT
        self.timestamp = datetime.now().isoformat()

    def execute(self, command: str) -> dict:
        """Execute a documentation command.

        Args:
            command: The command string to execute. First word is the command name,
                     rest is arguments.

        Returns:
            dict with results of the command execution.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "index":
            return self._index(args)
        elif cmd == "missing":
            return self._missing(args)
        elif cmd == "changelog":
            return self._changelog(args)
        elif cmd == "docstrings":
            return self._docstrings(args)
        elif cmd == "structure":
            return self._structure(args)
        else:
            return {
                "agent": self.name,
                "status": "error",
                "message": f"Unknown command: '{cmd}'. Available commands: {', '.join(self.COMMANDS)}",
                "timestamp": self.timestamp,
            }

    def _index(self, args: str) -> dict:
        """List all .md files in the project with sizes."""
        search_path = Path(args.strip()) if args.strip() else self.project_root
        md_files = []

        for md_file in search_path.rglob("*.md"):
            if any(skip in str(md_file) for skip in ["__pycache__", ".git", "node_modules", ".venv", "venv"]):
                continue
            try:
                stat = md_file.stat()
                md_files.append({
                    "path": str(md_file.relative_to(self.project_root)),
                    "size_bytes": stat.st_size,
                    "size_human": self._human_size(stat.st_size),
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                })
            except OSError as e:
                logger.warning(f"Could not stat {md_file}: {e}")

        md_files.sort(key=lambda x: x["path"])

        return {
            "agent": self.name,
            "command": "index",
            "status": "success",
            "total_files": len(md_files),
            "files": md_files,
            "message": f"Found {len(md_files)} Markdown files in project.",
            "timestamp": self.timestamp,
        }

    def _missing(self, args: str) -> dict:
        """Find Python modules without module-level docstrings."""
        search_path = Path(args.strip()) if args.strip() else self.project_root
        modules_without_docstrings = []
        modules_with_docstrings = []
        total_modules = 0

        for py_file in search_path.rglob("*.py"):
            if any(skip in str(py_file) for skip in ["__pycache__", ".git", "node_modules", ".venv", "venv"]):
                continue
            if py_file.name == "__init__.py":
                continue

            total_modules += 1
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                stripped = content.lstrip()

                has_docstring = False
                # Check if file starts with a docstring (after shebang/encoding/comments)
                lines = content.splitlines()
                for line in lines:
                    stripped_line = line.strip()
                    if not stripped_line or stripped_line.startswith("#"):
                        continue
                    if stripped_line.startswith('"""') or stripped_line.startswith("'''"):
                        has_docstring = True
                    break

                rel_path = str(py_file.relative_to(self.project_root))
                if has_docstring:
                    modules_with_docstrings.append(rel_path)
                else:
                    modules_without_docstrings.append(rel_path)

            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read {py_file}: {e}")

        return {
            "agent": self.name,
            "command": "missing",
            "status": "success",
            "total_modules": total_modules,
            "with_docstrings": len(modules_with_docstrings),
            "without_docstrings": len(modules_without_docstrings),
            "coverage_percent": round((len(modules_with_docstrings) / total_modules * 100) if total_modules > 0 else 0, 1),
            "missing_docstrings": modules_without_docstrings[:50],  # Limit output
            "message": f"{len(modules_without_docstrings)} of {total_modules} modules are missing docstrings.",
            "timestamp": self.timestamp,
        }

    def _changelog(self, args: str) -> dict:
        """Read git log and format as changelog."""
        count = 20
        if args.strip():
            try:
                count = int(args.strip())
            except ValueError:
                pass

        try:
            result = subprocess.run(
                ["git", "log", f"--oneline", f"-{count}"],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(self.project_root),
            )

            if result.returncode != 0:
                return {
                    "agent": self.name,
                    "command": "changelog",
                    "status": "error",
                    "message": f"Git log failed: {result.stderr.strip()}",
                    "timestamp": self.timestamp,
                }

            commits = result.stdout.strip().splitlines() if result.stdout else []

            # Format as changelog entries
            changelog_entries = []
            for commit in commits:
                parts = commit.split(" ", 1)
                if len(parts) == 2:
                    sha, message = parts
                    changelog_entries.append({
                        "sha": sha,
                        "message": message,
                    })

            changelog_text = "# Changelog\n\n"
            for entry in changelog_entries:
                changelog_text += f"- [{entry['sha']}] {entry['message']}\n"

            return {
                "agent": self.name,
                "command": "changelog",
                "status": "success",
                "commit_count": len(changelog_entries),
                "entries": changelog_entries,
                "formatted": changelog_text,
                "message": f"Generated changelog from {len(changelog_entries)} commits.",
                "timestamp": self.timestamp,
            }
        except FileNotFoundError:
            return {
                "agent": self.name,
                "command": "changelog",
                "status": "error",
                "message": "Git CLI not found. Ensure git is installed and in PATH.",
                "timestamp": self.timestamp,
            }
        except subprocess.TimeoutExpired:
            return {
                "agent": self.name,
                "command": "changelog",
                "status": "error",
                "message": "Git log timed out after 30 seconds.",
                "timestamp": self.timestamp,
            }

    def _docstrings(self, module_path: str) -> dict:
        """Analyze a module for docstring coverage."""
        if not module_path.strip():
            return {
                "agent": self.name,
                "command": "docstrings",
                "status": "error",
                "message": "Please provide a module path. Usage: docstrings <path/to/module.py>",
                "timestamp": self.timestamp,
            }

        target = self.project_root / module_path.strip()
        if not target.exists():
            return {
                "agent": self.name,
                "command": "docstrings",
                "status": "error",
                "message": f"Module not found: {module_path.strip()}",
                "timestamp": self.timestamp,
            }

        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(content)

            functions_with = []
            functions_without = []
            classes_with = []
            classes_without = []

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    docstring = ast.get_docstring(node)
                    entry = {"name": node.name, "line": node.lineno}
                    if docstring:
                        functions_with.append(entry)
                    else:
                        functions_without.append(entry)
                elif isinstance(node, ast.ClassDef):
                    docstring = ast.get_docstring(node)
                    entry = {"name": node.name, "line": node.lineno}
                    if docstring:
                        classes_with.append(entry)
                    else:
                        classes_without.append(entry)

            # Check module-level docstring
            module_docstring = ast.get_docstring(tree)

            total_items = len(functions_with) + len(functions_without) + len(classes_with) + len(classes_without)
            documented_items = len(functions_with) + len(classes_with) + (1 if module_docstring else 0)
            total_with_module = total_items + 1  # +1 for module itself
            coverage = round((documented_items / total_with_module * 100) if total_with_module > 0 else 0, 1)

            return {
                "agent": self.name,
                "command": "docstrings",
                "status": "success",
                "module": module_path.strip(),
                "has_module_docstring": bool(module_docstring),
                "functions": {
                    "with_docstring": functions_with,
                    "without_docstring": functions_without,
                },
                "classes": {
                    "with_docstring": classes_with,
                    "without_docstring": classes_without,
                },
                "coverage_percent": coverage,
                "message": f"Docstring coverage for {module_path.strip()}: {coverage}%.",
                "timestamp": self.timestamp,
            }

        except SyntaxError as e:
            return {
                "agent": self.name,
                "command": "docstrings",
                "status": "error",
                "message": f"Syntax error parsing {module_path.strip()}: {e}",
                "timestamp": self.timestamp,
            }
        except OSError as e:
            return {
                "agent": self.name,
                "command": "docstrings",
                "status": "error",
                "message": f"Could not read module: {e}",
                "timestamp": self.timestamp,
            }

    def _structure(self, args: str) -> dict:
        """Generate project directory tree."""
        search_path = Path(args.strip()) if args.strip() else self.project_root
        skip_dirs = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache", ".eggs", "dist", "build"}

        tree_lines = []
        dir_count = 0
        file_count = 0

        def _build_tree(path: Path, prefix: str = "", is_last: bool = True):
            nonlocal dir_count, file_count

            connector = "`-- " if is_last else "|-- "
            tree_lines.append(f"{prefix}{connector}{path.name}/")

            new_prefix = prefix + ("    " if is_last else "|   ")

            try:
                entries = sorted(path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            except PermissionError:
                return

            # Filter out skipped directories
            entries = [e for e in entries if not (e.is_dir() and e.name in skip_dirs)]

            for i, entry in enumerate(entries):
                is_entry_last = (i == len(entries) - 1)
                entry_connector = "`-- " if is_entry_last else "|-- "

                if entry.is_dir():
                    dir_count += 1
                    _build_tree(entry, new_prefix, is_entry_last)
                else:
                    file_count += 1
                    try:
                        size = entry.stat().st_size
                        size_str = self._human_size(size)
                    except OSError:
                        size_str = "?"
                    tree_lines.append(f"{new_prefix}{entry_connector}{entry.name} ({size_str})")

        # Start with root
        tree_lines.append(f"{search_path.name}/")
        try:
            entries = sorted(search_path.iterdir(), key=lambda e: (not e.is_dir(), e.name.lower()))
            entries = [e for e in entries if not (e.is_dir() and e.name in skip_dirs)]

            for i, entry in enumerate(entries):
                is_entry_last = (i == len(entries) - 1)
                entry_connector = "`-- " if is_entry_last else "|-- "

                if entry.is_dir():
                    dir_count += 1
                    _build_tree(entry, "", is_entry_last)
                else:
                    file_count += 1
                    try:
                        size = entry.stat().st_size
                        size_str = self._human_size(size)
                    except OSError:
                        size_str = "?"
                    tree_lines.append(f"{entry_connector}{entry.name} ({size_str})")
        except PermissionError:
            pass

        tree_text = "\n".join(tree_lines)

        return {
            "agent": self.name,
            "command": "structure",
            "status": "success",
            "directories": dir_count,
            "files": file_count,
            "tree": tree_text,
            "message": f"Project structure: {dir_count} directories, {file_count} files.",
            "timestamp": self.timestamp,
        }

    @staticmethod
    def _human_size(size_bytes: int) -> str:
        """Convert bytes to human-readable size string."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size_bytes < 1024:
                return f"{size_bytes:.1f} {unit}" if unit != "B" else f"{size_bytes} B"
            size_bytes /= 1024
        return f"{size_bytes:.1f} TB"


def ask_agent(query: str) -> str:
    """Entry point for the Documentation Agent.

    Args:
        query: The command string to execute.

    Returns:
        JSON string with the result of the command execution.
    """
    agent = DocumentationAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)
