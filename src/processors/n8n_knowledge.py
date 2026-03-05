"""
n8n Knowledge Synthesizer - Gera vault/Knowledge/n8n_capabilities.md.

Analisa todos os Modulos de Operacao extraidos dos fluxos n8n de referencia
e produz um Markdown com:
  - Todas as integracoes possiveis (pares de servicos)
  - Nodes disponiveis por categoria
  - Credenciais necessarias
  - Links para notas Obsidian relacionadas
"""

import json
import logging
from collections import defaultdict
from datetime import date
from pathlib import Path

import yaml

from src.extractors.n8n_extractor import (
    extract_all_workflows,
    get_integration_pairs,
    get_node_type_pairs,
    build_reference_index,
    _extract_service_name,
)

logger = logging.getLogger(__name__)


def classify_workflow(workflow_modules: list[dict]) -> str:
    """
    Classifica um workflow por categoria com base nos node_types presentes.

    Regras verificadas em ordem de prioridade:
      AI / LLM > Marketing > Communication > DevOps > Security >
      Data Processing > Media > General Automation (fallback)
    """
    node_types = {mod["node_type"] for mod in workflow_modules}
    type_str = " ".join(node_types).lower()

    # AI / LLM — any langchain node
    if "langchain" in type_str:
        return "AI / LLM"

    # Marketing — GoogleSheets + (Mail or HTTP or form)
    has_sheets = any("googlesheets" in t.lower() for t in node_types)
    has_mail_http = any(
        kw in type_str for kw in ("mail", "httprequest", "form", "formtrigger")
    )
    if has_sheets and has_mail_http:
        return "Marketing"

    # Communication — Telegram, WhatsApp, Slack, ElevenLabs
    comm_keywords = ("telegram", "whatsapp", "slack", "elevenlabs")
    if any(kw in type_str for kw in comm_keywords):
        return "Communication"

    # DevOps — ExecuteCommand, SSH, Docker, Code
    devops_keywords = ("executecommand", "ssh", "docker", "code")
    if any(kw in type_str for kw in devops_keywords):
        return "DevOps"

    # Security — IF + Webhook + HTTP (monitoring pattern)
    has_if = any("if" == t.rsplit(".", 1)[-1].lower() for t in node_types)
    has_webhook = any("webhook" in t.lower() for t in node_types)
    has_http = any("httprequest" in t.lower() for t in node_types)
    if has_if and has_webhook and has_http:
        return "Security"

    # Data Processing — Supabase, Postgres, MongoDB, MySQL, or spreadsheet-only
    data_keywords = ("supabase", "postgres", "mongodb", "mysql")
    if any(kw in type_str for kw in data_keywords):
        return "Data Processing"
    if has_sheets and not has_mail_http:
        return "Data Processing"

    # Media — Fal AI, image/video processing
    media_keywords = ("fal", "image", "video")
    if any(kw in type_str for kw in media_keywords):
        return "Media"

    return "General Automation"


def synthesize_capabilities(
    modules: list[dict],
) -> dict:
    """
    Analisa modulos extraidos e retorna dados sintetizados.

    Returns:
        {
            "integrations": [(service_a, service_b, workflow)],
            "services": {service_name: {"count": int, "workflows": set}},
            "node_types": {node_type: {"service": str, "versions": set}},
            "credentials": {cred_type: set(services)},
        }
    """
    integrations = get_integration_pairs(modules)

    services: dict[str, dict] = defaultdict(lambda: {"count": 0, "workflows": set()})
    node_types: dict[str, dict] = {}
    credentials: dict[str, set] = defaultdict(set)

    for mod in modules:
        svc = mod["service"]
        wf = mod["source_file"]
        services[svc]["count"] += 1
        services[svc]["workflows"].add(wf)

        ntype = mod["node_type"]
        if ntype not in node_types:
            node_types[ntype] = {"service": svc, "versions": set()}
        node_types[ntype]["versions"].add(mod["type_version"])

        for cred in mod.get("credential_types", []):
            credentials[cred].add(svc)

    node_pairs = get_node_type_pairs(modules)

    return {
        "integrations": integrations,
        "services": dict(services),
        "node_types": node_types,
        "credentials": dict(credentials),
        "node_pairs": node_pairs,
    }


