"""
Agente de Marketing - Chatbot RAG baseado nos chunks do curso.
Responde dúvidas usando exclusivamente o material carregado.
"""

import json
from pathlib import Path

from dotenv import load_dotenv

# Diretórios do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent
CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"

load_dotenv(PROJECT_ROOT / ".env")

SYSTEM_PROMPT = """Você é um Diretor de Marketing de elite. Seu conhecimento é 100% baseado no material do curso fornecido no contexto abaixo. Use uma linguagem profissional, estratégica e voltada para resultados. Se a resposta não estiver no contexto, diga honestamente: 'Essa estratégia não foi abordada no material do curso'. Nunca invente informações fora do contexto."""

TOP_K_CHUNKS = 5
MODEL = "llama-3.3-70b-versatile"  # Groq (padrão)


def load_chunks(chunks_dir: Path = CHUNKS_DIR) -> list[dict]:
    """
    Carrega chunks do ChromaDB (prioridade) ou dos arquivos .json em data/chunks.
    Tolera JSON vazio, inválido ou formato {"chunks": [...]}.
    """
    try:
        from src.utils.vector_db import count, get_all

        n = count()
        if n > 0:
            return get_all()
    except Exception:
        pass

    if not chunks_dir.exists():
        return []

    all_chunks = []
    for json_file in chunks_dir.glob("*.json"):
        try:
            raw = json_file.read_text(encoding="utf-8").strip()
            if not raw:
                continue
            data = json.loads(raw)
            if isinstance(data, list):
                all_chunks.extend(c for c in data if isinstance(c, dict) and c.get("content"))
            elif isinstance(data, dict):
                if "chunks" in data:
                    all_chunks.extend(
                        c for c in data["chunks"] if isinstance(c, dict) and c.get("content")
                    )
                elif data.get("content"):
                    all_chunks.append(data)
        except (json.JSONDecodeError, OSError) as e:
            print(f"[AVISO] Erro ao ler {json_file.name}: {e}")

    return all_chunks


def _keyword_search(chunks: list[dict], query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    """
    Busca simples por palavras-chave (fallback sem scikit-learn).
    Conta quantas palavras da query aparecem em cada chunk.
    """
    query_words = set(q.lower() for q in query.split() if len(q) > 2)

    scored = []
    for chunk in chunks:
        content = chunk.get("content", "").lower()
        matches = sum(1 for w in query_words if w in content)
        if matches > 0:
            scored.append((matches, chunk))

    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored[:top_k]]


def _vector_search(chunks: list[dict], query: str, top_k: int = TOP_K_CHUNKS) -> list[dict]:
    """
    Busca por similaridade de cosseno usando TF-IDF (scikit-learn).
    """
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    contents = [c.get("content", "") for c in chunks]
    if not contents or not any(contents):
        return []

    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),
    )
    try:
        doc_matrix = vectorizer.fit_transform(contents)
        query_vec = vectorizer.transform([query])
        scores = cosine_similarity(query_vec, doc_matrix).flatten()
        top_indices = scores.argsort()[-top_k:][::-1]
        return [chunks[i] for i in top_indices if scores[i] > 0]
    except ValueError:
        return _keyword_search(chunks, query, top_k)


def search_chunks(
    chunks: list[dict],
    query: str,
    top_k: int = TOP_K_CHUNKS,
    use_vector: bool = True,
) -> list[dict]:
    """
    Retorna os top_k chunks mais relevantes. Usa ChromaDB (busca semântica)
    quando disponível, senão TF-IDF ou keywords.
    """
    try:
        from src.utils.vector_db import count
        from src.utils.vector_db import search as chroma_search

        if count() > 0:
            return chroma_search(query, top_k)
    except Exception:
        pass

    if not chunks:
        return []

    if use_vector:
        try:
            return _vector_search(chunks, query, top_k)
        except ImportError:
            return _keyword_search(chunks, query, top_k)
    return _keyword_search(chunks, query, top_k)


def build_context(chunks: list[dict]) -> str:
    """Monta o contexto para o LLM a partir dos chunks."""
    parts = []
    for i, c in enumerate(chunks, 1):
        content = c.get("content", "")
        source = c.get("source_file", "N/A")
        parts.append(f"[Fonte {i}: {source}]\n{content}")
    return "\n\n---\n\n".join(parts)


def ask_agent(
    chunks: list[dict],
    question: str,
    model: str = MODEL,
    top_k: int = TOP_K_CHUNKS,
    chat_history: list[dict] | None = None,
) -> str:
    """
    Busca chunks relevantes (ChromaDB ou memória) e gera resposta via LLM.
    Suporta OpenAI, Groq e Gemini (via LLM_PROVIDER ou base_url no .env).
    """
    from src.utils.llm_client import chat_completion

    relevant = search_chunks(chunks or [], question, top_k)

    if not relevant:
        return "Nenhum conteúdo relevante encontrado no material do curso para sua pergunta."

    context = build_context(relevant)
    user_message = f"Contexto do curso:\n\n{context}\n\n---\n\nPergunta: {question}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    return chat_completion(messages, model=model)


def main():
    """Loop de chat no terminal."""
    print("Carregando chunks...")
    chunks = load_chunks()

    if not chunks:
        print("[ERRO] Nenhum chunk encontrado em data/chunks.")
        print("Execute o processor para gerar chunks antes de usar o agente.")
        return

    try:
        from src.utils.llm_client import _load_groq_keys

        if not _load_groq_keys():
            print(
                "[ERRO] Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env (obtenha em console.groq.com)"
            )
            return
    except Exception as e:
        print(f"[ERRO] Falha ao validar chaves: {e}")
        return

    print(f"[OK] {len(chunks)} chunks carregados.")
    print("\n" + "=" * 50)
    print("  Agente de Marketing - Diretor de Elite")
    print("  Baseado exclusivamente no material do curso")
    print("  Digite 'sair' para encerrar")
    print("=" * 50 + "\n")

    while True:
        try:
            question = input("Voce: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAte logo!")
            break

        if not question:
            continue

        if question.lower() in ("sair", "exit", "quit"):
            print("Ate logo!")
            break

        print("\nAgente: ", end="", flush=True)
        try:
            answer = ask_agent(chunks, question)
            print(answer)
        except Exception as e:
            print(f"[ERRO] {e}")

        print()


if __name__ == "__main__":
    main()
