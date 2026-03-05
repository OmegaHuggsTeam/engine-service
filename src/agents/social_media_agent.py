"""
Agente de Social Media - Repurposing e criação de conteúdo para redes sociais.
Transforma conceitos do curso em Threads, Reels e Legendas.
"""

from pathlib import Path

from dotenv import load_dotenv

from .marketing_agent import (
    CHUNKS_DIR,
    load_chunks,
    search_chunks,
    build_context,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SYSTEM_PROMPT = """Você é um Social Media Manager estrategista. Sua especialidade é pegar conceitos densos do curso e transformá-los em conteúdo viral e educativo para Instagram, LinkedIn e TikTok. Use o tom de voz do autor do curso para criar: Threads, Roteiros de Reels e Legendas. Sempre foque em retenção e engajamento."""

TOP_K_CHUNKS = 5
MODEL = "llama-3.3-70b-versatile"  # Groq (padrão)


def ask_agent(
    chunks: list[dict],
    question: str,
    model: str = MODEL,
    top_k: int = TOP_K_CHUNKS,
    chat_history: list[dict] | None = None,
) -> str:
    """Busca chunks e gera resposta via LLM (OpenAI/Groq/Gemini)."""
    from src.utils.llm_client import chat_completion

    relevant = search_chunks(chunks, question, top_k)
    if not relevant:
        return "Nenhum conteúdo relevante encontrado no material do curso para esse tópico."

    context = build_context(relevant)
    user_message = f"Contexto do curso:\n\n{context}\n\n---\n\nPergunta: {question}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    return chat_completion(messages, model=model)


def generate_social_pack(
    topic: str,
    chunks: list[dict] | None = None,
    model: str = MODEL,
    top_k: int = TOP_K_CHUNKS,
) -> dict[str, str]:
    """
    Gera conteúdo para redes sociais + 1 sugestão de imagem/vídeo para o tópico.

    Returns:
        dict com 'content' (threads, reels, legendas) e 'media_suggestion'
    """
    from src.utils.llm_client import chat_completion

    if chunks is None:
        chunks = load_chunks()

    relevant = search_chunks(chunks, topic, top_k)
    if not relevant:
        return {
            "content": "Nenhum conteúdo relevante encontrado no material do curso.",
            "media_suggestion": "N/A",
        }

    context = build_context(relevant)
    user_message = f"""Com base no contexto do curso abaixo, crie um pacote de conteúdo para redes sociais sobre o tópico: "{topic}"

Inclua:
1. Uma Thread (Twitter/LinkedIn) com 3-5 posts
2. Um roteiro de Reel/TikTok (15-30 seg)
3. Uma legenda para Instagram

E ao final, adicione uma seção obrigatória:
## SUGESTÃO DE MÍDIA
Descreva 1 ideia concreta de imagem ou vídeo para ilustrar esse tópico (cenário, elementos visuais, texto na tela, etc).

Contexto do curso:
{context}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
    full_response = chat_completion(messages, model=model)

    media_suggestion = "N/A"
    markers = ["## SUGESTÃO DE MÍDIA", "## SUGESTAO DE MIDIA", "## Sugestao de Midia"]
    for marker in markers:
        if marker in full_response:
            parts = full_response.split(marker, 1)
            if len(parts) >= 2:
                full_response = parts[0].strip()
                media_suggestion = parts[1].strip()
            break

    return {
        "content": full_response,
        "media_suggestion": media_suggestion,
    }


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
            print("[ERRO] Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env (obtenha em console.groq.com)")
            return
    except Exception as e:
        print(f"[ERRO] Falha ao validar chaves: {e}")
        return

    print(f"[OK] {len(chunks)} chunks carregados.")
    print("\n" + "=" * 50)
    print("  Agente Social Media - Repurposing de Conteudo")
    print("  Threads | Reels | Legendas | Sugestoes de midia")
    print("  Digite 'pack TOPICO' para gerar social pack completo")
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

        if question.lower().startswith("pack "):
            topic = question[5:].strip()
            if not topic:
                print("Use: pack <topico>")
                continue
            print(f"\nGerando social pack para: {topic}")
            try:
                result = generate_social_pack(topic, chunks)
                print("\n--- CONTEUDO ---\n")
                print(result["content"])
                print("\n--- SUGESTAO DE MIDIA ---\n")
                print(result["media_suggestion"])
            except Exception as e:
                print(f"[ERRO] {e}")
        else:
            print("\nAgente: ", end="", flush=True)
            try:
                answer = ask_agent(chunks, question)
                print(answer)
            except Exception as e:
                print(f"[ERRO] {e}")

        print()


if __name__ == "__main__":
    main()
