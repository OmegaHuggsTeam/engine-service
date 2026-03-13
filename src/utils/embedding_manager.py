"""
EmbeddingManager - Gerenciador multi-embedding para ChromaDB.
Suporta N modelos de embedding simultaneamente, cada um com sua colecao.
Busca em todas as colecoes e faz merge com cross-model boost.

Singleton thread-safe via from_env() (mesmo padrao do GraphManager).
"""

import logging
import os
import threading
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

_instance = None
_instance_lock = threading.Lock()

# Cross-model boost: resultados encontrados por multiplos modelos ganham +10%
CROSS_MODEL_BOOST = 0.10

# Registro de modelos suportados: nome -> {model_name, dimensions, type}
MODEL_REGISTRY = {
    "openai": {
        "model_name": "text-embedding-3-small",
        "dimensions": 1536,
        "type": "openai",
    },
    "nomic": {
        "model_name": "nomic-embed-text-v1.5",
        "dimensions": 768,
        "type": "sentence_transformer",
    },
    "minilm": {
        "model_name": "all-MiniLM-L6-v2",
        "dimensions": 384,
        "type": "sentence_transformer",
    },
}


def _make_collection_name(model_name: str) -> str:
    """Gera nome da colecao ChromaDB para um modelo."""
    return f"course_chunks_{model_name}"


