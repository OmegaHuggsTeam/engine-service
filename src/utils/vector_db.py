"""
Gerenciador do ChromaDB - Vector Database central.
Embeddings: OpenAI (se tiver créditos) ou all-MiniLM-L6-v2 local (100% grátis).

Multi-Embedding: Se EMBEDDING_MODELS tiver 2+ modelos (ex: "openai,nomic"),
delega add_chunks/search para EmbeddingManager. Caso contrario, comportamento
identico ao original (single-model).
"""

import os

os.environ["PYDANTIC_SKIP_VALIDATION"] = "1"

import logging
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_ROOT / "db" / "chroma"
COLLECTION_NAME = "course_chunks"
SELUM_ERRORS_COLLECTION = "selum_errors"

load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)


def _is_multi_embedding() -> bool:
    """Verifica se multi-embedding esta ativo (2+ modelos no EMBEDDING_MODELS)."""
    env_models = os.getenv("EMBEDDING_MODELS", "").strip()
    if not env_models:
        return False
    models = [m.strip() for m in env_models.split(",") if m.strip()]
    return len(models) >= 2


def _get_embedding_manager():
    """Retorna EmbeddingManager singleton (lazy import)."""
    from src.utils.embedding_manager import EmbeddingManager

    return EmbeddingManager.from_env()


def _is_kubernetes() -> bool:
    """Detecta execução dentro de um cluster Kubernetes (K3s)."""
    return bool(os.getenv("KUBERNETES_SERVICE_HOST"))


def _get_chroma_host() -> str | None:
    """
    Retorna host do ChromaDB para modo servidor.
    Fallback: em K8s usa 'chroma' (DNS interno CoreDNS).
    """
    host = os.getenv("CHROMA_HOST")
    if host:
        return host
    if _is_kubernetes():
        return "chroma"
    return None


def _get_client():
    """
    Retorna o cliente ChromaDB.
    Se CHROMA_HOST estiver definido (ou fallback K8s 'chroma'), usa HttpClient.
    Caso contrário, usa PersistentClient (modo local).
    """
    import chromadb

    host = _get_chroma_host()
    if host:
        port = int(os.getenv("CHROMA_PORT", "8000"))
        return chromadb.HttpClient(host=host, port=port)
    DB_PATH.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=str(DB_PATH))


def _get_embedding_function():
    """
    Retorna a função de embedding.
    Prioridade: OpenAI (se OPENAI_API_KEY) -> all-MiniLM-L6-v2 local (grátis).
    """
    from chromadb.utils import embedding_functions

    if os.getenv("OPENAI_API_KEY"):
        return embedding_functions.OpenAIEmbeddingFunction(
            model_name="text-embedding-3-small",
        )
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name="all-MiniLM-L6-v2",
    )


def get_collection():
    """Obtém ou cria a coleção de chunks."""
    client = _get_client()
    ef = _get_embedding_function()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def _chunk_to_metadata(chunk: dict) -> dict[str, str]:
    """
    Converte chunk para metadata ChromaDB.
    Força TODOS os valores a string (evita 'unable to infer type' no Python 3.14).
    """
    meta = {}
    for k, v in chunk.items():
        if k == "content":
            continue
        meta[str(k)] = "" if v is None else str(v)
    return meta


def _result_to_chunk(doc: str, meta: dict) -> dict:
    """Reconstrói dict do chunk a partir do resultado ChromaDB."""
    chunk = {"content": doc or "", **meta}
    return chunk


def add_chunks(chunks: list[dict], batch_size: int = 100) -> int:
    """
    Insere chunks na coleção ChromaDB.
    Usa source_file + chunk_index como id. Remove chunks existentes do mesmo
    source antes de inserir (para re-processamento).

    Se EMBEDDING_MODELS tiver 2+ modelos, delega para EmbeddingManager
    (insere em todas as colecoes). Retorna total de chunks inseridos.

    Returns:
        Número de chunks inseridos
    """
    if not chunks:
        return 0

    # Multi-embedding: delega para EmbeddingManager
    if _is_multi_embedding():
        try:
            manager = _get_embedding_manager()
            results = manager.add_chunks(chunks, batch_size=batch_size)
            # Retorna o max inserido (todos devem ser iguais se sem erro)
            total = max(results.values()) if results else 0
            logger.info(f"[Multi-Embedding] {total} chunks inseridos em {len(results)} modelos")
            return total
        except Exception as e:
            logger.error(f"Multi-embedding add_chunks falhou, fallback single-model: {e}")

    collection = get_collection()

    # Remove chunks do mesmo source_file para evitar duplicatas ao re-processar
    source_files = {str(c.get("source_file", "unknown")) for c in chunks}
    for sf in source_files:
        try:
            existing = collection.get(where={"source_file": sf}, include=[])
            if existing["ids"]:
                collection.delete(ids=existing["ids"])
        except Exception:
            pass

    for i in range(0, len(chunks), batch_size):
        batch = chunks[i : i + batch_size]
        ids = [
            f"{str(c.get('source_file', 'unknown'))}_{c.get('chunk_index', j)}"
            for j, c in enumerate(batch)
        ]
        documents = [str(c.get("content", "")) for c in batch]
        metadatas = [_chunk_to_metadata(c) for c in batch]
        # Dupla garantia: força chaves e valores a string (Python 3.14 / ChromaDB)
        metadatas = [
            {str(k): ("" if v is None else str(v)) for k, v in m.items()} for m in metadatas
        ]
        collection.add(ids=ids, documents=documents, metadatas=metadatas)

    print(f"[OK] {len(chunks)} chunks integrados ao ChromaDB")
    return len(chunks)


