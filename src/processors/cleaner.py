"""
Pós-processamento de transcrições com LLM.
Transforma transcrições brutas em texto limpo e estruturado em Markdown.
Usa Groq (llama-3.3-70b-versatile) como SSOT para estruturação em Markdown.
Processamento paralelo com ThreadPoolExecutor e múltiplas chaves Groq.
"""

import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic_core")

from dotenv import load_dotenv

# Diretórios do projeto
PROJECT_ROOT = Path(__file__).parent.parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"

# Carrega variáveis do .env
load_dotenv(PROJECT_ROOT / ".env")

SYSTEM_PROMPT = """Você é um editor técnico especialista em Inteligência Artificial. Sua tarefa é limpar transcrições de aulas de IA.

NÃO TRADUZA termos técnicos (ex: mantenha 'Embeddings', 'Weights', 'Fine-tuning', 'Prompt Engineering').

Organize o conteúdo em Markdown estruturado.

Se o instrutor citar pedaços de código ou bibliotecas (LangChain, PyTorch, OpenAI), formate-os em blocos de código (```)."""

MODEL = "llama-3.3-70b-versatile"  # Groq (padrão)


def get_files_to_process(processed_dir: Path = PROCESSED_DIR) -> list[Path]:
    """
    Retorna arquivos .txt que precisam ser processados (busca recursiva).
    Exclui arquivos com sufixo _clean e os que já possuem versão _clean.
    """
    if not processed_dir.exists():
        return []

    to_process = []
    for txt_file in processed_dir.rglob("*.txt"):
        if txt_file.stem.endswith("_clean"):
            continue
        clean_path = txt_file.parent / f"{txt_file.stem}_clean.txt"
        if clean_path.exists():
            continue
        to_process.append(txt_file)

    return sorted(to_process)


def clean_transcription(text: str, model: str = MODEL, on_key_used=None) -> str:
    """
    Processa o texto com o LLM (Groq). on_key_used(key_idx) para telemetria.
    """
    from src.utils.llm_client import chat_completion

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text},
    ]
    return chat_completion(messages, model=model, on_key_used=on_key_used)


def process_file(
    file_path: Path,
    output_dir: Path | None = None,
    model: str = MODEL,
    on_key_used=None,
) -> Path:
    """
    Processa um arquivo de transcrição e salva a versão limpa.
    on_key_used(key_idx) para telemetria no Dashboard.
    """
    text = file_path.read_text(encoding="utf-8", errors="replace")

    if not text.strip():
        print(f"  -> [AVISO] Arquivo vazio, pulando.")
        return file_path

    cleaned = clean_transcription(text, model, on_key_used=on_key_used)
    output_path = (output_dir or file_path.parent) / f"{file_path.stem}_clean.txt"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(cleaned, encoding="utf-8")

    return output_path


def process_files_parallel(
    files: list[Path],
    output_dir: Path | None = None,
    model: str = MODEL,
    max_workers: int = 10,
    progress_callback=None,
    key_used_callback=None,
) -> list[tuple[Path, Path | None, str | None, int]]:
    """
    Processa múltiplos arquivos em paralelo com ThreadPoolExecutor.
    key_used_callback(fp, key_idx) para telemetria (qual chave por arquivo).

    Returns:
        Lista de (file_path, output_path ou None, error ou None, key_idx)
    """
    if not files:
        return []

    results = []
    n = len(files)
    completed = 0

    def _process_one(fp: Path):
        key_used = [0]

        def _on_key(k):
            key_used[0] = k
            if key_used_callback:
                key_used_callback(fp, k)

        try:
            out = process_file(fp, output_dir=output_dir, model=model, on_key_used=_on_key)
            return (fp, out, None, key_used[0])
        except Exception as e:
            return (fp, None, str(e), key_used[0])

    with ThreadPoolExecutor(max_workers=min(max_workers, n)) as executor:
        futures = {executor.submit(_process_one, f): f for f in files}
        try:
            from tqdm import tqdm
            pbar = tqdm(total=n, desc=f"Processando {n} arquivos com {min(max_workers, n)} workers...", unit="arquivo")
        except ImportError:
            pbar = None

        for future in as_completed(futures):
            fp, out, err, key_idx = future.result()
            results.append((fp, out, err, key_idx))
            completed += 1
            if progress_callback:
                progress_callback(completed, n, fp, key_idx)
            if pbar:
                pbar.update(1)
                if err:
                    pbar.write(f"  [ERRO] {fp.name}: {err}")
                else:
                    pbar.write(f"  [OK] {fp.name} (chave {key_idx})")

        if pbar:
            pbar.close()

    return results


def main():
    """Processa todos os arquivos .txt pendentes em data/processed (paralelo)."""
    if not PROCESSED_DIR.exists():
        print(f"Pasta {PROCESSED_DIR} não existe. Execute setup_project.py primeiro.")
        return

    files = get_files_to_process()

    if not files:
        print("Nenhum arquivo para processar.")
        print("Arquivos com sufixo _clean ou que já possuem versão limpa são ignorados.")
        return

    import os
    from src.utils.llm_client import _load_groq_keys
    if not _load_groq_keys():
        print("[ERRO] Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env (obtenha em console.groq.com)")
        return

    n = len(files)
    print(f"Processando {n} arquivo(s) com até 10 workers (Groq)...\n")
    results = process_files_parallel(files, max_workers=10)
    errors = [(fp, err) for fp, out, err, _ in results if err]
    for fp, out, err, key_idx in results:
        if not err:
            try:
                rel = out.relative_to(PROCESSED_DIR) if out else fp.name
            except ValueError:
                rel = fp.name
            print(f"  -> [OK] {rel} (chave {key_idx})")
    if errors:
        print("\nErros:")
        for fp, err in errors:
            print(f"  -> [ERRO] {fp.name}: {err}")


if __name__ == "__main__":
    main()