def generate_capabilities_md(
    modules: list[dict],
    vault_path: str | Path = "vault",
) -> str:
    """
    Gera vault/Knowledge/n8n_capabilities.md a partir dos modulos extraidos.

    Returns:
        Caminho do arquivo gerado.
    """
    vault = Path(vault_path)
    knowledge_dir = vault / "Knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    caps = synthesize_capabilities(modules)

    # --- YAML frontmatter ---
    frontmatter = {
        "tags": ["knowledge", "n8n", "automation", "integrations"],
        "last_updated": str(date.today()),
        "total_modules": len(modules),
        "total_services": len(caps["services"]),
        "total_integrations": len(caps["integrations"]),
    }
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)

    lines = [
        f"---\n{fm_str}---",
        "",
        "# n8n Capabilities - Conhecimento Sintetizado",
        "",
        f"_Gerado: {date.today()} | {len(modules)} modulos de {len(caps['services'])} servicos_",
        "",
    ]

    # --- Integration Pairs ---
    lines += [
        "## Integracoes Possiveis",
        "",
    ]

    if caps["integrations"]:
        seen_pairs: set[tuple[str, str]] = set()
        for svc_a, svc_b, workflow in caps["integrations"]:
            pair_key = tuple(sorted([svc_a, svc_b]))
            if pair_key not in seen_pairs:
                seen_pairs.add(pair_key)
                wf_name = workflow.replace("n8n/", "")
                lines.append(
                    f"- O n8n neste bunker sabe conectar **{svc_a}** com **{svc_b}** "
                    f"(ref: _{wf_name}_)"
                )
        lines.append("")
    else:
        lines += ["_Nenhuma integracao entre servicos detectada._", ""]

    # --- Node Pairs ---
    lines += [
        "## Padroes de Conexao Mais Comuns",
        "",
    ]

    if caps["node_pairs"]:
        lines += [
            "| # | De | Para | Ocorrencias |",
            "|---|-----|------|-------------|",
        ]
        for rank, (src_type, tgt_type, count) in enumerate(caps["node_pairs"], 1):
            src_name = _extract_service_name(src_type)
            tgt_name = _extract_service_name(tgt_type)
            lines.append(
                f"| {rank} | {src_name} (`{src_type}`) "
                f"| {tgt_name} (`{tgt_type}`) | {count} |"
            )
        lines.append("")
    else:
        lines += ["_Nenhum padrao de conexao detectado._", ""]

    # --- Services catalog ---
    lines += [
        "## Servicos Disponiveis",
        "",
        "| Servico | Nodes | Workflows |",
        "|---------|-------|-----------|",
    ]

    for svc_name in sorted(caps["services"].keys()):
        info = caps["services"][svc_name]
        wf_list = ", ".join(w.replace("n8n/", "") for w in sorted(info["workflows"]))
        lines.append(f"| {svc_name} | {info['count']} | {wf_list} |")
    lines.append("")

    # --- Node Types ---
    lines += [
        "## Node Types de Referencia",
        "",
    ]

    ref_index = build_reference_index(modules)
    for ntype in sorted(ref_index.keys()):
        entry = ref_index[ntype]
        versions = ", ".join(str(v) for v in sorted(entry["type_versions"]))
        params = ", ".join(sorted(entry["parameter_keys"])) if entry["parameter_keys"] else "nenhum"
        lines.append(f"- `{ntype}` (v{versions})")
        lines.append(f"  - Parametros: {params}")
        if entry["credential_types"]:
            creds = ", ".join(sorted(entry["credential_types"]))
            lines.append(f"  - Credenciais: {creds}")
        lines.append("")

    # --- Credentials ---
    if caps["credentials"]:
        lines += [
            "## Credenciais Necessarias",
            "",
            "| Tipo de Credencial | Servicos |",
            "|-------------------|----------|",
        ]
        for cred_type in sorted(caps["credentials"].keys()):
            svcs = ", ".join(sorted(caps["credentials"][cred_type]))
            lines.append(f"| `{cred_type}` | {svcs} |")
        lines.append("")

    # --- Links ---
    lines += [
        "## Relacionados",
        "",
        "- [[Dashboard]]",
        "- [[External_Orchestration]]",
    ]

    content = "\n".join(lines) + "\n"
    out_path = knowledge_dir / "n8n_capabilities.md"
    out_path.write_text(content, encoding="utf-8")

    logger.info("Gerado: %s (%d integracoes, %d servicos)",
                out_path, len(caps["integrations"]), len(caps["services"]))
    return str(out_path)


