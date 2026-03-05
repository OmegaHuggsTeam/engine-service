"""
Cloud Provisioning Agent - Specialist for cloud infrastructure management.

Capabilities: cloud, infrastructure, provisioning, terraform, kubernetes

Commands:
    provision  - Generates IaC templates (Terraform/Docker Compose) for requested services
    status     - Checks status of running containers/services via docker CLI
    teardown   - Lists teardown procedures
    cost       - Estimates resource costs
    inventory  - Lists all running infrastructure (docker ps + docker compose ls)
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class CloudProvisioningAgent:
    """Specialist agent for cloud infrastructure provisioning and management."""

    CAPABILITIES = ["cloud", "infrastructure", "provisioning", "terraform", "kubernetes"]
    COMMANDS = ["provision", "status", "teardown", "cost", "inventory"]

    def __init__(self):
        self.name = "CloudProvisioningAgent"
        self.project_root = PROJECT_ROOT
        self.timestamp = datetime.now().isoformat()

    def execute(self, command: str) -> dict:
        """Execute a cloud provisioning command.

        Args:
            command: The command string to execute. First word is the command name,
                     rest is arguments.

        Returns:
            dict with results of the command execution.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "provision":
            return self._provision(args)
        elif cmd == "status":
            return self._status(args)
        elif cmd == "teardown":
            return self._teardown(args)
        elif cmd == "cost":
            return self._cost(args)
        elif cmd == "inventory":
            return self._inventory(args)
        else:
            return {
                "agent": self.name,
                "status": "error",
                "message": f"Unknown command: '{cmd}'. Available commands: {', '.join(self.COMMANDS)}",
                "timestamp": self.timestamp,
            }

    def _provision(self, service_name: str) -> dict:
        """Generate IaC templates (Docker Compose) for the requested service."""
        service = service_name.strip().lower() if service_name else "web"

        templates = {
            "web": {
                "version": "3.8",
                "services": {
                    "web": {
                        "image": "nginx:alpine",
                        "ports": ["80:80"],
                        "restart": "unless-stopped",
                    }
                },
            },
            "database": {
                "version": "3.8",
                "services": {
                    "db": {
                        "image": "postgres:15-alpine",
                        "ports": ["5432:5432"],
                        "environment": {
                            "POSTGRES_DB": "appdb",
                            "POSTGRES_USER": "appuser",
                            "POSTGRES_PASSWORD": "${DB_PASSWORD}",
                        },
                        "volumes": ["pgdata:/var/lib/postgresql/data"],
                        "restart": "unless-stopped",
                    }
                },
                "volumes": {"pgdata": {}},
            },
            "redis": {
                "version": "3.8",
                "services": {
                    "redis": {
                        "image": "redis:7-alpine",
                        "ports": ["6379:6379"],
                        "restart": "unless-stopped",
                    }
                },
            },
            "rabbitmq": {
                "version": "3.8",
                "services": {
                    "rabbitmq": {
                        "image": "rabbitmq:3-management-alpine",
                        "ports": ["5672:5672", "15672:15672"],
                        "restart": "unless-stopped",
                    }
                },
            },
        }

        if service in templates:
            compose_content = json.dumps(templates[service], indent=2)
            return {
                "agent": self.name,
                "command": "provision",
                "status": "success",
                "service": service,
                "template_type": "docker-compose",
                "content": compose_content,
                "message": f"Generated docker-compose.yml template for '{service}' service.",
                "timestamp": self.timestamp,
            }
        else:
            return {
                "agent": self.name,
                "command": "provision",
                "status": "success",
                "service": service,
                "template_type": "docker-compose",
                "content": json.dumps(
                    {
                        "version": "3.8",
                        "services": {
                            service: {
                                "image": f"{service}:latest",
                                "ports": ["8080:8080"],
                                "restart": "unless-stopped",
                            }
                        },
                    },
                    indent=2,
                ),
                "message": f"Generated generic docker-compose.yml template for '{service}' service.",
                "timestamp": self.timestamp,
            }

    def _status(self, args: str) -> dict:
        """Check status of running containers/services via docker CLI."""
        try:
            result = subprocess.run(
                ["docker", "ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Status}}\t{{.Ports}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout.strip() if result.stdout else "No containers running."
            error = result.stderr.strip() if result.stderr else None

            return {
                "agent": self.name,
                "command": "status",
                "status": "success" if result.returncode == 0 else "error",
                "output": output,
                "error": error,
                "returncode": result.returncode,
                "timestamp": self.timestamp,
            }
        except FileNotFoundError:
            return {
                "agent": self.name,
                "command": "status",
                "status": "error",
                "message": "Docker CLI not found. Please install Docker to use this command.",
                "timestamp": self.timestamp,
            }
        except subprocess.TimeoutExpired:
            return {
                "agent": self.name,
                "command": "status",
                "status": "error",
                "message": "Docker command timed out after 30 seconds.",
                "timestamp": self.timestamp,
            }

    def _teardown(self, args: str) -> dict:
        """List teardown procedures for infrastructure."""
        procedures = [
            "1. Stop running containers: docker compose down",
            "2. Remove volumes (if needed): docker compose down -v",
            "3. Remove images: docker image prune -a",
            "4. Remove networks: docker network prune",
            "5. Clean build cache: docker builder prune",
            "6. Full system cleanup: docker system prune -a --volumes",
        ]

        return {
            "agent": self.name,
            "command": "teardown",
            "status": "success",
            "procedures": procedures,
            "warning": "Destructive operations. Review before executing.",
            "message": "Teardown procedures listed. Execute manually after review.",
            "timestamp": self.timestamp,
        }

    def _cost(self, args: str) -> dict:
        """Estimate resource costs for infrastructure."""
        estimates = {
            "web": {"monthly_cloud_estimate": "$5-20", "local_resources": "~256MB RAM, minimal CPU"},
            "database": {"monthly_cloud_estimate": "$15-50", "local_resources": "~512MB RAM, moderate CPU"},
            "redis": {"monthly_cloud_estimate": "$10-30", "local_resources": "~128MB RAM, minimal CPU"},
            "rabbitmq": {"monthly_cloud_estimate": "$15-40", "local_resources": "~256MB RAM, low CPU"},
            "full_stack": {"monthly_cloud_estimate": "$50-150", "local_resources": "~2GB RAM, moderate CPU"},
        }

        service = args.strip().lower() if args else "full_stack"
        estimate = estimates.get(service, estimates["full_stack"])

        return {
            "agent": self.name,
            "command": "cost",
            "status": "success",
            "service": service,
            "estimate": estimate,
            "disclaimer": "Estimates are approximate and vary by provider and configuration.",
            "timestamp": self.timestamp,
        }

    def _inventory(self, args: str) -> dict:
        """List all running infrastructure (docker ps + docker compose ls)."""
        results = {}

        # Run docker ps
        try:
            ps_result = subprocess.run(
                ["docker", "ps", "--format", "table {{.ID}}\t{{.Names}}\t{{.Image}}\t{{.Status}}"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            results["containers"] = {
                "output": ps_result.stdout.strip() if ps_result.stdout else "No containers running.",
                "error": ps_result.stderr.strip() if ps_result.stderr else None,
                "returncode": ps_result.returncode,
            }
        except FileNotFoundError:
            results["containers"] = {"output": None, "error": "Docker CLI not found.", "returncode": -1}
        except subprocess.TimeoutExpired:
            results["containers"] = {"output": None, "error": "Command timed out.", "returncode": -1}

        # Run docker compose ls
        try:
            compose_result = subprocess.run(
                ["docker", "compose", "ls"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            results["compose_projects"] = {
                "output": compose_result.stdout.strip() if compose_result.stdout else "No compose projects found.",
                "error": compose_result.stderr.strip() if compose_result.stderr else None,
                "returncode": compose_result.returncode,
            }
        except FileNotFoundError:
            results["compose_projects"] = {"output": None, "error": "Docker Compose CLI not found.", "returncode": -1}
        except subprocess.TimeoutExpired:
            results["compose_projects"] = {"output": None, "error": "Command timed out.", "returncode": -1}

        return {
            "agent": self.name,
            "command": "inventory",
            "status": "success",
            "inventory": results,
            "timestamp": self.timestamp,
        }


def ask_agent(query: str) -> str:
    """Entry point for the Cloud Provisioning Agent.

    Args:
        query: The command string to execute.

    Returns:
        JSON string with the result of the command execution.
    """
    agent = CloudProvisioningAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)
