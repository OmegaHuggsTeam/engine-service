"""
Workflow Searcher - Busca workflows n8n via ChromaDB.

Indexa nomes e descrições (nós) de todos os JSONs em data/workflows/.
Usa coleção ChromaDB dedicada 'workflow_search' para busca semântica.

Uso:
  python tools/workflow_searcher.py index     # Indexar workflows
  python tools/workflow_searcher.py search airtable
  python tools/workflow_searcher.py search "telegram webhook" --top 5
"""

import os
os.environ["PYDANTIC_SKIP_VALIDATION"] = "1"

import argparse
import json
import sys
from pathlib import Path

# Reutiliza ChromaDB do projeto
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

WORKFLOWS_DIR = PROJECT_ROOT / "data" / "workflows"
COLLECTION_NAME = "workflow_search"


def _get_collection():
    """Obtém coleção ChromaDB para workflow search."""
    from src.utils.vector_db import _get_client, _get_embedding_function
    import chromadb

    client = _get_client()
    ef = _get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def _build_document(workflow: dict, rel_path: str) -> str:
    """
    Constrói documento searchable a partir do workflow.
    Inclui: nome, descrição, nomes e notas dos nós.
    """
    parts = []

    name = workflow.get("name") or workflow.get("meta", {}).get("name")
    if name:
        parts.append(str(name))

    desc = workflow.get("description")
    if desc:
        parts.append(str(desc))

    for node in workflow.get("nodes", []):
        n_name = node.get("name")
        if n_name:
            parts.append(str(n_name))
        n_type = node.get("type", "")
        if n_type and "n8n-nodes-base." in str(n_type):
            # Ex: n8n-nodes-base.telegramTrigger -> telegram trigger
            service = str(n_type).replace("n8n-nodes-base.", "").replace("_", " ")
            parts.append(service)
        n_notes = node.get("notes")
        if n_notes:
            parts.append(str(n_notes))

    # Categoria da pasta (ex: Activecampaign, Airtable)
    if "/" in rel_path:
        category = rel_path.split("/")[0]
        parts.append(category)

    return " ".join(parts) if parts else rel_path


def index_workflows(workflows_dir: Path | None = None) -> int:
    """
    Indexa todos os workflows em data/workflows/ no ChromaDB.
    Retorna quantidade de workflows indexados.
    """
    base = workflows_dir or WORKFLOWS_DIR
    if not base.exists():
        print(f"Pasta não encontrada: {base}")
        return 0

    collection = _get_collection()

    # Limpar coleção existente para re-indexação
    try:
        existing = collection.get(include=[])
        if existing.get("ids"):
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    paths = sorted(base.rglob("*.json"))
    ids = []
    documents = []
    metadatas = []

    for fp in paths:
        try:
            data = json.loads(fp.read_text(encoding="utf-8"))
        except Exception:
            continue

        if not isinstance(data, dict) or "nodes" not in data:
            continue

        rel_path = str(fp.relative_to(base))
        doc = _build_document(data, rel_path)
        wf_id = rel_path.replace("/", "_").replace("\\", "_")
        ids.append(wf_id)
        documents.append(doc)
        name = data.get("name") or data.get("meta", {}).get("name") or fp.stem
        metadatas.append({
            "path": rel_path,
            "name": str(name)[:200],
        })

    if not ids:
        print("Nenhum workflow válido encontrado.")
        return 0

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    print(f"[OK] {len(ids)} workflows indexados em ChromaDB ({COLLECTION_NAME})")
    return len(ids)


def search_workflows(query: str, top_k: int = 3) -> list[dict]:
    """
    Busca workflows por similaridade semântica.
    Retorna lista de dicts: path, name, score.
    """
    collection = _get_collection()
    total = collection.count()
    if total == 0:
        return []
    result = collection.query(
        query_texts=[query],
        n_results=min(top_k, total),
        include=["metadatas", "distances"],
    )

    if not result or not result.get("metadatas") or not result["metadatas"][0]:
        return []

    items = []
    metas = result["metadatas"][0]
    distances = result.get("distances", [[]])[0] or []

    for i, meta in enumerate(metas):
        meta = meta or {}
        dist = distances[i] if i < len(distances) else 0
        score = max(0.0, min(1.0, 1.0 - (dist / 2.0)))  # cosine distance -> similarity
        items.append({
            "path": meta.get("path", ""),
            "name": meta.get("name", ""),
            "score": round(score, 3),
        })

    return items


def main() -> int:
    parser = argparse.ArgumentParser(description="Busca workflows n8n via ChromaDB")
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("index", help="Indexar workflows em data/workflows/")
    sp = sub.add_parser("search", help="Buscar workflows")
    sp.add_argument("query", help="Termo de busca (ex: airtable, telegram)")
    sp.add_argument("--top", type=int, default=3, help="Quantidade de resultados (default: 3)")
    args = parser.parse_args()

    if args.cmd == "index":
        count = index_workflows()
        return 0 if count > 0 else 1

    if args.cmd == "search":
        results = search_workflows(args.query, args.top)
        if not results:
            print("Nenhum workflow encontrado.")
            return 0
        for i, r in enumerate(results, 1):
            print(f"{i}. {r['name'][:60]}...")
            print(f"   path: {r['path']} (score: {r['score']})")
        return 0

    return 1


if __name__ == "__main__":
    sys.exit(main())
