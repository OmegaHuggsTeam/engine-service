"""
Security Audit Agent - Specialist for security analysis and compliance.

Capabilities: security, auditing, vulnerability, compliance, penetration_testing

Commands:
    scan         - Scans project files for common security issues
    audit        - Checks .env for exposed secrets, validates file permissions concepts
    secrets      - Searches for potential leaked secrets in codebase
    dependencies - Checks requirements.txt/pyproject.toml for known vulnerable patterns
    report       - Generates a security summary combining all checks
"""

import json
import logging
import os
import re
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class SecurityAuditAgent:
    """Specialist agent for security analysis and compliance auditing."""

    CAPABILITIES = ["security", "auditing", "vulnerability", "compliance", "penetration_testing"]
    COMMANDS = ["scan", "audit", "secrets", "dependencies", "report"]

    # Patterns to detect potential security issues
    SECRET_PATTERNS = [
        (r'(?:password|passwd|pwd)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded password"),
        (r'(?:secret|secret_key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded secret"),
        (r'(?:api_key|apikey|api_token)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded API key"),
        (r'(?:access_key|access_token)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded access key"),
        (r'(?:private_key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded private key"),
        (r'(?:aws_secret|aws_key)\s*=\s*["\'][^"\']{8,}["\']', "Hardcoded AWS credential"),
    ]

    INJECTION_PATTERNS = [
        (r'execute\s*\(\s*["\'].*%s', "Potential SQL injection (string formatting in query)"),
        (r'execute\s*\(\s*f["\']', "Potential SQL injection (f-string in query)"),
        (r'execute\s*\(\s*["\'].*\+', "Potential SQL injection (concatenation in query)"),
        (r'\beval\s*\(', "Use of eval() - potential code injection"),
        (r'\bexec\s*\(', "Use of exec() - potential code injection"),
        (r'os\.system\s*\(', "Use of os.system() - potential command injection"),
        (r'subprocess\.call\s*\(\s*["\']', "Shell command via subprocess with string"),
        (r'__import__\s*\(', "Dynamic import - potential code injection"),
    ]

    def __init__(self):
        self.name = "SecurityAuditAgent"
        self.project_root = PROJECT_ROOT
        self.timestamp = datetime.now().isoformat()

    def execute(self, command: str) -> dict:
        """Execute a security audit command.

        Args:
            command: The command string to execute.

        Returns:
            dict with results of the command execution.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "scan":
            return self._scan(args)
        elif cmd == "audit":
            return self._audit(args)
        elif cmd == "secrets":
            return self._secrets(args)
        elif cmd == "dependencies":
            return self._dependencies(args)
        elif cmd == "report":
            return self._report(args)
        else:
            return {
                "agent": self.name,
                "status": "error",
                "message": f"Unknown command: '{cmd}'. Available commands: {', '.join(self.COMMANDS)}",
                "timestamp": self.timestamp,
            }

    def _scan(self, args: str) -> dict:
        """Scan project files for common security issues."""
        findings = []
        files_scanned = 0
        scan_path = Path(args.strip()) if args.strip() else self.project_root

        py_files = list(scan_path.rglob("*.py"))
        for py_file in py_files:
            # Skip __pycache__ and .git directories
            if "__pycache__" in str(py_file) or ".git" in str(py_file):
                continue

            files_scanned += 1
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()

                for line_num, line in enumerate(lines, 1):
                    # Check injection patterns
                    for pattern, description in self.INJECTION_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append({
                                "file": str(py_file.relative_to(self.project_root)),
                                "line": line_num,
                                "issue": description,
                                "severity": "HIGH",
                                "snippet": line.strip()[:120],
                            })

                    # Check secret patterns
                    for pattern, description in self.SECRET_PATTERNS:
                        if re.search(pattern, line, re.IGNORECASE):
                            findings.append({
                                "file": str(py_file.relative_to(self.project_root)),
                                "line": line_num,
                                "issue": description,
                                "severity": "CRITICAL",
                                "snippet": line.strip()[:80] + "...[REDACTED]",
                            })

            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read {py_file}: {e}")

        return {
            "agent": self.name,
            "command": "scan",
            "status": "success",
            "files_scanned": files_scanned,
            "findings_count": len(findings),
            "findings": findings[:50],  # Limit output
            "message": f"Scanned {files_scanned} Python files. Found {len(findings)} potential issues.",
            "timestamp": self.timestamp,
        }

    def _audit(self, args: str) -> dict:
        """Check .env files for exposed secrets and validate security posture."""
        findings = []

        # Check for .env files
        env_files = list(self.project_root.rglob(".env"))
        env_files += list(self.project_root.rglob(".env.*"))

        for env_file in env_files:
            if "__pycache__" in str(env_file) or ".git" in str(env_file):
                continue
            try:
                content = env_file.read_text(encoding="utf-8", errors="ignore")
                lines = content.splitlines()
                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" in line:
                        key, _, value = line.partition("=")
                        key = key.strip()
                        value = value.strip().strip("\"'")
                        sensitive_keywords = ["password", "secret", "key", "token", "credential", "auth"]
                        if any(kw in key.lower() for kw in sensitive_keywords) and value and value != "":
                            findings.append({
                                "file": str(env_file.relative_to(self.project_root)),
                                "line": line_num,
                                "key": key,
                                "issue": "Sensitive value found in .env file",
                                "severity": "WARNING",
                                "recommendation": "Ensure .env is in .gitignore and not committed.",
                            })
            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read {env_file}: {e}")

        # Check if .gitignore excludes .env
        gitignore_path = self.project_root / ".gitignore"
        gitignore_has_env = False
        if gitignore_path.exists():
            try:
                gitignore_content = gitignore_path.read_text(encoding="utf-8", errors="ignore")
                if ".env" in gitignore_content:
                    gitignore_has_env = True
            except OSError:
                pass

        return {
            "agent": self.name,
            "command": "audit",
            "status": "success",
            "env_files_found": len(env_files),
            "gitignore_excludes_env": gitignore_has_env,
            "findings_count": len(findings),
            "findings": findings,
            "message": f"Audited {len(env_files)} .env files. Found {len(findings)} items requiring attention.",
            "timestamp": self.timestamp,
        }

    def _secrets(self, args: str) -> dict:
        """Search for potential leaked secrets in the codebase."""
        findings = []
        files_scanned = 0
        scan_path = Path(args.strip()) if args.strip() else self.project_root

        # Scan Python files, config files, and other source files
        extensions = ["*.py", "*.js", "*.ts", "*.json", "*.yaml", "*.yml", "*.toml", "*.cfg", "*.ini"]

        for ext in extensions:
            for source_file in scan_path.rglob(ext):
                if any(skip in str(source_file) for skip in ["__pycache__", ".git", "node_modules", ".venv", "venv"]):
                    continue

                files_scanned += 1
                try:
                    content = source_file.read_text(encoding="utf-8", errors="ignore")
                    lines = content.splitlines()

                    for line_num, line in enumerate(lines, 1):
                        for pattern, description in self.SECRET_PATTERNS:
                            if re.search(pattern, line, re.IGNORECASE):
                                findings.append({
                                    "file": str(source_file.relative_to(self.project_root)),
                                    "line": line_num,
                                    "issue": description,
                                    "severity": "CRITICAL",
                                    "snippet": line.strip()[:80] + "...[REDACTED]",
                                })
                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read {source_file}: {e}")

        return {
            "agent": self.name,
            "command": "secrets",
            "status": "success",
            "files_scanned": files_scanned,
            "findings_count": len(findings),
            "findings": findings[:50],  # Limit output
            "message": f"Scanned {files_scanned} files for leaked secrets. Found {len(findings)} potential issues.",
            "timestamp": self.timestamp,
        }

    def _dependencies(self, args: str) -> dict:
        """Check requirements.txt and pyproject.toml for known vulnerable patterns."""
        findings = []

        # Known packages with historical vulnerabilities (simplified check)
        vulnerable_patterns = {
            "pyyaml": {"versions": ["<5.4"], "issue": "Arbitrary code execution via yaml.load()"},
            "django": {"versions": ["<3.2"], "issue": "Multiple security patches in older versions"},
            "flask": {"versions": ["<2.0"], "issue": "Security improvements in 2.x"},
            "requests": {"versions": ["<2.20"], "issue": "CVE-2018-18074 - Session cookie leak"},
            "urllib3": {"versions": ["<1.26"], "issue": "Multiple CVEs in older versions"},
            "pillow": {"versions": ["<9.0"], "issue": "Multiple CVEs in older versions"},
            "jinja2": {"versions": ["<3.0"], "issue": "Sandbox escape vulnerabilities"},
            "cryptography": {"versions": ["<3.3"], "issue": "Security fixes in newer versions"},
        }

        # Check requirements.txt
        req_files = ["requirements.txt", "requirements-dev.txt", "requirements-prod.txt"]
        for req_name in req_files:
            req_path = self.project_root / req_name
            if req_path.exists():
                try:
                    content = req_path.read_text(encoding="utf-8", errors="ignore")
                    for line in content.splitlines():
                        line = line.strip()
                        if not line or line.startswith("#"):
                            continue
                        pkg_name = re.split(r'[>=<!\[\]]', line)[0].strip().lower()
                        if pkg_name in vulnerable_patterns:
                            findings.append({
                                "file": req_name,
                                "package": pkg_name,
                                "declared": line.strip(),
                                "known_issue": vulnerable_patterns[pkg_name]["issue"],
                                "severity": "MEDIUM",
                                "recommendation": f"Verify {pkg_name} is up to date.",
                            })
                except (OSError, UnicodeDecodeError) as e:
                    logger.warning(f"Could not read {req_path}: {e}")

        # Check pyproject.toml
        pyproject_path = self.project_root / "pyproject.toml"
        if pyproject_path.exists():
            try:
                content = pyproject_path.read_text(encoding="utf-8", errors="ignore")
                for pkg_name in vulnerable_patterns:
                    if pkg_name in content.lower():
                        findings.append({
                            "file": "pyproject.toml",
                            "package": pkg_name,
                            "known_issue": vulnerable_patterns[pkg_name]["issue"],
                            "severity": "MEDIUM",
                            "recommendation": f"Verify {pkg_name} version in pyproject.toml is up to date.",
                        })
            except (OSError, UnicodeDecodeError) as e:
                logger.warning(f"Could not read {pyproject_path}: {e}")

        return {
            "agent": self.name,
            "command": "dependencies",
            "status": "success",
            "findings_count": len(findings),
            "findings": findings,
            "message": f"Checked dependency files. Found {len(findings)} packages to review.",
            "timestamp": self.timestamp,
        }

    def _report(self, args: str) -> dict:
        """Generate a security summary combining all checks."""
        scan_result = self._scan("")
        audit_result = self._audit("")
        secrets_result = self._secrets("")
        deps_result = self._dependencies("")

        total_findings = (
            scan_result["findings_count"]
            + audit_result["findings_count"]
            + secrets_result["findings_count"]
            + deps_result["findings_count"]
        )

        # Determine overall risk level
        if total_findings == 0:
            risk_level = "LOW"
        elif total_findings <= 5:
            risk_level = "MEDIUM"
        else:
            risk_level = "HIGH"

        return {
            "agent": self.name,
            "command": "report",
            "status": "success",
            "summary": {
                "total_findings": total_findings,
                "risk_level": risk_level,
                "scan_issues": scan_result["findings_count"],
                "audit_issues": audit_result["findings_count"],
                "secret_issues": secrets_result["findings_count"],
                "dependency_issues": deps_result["findings_count"],
            },
            "details": {
                "scan": scan_result,
                "audit": audit_result,
                "secrets": secrets_result,
                "dependencies": deps_result,
            },
            "message": f"Security report complete. Risk level: {risk_level}. Total findings: {total_findings}.",
            "timestamp": self.timestamp,
        }


def ask_agent(query: str) -> str:
    """Entry point for the Security Audit Agent.

    Args:
        query: The command string to execute.

    Returns:
        JSON string with the result of the command execution.
    """
    agent = SecurityAuditAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)