class EmbeddingManager:
    """
    Gerenciador multi-embedding thread-safe.
    Cada modelo de embedding tem sua propria colecao ChromaDB.
    """

    def __init__(self, model_names: list[str]):
        """
        Args:
            model_names: Lista de nomes de modelos (ex: ["openai", "nomic"]).
                         Devem estar no MODEL_REGISTRY.
        """
        self._lock = threading.Lock()
        self._models: dict[str, dict] = {}
        self._collections: dict[str, object] = {}

        for name in model_names:
            name = name.strip().lower()
            if name not in MODEL_REGISTRY:
                logger.warning(f"EmbeddingManager: modelo '{name}' nao encontrado no registry, ignorando")
                continue
            self._models[name] = MODEL_REGISTRY[name]

        if not self._models:
            raise ValueError(
                f"Nenhum modelo valido encontrado. Modelos disponiveis: {list(MODEL_REGISTRY.keys())}"
            )

        logger.info(f"EmbeddingManager initialized with models: {list(self._models.keys())}")

    @classmethod
    def from_env(cls) -> "EmbeddingManager":
        """
        Cria EmbeddingManager a partir do env var EMBEDDING_MODELS.
        Singleton thread-safe (mesmo padrao do GraphManager).
        """
        global _instance
        with _instance_lock:
            if _instance is None:
                env_models = os.getenv("EMBEDDING_MODELS", "").strip()
                if not env_models:
                    # Fallback: detectar modelo atual do vector_db
                    if os.getenv("OPENAI_API_KEY"):
                        model_names = ["openai"]
                    else:
                        model_names = ["minilm"]
                else:
                    model_names = [m.strip() for m in env_models.split(",") if m.strip()]

                _instance = cls(model_names)
            return _instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton (para testes)."""
        global _instance
        with _instance_lock:
            _instance = None

    def _get_client(self):
        """
        Retorna o cliente ChromaDB.
        Reutiliza o mesmo padrao de vector_db._get_client().
        """
        import chromadb

        host = os.getenv("CHROMA_HOST")
        if not host and bool(os.getenv("KUBERNETES_SERVICE_HOST")):
            host = "chroma"

        if host:
            port = int(os.getenv("CHROMA_PORT", "8000"))
            return chromadb.HttpClient(host=host, port=port)

        db_path = PROJECT_ROOT / "db" / "chroma"
        db_path.mkdir(parents=True, exist_ok=True)
        return chromadb.PersistentClient(path=str(db_path))

    def _get_embedding_function(self, model_name: str):
        """Retorna a funcao de embedding para o modelo especificado."""
        from chromadb.utils import embedding_functions

        info = self._models[model_name]

        if info["type"] == "openai":
            return embedding_functions.OpenAIEmbeddingFunction(
                model_name=info["model_name"],
            )
        elif info["type"] == "sentence_transformer":
            return embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=info["model_name"],
            )
        else:
            raise ValueError(f"Tipo de embedding desconhecido: {info['type']}")

    def _get_collection(self, model_name: str):
        """Obtem ou cria a colecao ChromaDB para um modelo."""
        with self._lock:
            if model_name not in self._collections:
                client = self._get_client()
                ef = self._get_embedding_function(model_name)
                collection_name = _make_collection_name(model_name)
                self._collections[model_name] = client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=ef,
                    metadata={"hnsw:space": "cosine"},
                )
            return self._collections[model_name]

    def _chunk_to_metadata(self, chunk: dict) -> dict[str, str]:
        """Converte chunk para metadata ChromaDB (forca tudo para string)."""
        meta = {}
        for k, v in chunk.items():
            if k == "content":
                continue
            meta[str(k)] = "" if v is None else str(v)
        return meta

    def _result_to_chunk(self, doc: str, meta: dict) -> dict:
        """Reconstroi dict do chunk a partir do resultado ChromaDB."""
        return {"content": doc or "", **meta}

    def add_chunks(self, chunks: list[dict], batch_size: int = 100) -> dict[str, int]:
        """
        Insere chunks em TODAS as colecoes ativas.
        Remove chunks existentes do mesmo source_file antes de inserir.

        Returns:
            Dict {model_name: count_inserted} para cada modelo
        """
        if not chunks:
            return {name: 0 for name in self._models}

        results = {}

        for model_name in self._models:
            try:
                collection = self._get_collection(model_name)

                # Remove chunks do mesmo source_file (evita duplicatas)
                source_files = {str(c.get("source_file", "unknown")) for c in chunks}
                for sf in source_files:
                    try:
                        existing = collection.get(where={"source_file": sf}, include=[])
                        if existing["ids"]:
                            collection.delete(ids=existing["ids"])
                    except Exception:
                        pass

                # Insere em batches
                for i in range(0, len(chunks), batch_size):
                    batch = chunks[i : i + batch_size]
                    ids = [
                        f"{str(c.get('source_file', 'unknown'))}_{c.get('chunk_index', j)}"
                        for j, c in enumerate(batch)
                    ]
                    documents = [str(c.get("content", "")) for c in batch]
                    metadatas = [self._chunk_to_metadata(c) for c in batch]
                    metadatas = [
                        {str(k): ("" if v is None else str(v)) for k, v in m.items()}
                        for m in metadatas
                    ]
                    collection.add(ids=ids, documents=documents, metadatas=metadatas)

                results[model_name] = len(chunks)
                logger.info(f"[OK] {len(chunks)} chunks integrados ao ChromaDB (modelo: {model_name})")

            except Exception as e:
                logger.error(f"Erro ao inserir chunks no modelo {model_name}: {e}")
                results[model_name] = 0

        return results

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """
        Busca em TODAS as colecoes ativas e faz merge com cross-model boost.
        Resultados encontrados por multiplos modelos recebem +10%.

        Returns:
            Lista de chunks ordenada por score, deduplicada
        """
        if not query or not query.strip():
            return []

        results_by_model: dict[str, list[dict]] = {}

        for model_name in self._models:
            try:
                model_results = self._search_single_model(query, model_name, top_k)
                if model_results:
                    results_by_model[model_name] = model_results
            except Exception as e:
                logger.warning(f"Search failed for model {model_name}: {e}")

        if not results_by_model:
            return []

        # Usar ResultMerger para combinar resultados
        from src.neural_link.rag.result_merger import ResultMerger

        merger = ResultMerger()

        # Pesos iguais para cada modelo
        num_models = len(results_by_model)
        weights = {name: 1.0 / num_models for name in results_by_model}

        merged = merger.merge(results_by_model, weights, top_k)

        return merged

    def search_with_model(self, query: str, model: str, top_k: int = 5) -> list[dict]:
        """
        Busca em uma colecao especifica (modelo unico).

        Args:
            query: Texto da busca
            model: Nome do modelo (ex: "openai", "nomic", "minilm")
            top_k: Numero maximo de resultados

        Returns:
            Lista de chunks com score
        """
        model = model.strip().lower()
        if model not in self._models:
            logger.warning(f"Modelo '{model}' nao esta ativo. Ativos: {list(self._models.keys())}")
            return []

        return self._search_single_model(query, model, top_k)

    def _search_single_model(self, query: str, model_name: str, top_k: int) -> list[dict]:
        """Busca semantica em uma colecao especifica."""
        collection = self._get_collection(model_name)
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
            chunk = self._result_to_chunk(doc, meta_clean)
            # ChromaDB cosine distance: 0 = identical, 2 = opposite
            # Convert to similarity score: 1 - (distance / 2)
            chunk["score"] = max(0.0, min(1.0, 1.0 - (dist / 2.0)))
            chunk["engine"] = model_name
            chunks.append(chunk)

        return chunks

    def list_models(self) -> list[dict]:
        """
        Lista modelos ativos com informacoes.

        Returns:
            Lista de dicts com {name, dimensions, collection_name, chunk_count}
        """
        models_info = []

        for name, info in self._models.items():
            collection_name = _make_collection_name(name)
            chunk_count = 0

            try:
                collection = self._get_collection(name)
                chunk_count = collection.count()
            except Exception as e:
                logger.warning(f"Erro ao contar chunks do modelo {name}: {e}")

            models_info.append({
                "name": name,
                "dimensions": info["dimensions"],
                "collection_name": collection_name,
                "chunk_count": chunk_count,
            })

        return models_info

    def remove_model(self, model: str) -> bool:
        """
        Remove a colecao de um modelo especifico.

        Args:
            model: Nome do modelo a remover

        Returns:
            True se removido com sucesso, False caso contrario
        """
        model = model.strip().lower()
        if model not in self._models:
            logger.warning(f"Modelo '{model}' nao esta ativo")
            return False

        try:
            client = self._get_client()
            collection_name = _make_collection_name(model)
            client.delete_collection(collection_name)

            # Remove do cache interno
            with self._lock:
                self._collections.pop(model, None)
                self._models.pop(model, None)

            logger.info(f"Modelo '{model}' removido (colecao: {collection_name})")
            return True

        except Exception as e:
            logger.error(f"Erro ao remover modelo {model}: {e}")
            return False

    @property
    def model_count(self) -> int:
        """Numero de modelos ativos."""
        return len(self._models)

    @property
    def model_names(self) -> list[str]:
        """Nomes dos modelos ativos."""
        return list(self._models.keys())
