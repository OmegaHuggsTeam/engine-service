"""
UseCase Indexer - Parse, indexa e sincroniza UseCase specs.

Le arquivos markdown no formato TEMPLATE.md, extrai metadata estruturada,
indexa no ChromaDB (category='usecase') e cria nos :UseCase no Neo4j
com relacionamentos para Skills, Agents e Modules.
"""

import json
import logging
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

DEFAULT_SPECS_DIR = Path(__file__).resolve().parent.parent.parent / "docs" / "specs" / "usecases"


def _extract_table_field(content: str, field: str) -> str:
    """Extrai valor de um campo em tabela markdown | Campo | Valor |."""
    pattern = re.compile(
        rf"\*\*{re.escape(field)}\*\*\s*\|\s*(.+)",
        re.IGNORECASE,
    )
    m = pattern.search(content)
    return m.group(1).strip() if m else ""


def _extract_section(content: str, header: str) -> str:
    """Extrai conteudo de uma secao ## header ate a proxima ## ou fim."""
    pattern = re.compile(
        rf"^##\s+{re.escape(header)}\s*\n(.*?)(?=^##\s|\Z)",
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(content)
    return m.group(1).strip() if m else ""


def _extract_list_items(section: str) -> list[str]:
    """Extrai items de lista markdown (- item ou 1. item)."""
    items = []
    for line in section.split("\n"):
        line = line.strip()
        if line.startswith("- ") or line.startswith("* "):
            items.append(line[2:].strip())
        elif re.match(r"^\d+\.\s", line):
            items.append(re.sub(r"^\d+\.\s", "", line).strip())
    return items


def _parse_priority(value: str) -> int:
    """Converte P0-P3 para inteiro (0=mais alto)."""
    m = re.match(r"P(\d)", value)
    return int(m.group(1)) if m else 2


def _parse_complexity(value: str) -> str:
    """Normaliza complexity para S/M/L/XL."""
    v = value.strip().upper()
    if v in ("S", "M", "L", "XL"):
        return v
    return "M"


def parse_usecase_spec(file_path: str | Path) -> dict:
    """
    Faz parse de um UseCase markdown no formato TEMPLATE.md.

    Returns:
        Dict estruturado com todos os campos do UseCase.
    """
    p = Path(file_path)
    content = p.read_text(encoding="utf-8")

    # Extract ID from title: # [UC-XXX] Nome
    title_re = re.compile(r"^#\s+\[(\w+-\w+-\d+)\]\s+(.+)", re.MULTILINE)
    m = title_re.search(content)
    uc_id = m.group(1) if m else p.stem
    uc_name = m.group(2).strip() if m else p.stem

    # Metadata table
    metadata_section = _extract_section(content, "Metadata")
    domain = _extract_table_field(metadata_section, "Domain")
    repos_str = _extract_table_field(metadata_section, "Repos")
    priority_str = _extract_table_field(metadata_section, "Priority")
    complexity_str = _extract_table_field(metadata_section, "Complexity")
    status = _extract_table_field(metadata_section, "Status") or "Spec"

    repos = [r.strip() for r in repos_str.split(",") if r.strip()]
    priority = _parse_priority(priority_str)
    complexity = _parse_complexity(complexity_str)

    # Acceptance Criteria
    ac_section = _extract_section(content, "Acceptance Criteria")
    acceptance_criteria = _extract_list_items(ac_section)
    if not acceptance_criteria and ac_section:
        # Try GIVEN/WHEN/THEN blocks
        blocks = re.split(r"\n\d+\.\s", ac_section)
        acceptance_criteria = [b.strip() for b in blocks if b.strip()]

    # Required Skills
    skills_section = _extract_section(content, "Required Skills")
    skills = []
    skill_re = re.compile(r"\*\*(\w+)\*\*\s*-\s*(existente|nova|new|existing)", re.IGNORECASE)
    for sm in skill_re.finditer(skills_section):
        skills.append({
            "id": sm.group(1).lower(),
            "name": sm.group(1),
            "status": "existing" if "exist" in sm.group(2).lower() else "new",
        })

    # Required Agent Capabilities
    agents_section = _extract_section(content, "Required Agent Capabilities")
    agents = []
    agent_re = re.compile(r"`(\w+_agent)`")
    for am in agent_re.finditer(agents_section):
        agents.append(am.group(1))

    # RAG Chunk References
    rag_section = _extract_section(content, "RAG Chunk References")
    rag_refs = _extract_list_items(rag_section)

    # Related Use Cases
    related_section = _extract_section(content, "Related Use Cases")
    depends_on = []
    enables = []
    dep_re = re.compile(r"Depends on.*?(UC-\w+-\d+)", re.IGNORECASE)
    for dm in dep_re.finditer(related_section):
        depends_on.append(dm.group(1))
    en_re = re.compile(r"Enables.*?(UC-\w+-\d+)", re.IGNORECASE)
    for em in en_re.finditer(related_section):
        enables.append(em.group(1))

    # Domain Context
    domain_context = _extract_section(content, "Domain Context")

    # Implementation Notes
    impl_notes = _extract_section(content, "Implementation Notes")

    return {
        "id": uc_id,
        "name": uc_name,
        "domain": domain.lower().strip(),
        "repos": repos,
        "priority": priority,
        "complexity": complexity,
        "status": status.strip(),
        "acceptance_criteria": acceptance_criteria,
        "acceptance_criteria_text": "\n".join(acceptance_criteria),
        "required_skills": skills,
        "required_agents": agents,
        "rag_references": rag_refs,
        "depends_on": depends_on,
        "enables": enables,
        "domain_context": domain_context,
        "implementation_notes": impl_notes,
        "source_file": str(p),
    }


def index_usecase_to_chromadb(spec: dict) -> int:
    """
    Cria chunks do UseCase spec e salva no ChromaDB.

    Cada secao do spec vira um chunk separado para busca precisa.
    category='usecase', agent_specialty baseado no domain.

    Returns:
        Numero de chunks salvos.
    """
    from src.utils.vector_db import add_chunks

    domain = spec["domain"]
    specialty_map = {
        "campaigns": "crm_backend",
        "journeys": "crm_backend",
        "segments": "crm_data",
        "contacts": "crm_backend",
        "tracker": "crm_integration",
        "integrations": "crm_integration",
        "analytics": "crm_data",
        "sms_delivery": "sendspeed_sms",
        "campaign_management": "sendspeed_admin",
        "billing": "sendspeed_admin",
        "anti_fraud": "sendspeed_admin",
        "administration": "sendspeed_admin",
        "api_platform": "sendspeed_api",
    }
    specialty = specialty_map.get(domain, "crm_backend")

    chunks = []
    base_meta = {
        "category": "usecase",
        "agent_specialty": specialty,
        "domain": domain,
        "usecase_id": spec["id"],
        "priority": str(spec["priority"]),
        "complexity": spec["complexity"],
        "status": spec["status"],
    }

    # Chunk 1: Overview (metadata + domain context)
    overview = (
        f"UseCase {spec['id']}: {spec['name']}\n"
        f"Domain: {domain}\n"
        f"Priority: P{spec['priority']} | Complexity: {spec['complexity']}\n"
        f"Repos: {', '.join(spec['repos'])}\n\n"
        f"{spec['domain_context'][:600]}"
    )
    chunks.append({
        **base_meta,
        "content": overview,
        "source_file": f"usecase/{spec['id']}/overview",
        "chunk_index": 0,
        "char_count": len(overview),
    })

    # Chunk 2: Acceptance Criteria (ancora de precisao)
    if spec["acceptance_criteria"]:
        ac_text = f"UseCase {spec['id']} - Acceptance Criteria:\n"
        ac_text += "\n".join(f"- {ac}" for ac in spec["acceptance_criteria"])
        chunks.append({
            **base_meta,
            "content": ac_text,
            "source_file": f"usecase/{spec['id']}/acceptance_criteria",
            "chunk_index": 1,
            "char_count": len(ac_text),
        })

    # Chunk 3: Skills + Agents
    if spec["required_skills"] or spec["required_agents"]:
        sa_text = f"UseCase {spec['id']} - Required Skills & Agents:\n"
        for s in spec["required_skills"]:
            sa_text += f"- Skill: {s['name']} ({s['status']})\n"
        for a in spec["required_agents"]:
            sa_text += f"- Agent: {a}\n"
        chunks.append({
            **base_meta,
            "content": sa_text,
            "source_file": f"usecase/{spec['id']}/skills_agents",
            "chunk_index": 2,
            "char_count": len(sa_text),
        })

    # Chunk 4: Implementation Notes
    if spec["implementation_notes"]:
        impl_text = f"UseCase {spec['id']} - Implementation Notes:\n{spec['implementation_notes'][:700]}"
        chunks.append({
            **base_meta,
            "content": impl_text,
            "source_file": f"usecase/{spec['id']}/implementation",
            "chunk_index": 3,
            "char_count": len(impl_text),
        })

    if not chunks:
        return 0

    return add_chunks(chunks)


def index_usecase_to_graph(spec: dict, graph=None) -> dict:
    """
    Cria :UseCase node no Neo4j com relacionamentos.

    Relationships:
      - REQUIRES_SKILL -> :Skill
      - ASSIGNED_TO -> :Agent
      - DEPENDS_ON -> :UseCase

    Returns:
        Dict com stats.
    """
    try:
        from src.neural_link.graph.manager import GraphManager
        from src.neural_link.graph import queries
    except ImportError:
        logger.debug("Neural Link nao disponivel.")
        return {"skipped": True}

    if graph is None:
        try:
            graph = GraphManager.from_env()
            if not graph.verify_connectivity():
                return {"skipped": True}
        except Exception:
            return {"skipped": True}

    stats = {"node_created": False, "skills_linked": 0, "agents_linked": 0, "deps_linked": 0, "errors": []}
    now = datetime.now(timezone.utc).isoformat()

    batch: list[tuple[str, dict]] = []

    # Upsert UseCase node
    batch.append((queries.UPSERT_USE_CASE, {
        "id": spec["id"],
        "name": spec["name"],
        "domain": spec["domain"],
        "status": spec["status"],
        "acceptance_criteria": spec.get("acceptance_criteria_text", ""),
        "priority": spec["priority"],
        "complexity": spec["complexity"],
        "repos": json.dumps(spec["repos"]),
        "created_at": now,
    }))
    stats["node_created"] = True

    # Link to Skills
    for skill in spec.get("required_skills", []):
        batch.append((queries.CREATE_USECASE_REQUIRES_SKILL, {
            "usecase_id": spec["id"],
            "skill_id": skill["id"],
            "criticality": "required",
        }))
        stats["skills_linked"] += 1

    # Link to Agents
    for agent_id in spec.get("required_agents", []):
        batch.append((queries.CREATE_USECASE_ASSIGNED_AGENT, {
            "usecase_id": spec["id"],
            "agent_id": agent_id,
            "role": "primary",
        }))
        stats["agents_linked"] += 1

    # Link dependencies
    for dep_id in spec.get("depends_on", []):
        batch.append((queries.CREATE_USECASE_DEPENDS_ON, {
            "usecase_id": spec["id"],
            "depends_on_id": dep_id,
        }))
        stats["deps_linked"] += 1

    try:
        graph.execute_write_batch(batch)
    except Exception as e:
        stats["errors"].append(str(e))
        logger.error("UseCase graph sync failed for %s: %s", spec["id"], e)

    logger.info(
        "UseCase %s indexed: skills=%d, agents=%d, deps=%d",
        spec["id"], stats["skills_linked"], stats["agents_linked"], stats["deps_linked"],
    )
    return stats


def index_all_usecases(
    specs_dir: Optional[str | Path] = None,
    *,
    save_to_chromadb: bool = True,
    save_to_graph: bool = True,
) -> dict:
    """
    Escaneia docs/specs/usecases/*.md e indexa todos.

    Returns:
        Dict com stats agregados.
    """
    specs_path = Path(specs_dir) if specs_dir else DEFAULT_SPECS_DIR

    results = {
        "total_files": 0,
        "usecases_indexed": 0,
        "chunks_saved": 0,
        "graph_nodes": 0,
        "errors": [],
    }

    if not specs_path.exists():
        logger.warning("Diretorio de specs nao encontrado: %s", specs_path)
        return results

    md_files = sorted(specs_path.glob("UC-*.md"))
    results["total_files"] = len(md_files)

    for md_file in md_files:
        if md_file.name == "TEMPLATE.md":
            continue

        try:
            spec = parse_usecase_spec(md_file)

            if save_to_chromadb:
                n = index_usecase_to_chromadb(spec)
                results["chunks_saved"] += n

            if save_to_graph:
                gs = index_usecase_to_graph(spec)
                if gs.get("node_created"):
                    results["graph_nodes"] += 1

            results["usecases_indexed"] += 1
            logger.info("Indexed: %s - %s", spec["id"], spec["name"])

        except Exception as e:
            results["errors"].append({"file": str(md_file), "error": str(e)})
            logger.error("Erro ao indexar %s: %s", md_file, e)

    logger.info(
        "UseCase Indexer: %d indexed, %d chunks, %d graph nodes, %d errors",
        results["usecases_indexed"], results["chunks_saved"],
        results["graph_nodes"], len(results["errors"]),
    )
    return results


def main():
    """CLI: python -m src.extractors.usecase_indexer"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Indexa UseCase specs no ChromaDB e Neo4j")
    parser.add_argument("--dir", help="Diretorio com specs (default: docs/specs/usecases/)")
    parser.add_argument("--no-chromadb", action="store_true")
    parser.add_argument("--no-graph", action="store_true")
    parser.add_argument("--parse-only", help="Apenas parse um arquivo (debug)")
    args = parser.parse_args()

    if args.parse_only:
        spec = parse_usecase_spec(args.parse_only)
        print(json.dumps(spec, indent=2, ensure_ascii=False, default=str))
        return

    results = index_all_usecases(
        specs_dir=args.dir,
        save_to_chromadb=not args.no_chromadb,
        save_to_graph=not args.no_graph,
    )
    print(json.dumps(results, indent=2, default=str))


if __name__ == "__main__":
    main()
