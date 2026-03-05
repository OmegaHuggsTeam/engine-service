"""
n8n Workflow Extractor - Converte fluxos n8n JSON em Modulos de Operacao.

Em vez de pedacos de texto, cada chunk e um Modulo de Operacao:
um objeto contendo o Node (tipo, parametros) e suas conexoes imediatas.

Detecta automaticamente se um .json e um fluxo n8n valido (possui "nodes"
e "connections") e extrai chunks estruturados para indexacao no ChromaDB.
"""

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# Node types to skip (visual-only, no operational value)
SKIP_NODE_TYPES = {"n8n-nodes-base.stickyNote", "n8n-nodes-base.noOp"}


def is_n8n_workflow(file_path: str | Path) -> bool:
    """
    Detecta se um arquivo JSON e um fluxo n8n valido.

    Criterios:
      - Extensao .json
      - Contem chave "nodes" (lista) e "connections" (dict)
      - Pelo menos 1 node com campo "type"
    """
    p = Path(file_path)
    if p.suffix.lower() != ".json":
        return False
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return False

    if not isinstance(data, dict):
        return False
    nodes = data.get("nodes")
    connections = data.get("connections")
    if not isinstance(nodes, list) or not isinstance(connections, dict):
        return False
    if not nodes:
        return False
    return any(isinstance(n, dict) and "type" in n for n in nodes)


def _extract_service_name(node_type: str) -> str:
    """
    Extrai o nome legivel do servico a partir do tipo do node.

    Exemplos:
      "n8n-nodes-base.googleSheets" -> "Google Sheets"
      "@n8n/n8n-nodes-langchain.lmChatGroq" -> "Groq"
      "@elevenlabs/n8n-nodes-elevenlabs.elevenLabs" -> "ElevenLabs"
      "n8n-nodes-base.webhook" -> "Webhook"
    """
    # Take last segment after the dot
    base = node_type.rsplit(".", 1)[-1] if "." in node_type else node_type

    # CamelCase to Title Case
    import re
    parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", base)
    parts = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1 \2", parts)
    name = parts.strip().title()

    # Common renames
    renames = {
        "Google Sheets": "Google Sheets",
        "Http Request": "HTTP Request",
        "Lm Chat Groq": "Groq",
        "Lm Chat Open Ai": "OpenAI",
        "Chat Trigger": "Chat Trigger",
        "Eleven Labs": "ElevenLabs",
        "Respond To Webhook": "Respond to Webhook",
        "Tavily Tool": "Tavily",
    }
    return renames.get(name, name)


def _get_node_connections(node_name: str, connections: dict) -> dict[str, list[str]]:
    """
    Retorna as conexoes imediatas de um node.

    Returns:
        {"outputs": ["NodeB", "NodeC"], "inputs_from": ["NodeA"]}
    """
    outputs: list[str] = []
    inputs_from: list[str] = []

    # Outputs: connections[node_name] -> targets
    if node_name in connections:
        for conn_type_data in connections[node_name].values():
            for output_group in conn_type_data:
                for conn in output_group:
                    if isinstance(conn, dict) and "node" in conn:
                        target = conn["node"]
                        if target not in outputs:
                            outputs.append(target)

    # Inputs: scan all connections for targets pointing to this node
    for source_name, conn_types in connections.items():
        for conn_type_data in conn_types.values():
            for output_group in conn_type_data:
                for conn in output_group:
                    if isinstance(conn, dict) and conn.get("node") == node_name:
                        if source_name not in inputs_from:
                            inputs_from.append(source_name)

    return {"outputs": outputs, "inputs_from": inputs_from}


def _sanitize_params(parameters: dict) -> dict:
    """Remove campos muito grandes (HTML, base64) para manter chunks compactos."""
    sanitized = {}
    for key, value in parameters.items():
        if isinstance(value, str) and len(value) > 500:
            sanitized[key] = f"<truncated, {len(value)} chars>"
        else:
            sanitized[key] = value
    return sanitized


