"""Trigger node sandbox runner.

Reads NODE_TYPE, NODE_SUBTYPE, and NODE_CONFIG from environment variables.
Evaluates the trigger condition and writes result to /tmp/result.json.
"""

import json
import os
import sys
from datetime import datetime, timezone


def main() -> None:
    node_type = os.environ.get("NODE_TYPE", "trigger")
    node_subtype = os.environ.get("NODE_SUBTYPE", "manual")
    node_config = os.environ.get("NODE_CONFIG", "{}")

    try:
        config = json.loads(node_config)
    except json.JSONDecodeError:
        config = {}

    result = {
        "result": True,
        "type": node_type,
        "subtype": node_subtype,
        "config": config,
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
            "type": "trigger",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open("/tmp/result.json", "w") as f:
            json.dump(error, f, indent=2)
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