def generate_recipes_md(
    modules: list[dict],
    vault_path: str | Path = "vault",
) -> str:
    """
    Gera vault/Knowledge/n8n_recipes.md — biblioteca de receitas agrupadas por categoria.

    Steps:
      1. Agrupa modulos por source_file (cada source_file = um workflow)
      2. Classifica cada workflow via classify_workflow()
      3. Agrupa workflows por categoria
      4. Renderiza Markdown com YAML frontmatter

    Returns:
        Caminho do arquivo gerado.
    """
    vault = Path(vault_path)
    knowledge_dir = vault / "Knowledge"
    knowledge_dir.mkdir(parents=True, exist_ok=True)

    # Group modules by workflow (source_file)
    workflows: dict[str, list[dict]] = defaultdict(list)
    for mod in modules:
        workflows[mod["source_file"]].append(mod)

    # Classify each workflow and group by category
    categorized: dict[str, list[tuple[str, list[dict]]]] = defaultdict(list)
    for wf_name, wf_modules in sorted(workflows.items()):
        category = classify_workflow(wf_modules)
        categorized[category].append((wf_name, wf_modules))

    # --- YAML frontmatter ---
    frontmatter = {
        "tags": ["knowledge", "n8n", "recipes", "automation"],
        "last_updated": str(date.today()),
        "total_workflows": len(workflows),
        "categories": sorted(categorized.keys()),
    }
    fm_str = yaml.dump(frontmatter, default_flow_style=False, allow_unicode=True, sort_keys=False)

    lines = [
        f"---\n{fm_str}---",
        "",
        "# n8n Recipe Library",
        "",
        f"_Gerado: {date.today()} | {len(workflows)} workflows em "
        f"{len(categorized)} categorias_",
        "",
    ]

    # Render each category
    for category in sorted(categorized.keys()):
        wf_list = categorized[category]
        lines += [f"## {category}", ""]

        for wf_name, wf_modules in wf_list:
            display_name = wf_name.replace("n8n/", "")
            lines.append(f"### {display_name}")
            lines.append("")

            # Node chain
            ordered_nodes = sorted(wf_modules, key=lambda m: m["chunk_index"])
            chain_parts = [_extract_service_name(m["node_type"]) for m in ordered_nodes]
            lines.append(f"**Fluxo:** {' -> '.join(chain_parts)}")
            lines.append("")

            # Services
            services = sorted({m["service"] for m in wf_modules})
            lines.append(f"**Servicos:** {', '.join(services)}")

            # Credentials
            creds = sorted({c for m in wf_modules for c in m.get("credential_types", [])})
            if creds:
                lines.append(f"**Credenciais:** {', '.join(f'`{c}`' for c in creds)}")

            lines += [""]

    # --- Links ---
    lines += [
        "## Relacionados",
        "",
        "- [[n8n_capabilities]]",
        "- [[Dashboard]]",
    ]

    content = "\n".join(lines) + "\n"
    out_path = knowledge_dir / "n8n_recipes.md"
    out_path.write_text(content, encoding="utf-8")

    logger.info("Gerado: %s (%d workflows, %d categorias)",
                out_path, len(workflows), len(categorized))
    return str(out_path)


