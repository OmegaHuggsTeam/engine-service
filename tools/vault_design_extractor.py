"""Vault Design DNA Extractor — scans vault/ and generates visual identity metadata.

Reads all Markdown files in the vault/ directory tree, extracts YAML frontmatter,
builds a [[WikiLink]] connection graph, aggregates tag clouds, and writes the
result to specs/vault_dna.json.

Usage:
    python tools/vault_design_extractor.py
    python tools/vault_design_extractor.py --vault-path /custom/vault
    python tools/vault_design_extractor.py --output specs/custom_dna.json
"""

import json
import logging
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Frontmatter parser (no external YAML dependency required)
# ---------------------------------------------------------------------------

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_WIKILINK_RE = re.compile(r"\[\[([^\]|]+?)(?:\|[^\]]+?)?\]\]")
_YAML_LIST_ITEM = re.compile(r"^\s+-\s+(.+)$")


def _parse_simple_yaml(text: str) -> dict:
    """Minimal YAML frontmatter parser (flat keys, string/list values only).

    Handles:
        key: value
        key:
          - item1
          - item2
        key: 'quoted value'
    """
    result: dict = {}
    current_key: str | None = None

    for line in text.splitlines():
        list_match = _YAML_LIST_ITEM.match(line)
        if list_match and current_key is not None:
            if not isinstance(result.get(current_key), list):
                result[current_key] = []
            value = list_match.group(1).strip().strip("'\"")
            result[current_key].append(value)
            continue

        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip().strip("'\"")
            if not key:
                continue
            current_key = key
            if value:
                # Inline list: [a, b, c]
                if value.startswith("[") and value.endswith("]"):
                    items = [v.strip().strip("'\"") for v in value[1:-1].split(",")]
                    result[key] = [i for i in items if i]
                else:
                    result[key] = value
            else:
                result[key] = None

    return result


def extract_frontmatter(file_path: Path) -> dict | None:
    """Extract YAML frontmatter from a Markdown file.

    Returns parsed dict or None if no frontmatter found.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.warning("Cannot read %s: %s", file_path, exc)
        return None

    match = _FRONTMATTER_RE.match(content)
    if not match:
        return None

    return _parse_simple_yaml(match.group(1))


def extract_wikilinks(file_path: Path) -> list[str]:
    """Extract all [[WikiLink]] targets from a Markdown file."""
    try:
        content = file_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    return _WIKILINK_RE.findall(content)


# ---------------------------------------------------------------------------
# Vault scanning
# ---------------------------------------------------------------------------

def scan_vault(vault_path: Path) -> list[Path]:
    """Return all .md files under vault_path, sorted by relative path."""
    if not vault_path.is_dir():
        logger.error("Vault path does not exist: %s", vault_path)
        return []
    files = sorted(vault_path.rglob("*.md"))
    logger.info("Found %d Markdown files in %s", len(files), vault_path)
    return files


def build_tag_cloud(files: list[Path]) -> dict[str, int]:
    """Aggregate tag counts across all files with frontmatter."""
    counter: Counter = Counter()
    for f in files:
        fm = extract_frontmatter(f)
        if fm and "tags" in fm:
            tags = fm["tags"]
            if isinstance(tags, list):
                counter.update(tags)
            elif isinstance(tags, str):
                counter.update(t.strip() for t in tags.split(","))
    return dict(counter.most_common())


def build_connection_graph(files: list[Path]) -> dict[str, list[str]]:
    """Build adjacency list from [[WikiLink]] references.

    Keys are file stems (e.g. 'AgentSelector'), values are lists of
    referenced stems.
    """
    graph: dict[str, list[str]] = {}
    for f in files:
        links = extract_wikilinks(f)
        if links:
            graph[f.stem] = sorted(set(links))
    return graph


def build_categories(files: list[Path], vault_path: Path) -> dict[str, list[str]]:
    """Group files by their immediate parent directory (category)."""
    categories: dict[str, list[str]] = {}
    for f in files:
        try:
            rel = f.relative_to(vault_path)
        except ValueError:
            continue
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "root"
        categories.setdefault(category, []).append(f.stem)
    for cat in categories:
        categories[cat].sort()
    return dict(sorted(categories.items()))


def build_frontmatter_schema(files: list[Path]) -> dict[str, int]:
    """Count how many files use each frontmatter key."""
    counter: Counter = Counter()
    for f in files:
        fm = extract_frontmatter(f)
        if fm:
            counter.update(fm.keys())
    return dict(counter.most_common())


# ---------------------------------------------------------------------------
# Main generator
# ---------------------------------------------------------------------------

def generate_vault_dna(vault_path: Path, output_path: Path) -> dict:
    """Scan vault and write specs/vault_dna.json.

    Returns the generated DNA dict.
    """
    files = scan_vault(vault_path)

    fm_count = sum(1 for f in files if extract_frontmatter(f) is not None)
    tag_cloud = build_tag_cloud(files)

    dna = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "vault_path": str(vault_path),
        "stats": {
            "total_files": len(files),
            "with_frontmatter": fm_count,
            "total_tags": sum(tag_cloud.values()),
            "unique_tags": len(tag_cloud),
        },
        "tag_cloud": tag_cloud,
        "categories": build_categories(files, vault_path),
        "connection_graph": build_connection_graph(files),
        "frontmatter_schema": build_frontmatter_schema(files),
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dna, indent=2, ensure_ascii=False), encoding="utf-8")
    logger.info("Wrote vault DNA to %s", output_path)
    return dna


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    """CLI entry point."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="Vault Design DNA Extractor")
    parser.add_argument(
        "--vault-path",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "vault",
        help="Path to the vault directory (default: vault/)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "specs" / "vault_dna.json",
        help="Output JSON path (default: specs/vault_dna.json)",
    )
    args = parser.parse_args()

    dna = generate_vault_dna(args.vault_path, args.output)

    print(f"Vault DNA extracted: {dna['stats']['total_files']} files, "
          f"{dna['stats']['with_frontmatter']} with frontmatter, "
          f"{dna['stats']['unique_tags']} unique tags")
    print(f"Output: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
