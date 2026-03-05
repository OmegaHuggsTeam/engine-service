"""
ConceptExtractor - Extrai conceitos de texto.
Primeiro tenta rule-based (match contra conceitos conhecidos no grafo).
Se < 2 conceitos encontrados, faz LLM extraction via chat_completion().
"""

import hashlib
import json
import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)

# Cache em memoria para conceitos ja extraidos
_concept_cache: dict[str, list[dict]] = {}


def _hash_text(text: str) -> str:
    return hashlib.md5(text[:500].encode()).hexdigest()


def extract_concepts_rule_based(
    text: str,
    known_concepts: list[str] | None = None,
) -> list[dict]:
    """
    Extrai conceitos via rule-based matching.
    Retorna lista de dicts com name, confidence, source='extracted'.
    """
    text_lower = text.lower()
    found = []

    # Match contra conceitos conhecidos do grafo
    if known_concepts:
        for concept_name in known_concepts:
            if concept_name.lower() in text_lower:
                found.append({
                    "name": concept_name,
                    "confidence": 0.9,
                    "source": "extracted",
                })

    # Patterns comuns de tecnologia/dominio
    tech_patterns = [
        r'\b(python|javascript|typescript|rust|go|java|c\+\+)\b',
        r'\b(selenium|chromadb|neo4j|fastapi|flask|django|react|vue)\b',
        r'\b(docker|kubernetes|aws|gcp|azure)\b',
        r'\b(rag|llm|gpt|embedding|vector|transformer|bert)\b',
        r'\b(api|rest|graphql|webhook|websocket)\b',
        r'\b(tdd|ci/cd|devops|mlops|gitops)\b',
        r'\b(marketing|seo|analytics|funnel|conversion)\b',
        r'\b(postgresql|mongodb|redis|sqlite|supabase)\b',
    ]

    for pattern in tech_patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            name = match.strip()
            if name and not any(c["name"].lower() == name for c in found):
                found.append({
                    "name": name,
                    "confidence": 0.7,
                    "source": "extracted",
                })

    return found


def extract_concepts_llm(text: str) -> list[dict]:
    """
    Extrai conceitos via LLM (fallback quando rule-based encontra < 2).
    Usa chat_completion() existente.
    """
    try:
        from src.utils.llm_client import chat_completion

        prompt = (
            "Extract the main technical concepts, technologies, and domain topics "
            "from this text. Return ONLY a JSON array of objects with 'name' and 'domain' fields. "
            "Example: [{\"name\": \"RAG\", \"domain\": \"AI\"}, {\"name\": \"Neo4j\", \"domain\": \"database\"}]\n\n"
            f"Text: {text[:1000]}"
        )

        response = chat_completion([
            {"role": "system", "content": "You are a concept extractor. Return only valid JSON."},
            {"role": "user", "content": prompt},
        ])

        # Parse JSON da resposta
        # Tenta extrair JSON de dentro da resposta
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            concepts_raw = json.loads(json_match.group())
            return [
                {
                    "name": c.get("name", ""),
                    "domain": c.get("domain", "general"),
                    "confidence": 0.8,
                    "source": "extracted",
                }
                for c in concepts_raw
                if c.get("name")
            ]
    except Exception as e:
        logger.warning(f"LLM concept extraction failed: {e}")

    return []


def extract_concepts(
    text: str,
    known_concepts: list[str] | None = None,
    min_rule_based: int = 2,
    use_cache: bool = True,
) -> list[dict]:
    """
    Extrai conceitos de texto usando estrategia hibrida:
    1. Rule-based matching (rapido, sem custo)
    2. LLM fallback se < min_rule_based conceitos encontrados

    Args:
        text: Texto para extrair conceitos
        known_concepts: Lista de nomes de conceitos ja conhecidos no grafo
        min_rule_based: Minimo de conceitos rule-based antes de usar LLM
        use_cache: Usar cache em memoria

    Returns:
        Lista de dicts com name, confidence, source, domain (opcional)
    """
    if not text or not text.strip():
        return []

    cache_key = _hash_text(text)
    if use_cache and cache_key in _concept_cache:
        return _concept_cache[cache_key]

    # Tenta rule-based primeiro
    concepts = extract_concepts_rule_based(text, known_concepts)

    # LLM fallback se poucos conceitos
    if len(concepts) < min_rule_based:
        llm_concepts = extract_concepts_llm(text)
        # Merge sem duplicatas
        existing_names = {c["name"].lower() for c in concepts}
        for c in llm_concepts:
            if c["name"].lower() not in existing_names:
                concepts.append(c)
                existing_names.add(c["name"].lower())

    if use_cache:
        _concept_cache[cache_key] = concepts

    return concepts


def get_known_concept_names(graph_manager: Optional[object] = None) -> list[str]:
    """Busca nomes de conceitos ja existentes no grafo."""
    if graph_manager is None:
        return []
    try:
        results = graph_manager.execute_read(
            "MATCH (c:Concept) RETURN c.name AS name LIMIT 1000"
        )
        return [r["name"] for r in results if r.get("name")]
    except Exception:
        return []
