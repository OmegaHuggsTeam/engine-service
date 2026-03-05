"""
Agente de Engenharia de IA - Prompt Engineering e Automação.
Cria prompts estruturados e sugere automações baseadas no curso.
"""

from pathlib import Path

from dotenv import load_dotenv

from .marketing_agent import (
    load_chunks,
    search_chunks,
    build_context,
)

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

SYSTEM_PROMPT = """Você é um Engenheiro de IA e Especialista em Prompt Engineering. Sua função é ajudar o usuário a criar prompts melhores, estruturar automações no Make.com/n8n e otimizar o uso de ferramentas de IA citadas no curso. Você deve sempre sugerir formas de automatizar os processos que os outros agentes (Marketing, Social, Analytics) identificarem."""

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
        return "Nenhum conteúdo relevante encontrado no material do curso para sua pergunta."

    context = build_context(relevant)
    user_message = f"Contexto do curso:\n\n{context}\n\n---\n\nPergunta: {question}"

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    if chat_history:
        for msg in chat_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
    messages.append({"role": "user", "content": user_message})

    return chat_completion(messages, model=model)


def generate_prompt(
    task: str,
    chunks: list[dict] | None = None,
    model: str = MODEL,
    top_k: int = TOP_K_CHUNKS,
) -> str:
    """
    Gera um prompt estruturado para uma tarefa, usando técnicas do curso
    (Chain of Thought, Few-Shot, etc.) baseado nas diretrizes do material.

    Args:
        task: Tarefa simples, ex: "Criar um anúncio"
        chunks: Chunks carregados (opcional)

    Returns:
        Prompt estruturado pronto para uso
    """
    from src.utils.llm_client import chat_completion

    if chunks is None:
        chunks = load_chunks()

    relevant = search_chunks(
        chunks,
        f"prompt engineering IA automação Make n8n ChatGPT",
        top_k=top_k,
    )

    context = build_context(relevant) if relevant else "Nenhuma diretriz específica encontrada."

    user_message = f"""Com base no material do curso e nas melhores práticas de Prompt Engineering, crie um prompt estruturado para a seguinte tarefa:

Tarefa: {task}

O prompt deve:
1. Usar técnicas como Chain of Thought (CoT) ou Few-Shot quando apropriado
2. Ser estruturado (role, contexto, instruções, formato de saída)
3. Seguir diretrizes citadas no curso sobre uso de IA
4. Incluir variáveis/placeholders quando fizer sentido (ex: {{produto}}, {{público}})
5. Ser pronto para uso em ChatGPT, Claude ou ferramentas similares

Contexto do curso:
{context}"""

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]
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
            print("[ERRO] Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env (obtenha em console.groq.com)")
            return
    except Exception as e:
        print(f"[ERRO] Falha ao validar chaves: {e}")
        return

    print(f"[OK] {len(chunks)} chunks carregados.")
    print("\n" + "=" * 50)
    print("  Agente AI Engineer - Prompt Engineering")
    print("  Prompts | Automacao | Make.com | n8n")
    print("  Digite 'prompt TAREFA' para gerar prompt estruturado")
    print("  Ex: prompt Criar um anuncio para Facebook")
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

        if question.lower().startswith("prompt "):
            task = question[7:].strip()
            if not task:
                print("Use: prompt <tarefa>")
                print("Ex: prompt Criar um anuncio para Facebook")
                continue
            print(f"\nGerando prompt para: {task}")
            try:
                result = generate_prompt(task, chunks)
                print("\n--- PROMPT ESTRUTURADO ---\n")
                print(result)
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
