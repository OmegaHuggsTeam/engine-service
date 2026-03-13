"""Transform node sandbox runner.

Reads NODE_TYPE, NODE_SUBTYPE, and NODE_CONFIG from environment variables.
Applies data transformations (map, filter, reshape, jmespath) and writes
result to /tmp/result.json.

Supported transform subtypes:
  - jmespath: apply a JMESPath expression to input data
  - map_fields: rename/remap fields in input data
  - filter_fields: keep only specified fields
  - reshape: restructure data using a template
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

import jmespath


def transform_jmespath(config: dict) -> dict:
    """Apply a JMESPath expression to input data."""
    expression = config.get("expression", "@")
    data = config.get("data", {})
    result = jmespath.search(expression, data)
    return {"transformed": result}


def transform_map_fields(config: dict) -> dict:
    """Rename/remap fields in input data."""
    field_map = config.get("field_map", {})
    data = config.get("data", {})
    transformed = {}
    for old_key, new_key in field_map.items():
        if old_key in data:
            transformed[new_key] = data[old_key]
    # Keep unmapped fields
    for key, value in data.items():
        if key not in field_map:
            transformed[key] = value
    return {"transformed": transformed}


def transform_filter_fields(config: dict) -> dict:
    """Keep only specified fields from input data."""
    fields = config.get("fields", [])
    data = config.get("data", {})
    transformed = {k: v for k, v in data.items() if k in fields}
    return {"transformed": transformed}


def transform_jq(config: dict) -> dict:
    """Apply a jq filter to input data (uses OS-level jq)."""
    jq_filter = config.get("filter", ".")
    data = config.get("data", {})
    try:
        proc = subprocess.run(
            ["jq", jq_filter],
            input=json.dumps(data),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if proc.returncode == 0:
            return {"transformed": json.loads(proc.stdout)}
        return {"transformed": None, "error": proc.stderr.strip()}
    except (subprocess.TimeoutExpired, FileNotFoundError) as exc:
        return {"transformed": None, "error": str(exc)}


TRANSFORM_MAP = {
    "jmespath": transform_jmespath,
    "map_fields": transform_map_fields,
    "filter_fields": transform_filter_fields,
    "jq": transform_jq,
}


def main() -> None:
    node_type = os.environ.get("NODE_TYPE", "transform")
    node_subtype = os.environ.get("NODE_SUBTYPE", "jmespath")
    node_config = os.environ.get("NODE_CONFIG", "{}")

    try:
        config = json.loads(node_config)
    except json.JSONDecodeError:
        config = {}

    transform_func = TRANSFORM_MAP.get(node_subtype, transform_jmespath)
    transform_result = transform_func(config)

    result = {
        "result": True,
        "type": node_type,
        "subtype": node_subtype,
        **transform_result,
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
            "type": "transform",
            "error": str(exc),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        with open("/tmp/result.json", "w") as f:
            json.dump(error, f, indent=2)
        print(json.dumps(error), file=sys.stderr)
        sys.exit(1)
