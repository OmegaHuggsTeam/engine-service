"""Condition node sandbox runner.

Reads NODE_TYPE, NODE_SUBTYPE, and NODE_CONFIG from environment variables.
Evaluates the condition expression and writes a boolean result to /tmp/result.json.

Supported operators in NODE_CONFIG:
  {"field": "score", "operator": "gte", "value": 50, "context": {"score": 75}}
  {"expression": "true"}
"""

import json
import operator
import os
import sys
from datetime import datetime, timezone

OPERATORS = {
    "eq": operator.eq,
    "ne": operator.ne,
    "gt": operator.gt,
    "gte": operator.ge,
    "lt": operator.lt,
    "lte": operator.le,
    "contains": lambda a, b: b in a if isinstance(a, (str, list)) else False,
}


def evaluate_condition(config: dict) -> bool:
    """Evaluate a condition from the config dict."""
    # Simple expression mode
    if "expression" in config:
        return str(config["expression"]).lower() in ("true", "1", "yes")

    # Field-operator-value mode
    field = config.get("field")
    op_name = config.get("operator", "eq")
    expected = config.get("value")
    context = config.get("context", {})

    if field is None or expected is None:
        return False

    actual = context.get(field)
    if actual is None:
        return False

    op_func = OPERATORS.get(op_name, operator.eq)
    try:
        return bool(op_func(actual, expected))
    except (TypeError, ValueError):
        return False


def main() -> None:
    node_type = os.environ.get("NODE_TYPE", "condition")
    node_subtype = os.environ.get("NODE_SUBTYPE", "")
    node_config = os.environ.get("NODE_CONFIG", "{}")

    try:
        config = json.loads(node_config)
    except json.JSONDecodeError:
        config = {}

    condition_result = evaluate_condition(config)

    result = {
        "result": condition_result,
        "type": node_type,
        "subtype": node_subtype,
        "evaluated": node_config,
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
            "type": "condition",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open("/tmp/result.json", "w") as f:
            json.dump(error, f, indent=2)
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