def generate_master_context(
    modules: list[dict],
    output_dir: str | Path = "data/chunks",
) -> str:
    """
    Gera data/chunks/n8n_master_context.json — chunks para o SpecialistAgent.

    Cada chunk contem best practices para uma categoria + um chunk global de padroes.
    O SpecialistAgent carrega via load_knowledge("n8n_master_context").

    Returns:
        Caminho do arquivo gerado.
    """
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Group modules by workflow
    workflows: dict[str, list[dict]] = defaultdict(list)
    for mod in modules:
        workflows[mod["source_file"]].append(mod)

    # Classify and group by category
    category_modules: dict[str, list[dict]] = defaultdict(list)
    for wf_name, wf_modules in workflows.items():
        category = classify_workflow(wf_modules)
        category_modules[category].extend(wf_modules)

    # Node pairs for global patterns
    node_pairs = get_node_type_pairs(modules)

    chunks: list[dict] = []
    chunk_idx = 0

    # One chunk per category
    for category in sorted(category_modules.keys()):
        cat_mods = category_modules[category]

        # Collect node types, versions, credentials, and pairs for this category
        node_info: dict[str, dict] = {}
        for mod in cat_mods:
            ntype = mod["node_type"]
            if ntype not in node_info:
                node_info[ntype] = {
                    "service": mod["service"],
                    "versions": set(),
                    "creds": set(),
                }
            node_info[ntype]["versions"].add(str(mod["type_version"]))
            node_info[ntype]["creds"].update(mod.get("credential_types", []))

        # Build content
        content_parts = [f"## Best Practices: {category}", ""]
        content_parts.append(f"Para tarefas de {category}, use:")
        for ntype in sorted(node_info.keys()):
            info = node_info[ntype]
            versions = ", ".join(sorted(info["versions"]))
            line = f"- {info['service']}: `{ntype}` (v{versions})"
            if info["creds"]:
                cred_list = ", ".join(sorted(info["creds"]))
                line += f" — credenciais: {cred_list}"
            content_parts.append(line)

        # Category-specific pairs
        cat_type_set = set(node_info.keys())
        cat_pairs = [
            (s, t, c) for s, t, c in node_pairs
            if s in cat_type_set or t in cat_type_set
        ]
        if cat_pairs:
            content_parts += ["", "### Padroes de Conexao"]
            for src, tgt, count in cat_pairs[:5]:
                src_name = _extract_service_name(src)
                tgt_name = _extract_service_name(tgt)
                content_parts.append(f"- {src_name} -> {tgt_name} ({count}x)")

        content = "\n".join(content_parts)

        chunks.append({
            "content": content,
            "source_file": "n8n_master_context",
            "category": "n8n_master_context",
            "agent_specialty": "automation",
            "chunk_index": chunk_idx,
        })
        chunk_idx += 1

    # Global patterns chunk (last)
    global_parts = ["## Padroes Globais de Conexao", ""]
    if node_pairs:
        global_parts.append("Top conexoes node-to-node:")
        for src, tgt, count in node_pairs[:10]:
            src_name = _extract_service_name(src)
            tgt_name = _extract_service_name(tgt)
            global_parts.append(f"- {src_name} -> {tgt_name} ({count}x)")
    else:
        global_parts.append("_Nenhum padrao detectado._")

    global_parts += ["", f"Total de workflows analisados: {len(workflows)}"]

    chunks.append({
        "content": "\n".join(global_parts),
        "source_file": "n8n_master_context",
        "category": "n8n_master_context",
        "agent_specialty": "automation",
        "chunk_index": chunk_idx,
    })

    out_path = out_dir / "n8n_master_context.json"
    out_path.write_text(json.dumps(chunks, indent=2, ensure_ascii=False), encoding="utf-8")

    logger.info("Gerado: %s (%d chunks)", out_path, len(chunks))
    return str(out_path)
