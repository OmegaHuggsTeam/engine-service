"""
Processor base para chunking de textos.
Implementa Recursive Character Text Splitting conforme Blueprint.
"""

from pathlib import Path
from typing import Optional

# Configurações do chunking (Blueprint)
CHUNK_SIZE = 900  # 800-1000 tokens (~4 chars por token)
CHUNK_OVERLAP = 100  # ~10-15% do chunk_size
SEPARATORS = ["\n\n", "\n", ". ", " ", ""]


def _simple_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """
    Split recursivo simples (fallback sem langchain).
    Divide por parágrafos, depois por sentenças, depois por palavras.
    """
    separators = ["\n\n", "\n", ". ", " "]

    def split_recursive(text_part: str, sep_index: int = 0) -> list[str]:
        if sep_index >= len(separators):
            return (
                [
                    text_part[i : i + chunk_size]
                    for i in range(0, len(text_part), chunk_size - overlap)
                ]
                if text_part
                else []
            )

        sep = separators[sep_index]
        parts = text_part.split(sep) if sep else list(text_part)

        current_chunk = ""
        result = []

        for i, part in enumerate(parts):
            to_add = part + (sep if i < len(parts) - 1 and sep else "")

            if len(current_chunk) + len(to_add) <= chunk_size:
                current_chunk += to_add
            else:
                if current_chunk:
                    result.append(current_chunk.strip())
                if len(to_add) > chunk_size:
                    result.extend(split_recursive(to_add, sep_index + 1))
                    current_chunk = ""
                else:
                    current_chunk = to_add[-overlap:] if overlap else "" + to_add

        if current_chunk.strip():
            result.append(current_chunk.strip())

        return result

    return split_recursive(text)


def split_text(
    text: str,
    chunk_size: int = CHUNK_SIZE,
    chunk_overlap: int = CHUNK_OVERLAP,
    use_langchain: bool = True,
) -> list[dict]:
    """
    Divide o texto em chunks com overlap.

    Args:
        text: Texto a ser dividido
        chunk_size: Tamanho aproximado do chunk em caracteres
        chunk_overlap: Overlap entre chunks
        use_langchain: Se True, usa RecursiveCharacterTextSplitter do LangChain

    Returns:
        Lista de dicts com 'content' e metadata base
    """
    if use_langchain:
        try:
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=SEPARATORS,
                length_function=len,
            )
            chunks = splitter.split_text(text)
        except ImportError:
            chunks = _simple_split(text, chunk_size, chunk_overlap)
    else:
        chunks = _simple_split(text, chunk_size, chunk_overlap)

    return [{"content": c, "char_count": len(c)} for c in chunks]


def process_txt_file(
    file_path: Path,
    source_file: Optional[str] = None,
    category: Optional[str] = None,
    output_dir: Optional[Path] = None,
    agent_specialty: Optional[str] = None,
) -> list[dict]:
    """
    Lê um arquivo .txt da pasta raw e executa o split inicial.

    Args:
        file_path: Caminho para o arquivo .txt
        source_file: Nome do curso/aula (metadata)
        category: Categoria (Marketing, Analytics, etc)
        output_dir: Diretório para salvar chunks (opcional)

    Returns:
        Lista de chunks com metadata
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {file_path}")

    if file_path.suffix.lower() != ".txt":
        raise ValueError(f"Esperado arquivo .txt, recebido: {file_path.suffix}")

    text = file_path.read_text(encoding="utf-8", errors="replace")
    source_name = source_file or file_path.stem

    chunks = split_text(text)

    # Adiciona metadata conforme Blueprint
    for i, chunk in enumerate(chunks):
        chunk["source_file"] = source_name
        chunk["chunk_index"] = i
        chunk["category"] = category or "Uncategorized"
        chunk["timestamp"] = None  # Preenchido quando for vídeo
        chunk["agent_specialty"] = agent_specialty or "Uncategorized"

    if output_dir:
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        safe_name = source_name.replace("/", "_").replace("\\", "_")
        output_file = output_dir / f"{safe_name}_chunks.json"
        import json

        output_file.write_text(
            json.dumps(chunks, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"[OK] Chunks salvos em: {output_file}")

    # Insere automaticamente no ChromaDB
    try:
        from src.utils.vector_db import add_chunks

        added = add_chunks(chunks)
        print(f"[OK] {added} chunks inseridos no ChromaDB")
    except Exception as e:
        print(f"[AVISO] ChromaDB: {e}")

    return chunks


def _get_source_name(file_path: Path, base_dir: Path) -> str:
    """Retorna source_file com subpath (ex: IA_Basica/aula_01)."""
    try:
        rel = file_path.relative_to(base_dir)
        return str(rel.with_suffix("")).replace("\\", "/")
    except ValueError:
        return file_path.stem


def main():
    """Processa arquivos .txt em data/raw e data/processed (busca recursiva)."""
    project_root = Path(__file__).parent.parent.parent
    raw_dir = project_root / "data" / "raw"
    processed_dir = project_root / "data" / "processed"
    chunks_dir = project_root / "data" / "chunks"

    if not chunks_dir.exists():
        chunks_dir.mkdir(parents=True, exist_ok=True)

    # Processa _clean.txt de data/processed (prioridade)
    clean_files = sorted(processed_dir.rglob("*_clean.txt")) if processed_dir.exists() else []
    if clean_files:
        for txt_file in clean_files:
            source_name = _get_source_name(txt_file, processed_dir).replace("_clean", "")
            print(
                f"\nProcessando: {txt_file.relative_to(processed_dir) if processed_dir in txt_file.parents else txt_file.name}"
            )
            chunks = process_txt_file(txt_file, source_file=source_name, output_dir=chunks_dir)
            print(f"  -> {len(chunks)} chunks gerados")
        return

    # Fallback: .txt de data/raw
    if not raw_dir.exists():
        print(f"Pasta {raw_dir} não existe. Execute setup_project.py primeiro.")
        return

    txt_files = sorted(raw_dir.rglob("*.txt"))
    if not txt_files:
        print(f"Nenhum arquivo .txt encontrado em {raw_dir}")
        print("Adicione arquivos .txt na pasta data/raw para processar.")
        return

    for txt_file in txt_files:
        source_name = _get_source_name(txt_file, raw_dir)
        print(
            f"\nProcessando: {txt_file.relative_to(raw_dir) if raw_dir in txt_file.parents else txt_file.name}"
        )
        chunks = process_txt_file(txt_file, source_file=source_name, output_dir=chunks_dir)
        print(f"  -> {len(chunks)} chunks gerados")


if __name__ == "__main__":
    main()