def search(query: str, top_k: int = 5) -> list[dict]:
    """
    Busca semântica por similaridade usando embeddings.

    Se EMBEDDING_MODELS tiver 2+ modelos, delega para EmbeddingManager
    (busca em todas as colecoes e faz merge). Caso contrario, busca single-model.

    Returns:
        Lista de chunks (dicts com content, source_file, etc.)
    """
    # Multi-embedding: delega para EmbeddingManager
    if _is_multi_embedding():
        try:
            manager = _get_embedding_manager()
            return manager.search(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Multi-embedding search falhou, fallback single-model: {e}")

    collection = get_collection()
    result = collection.query(query_texts=[query], n_results=top_k)

    if not result or not result["documents"] or not result["documents"][0]:
        return []

    chunks = []
    docs = result["documents"][0]
    metas = result["metadatas"][0] if result.get("metadatas") else [{}] * len(docs)

    for doc, meta in zip(docs, metas):
        meta_clean = {k: v for k, v in (meta or {}).items() if k != "content"}
        chunks.append(_result_to_chunk(doc, meta_clean))

    return chunks


def search_with_scores(query: str, top_k: int = 5) -> list[dict]:
    """
    Busca semantica retornando scores junto aos resultados.
    Cada dict contem: content, source_file, ..., score (0-1, maior = mais relevante).

    Se EMBEDDING_MODELS tiver 2+ modelos, delega para EmbeddingManager
    (que ja retorna scores normalizados e merged).
    """
    # Multi-embedding: delega para EmbeddingManager (search ja retorna scores)
    if _is_multi_embedding():
        try:
            manager = _get_embedding_manager()
            return manager.search(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Multi-embedding search_with_scores falhou, fallback single-model: {e}")

    collection = get_collection()
    result = collection.query(
        query_texts=[query],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    if not result or not result["documents"] or not result["documents"][0]:
        return []

    chunks = []
    docs = result["documents"][0]
    metas = result["metadatas"][0] if result.get("metadatas") else [{}] * len(docs)
    distances = result["distances"][0] if result.get("distances") else [0.0] * len(docs)

    for doc, meta, dist in zip(docs, metas, distances):
        meta_clean = {k: v for k, v in (meta or {}).items() if k != "content"}
        chunk = _result_to_chunk(doc, meta_clean)
        # ChromaDB cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity score: 1 - (distance / 2)
        chunk["score"] = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
        chunks.append(chunk)

    return chunks


def get_all() -> list[dict]:
    """Retorna todos os chunks da coleção."""
    collection = get_collection()
    result = collection.get(include=["documents", "metadatas"])

    if not result or not result["documents"]:
        return []

    return [
        _result_to_chunk(doc, meta or {})
        for doc, meta in zip(result["documents"], result["metadatas"] or [])
    ]


def get_by_category(chunk_type: str) -> list[dict]:
    """
    Retorna chunks filtrados por categoria (ex: 'n8n_templates', 'Uncategorized').
    Tenta ChromaDB where filter; fallback: filtra get_all() por category, agent_specialty ou source_file.
    """
    collection = get_collection()
    try:
        result = collection.get(
            where={"category": chunk_type},
            include=["documents", "metadatas"],
        )
        if result and result.get("documents"):
            return [
                _result_to_chunk(doc, meta or {})
                for doc, meta in zip(result["documents"], result["metadatas"] or [])
            ]
    except Exception:
        pass

    # Fallback: filtra get_all por category, agent_specialty ou source_file
    all_chunks = get_all()
    ct_lower = chunk_type.lower()
    return [
        c
        for c in all_chunks
        if (
            (c.get("category") or "").lower() == ct_lower
            or (c.get("agent_specialty") or "").lower() == ct_lower
            or ct_lower in (c.get("source_file") or "").lower()
        )
    ]


def count() -> int:
    """Retorna a quantidade de chunks na coleção."""
    collection = get_collection()
    return collection.count()


def get_source_files() -> set[str]:
    """Retorna o conjunto de source_file presentes no ChromaDB (arquivos já processados)."""
    collection = get_collection()
    result = collection.get(include=["metadatas"])
    if not result or not result.get("metadatas"):
        return set()
    sources = set()
    for meta in result["metadatas"] or []:
        sf = (meta or {}).get("source_file")
        if sf:
            sources.add(str(sf))
    return sources


def get_agent_chunk_counts() -> dict[str, int]:
    """Retorna {agent_specialty: count} para visão por agente."""
    collection = get_collection()
    result = collection.get(include=["metadatas"])
    if not result or not result.get("metadatas"):
        return {}
    counts = {}
    for meta in result["metadatas"] or []:
        agent = (meta or {}).get("agent_specialty") or "Uncategorized"
        agent = str(agent) if agent else "Uncategorized"
        counts[agent] = counts.get(agent, 0) + 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def clear():
    """Remove todos os chunks da coleção (use com cuidado)."""
    client = _get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass


def _get_errors_collection():
    """Coleção para snapshots de erro do Modo Cartógrafo (Selum)."""
    client = _get_client()
    ef = _get_embedding_function()
    return client.get_or_create_collection(
        name=SELUM_ERRORS_COLLECTION,
        embedding_function=ef,
        metadata={"hnsw:space": "cosine"},
    )


def add_error_snapshot(content: str, metadata: dict | None = None) -> None:
    """
    Registra snapshot de erro no RAG (coleção selum_errors).
    Usado pelo Modo Cartógrafo para não desistir no primeiro erro.
    """
    collection = _get_errors_collection()
    meta = metadata or {}
    meta = {str(k): ("" if v is None else str(v)) for k, v in meta.items()}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    uid = f"err_{ts}_{abs(hash(content)) % 10**8}"
    collection.add(ids=[uid], documents=[content], metadatas=[meta])
