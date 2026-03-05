"""
FrontendAgent - Specialist for UI/UX and frontend development.

Capabilities: frontend, ui_design, react, css, accessibility
Commands: components, themes, accessibility, assets, mockup
"""

import json
import logging
import os
import re
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class FrontendAgent:
    """Specialist agent for UI/UX and frontend development tasks."""

    def __init__(self):
        self.capabilities = ["frontend", "ui_design", "react", "css", "accessibility"]
        self.commands = ["components", "themes", "accessibility", "assets", "mockup"]
        self.project_root = PROJECT_ROOT

    def execute(self, command: str) -> dict:
        """Dispatch to sub-methods based on command text."""
        command_lower = command.strip().lower()

        if command_lower.startswith("components"):
            return self._list_components()
        elif command_lower.startswith("themes"):
            return self._generate_themes()
        elif command_lower.startswith("accessibility"):
            return self._check_accessibility()
        elif command_lower.startswith("assets"):
            return self._inventory_assets()
        elif command_lower.startswith("mockup"):
            description = command_lower.replace("mockup", "", 1).strip()
            return self._generate_mockup(description)
        else:
            return {
                "status": "error",
                "message": f"Unknown command: {command}",
                "available_commands": self.commands,
            }

    def _list_components(self) -> dict:
        """Lists all .html, .css, .js, .tsx files in project."""
        extensions = [".html", ".css", ".js", ".tsx"]
        found_files = {}

        for ext in extensions:
            files = []
            for f in self.project_root.rglob(f"*{ext}"):
                # Skip node_modules and hidden directories
                parts = f.parts
                if any(p.startswith(".") or p == "node_modules" for p in parts):
                    continue
                files.append(str(f.relative_to(self.project_root)))
            found_files[ext] = sorted(files)

        total = sum(len(v) for v in found_files.values())
        return {
            "status": "success",
            "command": "components",
            "total_files": total,
            "files_by_type": found_files,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_themes(self) -> dict:
        """Generates CSS theme variables for dark/light themes."""
        light_theme = {
            "--color-primary": "#3b82f6",
            "--color-primary-hover": "#2563eb",
            "--color-secondary": "#64748b",
            "--color-background": "#ffffff",
            "--color-surface": "#f8fafc",
            "--color-text": "#0f172a",
            "--color-text-secondary": "#475569",
            "--color-border": "#e2e8f0",
            "--color-error": "#ef4444",
            "--color-success": "#22c55e",
            "--color-warning": "#f59e0b",
            "--font-family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            "--font-size-base": "16px",
            "--font-size-sm": "14px",
            "--font-size-lg": "18px",
            "--border-radius": "8px",
            "--shadow-sm": "0 1px 2px rgba(0,0,0,0.05)",
            "--shadow-md": "0 4px 6px rgba(0,0,0,0.1)",
        }

        dark_theme = {
            "--color-primary": "#60a5fa",
            "--color-primary-hover": "#93bbfd",
            "--color-secondary": "#94a3b8",
            "--color-background": "#0f172a",
            "--color-surface": "#1e293b",
            "--color-text": "#f1f5f9",
            "--color-text-secondary": "#94a3b8",
            "--color-border": "#334155",
            "--color-error": "#f87171",
            "--color-success": "#4ade80",
            "--color-warning": "#fbbf24",
            "--font-family": "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
            "--font-size-base": "16px",
            "--font-size-sm": "14px",
            "--font-size-lg": "18px",
            "--border-radius": "8px",
            "--shadow-sm": "0 1px 2px rgba(0,0,0,0.2)",
            "--shadow-md": "0 4px 6px rgba(0,0,0,0.3)",
        }

        return {
            "status": "success",
            "command": "themes",
            "light": light_theme,
            "dark": dark_theme,
            "timestamp": datetime.now().isoformat(),
        }

    def _check_accessibility(self) -> dict:
        """Checks HTML files for basic a11y issues using regex."""
        issues = []
        html_files = list(self.project_root.rglob("*.html"))

        # Filter out hidden dirs and node_modules
        html_files = [
            f for f in html_files
            if not any(p.startswith(".") or p == "node_modules" for p in f.parts)
        ]

        for html_file in html_files:
            try:
                content = html_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(html_file.relative_to(self.project_root))

                # Check for images missing alt tags
                img_tags = re.findall(r"<img\s[^>]*?>", content, re.IGNORECASE | re.DOTALL)
                for img in img_tags:
                    if not re.search(r'\balt\s*=', img, re.IGNORECASE):
                        issues.append({
                            "file": rel_path,
                            "issue": "img tag missing alt attribute",
                            "severity": "error",
                            "snippet": img[:100],
                        })

                # Check for missing aria labels on interactive elements
                interactive_tags = re.findall(
                    r"<(button|input|select|textarea)\s[^>]*?>",
                    content, re.IGNORECASE | re.DOTALL,
                )
                for tag in interactive_tags:
                    if not re.search(r'aria-label', tag, re.IGNORECASE):
                        issues.append({
                            "file": rel_path,
                            "issue": f"Interactive element possibly missing aria-label",
                            "severity": "warning",
                            "snippet": tag[:100],
                        })

                # Check for missing lang attribute on html tag
                html_tag = re.search(r"<html\s[^>]*?>", content, re.IGNORECASE)
                if html_tag and not re.search(r'\blang\s*=', html_tag.group(), re.IGNORECASE):
                    issues.append({
                        "file": rel_path,
                        "issue": "html tag missing lang attribute",
                        "severity": "warning",
                        "snippet": html_tag.group()[:100],
                    })

                # Check for missing form labels
                input_tags = re.findall(r"<input\s[^>]*?>", content, re.IGNORECASE | re.DOTALL)
                label_fors = re.findall(r'<label\s[^>]*for\s*=\s*["\']([^"\']+)', content, re.IGNORECASE)
                for inp in input_tags:
                    id_match = re.search(r'id\s*=\s*["\']([^"\']+)', inp, re.IGNORECASE)
                    if id_match and id_match.group(1) not in label_fors:
                        issues.append({
                            "file": rel_path,
                            "issue": f"Input with id='{id_match.group(1)}' has no associated label",
                            "severity": "warning",
                            "snippet": inp[:100],
                        })

            except Exception as e:
                logger.warning(f"Error reading {html_file}: {e}")

        return {
            "status": "success",
            "command": "accessibility",
            "files_scanned": len(html_files),
            "total_issues": len(issues),
            "issues": issues,
            "timestamp": datetime.now().isoformat(),
        }

    def _inventory_assets(self) -> dict:
        """Inventories static assets (images, fonts, icons) in project."""
        asset_categories = {
            "images": [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".ico", ".bmp"],
            "fonts": [".woff", ".woff2", ".ttf", ".otf", ".eot"],
            "icons": [".ico", ".svg"],
            "videos": [".mp4", ".webm", ".avi", ".mov"],
            "audio": [".mp3", ".wav", ".ogg"],
        }

        inventory = {}
        total_size = 0

        for category, extensions in asset_categories.items():
            files = []
            for ext in extensions:
                for f in self.project_root.rglob(f"*{ext}"):
                    parts = f.parts
                    if any(p.startswith(".") or p == "node_modules" for p in parts):
                        continue
                    # Avoid duplicates (svg is in both images and icons)
                    rel = str(f.relative_to(self.project_root))
                    if rel not in [fi["path"] for fi in files]:
                        size = f.stat().st_size if f.exists() else 0
                        total_size += size
                        files.append({
                            "path": rel,
                            "size_bytes": size,
                        })
            inventory[category] = sorted(files, key=lambda x: x["path"])

        total_files = sum(len(v) for v in inventory.values())
        return {
            "status": "success",
            "command": "assets",
            "total_assets": total_files,
            "total_size_bytes": total_size,
            "inventory": inventory,
            "timestamp": datetime.now().isoformat(),
        }

    def _generate_mockup(self, description: str) -> dict:
        """Generates ASCII mockup of a simple component layout based on description."""
        description_lower = description.lower() if description else ""

        if "nav" in description_lower or "header" in description_lower:
            mockup = (
                "+----------------------------------------------------------+\n"
                "|  [Logo]    Home    About    Services    Contact    [Menu] |\n"
                "+----------------------------------------------------------+"
            )
        elif "card" in description_lower:
            mockup = (
                "+------------------------+\n"
                "|  [Image Placeholder]   |\n"
                "|                        |\n"
                "|  Title Text            |\n"
                "|  Description goes here |\n"
                "|  and wraps to next...  |\n"
                "|                        |\n"
                "|  [Button]   [Link]     |\n"
                "+------------------------+"
            )
        elif "form" in description_lower or "login" in description_lower:
            mockup = (
                "+------------------------------+\n"
                "|        Login Form             |\n"
                "|                               |\n"
                "|  Username:                    |\n"
                "|  +------------------------+   |\n"
                "|  |                        |   |\n"
                "|  +------------------------+   |\n"
                "|                               |\n"
                "|  Password:                    |\n"
                "|  +------------------------+   |\n"
                "|  |                        |   |\n"
                "|  +------------------------+   |\n"
                "|                               |\n"
                "|  [  Submit  ]  [  Cancel  ]   |\n"
                "+------------------------------+"
            )
        elif "table" in description_lower or "list" in description_lower:
            mockup = (
                "+------+----------------+----------+--------+\n"
                "| ID   | Name           | Status   | Action |\n"
                "+------+----------------+----------+--------+\n"
                "| 001  | Item One       | Active   | [Edit] |\n"
                "| 002  | Item Two       | Pending  | [Edit] |\n"
                "| 003  | Item Three     | Inactive | [Edit] |\n"
                "+------+----------------+----------+--------+\n"
                "|  < Prev  |  Page 1 of 5  |  Next >        |\n"
                "+------+----------------+----------+--------+"
            )
        elif "footer" in description_lower:
            mockup = (
                "+----------------------------------------------------------+\n"
                "|  Company Name         Links         Social    Newsletter  |\n"
                "|  123 Main St          About         [f] [t]  [Email    ] |\n"
                "|  City, State          Privacy       [i] [g]  [Subscribe] |\n"
                "|                       Terms                              |\n"
                "|  (c) 2026 Company. All rights reserved.                  |\n"
                "+----------------------------------------------------------+"
            )
        elif "sidebar" in description_lower or "menu" in description_lower:
            mockup = (
                "+------------------+-----------------------------------+\n"
                "|  [Logo]          |                                   |\n"
                "|                  |          Main Content             |\n"
                "|  > Dashboard     |                                   |\n"
                "|    Analytics     |   +---------------------------+   |\n"
                "|    Settings      |   |                           |   |\n"
                "|    Users         |   |     Content Area          |   |\n"
                "|    Reports       |   |                           |   |\n"
                "|                  |   +---------------------------+   |\n"
                "|  [Logout]        |                                   |\n"
                "+------------------+-----------------------------------+"
            )
        else:
            mockup = (
                "+----------------------------------------------------------+\n"
                "|  [Header / Navigation Bar]                               |\n"
                "+----------------------------------------------------------+\n"
                "|                                                          |\n"
                "|   +-------------------+   +-------------------+         |\n"
                "|   |   Component A     |   |   Component B     |         |\n"
                "|   |                   |   |                   |         |\n"
                "|   +-------------------+   +-------------------+         |\n"
                "|                                                          |\n"
                "|   +----------------------------------------------+      |\n"
                "|   |          Main Content Area                   |      |\n"
                "|   |                                              |      |\n"
                "|   +----------------------------------------------+      |\n"
                "|                                                          |\n"
                "+----------------------------------------------------------+\n"
                "|  [Footer]                                                |\n"
                "+----------------------------------------------------------+"
            )

        return {
            "status": "success",
            "command": "mockup",
            "description": description if description else "default layout",
            "mockup": mockup,
            "timestamp": datetime.now().isoformat(),
        }


def ask_agent(query: str) -> str:
    """Entry point for the FrontendAgent. Creates instance, executes query, returns JSON."""
    agent = FrontendAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "components"
    print(ask_agent(query))
