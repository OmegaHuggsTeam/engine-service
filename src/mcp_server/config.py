"""
MCP configuration generator — prints ready-to-paste JSON for Claude Desktop
and Cursor so they can discover this MCP server.

Usage:
    python -m src.mcp_server.config          # prints both configs
    python -c "from src.mcp_server.config import generate_claude_desktop_config; ..."
"""

import json
import os
import sys
from pathlib import Path


def _detect_project_dir() -> str:
    """Best-effort detection of the engine-service project root."""
    # Walk up from this file looking for requirements.txt
    here = Path(__file__).resolve().parent
    for ancestor in [here, here.parent, here.parent.parent, here.parent.parent.parent]:
        if (ancestor / "requirements.txt").exists():
            return str(ancestor)
    return str(here.parent.parent)


def _detect_python() -> str:
    """Return the Python interpreter path (prefer venv if active)."""
    return sys.executable


def generate_claude_desktop_config(project_dir: str | None = None) -> dict:
    """Return a dict suitable for ``claude_desktop_config.json`` ``mcpServers``."""
    project_dir = project_dir or _detect_project_dir()
    python = _detect_python()

    return {
        "mcpServers": {
            "engine-service": {
                "command": python,
                "args": ["-m", "src.mcp_server.server"],
                "cwd": project_dir,
                "env": {
                    "PYTHONPATH": project_dir,
                },
            }
        }
    }


def generate_cursor_config(project_dir: str | None = None) -> dict:
    """Return a dict suitable for ``.cursor/mcp.json``."""
    project_dir = project_dir or _detect_project_dir()
    python = _detect_python()

    return {
        "mcpServers": {
            "engine-service": {
                "command": python,
                "args": ["-m", "src.mcp_server.server"],
                "cwd": project_dir,
                "env": {
                    "PYTHONPATH": project_dir,
                },
            }
        }
    }


def print_configs() -> None:
    """Print both configs to stdout for easy copy-paste."""
    project_dir = _detect_project_dir()

    print("=" * 60)
    print("Claude Desktop  (~/.claude/claude_desktop_config.json)")
    print("=" * 60)
    print(json.dumps(generate_claude_desktop_config(project_dir), indent=2))
    print()

    print("=" * 60)
    print("Cursor  (.cursor/mcp.json)")
    print("=" * 60)
    print(json.dumps(generate_cursor_config(project_dir), indent=2))
    print()

    print("=" * 60)
    print("Claude Code  (claude mcp add)")
    print("=" * 60)
    python = _detect_python()
    print(f'claude mcp add engine-service -- {python} -m src.mcp_server.server')
    print(f'  (run from: {project_dir})')
    print()


if __name__ == "__main__":
    print_configs()
