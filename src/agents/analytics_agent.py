"""
Agente de Analytics - Análise de métricas, funil e otimização.
Interpreta dados sob a ótica das metodologias do curso.
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

SYSTEM_PROMPT = """Você é um Analista de Dados e Growth Hacker. Sua função é interpretar métricas de marketing (CTR, CPC, ROAS, LTV) sob a ótica estrita das fórmulas e benchmarks ensinados no curso. Você é cético, focado em ROI e sempre sugere onde o 'balde está furado' (gargalos do funil) com base no conhecimento disponível nos chunks."""

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


def analyze_funnel(
    data: str,
    chunks: list[dict] | None = None,
    model: str = MODEL,
    top_k: int = TOP_K_CHUNKS,
) -> str:
    """
    Analisa métricas do funil comparando com taxas de conversão ideais do curso.

    Args:
        data: Descrição dos números, ex: "Tive 1000 cliques e 10 vendas"
              ou "1000 visitantes, 50 leads, 5 vendas"
        chunks: Chunks carregados (opcional, carrega automaticamente se None)

    Returns:
        Análise comparativa com benchmarks do curso e sugestões de gargalos.
    """
    from src.utils.llm_client import chat_completion

    if chunks is None:
        chunks = load_chunks()

    relevant = search_chunks(
        chunks,
        "conversão taxa funil métricas CTR CPC ROAS LTV benchmark conversão ideal",
        top_k=top_k,
    )

    context = build_context(relevant) if relevant else "Nenhum benchmark específico encontrado no material."

    user_message = f"""Analise os dados do funil abaixo e compare com as taxas de conversão e benchmarks mencionados no material do curso.

Dados fornecidos pelo usuário:
{data}

Com base no contexto do curso:
1. Extraia os números mencionados e calcule as taxas de conversão (ex: cliques->vendas, visitantes->leads, etc)
2. Compare com os benchmarks/ideais citados no material
3. Identifique onde o "balde está furado" - os gargalos do funil
4. Sugira prioridades de otimização baseadas estritamente no que o curso ensina

Se o curso não mencionar benchmarks específicos para essas métricas, diga isso e analise com base em boas práticas gerais de funil de conversão.

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
    print("  Agente de Analytics - Growth Hacker")
    print("  Metricas | Funil | ROI | Gargalos")
    print("  Digite 'funil DADOS' para analise de conversao")
    print("  Ex: funil Tive 1000 cliques e 10 vendas")
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

        if question.lower().startswith("funil "):
            data = question[6:].strip()
            if not data:
                print("Use: funil <seus numeros>")
                print("Ex: funil Tive 1000 cliques e 10 vendas")
                continue
            print(f"\nAnalisando funil: {data}")
            try:
                result = analyze_funnel(data, chunks)
                print("\nAgente:\n")
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
