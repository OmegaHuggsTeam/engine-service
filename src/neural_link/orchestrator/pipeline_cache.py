"""
PipelineCache - Two-tier cache for orchestrator responses.

Tier 1: Exact SHA-256 hash match (fast, zero-cost lookup)
Tier 2: Semantic similarity via sentence-transformers (catches paraphrases)

Follows GroqRouter cache pattern (TTL, FIFO eviction, max entries).
"""

import hashlib
import logging
import time
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Configuration
EXACT_TTL_SECONDS = 600       # 10 minutes
SEMANTIC_TTL_SECONDS = 300    # 5 minutes
MAX_EXACT_ENTRIES = 512
MAX_SEMANTIC_ENTRIES = 256
SEMANTIC_THRESHOLD = 0.92     # Cosine similarity threshold


@dataclass
class _ExactEntry:
    answer: str
    expires_at: float


@dataclass
class _SemanticEntry:
    embedding: object  # torch.Tensor or numpy array
    query: str
    answer: str
    expires_at: float


class PipelineCache:
    """
    Two-tier cache for NeuralLinkOrchestrator responses.

    Tier 1 (exact): SHA-256 hash of normalized query.
    Tier 2 (semantic): Cosine similarity >= threshold using sentence-transformers.
    """

    def __init__(
        self,
        similarity_threshold: float = SEMANTIC_THRESHOLD,
        exact_ttl: float = EXACT_TTL_SECONDS,
        semantic_ttl: float = SEMANTIC_TTL_SECONDS,
    ):
        self._exact: dict[str, _ExactEntry] = {}
        self._semantic: list[_SemanticEntry] = []
        self._threshold = similarity_threshold
        self._exact_ttl = exact_ttl
        self._semantic_ttl = semantic_ttl
        self._encoder = None  # lazy load
        self._hits = 0
        self._misses = 0

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    @property
    def stats(self) -> dict:
        return {
            "exact_entries": len(self._exact),
            "semantic_entries": len(self._semantic),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self.hit_rate, 3),
        }

    def get(self, query: str) -> Optional[str]:
        """Try exact match first, then semantic. Returns cached answer or None."""
        now = time.monotonic()

        # Tier 1: exact hash
        key = self._hash_key(query)
        entry = self._exact.get(key)
        if entry is not None:
            if now < entry.expires_at:
                self._hits += 1
                logger.debug("Pipeline cache HIT (exact) for query hash %s", key[:8])
                return entry.answer
            else:
                del self._exact[key]

        # Tier 2: semantic similarity
        if self._semantic:
            answer = self._semantic_lookup(query, now)
            if answer is not None:
                self._hits += 1
                logger.debug("Pipeline cache HIT (semantic) for query: %s", query[:50])
                return answer

        self._misses += 1
        return None

    def put(self, query: str, answer: str) -> None:
        """Store in both tiers."""
        now = time.monotonic()

        # Tier 1: exact
        key = self._hash_key(query)
        self._exact[key] = _ExactEntry(
            answer=answer,
            expires_at=now + self._exact_ttl,
        )
        self._evict_exact()

        # Tier 2: semantic
        try:
            encoder = self._get_encoder()
            if encoder is not None:
                embedding = encoder.encode(query, convert_to_tensor=False)
                self._semantic.append(_SemanticEntry(
                    embedding=embedding,
                    query=query,
                    answer=answer,
                    expires_at=now + self._semantic_ttl,
                ))
                self._evict_semantic(now)
        except Exception as e:
            logger.debug("Semantic cache put failed: %s", e)

    def clear(self) -> None:
        """Clear all cache entries."""
        self._exact.clear()
        self._semantic.clear()
        self._hits = 0
        self._misses = 0

    def _hash_key(self, query: str) -> str:
        normalized = query.strip().lower()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:16]

    def _get_encoder(self):
        """Lazy load sentence-transformers encoder."""
        if self._encoder is None:
            try:
                from sentence_transformers import SentenceTransformer
                self._encoder = SentenceTransformer("all-MiniLM-L6-v2")
                logger.info("Loaded sentence-transformers encoder for semantic cache")
            except ImportError:
                logger.debug("sentence-transformers not available, semantic cache disabled")
                self._encoder = False  # sentinel to avoid retry
        return self._encoder if self._encoder is not False else None

    def _semantic_lookup(self, query: str, now: float) -> Optional[str]:
        """Find semantically similar cached query."""
        try:
            encoder = self._get_encoder()
            if encoder is None:
                return None

            import numpy as np
            q_emb = encoder.encode(query, convert_to_tensor=False)

            best_score = 0.0
            best_answer = None

            for entry in self._semantic:
                if now >= entry.expires_at:
                    continue
                # Cosine similarity
                dot = float(np.dot(q_emb, entry.embedding))
                norm_q = float(np.linalg.norm(q_emb))
                norm_e = float(np.linalg.norm(entry.embedding))
                if norm_q == 0 or norm_e == 0:
                    continue
                sim = dot / (norm_q * norm_e)
                if sim >= self._threshold and sim > best_score:
                    best_score = sim
                    best_answer = entry.answer

            return best_answer

        except Exception as e:
            logger.debug("Semantic lookup failed: %s", e)
            return None

    def _evict_exact(self) -> None:
        """FIFO eviction for exact cache."""
        while len(self._exact) > MAX_EXACT_ENTRIES:
            oldest_key = next(iter(self._exact))
            del self._exact[oldest_key]

    def _evict_semantic(self, now: float) -> None:
        """Remove expired + FIFO eviction for semantic cache."""
        # Remove expired
        self._semantic = [e for e in self._semantic if now < e.expires_at]
        # FIFO if still over limit
        while len(self._semantic) > MAX_SEMANTIC_ENTRIES:
            self._semantic.pop(0)
