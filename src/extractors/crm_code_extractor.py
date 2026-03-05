"""
CRM Code Extractor - Extrai chunks estruturados de repositorios CRM.

Suporta Express.js routes, React/TSX components, TypeScript services,
data models e Kafka workers. Cada funcao retorna chunks compativeis
com add_chunks() do vector_db.py.

Estrategia: regex-first (rapido, zero-cost) seguindo o padrao do
concept_extractor.py (rule-based + fallback).
"""

import json
import logging
import re
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# ============================================================
# File Detection
# ============================================================

# Patterns para detectar tipo de arquivo
_EXPRESS_PATTERNS = [
    re.compile(r"router\.(get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    re.compile(r"app\.(get|post|put|patch|delete)\s*\(", re.IGNORECASE),
    re.compile(r"express\.Router\(\)"),
]

_REACT_PATTERNS = [
    re.compile(r"(?:export\s+default|export\s+function|export\s+const)\s+\w+"),
    re.compile(r"(?:useState|useEffect|useRef|useCallback|useMemo)\s*[\(<]"),
    re.compile(r"<\w+[A-Z]\w*[\s/>]"),  # JSX tags
]

_SERVICE_PATTERNS = [
    re.compile(r"(?:class|const)\s+\w+Service"),
    re.compile(r"module\.exports\s*=\s*\{"),
    re.compile(r"export\s+(?:class|const|function)\s+\w+(?:Service|Controller|Handler)"),
]

_MODEL_PATTERNS = [
    re.compile(r"(?:interface|type)\s+\w+\s*(?:extends|=)\s*\{", re.MULTILINE),
    re.compile(r"(?:new\s+)?Schema\s*\(\s*\{"),
    re.compile(r"mongoose\.model\s*\("),
    re.compile(r"export\s+(?:interface|type)\s+\w+"),
]

_KAFKA_PATTERNS = [
    re.compile(r"(?:consumer|producer|kafka)", re.IGNORECASE),
    re.compile(r"\.subscribe\s*\(\s*\{?\s*topic"),
    re.compile(r"\.send\s*\(\s*\{?\s*topic"),
    re.compile(r"KafkaConsumer|KafkaProducer|KafkaService"),
]

# Domain inference from file path
_DOMAIN_PATTERNS = {
    "campaigns": re.compile(r"campaign", re.IGNORECASE),
    "journeys": re.compile(r"journey|flow", re.IGNORECASE),
    "segments": re.compile(r"segment|cohort|behavior", re.IGNORECASE),
    "contacts": re.compile(r"contact|person|list(?!en)", re.IGNORECASE),
    "tracker": re.compile(r"track|collect|event|smart(?:block|modal)|minigame|buyer", re.IGNORECASE),
    "integrations": re.compile(r"integrat|adapter|credential|sms|email|resend", re.IGNORECASE),
    "analytics": re.compile(r"analytic|clickhouse|metric|kpi|attribution", re.IGNORECASE),
    "ontology": re.compile(r"ontolog|object(?:type|instance)|signal|field", re.IGNORECASE),
    "rules": re.compile(r"rule|regra|template", re.IGNORECASE),
    "auth": re.compile(r"auth|jwt|verify|sub.?user", re.IGNORECASE),
}

# Agent specialty mapping
_DOMAIN_TO_SPECIALTY = {
    "campaigns": "crm_backend",
    "journeys": "crm_backend",
    "segments": "crm_data",
    "contacts": "crm_backend",
    "tracker": "crm_integration",
    "integrations": "crm_integration",
    "analytics": "crm_data",
    "ontology": "crm_backend",
    "rules": "crm_backend",
    "auth": "crm_backend",
}


def _read_file(file_path: Path) -> str:
    """Le arquivo com fallback de encoding."""
    for enc in ("utf-8", "utf-8-sig", "latin-1"):
        try:
            return file_path.read_text(encoding=enc)
        except (UnicodeDecodeError, UnicodeError):
            continue
    return ""


def _count_pattern_matches(content: str, patterns: list[re.Pattern]) -> int:
    """Conta quantos patterns casam no conteudo."""
    return sum(1 for p in patterns if p.search(content))


def _infer_domain(file_path: str, content: str = "") -> str:
    """Infere dominio CRM a partir do path e conteudo."""
    text = f"{file_path} {content[:500]}"
    for domain, pattern in _DOMAIN_PATTERNS.items():
        if pattern.search(text):
            return domain
    return "general"


def _infer_language(file_path: str) -> str:
    """Infere linguagem pelo sufixo."""
    p = file_path.lower()
    if p.endswith(".tsx"):
        return "tsx"
    if p.endswith(".ts"):
        return "typescript"
    if p.endswith(".jsx"):
        return "jsx"
    if p.endswith(".js"):
        return "javascript"
    return "unknown"


def is_express_route(file_path: str | Path) -> bool:
    """Detecta se arquivo contem Express.js routes."""
    p = Path(file_path)
    if p.suffix.lower() not in (".js", ".ts"):
        return False
    content = _read_file(p)
    return _count_pattern_matches(content, _EXPRESS_PATTERNS) >= 1


def is_react_component(file_path: str | Path) -> bool:
    """Detecta se arquivo e um React component (JSX/TSX)."""
    p = Path(file_path)
    if p.suffix.lower() not in (".tsx", ".jsx"):
        return False
    content = _read_file(p)
    return _count_pattern_matches(content, _REACT_PATTERNS) >= 2


def is_typescript_service(file_path: str | Path) -> bool:
    """Detecta se arquivo e um service/controller TypeScript."""
    p = Path(file_path)
    if p.suffix.lower() not in (".js", ".ts"):
        return False
    content = _read_file(p)
    return _count_pattern_matches(content, _SERVICE_PATTERNS) >= 1


def is_data_model(file_path: str | Path) -> bool:
    """Detecta se arquivo define modelos/schemas/interfaces."""
    p = Path(file_path)
    if p.suffix.lower() not in (".js", ".ts", ".tsx"):
        return False
    content = _read_file(p)
    return _count_pattern_matches(content, _MODEL_PATTERNS) >= 1


def is_kafka_worker(file_path: str | Path) -> bool:
    """Detecta se arquivo contem Kafka consumer/producer."""
    p = Path(file_path)
    if p.suffix.lower() not in (".js", ".ts"):
        return False
    content = _read_file(p)
    return _count_pattern_matches(content, _KAFKA_PATTERNS) >= 2


# ============================================================
# Extraction Functions
# ============================================================

def _extract_route_info(content: str) -> list[dict]:
    """Extrai informacoes de rotas Express de um arquivo."""
    routes = []
    # Match router.get('/path', middleware, handler) patterns
    route_re = re.compile(
        r"(?:router|app)\.(get|post|put|patch|delete)\s*\(\s*['\"]([^'\"]+)['\"]"
        r"(?:\s*,\s*(\w+))?",
        re.IGNORECASE,
    )
    for m in route_re.finditer(content):
        routes.append({
            "method": m.group(1).upper(),
            "path": m.group(2),
            "middleware": m.group(3) or "",
        })
    return routes


def _extract_function_names(content: str) -> list[str]:
    """Extrai nomes de funcoes/metodos exportados."""
    names = []
    patterns = [
        re.compile(r"(?:async\s+)?function\s+(\w+)"),
        re.compile(r"(?:exports\.)?(\w+)\s*=\s*(?:async\s+)?\(?"),
        re.compile(r"(\w+)\s*(?::\s*\w+)?\s*(?:=>\s*\{|=\s*async)"),
    ]
    for p in patterns:
        for m in p.finditer(content):
            name = m.group(1)
            if name not in names and not name.startswith("_") and len(name) > 2:
                names.append(name)
    return names[:20]  # Cap at 20


def _extract_component_info(content: str) -> dict:
    """Extrai informacoes de um React component."""
    info: dict[str, Any] = {"hooks": [], "props": [], "imports": []}

    # Hooks
    hook_re = re.compile(r"(use\w+)\s*[\(<]")
    info["hooks"] = list(set(hook_re.findall(content)))

    # Props interface
    props_re = re.compile(
        r"(?:interface|type)\s+(\w*Props\w*)\s*(?:=\s*)?\{([^}]*)\}",
        re.DOTALL,
    )
    m = props_re.search(content)
    if m:
        info["props_name"] = m.group(1)
        # Extract field names from props
        fields = re.findall(r"(\w+)\s*[?:]", m.group(2))
        info["props"] = fields[:15]

    # Imports
    import_re = re.compile(r"import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]")
    info["imports"] = list(set(import_re.findall(content)))[:20]

    return info


def _extract_model_fields(content: str) -> list[dict]:
    """Extrai campos de interface/type/schema."""
    fields = []

    # TypeScript interface fields
    field_re = re.compile(r"(\w+)\s*(\?)?:\s*([^;\n,}]+)")
    for m in field_re.finditer(content):
        name = m.group(1)
        if name in ("return", "const", "let", "var", "import", "export", "function"):
            continue
        fields.append({
            "name": name,
            "optional": bool(m.group(2)),
            "type": m.group(3).strip()[:50],
        })

    return fields[:30]  # Cap


def _extract_kafka_info(content: str) -> dict:
    """Extrai informacoes de Kafka consumer/producer."""
    info: dict[str, Any] = {"topics": [], "type": "unknown"}

    # Topics
    topic_re = re.compile(r"topic\s*:\s*['\"]([^'\"]+)['\"]")
    info["topics"] = list(set(topic_re.findall(content)))

    # Type detection
    if re.search(r"consumer|subscribe", content, re.IGNORECASE):
        info["type"] = "consumer"
    if re.search(r"producer|send", content, re.IGNORECASE):
        if info["type"] == "consumer":
            info["type"] = "both"
        else:
            info["type"] = "producer"

    # Group ID
    group_re = re.compile(r"groupId\s*:\s*['\"]([^'\"]+)['\"]")
    m = group_re.search(content)
    if m:
        info["group_id"] = m.group(1)

    return info


def extract_express_routes(file_path: str | Path) -> list[dict]:
    """
    Extrai route handlers Express.js como chunks.

    Cada rota vira um chunk com: method, path, middleware, handler body.
    category='crm_backend', agent_specialty inferido por dominio.
    """
    p = Path(file_path)
    content = _read_file(p)
    file_str = str(p)
    domain = _infer_domain(file_str, content)
    specialty = _DOMAIN_TO_SPECIALTY.get(domain, "crm_backend")

    routes = _extract_route_info(content)
    if not routes:
        # Se nao encontrou pattern exato, trata como single chunk
        routes = [{"method": "MIXED", "path": "/", "middleware": ""}]

    chunks = []
    functions = _extract_function_names(content)

    for idx, route in enumerate(routes):
        desc = f"Express Route: {route['method']} {route['path']}"
        if route["middleware"]:
            desc += f"\nMiddleware: {route['middleware']}"
        desc += f"\nFunctions: {', '.join(functions[:10])}"
        desc += f"\nDomain: {domain}"

        chunks.append({
            "content": desc + "\n\n" + content[:800],
            "source_file": f"crm/{file_str}",
            "chunk_index": idx,
            "category": "crm_backend",
            "agent_specialty": specialty,
            "domain": domain,
            "language": _infer_language(file_str),
            "module_type": "route",
            "route_method": route["method"],
            "route_path": route["path"],
            "char_count": len(desc) + min(len(content), 800),
        })

    logger.debug("Extraidas %d rotas de %s", len(chunks), p.name)
    return chunks


def extract_react_components(file_path: str | Path) -> list[dict]:
    """
    Extrai React components como chunks.

    Cada componente vira um chunk com: nome, props, hooks, imports.
    category='crm_frontend', agent_specialty='crm_frontend'.
    """
    p = Path(file_path)
    content = _read_file(p)
    file_str = str(p)
    domain = _infer_domain(file_str, content)

    info = _extract_component_info(content)

    # Extract component name from filename or export
    comp_name = p.stem
    export_re = re.compile(r"export\s+(?:default\s+)?(?:function|const|class)\s+(\w+)")
    m = export_re.search(content)
    if m:
        comp_name = m.group(1)

    desc = f"React Component: {comp_name}\n"
    desc += f"File: {p.name}\n"
    if info["hooks"]:
        desc += f"Hooks: {', '.join(info['hooks'])}\n"
    if info["props"]:
        desc += f"Props: {', '.join(info['props'])}\n"
    desc += f"Domain: {domain}\n"

    # Include key imports
    lib_imports = [i for i in info["imports"] if not i.startswith(".")]
    if lib_imports:
        desc += f"Libraries: {', '.join(lib_imports[:8])}\n"

    chunk = {
        "content": desc + "\n" + content[:800],
        "source_file": f"crm/{file_str}",
        "chunk_index": 0,
        "category": "crm_frontend",
        "agent_specialty": "crm_frontend",
        "domain": domain,
        "language": _infer_language(file_str),
        "module_type": "component",
        "component_name": comp_name,
        "hooks": json.dumps(info["hooks"]),
        "char_count": len(desc) + min(len(content), 800),
    }

    logger.debug("Extraido componente %s de %s", comp_name, p.name)
    return [chunk]


def extract_typescript_services(file_path: str | Path) -> list[dict]:
    """
    Extrai TypeScript services/controllers como chunks.

    Cada service vira um chunk com: nome, metodos, dependencias.
    category='crm_service', agent_specialty inferido por dominio.
    """
    p = Path(file_path)
    content = _read_file(p)
    file_str = str(p)
    domain = _infer_domain(file_str, content)
    specialty = _DOMAIN_TO_SPECIALTY.get(domain, "crm_backend")

    functions = _extract_function_names(content)

    # Try to extract class/service name
    name_re = re.compile(r"(?:class|const)\s+(\w+(?:Service|Controller|Handler|Worker))")
    m = name_re.search(content)
    service_name = m.group(1) if m else p.stem

    desc = f"Service: {service_name}\n"
    desc += f"File: {p.name}\n"
    desc += f"Methods: {', '.join(functions[:15])}\n"
    desc += f"Domain: {domain}\n"

    chunk = {
        "content": desc + "\n" + content[:800],
        "source_file": f"crm/{file_str}",
        "chunk_index": 0,
        "category": "crm_service",
        "agent_specialty": specialty,
        "domain": domain,
        "language": _infer_language(file_str),
        "module_type": "service",
        "service_name": service_name,
        "methods": json.dumps(functions[:15]),
        "char_count": len(desc) + min(len(content), 800),
    }

    logger.debug("Extraido service %s de %s", service_name, p.name)
    return [chunk]


def extract_data_models(file_path: str | Path) -> list[dict]:
    """
    Extrai data models/interfaces/schemas como chunks.

    Cada modelo vira um chunk com: nome, campos, tipos.
    category='crm_model', agent_specialty='data_engineering'.
    """
    p = Path(file_path)
    content = _read_file(p)
    file_str = str(p)
    domain = _infer_domain(file_str, content)

    fields = _extract_model_fields(content)

    # Try to extract model/interface names
    name_re = re.compile(r"(?:interface|type|class)\s+(\w+)")
    names = list(set(name_re.findall(content)))[:5]
    model_name = names[0] if names else p.stem

    desc = f"Data Model: {model_name}\n"
    desc += f"File: {p.name}\n"
    if names and len(names) > 1:
        desc += f"Types: {', '.join(names)}\n"
    if fields:
        field_strs = [f"{f['name']}: {f['type']}" for f in fields[:10]]
        desc += f"Fields: {', '.join(field_strs)}\n"
    desc += f"Domain: {domain}\n"

    chunk = {
        "content": desc + "\n" + content[:800],
        "source_file": f"crm/{file_str}",
        "chunk_index": 0,
        "category": "crm_model",
        "agent_specialty": "crm_data",
        "domain": domain,
        "language": _infer_language(file_str),
        "module_type": "model",
        "model_name": model_name,
        "field_count": str(len(fields)),
        "char_count": len(desc) + min(len(content), 800),
    }

    logger.debug("Extraido modelo %s de %s", model_name, p.name)
    return [chunk]


def extract_kafka_workers(file_path: str | Path) -> list[dict]:
    """
    Extrai Kafka consumers/producers como chunks.

    Cada worker vira um chunk com: topics, tipo (consumer/producer), group_id.
    category='crm_data_pipeline', agent_specialty='crm_data'.
    """
    p = Path(file_path)
    content = _read_file(p)
    file_str = str(p)
    domain = _infer_domain(file_str, content)

    info = _extract_kafka_info(content)

    desc = f"Kafka {info['type'].title()}: {p.stem}\n"
    desc += f"File: {p.name}\n"
    if info["topics"]:
        desc += f"Topics: {', '.join(info['topics'])}\n"
    if info.get("group_id"):
        desc += f"Group ID: {info['group_id']}\n"
    desc += f"Domain: {domain}\n"

    chunk = {
        "content": desc + "\n" + content[:800],
        "source_file": f"crm/{file_str}",
        "chunk_index": 0,
        "category": "crm_data_pipeline",
        "agent_specialty": "crm_data",
        "domain": domain,
        "language": _infer_language(file_str),
        "module_type": "kafka_worker",
        "kafka_type": info["type"],
        "kafka_topics": json.dumps(info["topics"]),
        "char_count": len(desc) + min(len(content), 800),
    }

    logger.debug("Extraido Kafka %s de %s", info["type"], p.name)
    return [chunk]


# ============================================================
# Auto-routing: detect file type and extract
# ============================================================

def detect_and_extract(file_path: str | Path) -> list[dict]:
    """
    Detecta o tipo de arquivo e extrai chunks automaticamente.

    Prioridade de deteccao:
    1. Kafka worker (mais especifico)
    2. Express route
    3. Data model
    4. React component
    5. TypeScript service (fallback generico)

    Returns:
        Lista de chunks ou lista vazia se nao reconhecido.
    """
    p = Path(file_path)
    if p.suffix.lower() not in (".js", ".ts", ".tsx", ".jsx"):
        return []

    # Skip common non-code files
    skip_names = {"package.json", "tsconfig.json", "vite.config.ts",
                  "tailwind.config.ts", "postcss.config.js", ".eslintrc.js",
                  "jest.config.js", "index.css", "index.html"}
    if p.name in skip_names:
        return []

    # Skip node_modules, dist, build
    parts = set(p.parts)
    if parts & {"node_modules", "dist", "build", ".next", ".cache"}:
        return []

    try:
        if is_kafka_worker(p):
            return extract_kafka_workers(p)
        if is_express_route(p):
            return extract_express_routes(p)
        if is_data_model(p):
            return extract_data_models(p)
        if is_react_component(p):
            return extract_react_components(p)
        if is_typescript_service(p):
            return extract_typescript_services(p)
    except Exception as e:
        logger.warning("Erro ao extrair %s: %s", p, e)

    return []


# ============================================================
# Graph Sync
# ============================================================

def sync_crm_modules_to_graph(
    modules: list[dict],
    graph=None,
) -> dict:
    """
    Sincroniza modulos CRM extraidos no grafo Neo4j.

    Cria nos :Module com relacionamentos:
      - (Module)-[:CALLS]->(Module) para service->service
      - (Module)-[:RENDERS]->(Module) para page->component

    Usa MERGE para idempotencia.

    Args:
        modules: Lista de chunks extraidos via extract_* functions.
        graph: GraphManager opcional.

    Returns:
        Dict com stats: modules_created, relationships, errors.
    """
    try:
        from src.neural_link.graph.manager import GraphManager
        from src.neural_link.graph import queries
    except ImportError:
        logger.debug("Neural Link nao disponivel - graph sync ignorado.")
        return {"skipped": True}

    if graph is None:
        try:
            graph = GraphManager.from_env()
            if not graph.verify_connectivity():
                logger.debug("Neo4j inacessivel - graph sync ignorado.")
                return {"skipped": True}
        except Exception:
            logger.debug("Neo4j inacessivel - graph sync ignorado.")
            return {"skipped": True}

    stats = {"modules_created": 0, "relationships": 0, "errors": []}
    batch: list[tuple[str, dict]] = []

    for mod in modules:
        module_id = mod["source_file"]
        module_type = mod.get("module_type", "unknown")
        repo = mod.get("repo", "unknown")
        domain = mod.get("domain", "general")

        # Extract a human-readable name
        name = (
            mod.get("service_name")
            or mod.get("component_name")
            or mod.get("model_name")
            or Path(mod["source_file"]).stem
        )

        desc = mod.get("content", "")[:200]

        batch.append((queries.UPSERT_MODULE, {
            "id": module_id,
            "name": name,
            "type": module_type,
            "repo": repo,
            "file_path": mod["source_file"],
            "language": mod.get("language", "unknown"),
            "domain": domain,
            "description": desc,
        }))
        stats["modules_created"] += 1

    if not batch:
        return stats

    try:
        graph.execute_write_batch(batch)
    except Exception as e:
        stats["errors"].append(str(e))
        logger.error("CRM graph sync batch failed: %s", e)

    logger.info(
        "CRM GraphSync: %d modules created, %d errors",
        stats["modules_created"],
        len(stats["errors"]),
    )
    return stats


def extract_all_from_directory(search_dir: str | Path, repo_name: str = "") -> list[dict]:
    """
    Busca recursivamente todos os arquivos de codigo em um diretorio
    e extrai chunks de cada um.

    Args:
        search_dir: Diretorio raiz para busca.
        repo_name: Nome do repo para metadata.

    Returns:
        Lista de todos os chunks extraidos.
    """
    search_path = Path(search_dir)
    all_chunks: list[dict] = []
    extensions = {".js", ".ts", ".tsx", ".jsx"}

    for ext in extensions:
        for code_file in search_path.rglob(f"*{ext}"):
            if any(p in code_file.parts for p in ("node_modules", "dist", "build", ".next")):
                continue

            chunks = detect_and_extract(code_file)
            for chunk in chunks:
                if repo_name:
                    chunk["repo"] = repo_name
            all_chunks.extend(chunks)

    logger.info("Total: %d chunks extraidos de %s", len(all_chunks), search_dir)
    return all_chunks
