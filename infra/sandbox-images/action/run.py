"""Action node sandbox runner.

Reads NODE_TYPE, NODE_SUBTYPE, and NODE_CONFIG from environment variables.
Executes a CRM action (tag, score, notify, etc.) via HTTP and writes result
to /tmp/result.json.

Supported action subtypes:
  - add_tag: adds a tag to a contact
  - update_score: updates a contact's score
  - send_notification: sends a notification
  - webhook: calls an arbitrary webhook URL
"""

import json
import os
import sys
from datetime import datetime, timezone

import httpx


TIMEOUT_SECONDS = 10


def execute_action(config: dict, subtype: str) -> dict:
    """Execute the CRM action based on subtype and config."""
    crm_api_url = os.environ.get("CRM_API_URL", "")
    crm_api_token = os.environ.get("CRM_API_TOKEN", "")

    # If no CRM URL configured, run in dry-run mode
    if not crm_api_url:
        return {
            "action": "completed",
            "mode": "dry-run",
            "subtype": subtype,
            "config": config,
        }

    headers = {
        "Content-Type": "application/json",
    }
    if crm_api_token:
        headers["Authorization"] = f"Bearer {crm_api_token}"

    endpoint_map = {
        "add_tag": "/api/v1/contacts/tags",
        "update_score": "/api/v1/contacts/score",
        "send_notification": "/api/v1/notifications",
        "webhook": config.get("webhook_url", ""),
    }

    endpoint = endpoint_map.get(subtype, f"/api/v1/actions/{subtype}")

    # For webhook subtype, use the URL directly from config
    if subtype == "webhook":
        url = config.get("webhook_url", crm_api_url)
    else:
        url = f"{crm_api_url.rstrip('/')}{endpoint}"

    payload = config.get("payload", config)

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(url, json=payload, headers=headers)
            return {
                "action": "completed",
                "mode": "live",
                "subtype": subtype,
                "status_code": response.status_code,
                "response": response.text[:500],
            }
    except httpx.HTTPError as exc:
        return {
            "action": "failed",
            "mode": "live",
            "subtype": subtype,
            "error": str(exc),
        }


def main() -> None:
    node_type = os.environ.get("NODE_TYPE", "action")
    node_subtype = os.environ.get("NODE_SUBTYPE", "")
    node_config = os.environ.get("NODE_CONFIG", "{}")

    try:
        config = json.loads(node_config)
    except json.JSONDecodeError:
        config = {}

    action_result = execute_action(config, node_subtype)

    result = {
        "result": action_result.get("action") == "completed",
        "type": node_type,
        "subtype": node_subtype,
        **action_result,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with open("/tmp/result.json", "w") as f:
        json.dump(result, f, indent=2)

    print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        error = {
            "result": False,
            "type": "action",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open("/tmp/result.json", "w") as f:
            json.dump(error, f, indent=2)
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
