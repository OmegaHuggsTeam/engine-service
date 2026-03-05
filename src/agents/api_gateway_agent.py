"""
APIGatewayAgent - Specialist for API management and security.

Capabilities: api_gateway, rate_limiting, authentication, api_versioning
Commands: routes, health, endpoints, middleware, security
"""

import json
import logging
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class APIGatewayAgent:
    """Specialist agent for API management and security tasks."""

    def __init__(self):
        self.capabilities = ["api_gateway", "rate_limiting", "authentication", "api_versioning"]
        self.commands = ["routes", "health", "endpoints", "middleware", "security"]
        self.project_root = PROJECT_ROOT

    def execute(self, command: str) -> dict:
        """Dispatch to sub-methods based on command text."""
        command_lower = command.strip().lower()

        if command_lower.startswith("routes"):
            return self._discover_routes()
        elif command_lower.startswith("health"):
            return self._check_health()
        elif command_lower.startswith("endpoints"):
            return self._list_endpoints()
        elif command_lower.startswith("middleware"):
            return self._list_middleware()
        elif command_lower.startswith("security"):
            return self._check_security()
        else:
            return {
                "status": "error",
                "message": f"Unknown command: {command}",
                "available_commands": self.commands,
            }

    def _discover_routes(self) -> dict:
        """Discovers FastAPI/Flask routes by scanning .py files for route decorator patterns."""
        route_patterns = [
            # FastAPI patterns
            re.compile(r'@(?:app|router)\.(get|post|put|delete|patch|options|head)\s*\(\s*["\']([^"\']+)["\']'),
            # Flask patterns
            re.compile(r'@(?:app|blueprint|bp)\.(route)\s*\(\s*["\']([^"\']+)["\']'),
            # APIRouter include
            re.compile(r'app\.include_router\s*\(\s*(\w+)'),
        ]

        routes = []
        files_scanned = 0

        for py_file in self.project_root.rglob("*.py"):
            parts = py_file.parts
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
                continue

            files_scanned += 1
            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(self.project_root))

                for pattern in route_patterns[:2]:
                    matches = pattern.findall(content)
                    for match in matches:
                        method = match[0].upper()
                        path = match[1]
                        routes.append({
                            "file": rel_path,
                            "method": method if method != "ROUTE" else "GET",
                            "path": path,
                        })

                # Check for router includes
                router_matches = route_patterns[2].findall(content)
                for router_name in router_matches:
                    routes.append({
                        "file": rel_path,
                        "method": "INCLUDE",
                        "path": f"<router: {router_name}>",
                    })

            except Exception as e:
                logger.warning(f"Error reading {py_file}: {e}")

        return {
            "status": "success",
            "command": "routes",
            "files_scanned": files_scanned,
            "total_routes": len(routes),
            "routes": routes,
            "timestamp": datetime.now().isoformat(),
        }

    def _check_health(self) -> dict:
        """Checks if webhook_listener is running on localhost:8765."""
        health_status = {}

        # Check webhook listener
        try:
            req = urllib.request.Request("http://localhost:8765", method="GET")
            with urllib.request.urlopen(req, timeout=3) as response:
                health_status["webhook_listener"] = {
                    "status": "running",
                    "http_code": response.status,
                    "url": "http://localhost:8765",
                }
        except urllib.error.URLError as e:
            health_status["webhook_listener"] = {
                "status": "not_reachable",
                "url": "http://localhost:8765",
                "error": str(e.reason),
            }
        except Exception as e:
            health_status["webhook_listener"] = {
                "status": "error",
                "url": "http://localhost:8765",
                "error": str(e),
            }

        # Also check common API ports
        common_ports = [
            ("localhost:8000", "FastAPI/Uvicorn"),
            ("localhost:5000", "Flask"),
            ("localhost:3000", "Node/React"),
        ]

        for url, service_name in common_ports:
            try:
                req = urllib.request.Request(f"http://{url}", method="GET")
                with urllib.request.urlopen(req, timeout=2) as response:
                    health_status[service_name] = {
                        "status": "running",
                        "http_code": response.status,
                        "url": f"http://{url}",
                    }
            except Exception:
                health_status[service_name] = {
                    "status": "not_reachable",
                    "url": f"http://{url}",
                }

        return {
            "status": "success",
            "command": "health",
            "services": health_status,
            "timestamp": datetime.now().isoformat(),
        }

    def _list_endpoints(self) -> dict:
        """Lists all discovered API endpoints with HTTP methods."""
        route_data = self._discover_routes()
        routes = route_data.get("routes", [])

        # Group endpoints by path
        endpoint_map = {}
        for route in routes:
            path = route["path"]
            method = route["method"]
            if path not in endpoint_map:
                endpoint_map[path] = {
                    "path": path,
                    "methods": [],
                    "files": [],
                }
            if method not in endpoint_map[path]["methods"]:
                endpoint_map[path]["methods"].append(method)
            if route["file"] not in endpoint_map[path]["files"]:
                endpoint_map[path]["files"].append(route["file"])

        endpoints = sorted(endpoint_map.values(), key=lambda x: x["path"])

        return {
            "status": "success",
            "command": "endpoints",
            "total_endpoints": len(endpoints),
            "endpoints": endpoints,
            "timestamp": datetime.now().isoformat(),
        }

    def _list_middleware(self) -> dict:
        """Lists middleware patterns found in codebase (CORS, auth, logging)."""
        middleware_patterns = {
            "CORS": [
                re.compile(r'CORSMiddleware', re.IGNORECASE),
                re.compile(r'cors\s*=', re.IGNORECASE),
                re.compile(r'Access-Control-Allow', re.IGNORECASE),
            ],
            "Authentication": [
                re.compile(r'auth(?:entication)?_middleware', re.IGNORECASE),
                re.compile(r'Bearer\s+', re.IGNORECASE),
                re.compile(r'JWT|json.?web.?token', re.IGNORECASE),
                re.compile(r'OAuth', re.IGNORECASE),
                re.compile(r'api[_-]?key', re.IGNORECASE),
            ],
            "Logging": [
                re.compile(r'logging\.middleware', re.IGNORECASE),
                re.compile(r'request.?log', re.IGNORECASE),
                re.compile(r'access.?log', re.IGNORECASE),
            ],
            "Rate Limiting": [
                re.compile(r'rate.?limit', re.IGNORECASE),
                re.compile(r'throttl', re.IGNORECASE),
                re.compile(r'SlowAPI|Limiter', re.IGNORECASE),
            ],
            "Session": [
                re.compile(r'session.?middleware', re.IGNORECASE),
                re.compile(r'SessionMiddleware', re.IGNORECASE),
            ],
            "Compression": [
                re.compile(r'GZipMiddleware', re.IGNORECASE),
                re.compile(r'compress', re.IGNORECASE),
            ],
        }

        found_middleware = {}

        for py_file in self.project_root.rglob("*.py"):
            parts = py_file.parts
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(self.project_root))

                for mw_type, patterns in middleware_patterns.items():
                    for pattern in patterns:
                        matches = pattern.findall(content)
                        if matches:
                            if mw_type not in found_middleware:
                                found_middleware[mw_type] = []
                            found_middleware[mw_type].append({
                                "file": rel_path,
                                "matches": len(matches),
                                "pattern": pattern.pattern,
                            })
                            break  # One match per type per file is enough

            except Exception as e:
                logger.warning(f"Error reading {py_file}: {e}")

        return {
            "status": "success",
            "command": "middleware",
            "middleware_types_found": list(found_middleware.keys()),
            "details": found_middleware,
            "timestamp": datetime.now().isoformat(),
        }

    def _check_security(self) -> dict:
        """Checks API files for security best practices."""
        checks = {
            "cors_configured": False,
            "auth_headers_present": False,
            "rate_limiting_present": False,
            "https_enforced": False,
            "input_validation": False,
            "error_handling": False,
        }
        findings = []

        security_patterns = {
            "cors_configured": re.compile(r'CORSMiddleware|Access-Control-Allow-Origin', re.IGNORECASE),
            "auth_headers_present": re.compile(r'Authorization|Bearer|api[_-]?key|x-api-key', re.IGNORECASE),
            "rate_limiting_present": re.compile(r'rate.?limit|throttl|SlowAPI|Limiter', re.IGNORECASE),
            "https_enforced": re.compile(r'HTTPSRedirectMiddleware|ssl|https://', re.IGNORECASE),
            "input_validation": re.compile(r'pydantic|BaseModel|validator|Schema|validate', re.IGNORECASE),
            "error_handling": re.compile(r'exception_handler|HTTPException|try\s*:', re.IGNORECASE),
        }

        # Patterns that indicate security issues
        issue_patterns = {
            "hardcoded_secret": re.compile(r'(?:secret|password|api_key|token)\s*=\s*["\'][^"\']{8,}["\']', re.IGNORECASE),
            "debug_mode": re.compile(r'debug\s*=\s*True', re.IGNORECASE),
            "wildcard_cors": re.compile(r'allow_origins\s*=\s*\[\s*["\']\*["\']\s*\]', re.IGNORECASE),
            "no_auth_route": re.compile(r'@app\.(get|post|put|delete)\s*\([^)]*\)\s*\n(?:async\s+)?def\s+\w+\s*\(\s*\)', re.IGNORECASE),
        }

        for py_file in self.project_root.rglob("*.py"):
            parts = py_file.parts
            if any(p.startswith(".") or p in ("node_modules", "__pycache__", ".venv", "venv") for p in parts):
                continue

            try:
                content = py_file.read_text(encoding="utf-8", errors="ignore")
                rel_path = str(py_file.relative_to(self.project_root))

                # Check for good practices
                for check_name, pattern in security_patterns.items():
                    if pattern.search(content):
                        checks[check_name] = True

                # Check for security issues
                for issue_name, pattern in issue_patterns.items():
                    matches = pattern.findall(content)
                    if matches:
                        findings.append({
                            "file": rel_path,
                            "issue": issue_name,
                            "severity": "high" if issue_name == "hardcoded_secret" else "medium",
                            "occurrences": len(matches) if isinstance(matches[0], str) else len(matches),
                        })

            except Exception as e:
                logger.warning(f"Error reading {py_file}: {e}")

        # Calculate score
        passed = sum(1 for v in checks.values() if v)
        total = len(checks)
        score = round(passed / total * 100) if total > 0 else 0

        return {
            "status": "success",
            "command": "security",
            "security_score": f"{score}%",
            "checks": checks,
            "issues_found": len(findings),
            "findings": findings,
            "recommendations": [
                rec for rec in [
                    "Configure CORS properly" if not checks["cors_configured"] else None,
                    "Add authentication headers to routes" if not checks["auth_headers_present"] else None,
                    "Implement rate limiting" if not checks["rate_limiting_present"] else None,
                    "Enforce HTTPS" if not checks["https_enforced"] else None,
                    "Add input validation with Pydantic" if not checks["input_validation"] else None,
                    "Add proper error handling" if not checks["error_handling"] else None,
                ] if rec is not None
            ],
            "timestamp": datetime.now().isoformat(),
        }


def ask_agent(query: str) -> str:
    """Entry point for the APIGatewayAgent. Creates instance, executes query, returns JSON."""
    agent = APIGatewayAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "routes"
    print(ask_agent(query))