def extract_operation_modules(file_path: str | Path) -> list[dict]:
    """
    Extrai Modulos de Operacao de um fluxo n8n.

    Cada modulo contem:
      - node_name: Nome do node no fluxo
      - node_type: Tipo completo (ex: "n8n-nodes-base.googleSheets")
      - service: Nome legivel do servico (ex: "Google Sheets")
      - type_version: Versao do node
      - parameters: Parametros do node (sanitizados)
      - connections: {"outputs": [...], "inputs_from": [...]}
      - credential_types: Lista de tipos de credencial usados
      - content: Texto descritivo para indexacao
      - source_file: Nome do arquivo de origem
      - category: "n8n_workflow"
      - chunk_index: Indice sequencial
      - agent_specialty: "automation"

    Returns:
        Lista de dicts (Modulos de Operacao), prontos para ChromaDB.
    """
    p = Path(file_path)
    if not is_n8n_workflow(p):
        raise ValueError(f"Arquivo nao e um fluxo n8n valido: {p}")

    data = json.loads(p.read_text(encoding="utf-8"))
    nodes = data["nodes"]
    connections = data.get("connections", {})
    workflow_name = data.get("name", p.stem)

    modules: list[dict] = []
    chunk_idx = 0

    for node in nodes:
        if not isinstance(node, dict):
            continue
        node_type = node.get("type", "")
        if node_type in SKIP_NODE_TYPES:
            continue

        node_name = node.get("name", "unnamed")
        parameters = _sanitize_params(node.get("parameters", {}))
        type_version = node.get("typeVersion", 1)
        node_conns = _get_node_connections(node_name, connections)
        service = _extract_service_name(node_type)

        # Extract credential types
        cred_types = []
        creds = node.get("credentials", {})
        if isinstance(creds, dict):
            cred_types = list(creds.keys())

        # Build descriptive content for text indexing
        conn_desc_parts = []
        if node_conns["inputs_from"]:
            conn_desc_parts.append(f"Recebe dados de: {', '.join(node_conns['inputs_from'])}")
        if node_conns["outputs"]:
            conn_desc_parts.append(f"Envia dados para: {', '.join(node_conns['outputs'])}")
        conn_desc = ". ".join(conn_desc_parts) if conn_desc_parts else "Node isolado."

        param_keys = list(parameters.keys()) if parameters else []
        param_summary = f"Parametros: {', '.join(param_keys)}" if param_keys else "Sem parametros."

        content = (
            f"n8n Node: {node_name} ({service})\n"
            f"Tipo: {node_type} v{type_version}\n"
            f"{param_summary}\n"
            f"{conn_desc}\n"
            f"Workflow: {workflow_name}"
        )

        module = {
            "node_name": node_name,
            "node_type": node_type,
            "service": service,
            "type_version": type_version,
            "parameters": parameters,
            "connections": node_conns,
            "credential_types": cred_types,
            "content": content,
            "source_file": f"n8n/{workflow_name}",
            "chunk_index": chunk_idx,
            "category": "n8n_workflow",
            "agent_specialty": "automation",
            "char_count": len(content),
        }
        modules.append(module)
        chunk_idx += 1

    logger.info("Extraidos %d modulos de operacao de %s", len(modules), p.name)
    return modules


def extract_all_workflows(search_dir: str | Path) -> list[dict]:
    """
    Busca recursivamente todos os fluxos n8n em um diretorio
    e extrai Modulos de Operacao de cada um.
    """
    search_path = Path(search_dir)
    all_modules: list[dict] = []

    for json_file in search_path.rglob("*.json"):
        if json_file.name.startswith("._"):
            continue  # Skip macOS resource forks
        if is_n8n_workflow(json_file):
            try:
                modules = extract_operation_modules(json_file)
                all_modules.extend(modules)
                logger.info("  %s: %d modulos", json_file.name, len(modules))
            except Exception as e:
                logger.warning("Erro ao extrair %s: %s", json_file, e)

    logger.info("Total: %d modulos de operacao extraidos", len(all_modules))
    return all_modules


def get_integration_pairs(modules: list[dict]) -> list[tuple[str, str, str]]:
    """
    Descobre pares de integracao a partir dos modulos extraidos.

    Percorre as conexoes e retorna tuplas (service_a, service_b, workflow_name)
    para cada conexao direta entre servicos distintos.
    """
    # Build lookup: node_name -> service (per workflow)
    node_service_map: dict[str, dict[str, str]] = {}  # source_file -> {node_name: service}
    for mod in modules:
        sf = mod["source_file"]
        node_service_map.setdefault(sf, {})[mod["node_name"]] = mod["service"]

    pairs: list[tuple[str, str, str]] = []
    seen: set[tuple[str, str, str]] = set()

    for mod in modules:
        sf = mod["source_file"]
        service_a = mod["service"]
        lookup = node_service_map.get(sf, {})

        for target_name in mod["connections"].get("outputs", []):
            service_b = lookup.get(target_name)
            if service_b and service_b != service_a:
                # Normalize order for dedup
                pair = tuple(sorted([service_a, service_b]))
                key = (pair[0], pair[1], sf)
                if key not in seen:
                    seen.add(key)
                    pairs.append((service_a, service_b, sf))

    return pairs


def get_node_type_pairs(modules: list[dict]) -> list[tuple[str, str, int]]:
    """
    Descobre os pares de conexao node-type mais comuns entre todos os workflows.

    Percorre as conexoes de saida de cada modulo e resolve os nomes dos nodes
    de destino para seus respectivos node_types. Conta ocorrencias com Counter.

    Returns:
        Lista de (source_type, target_type, count) ordenada por count decrescente.
    """
    # Build lookup: source_file -> {node_name: node_type}
    node_type_map: dict[str, dict[str, str]] = {}
    for mod in modules:
        sf = mod["source_file"]
        node_type_map.setdefault(sf, {})[mod["node_name"]] = mod["node_type"]

    pair_counter: Counter = Counter()

    for mod in modules:
        sf = mod["source_file"]
        source_type = mod["node_type"]
        lookup = node_type_map.get(sf, {})

        for target_name in mod["connections"].get("outputs", []):
            target_type = lookup.get(target_name)
            if target_type:
                pair_counter[(source_type, target_type)] += 1

    return [
        (src, tgt, count)
        for (src, tgt), count in pair_counter.most_common()
    ]


