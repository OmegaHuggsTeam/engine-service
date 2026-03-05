"""
Data Engineering Agent - Specialist for ETL and data pipelines.

Capabilities: data_engineering, etl, data_pipeline_advanced, spark, airflow

Commands:
    sources   - Discovers data files in data/ directory with sizes and line counts
    transform - Describes available transformations
    validate  - Validates JSON/CSV files for basic integrity
    schema    - Infers schema from a JSON file
    pipeline  - Shows status of mcp-engine-service pipeline
"""

import csv
import io
import json
import logging
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent.parent

logger = logging.getLogger(__name__)


class DataEngineeringAgent:
    """Specialist agent for ETL and data pipeline management."""

    CAPABILITIES = ["data_engineering", "etl", "data_pipeline_advanced", "spark", "airflow"]
    COMMANDS = ["sources", "transform", "validate", "schema", "pipeline"]

    def __init__(self):
        self.name = "DataEngineeringAgent"
        self.project_root = PROJECT_ROOT
        self.data_dir = PROJECT_ROOT / "data"
        self.timestamp = datetime.now().isoformat()

    def execute(self, command: str) -> dict:
        """Execute a data engineering command.

        Args:
            command: The command string to execute. First word is the command name,
                     rest is arguments.

        Returns:
            dict with results of the command execution.
        """
        parts = command.strip().split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        if cmd == "sources":
            return self._sources(args)
        elif cmd == "transform":
            return self._transform(args)
        elif cmd == "validate":
            return self._validate(args)
        elif cmd == "schema":
            return self._schema(args)
        elif cmd == "pipeline":
            return self._pipeline(args)
        else:
            return {
                "agent": self.name,
                "status": "error",
                "message": f"Unknown command: '{cmd}'. Available commands: {', '.join(self.COMMANDS)}",
                "timestamp": self.timestamp,
            }

    def _sources(self, args: str) -> dict:
        """Discover data files in data/ directory with sizes and line counts."""
        search_path = Path(args.strip()) if args.strip() else self.data_dir
        data_extensions = {".csv", ".json", ".txt", ".md", ".tsv", ".xml", ".yaml", ".yml"}
        data_files = []

        if not search_path.exists():
            return {
                "agent": self.name,
                "command": "sources",
                "status": "warning",
                "message": f"Data directory not found: {search_path}",
                "data_files": [],
                "timestamp": self.timestamp,
            }

        for data_file in search_path.rglob("*"):
            if data_file.is_file() and data_file.suffix.lower() in data_extensions:
                if any(skip in str(data_file) for skip in ["__pycache__", ".git"]):
                    continue
                try:
                    stat = data_file.stat()
                    # Count lines
                    line_count = 0
                    try:
                        content = data_file.read_text(encoding="utf-8", errors="ignore")
                        line_count = len(content.splitlines())
                    except OSError:
                        pass

                    data_files.append({
                        "path": str(data_file.relative_to(self.project_root)),
                        "name": data_file.name,
                        "extension": data_file.suffix,
                        "size_bytes": stat.st_size,
                        "size_human": self._human_size(stat.st_size),
                        "line_count": line_count,
                        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    })
                except OSError as e:
                    logger.warning(f"Could not stat {data_file}: {e}")

        data_files.sort(key=lambda x: x["path"])

        # Summary by extension
        ext_summary = {}
        for f in data_files:
            ext = f["extension"]
            if ext not in ext_summary:
                ext_summary[ext] = {"count": 0, "total_size": 0, "total_lines": 0}
            ext_summary[ext]["count"] += 1
            ext_summary[ext]["total_size"] += f["size_bytes"]
            ext_summary[ext]["total_lines"] += f["line_count"]

        return {
            "agent": self.name,
            "command": "sources",
            "status": "success",
            "total_files": len(data_files),
            "files": data_files,
            "summary_by_extension": ext_summary,
            "message": f"Found {len(data_files)} data files in {search_path}.",
            "timestamp": self.timestamp,
        }

    def _transform(self, args: str) -> dict:
        """Describe available transformations."""
        transformations = {
            "chunk": {
                "description": "Split large files into smaller chunks for processing.",
                "parameters": ["chunk_size", "overlap", "format"],
                "supported_inputs": [".txt", ".md", ".json", ".csv"],
                "example": "transform chunk --size 1000 --overlap 200 input.txt",
            },
            "clean": {
                "description": "Clean and normalize text data. Removes extra whitespace, special characters, and normalizes encoding.",
                "parameters": ["remove_html", "normalize_unicode", "lowercase"],
                "supported_inputs": [".txt", ".md", ".csv"],
                "example": "transform clean --normalize-unicode input.txt",
            },
            "normalize": {
                "description": "Normalize data structures. Flatten nested JSON, standardize column names in CSV.",
                "parameters": ["flatten_depth", "rename_columns", "fill_missing"],
                "supported_inputs": [".json", ".csv"],
                "example": "transform normalize --flatten input.json",
            },
            "deduplicate": {
                "description": "Remove duplicate records from data files.",
                "parameters": ["key_columns", "similarity_threshold"],
                "supported_inputs": [".csv", ".json"],
                "example": "transform deduplicate --key id input.csv",
            },
            "convert": {
                "description": "Convert between data formats (JSON to CSV, CSV to JSON, etc.).",
                "parameters": ["output_format", "delimiter"],
                "supported_inputs": [".json", ".csv", ".tsv"],
                "example": "transform convert --to csv input.json",
            },
        }

        transform_name = args.strip().lower() if args.strip() else None

        if transform_name and transform_name in transformations:
            return {
                "agent": self.name,
                "command": "transform",
                "status": "success",
                "transformation": transform_name,
                "details": transformations[transform_name],
                "message": f"Details for '{transform_name}' transformation.",
                "timestamp": self.timestamp,
            }

        return {
            "agent": self.name,
            "command": "transform",
            "status": "success",
            "available_transformations": transformations,
            "message": f"Available transformations: {', '.join(transformations.keys())}. Use 'transform <name>' for details.",
            "timestamp": self.timestamp,
        }

    def _validate(self, file_path: str) -> dict:
        """Validate JSON/CSV files for basic integrity."""
        if not file_path.strip():
            return {
                "agent": self.name,
                "command": "validate",
                "status": "error",
                "message": "Please provide a file path. Usage: validate <path/to/file>",
                "timestamp": self.timestamp,
            }

        target = self.project_root / file_path.strip()
        if not target.exists():
            return {
                "agent": self.name,
                "command": "validate",
                "status": "error",
                "message": f"File not found: {file_path.strip()}",
                "timestamp": self.timestamp,
            }

        ext = target.suffix.lower()

        if ext == ".json":
            return self._validate_json(target, file_path.strip())
        elif ext == ".csv":
            return self._validate_csv(target, file_path.strip())
        else:
            return {
                "agent": self.name,
                "command": "validate",
                "status": "warning",
                "message": f"Validation not supported for '{ext}' files. Supported: .json, .csv",
                "timestamp": self.timestamp,
            }

    def _validate_json(self, file_path: Path, rel_path: str) -> dict:
        """Validate a JSON file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(content)

            # Gather info about the JSON structure
            info = {
                "type": type(data).__name__,
                "size_bytes": file_path.stat().st_size,
            }

            if isinstance(data, list):
                info["record_count"] = len(data)
                if data and isinstance(data[0], dict):
                    info["sample_keys"] = list(data[0].keys())[:20]
            elif isinstance(data, dict):
                info["top_level_keys"] = list(data.keys())[:20]

            return {
                "agent": self.name,
                "command": "validate",
                "status": "success",
                "file": rel_path,
                "format": "json",
                "valid": True,
                "info": info,
                "message": f"JSON file '{rel_path}' is valid.",
                "timestamp": self.timestamp,
            }

        except json.JSONDecodeError as e:
            return {
                "agent": self.name,
                "command": "validate",
                "status": "success",
                "file": rel_path,
                "format": "json",
                "valid": False,
                "error": str(e),
                "error_line": e.lineno,
                "error_col": e.colno,
                "message": f"JSON file '{rel_path}' is INVALID: {e.msg} at line {e.lineno}, col {e.colno}.",
                "timestamp": self.timestamp,
            }
        except OSError as e:
            return {
                "agent": self.name,
                "command": "validate",
                "status": "error",
                "file": rel_path,
                "message": f"Could not read file: {e}",
                "timestamp": self.timestamp,
            }

    def _validate_csv(self, file_path: Path, rel_path: str) -> dict:
        """Validate a CSV file."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            reader = csv.reader(io.StringIO(content))

            rows = list(reader)
            if not rows:
                return {
                    "agent": self.name,
                    "command": "validate",
                    "status": "success",
                    "file": rel_path,
                    "format": "csv",
                    "valid": True,
                    "info": {"row_count": 0, "message": "File is empty."},
                    "message": f"CSV file '{rel_path}' is valid but empty.",
                    "timestamp": self.timestamp,
                }

            header = rows[0]
            col_count = len(header)
            inconsistent_rows = []

            for i, row in enumerate(rows[1:], start=2):
                if len(row) != col_count:
                    inconsistent_rows.append({
                        "row": i,
                        "expected_cols": col_count,
                        "actual_cols": len(row),
                    })

            valid = len(inconsistent_rows) == 0

            return {
                "agent": self.name,
                "command": "validate",
                "status": "success",
                "file": rel_path,
                "format": "csv",
                "valid": valid,
                "info": {
                    "header": header[:20],
                    "column_count": col_count,
                    "row_count": len(rows) - 1,
                    "inconsistent_rows": inconsistent_rows[:20],
                },
                "message": f"CSV file '{rel_path}' {'is valid' if valid else 'has inconsistencies'}. {len(rows)-1} data rows, {col_count} columns.",
                "timestamp": self.timestamp,
            }

        except csv.Error as e:
            return {
                "agent": self.name,
                "command": "validate",
                "status": "success",
                "file": rel_path,
                "format": "csv",
                "valid": False,
                "error": str(e),
                "message": f"CSV file '{rel_path}' is INVALID: {e}",
                "timestamp": self.timestamp,
            }
        except OSError as e:
            return {
                "agent": self.name,
                "command": "validate",
                "status": "error",
                "file": rel_path,
                "message": f"Could not read file: {e}",
                "timestamp": self.timestamp,
            }

    def _schema(self, file_path: str) -> dict:
        """Infer schema from a JSON file by reading the first object."""
        if not file_path.strip():
            return {
                "agent": self.name,
                "command": "schema",
                "status": "error",
                "message": "Please provide a JSON file path. Usage: schema <path/to/file.json>",
                "timestamp": self.timestamp,
            }

        target = self.project_root / file_path.strip()
        if not target.exists():
            return {
                "agent": self.name,
                "command": "schema",
                "status": "error",
                "message": f"File not found: {file_path.strip()}",
                "timestamp": self.timestamp,
            }

        try:
            content = target.read_text(encoding="utf-8", errors="ignore")
            data = json.loads(content)

            schema = {}

            def _infer_type(value):
                """Infer the type of a JSON value."""
                if value is None:
                    return "null"
                elif isinstance(value, bool):
                    return "boolean"
                elif isinstance(value, int):
                    return "integer"
                elif isinstance(value, float):
                    return "float"
                elif isinstance(value, str):
                    return "string"
                elif isinstance(value, list):
                    if value:
                        inner_types = list(set(_infer_type(v) for v in value[:5]))
                        return f"array<{','.join(inner_types)}>"
                    return "array<empty>"
                elif isinstance(value, dict):
                    return "object"
                return type(value).__name__

            # Get schema from first object
            sample = None
            if isinstance(data, list) and data:
                sample = data[0]
            elif isinstance(data, dict):
                sample = data

            if sample and isinstance(sample, dict):
                for key, value in sample.items():
                    schema[key] = {
                        "type": _infer_type(value),
                        "nullable": value is None,
                        "sample": str(value)[:100] if value is not None else None,
                    }
            else:
                schema = {"_root": {"type": _infer_type(data), "sample": str(data)[:200]}}

            return {
                "agent": self.name,
                "command": "schema",
                "status": "success",
                "file": file_path.strip(),
                "schema": schema,
                "field_count": len(schema),
                "message": f"Inferred schema with {len(schema)} fields from '{file_path.strip()}'.",
                "timestamp": self.timestamp,
            }

        except json.JSONDecodeError as e:
            return {
                "agent": self.name,
                "command": "schema",
                "status": "error",
                "message": f"Invalid JSON in {file_path.strip()}: {e}",
                "timestamp": self.timestamp,
            }
        except OSError as e:
            return {
                "agent": self.name,
                "command": "schema",
                "status": "error",
                "message": f"Could not read file: {e}",
                "timestamp": self.timestamp,
            }

    def _pipeline(self, args: str) -> dict:
        """Show status of the mcp-engine-service pipeline."""
        pipeline_dirs = {
            "raw": self.data_dir / "raw",
            "processed": self.data_dir / "processed",
            "chunks": self.data_dir / "chunks",
        }

        status = {}
        for stage, stage_dir in pipeline_dirs.items():
            if stage_dir.exists():
                files = [f for f in stage_dir.rglob("*") if f.is_file()]
                total_size = sum(f.stat().st_size for f in files if f.exists())
                status[stage] = {
                    "exists": True,
                    "file_count": len(files),
                    "total_size_bytes": total_size,
                    "total_size_human": self._human_size(total_size),
                    "files": [
                        {
                            "name": f.name,
                            "size": self._human_size(f.stat().st_size),
                            "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        }
                        for f in sorted(files, key=lambda x: x.name)[:20]
                    ],
                }
            else:
                status[stage] = {
                    "exists": False,
                    "file_count": 0,
                    "total_size_bytes": 0,
                    "total_size_human": "0 B",
                    "files": [],
                }

        # Determine pipeline health
        all_exist = all(s["exists"] for s in status.values())
        has_data = any(s["file_count"] > 0 for s in status.values())

        if all_exist and has_data:
            health = "HEALTHY"
        elif all_exist:
            health = "IDLE"
        else:
            health = "INCOMPLETE"

        return {
            "agent": self.name,
            "command": "pipeline",
            "status": "success",
            "pipeline_health": health,
            "stages": status,
            "message": "Pipeline status: {}. Stages: {}.".format(
                health,
                ", ".join("{}({} files)".format(k, v["file_count"]) for k, v in status.items()),
            ),
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
    """Entry point for the Data Engineering Agent.

    Args:
        query: The command string to execute.

    Returns:
        JSON string with the result of the command execution.
    """
    agent = DataEngineeringAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2)