def sync_modules_to_graph(
    modules: list[dict],
    graph=None,
) -> dict:
    """
    Sincroniza modulos de operacao n8n no grafo Neo4j.

    Cria nos Service e N8nNode com relacionamentos:
      - (Service)-[:USES]->(N8nNode)
      - (N8nNode)-[:CONNECTS_TO]->(N8nNode)

    Usa MERGE para idempotencia — re-executar nao cria duplicatas.

    Args:
        modules: Lista de modulos extraidos via extract_operation_modules().
        graph: GraphManager opcional (default: GraphManager.from_env()).

    Returns:
        Dict com stats: services, nodes, uses_edges, connects_edges, errors.
    """
    try:
        from src.neural_link.graph.manager import GraphManager
        from src.neural_link.graph import queries
    except ImportError:
        logger.debug("Neural Link nao disponivel — graph sync ignorado.")
        return {"skipped": True}

    if graph is None:
        try:
            graph = GraphManager.from_env()
            if not graph.verify_connectivity():
                logger.debug("Neo4j inacessivel — graph sync ignorado.")
                return {"skipped": True}
        except Exception:
            logger.debug("Neo4j inacessivel — graph sync ignorado.")
            return {"skipped": True}

    stats = {"services": 0, "nodes": 0, "uses_edges": 0, "connects_edges": 0, "errors": []}

    # Build lookup: (source_file, node_name) -> module for connection resolution
    node_lookup: dict[tuple[str, str], dict] = {}
    for mod in modules:
        node_lookup[(mod["source_file"], mod["node_name"])] = mod

    seen_services: set[str] = set()
    batch: list[tuple[str, dict]] = []

    for mod in modules:
        service_name = mod["service"]
        service_id = service_name.lower().replace(" ", "_")
        workflow = mod["source_file"]
        node_id = f"{workflow}/{mod['node_name']}"

        # Upsert Service (once per unique service)
        if service_id not in seen_services:
            seen_services.add(service_id)
            batch.append((queries.UPSERT_SERVICE, {
                "id": service_id,
                "name": service_name,
            }))
            stats["services"] += 1

        # Upsert N8nNode
        batch.append((queries.UPSERT_N8N_NODE, {
            "id": node_id,
            "name": mod["node_name"],
            "node_type": mod["node_type"],
            "service": service_name,
            "type_version": mod["type_version"],
            "workflow": workflow,
        }))
        stats["nodes"] += 1

        # (Service)-[:USES]->(N8nNode)
        batch.append((queries.CREATE_SERVICE_USES_NODE, {
            "service_id": service_id,
            "node_id": node_id,
        }))
        stats["uses_edges"] += 1

        # (N8nNode)-[:CONNECTS_TO]->(N8nNode) for each output
        for target_name in mod["connections"].get("outputs", []):
            target_key = (workflow, target_name)
            if target_key in node_lookup:
                target_id = f"{workflow}/{target_name}"
                batch.append((queries.CREATE_NODE_CONNECTS_TO, {
                    "source_id": node_id,
                    "target_id": target_id,
                }))
                stats["connects_edges"] += 1

    if not batch:
        return stats

    # Execute all in a single transaction
    try:
        graph.execute_write_batch(batch)
    except Exception as e:
        stats["errors"].append(str(e))
        logger.error("Graph sync batch failed: %s", e)

    logger.info(
        "GraphSynergy: %d services, %d nodes, %d USES, %d CONNECTS_TO",
        stats["services"], stats["nodes"],
        stats["uses_edges"], stats["connects_edges"],
    )
    return stats


def build_reference_index(modules: list[dict]) -> dict[str, dict[str, Any]]:
    """
    Constroi um indice de referencia a partir dos modulos extraidos.

    Retorna:
        {node_type: {"parameter_keys": set, "type_versions": set, "credential_types": set}}

    Usado pelo validador para verificar fluxos gerados por agentes.
    """
    index: dict[str, dict[str, Any]] = {}

    for mod in modules:
        ntype = mod["node_type"]
        if ntype not in index:
            index[ntype] = {
                "parameter_keys": set(),
                "type_versions": set(),
                "credential_types": set(),
            }
        entry = index[ntype]
        entry["parameter_keys"].update(mod["parameters"].keys())
        entry["type_versions"].add(mod["type_version"])
        entry["credential_types"].update(mod["credential_types"])

    return index
