"""
Docling Document Extractor - Parsing de documentos complexos via Docling Serve.

Suporta PDF, DOCX, PPTX, HTML e imagens (OCR) via Docling Serve HTTP API (porta 5001).
Converte documentos em Markdown, aplica chunking RecursiveCharacterTextSplitter,
e retorna chunks estruturados para indexacao no ChromaDB.

Fallback: se Docling Serve estiver indisponivel, tenta usar docling local (pip install docling).
"""

import logging
import os
from pathlib import Path
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# Extensoes suportadas pelo Docling
SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".pptx", ".html", ".png", ".jpg", ".jpeg", ".tiff"}

# Docling Serve URL (Docker interno: http://docling:5001, local dev: http://localhost:5001)
DOCLING_SERVE_URL = os.environ.get("DOCLING_SERVE_URL", "http://localhost:5001")

# Chunking defaults (maiores que processor.py pois documentos sao mais densos)
DEFAULT_CHUNK_SIZE = 3600
DEFAULT_CHUNK_OVERLAP = 400


def is_docling_compatible(file_path: str | Path) -> bool:
    """
    Verifica se a extensao do arquivo e suportada pelo Docling.

    Extensoes suportadas: .pdf, .docx, .pptx, .html, .png, .jpg, .jpeg, .tiff

    Args:
        file_path: Caminho para o arquivo.

    Returns:
        True se a extensao e suportada, False caso contrario.
    """
    p = Path(file_path)
    return p.suffix.lower() in SUPPORTED_EXTENSIONS


def _split_text(text: str, chunk_size: int, chunk_overlap: int) -> list[str]:
    """
    Divide texto em chunks usando RecursiveCharacterTextSplitter (langchain).
    Fallback para split simples se langchain nao estiver disponivel.

    Segue o mesmo padrao de src/processors/processor.py.
    """
    try:
        try:
            from langchain_text_splitters import RecursiveCharacterTextSplitter
        except ImportError:
            from langchain.text_splitter import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
            length_function=len,
        )
        return splitter.split_text(text)
    except ImportError:
        logger.warning("langchain nao disponivel — usando split simples.")
        return _simple_split(text, chunk_size, chunk_overlap)


def _simple_split(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Fallback: split por tamanho fixo com overlap."""
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap if overlap < (end - start) else end
    return [c.strip() for c in chunks if c.strip()]


async def _convert_via_serve(file_path: Path, timeout: float = 120.0) -> str:
    """
    Envia arquivo para Docling Serve e retorna o Markdown resultante.

    Endpoint: POST /v1/convert/file
    Content-Type: multipart/form-data

    Args:
        file_path: Caminho do arquivo a ser convertido.
        timeout: Timeout em segundos para a requisicao HTTP.

    Returns:
        Texto Markdown do documento convertido.

    Raises:
        httpx.HTTPStatusError: Se a API retornar erro.
        httpx.ConnectError: Se Docling Serve estiver indisponivel.
    """
    url = f"{DOCLING_SERVE_URL}/v1/convert/file"

    async with httpx.AsyncClient(timeout=timeout) as client:
        with open(file_path, "rb") as f:
            files = {"file": (file_path.name, f, "application/octet-stream")}
            response = await client.post(url, files=files)

        response.raise_for_status()
        data = response.json()

    # Docling Serve retorna {"document": {"md_content": "..."}} ou {"content": "..."}
    if isinstance(data, dict):
        # Tenta diferentes formatos de resposta do Docling Serve
        if "document" in data and isinstance(data["document"], dict):
            md = data["document"].get("md_content", "")
            if not md:
                md = data["document"].get("content", "")
            return md
        if "md_content" in data:
            return data["md_content"]
        if "content" in data:
            return data["content"]
        # Se nenhum campo conhecido, tenta serializar
        logger.warning("Formato de resposta inesperado do Docling Serve: %s", list(data.keys()))
        return str(data)

    return str(data)


def _convert_via_local(file_path: Path) -> str:
    """
    Fallback: converte documento usando docling local (pip install docling).

    Usa DocumentConverter da biblioteca docling para conversao offline.

    Args:
        file_path: Caminho do arquivo a ser convertido.

    Returns:
        Texto Markdown do documento convertido.

    Raises:
        ImportError: Se docling nao estiver instalado.
    """
    from docling.document_converter import DocumentConverter

    converter = DocumentConverter()
    result = converter.convert(str(file_path))
    return result.document.export_to_markdown()


async def extract_with_docling(
    file_path: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    category: str = "documents",
) -> list[dict]:
    """
    Extrai e chunka um documento usando Docling.

    Fluxo:
    1. Valida extensao do arquivo.
    2. Tenta converter via Docling Serve (HTTP API).
    3. Fallback: converte via docling local se Serve indisponivel.
    4. Aplica RecursiveCharacterTextSplitter no Markdown resultante.
    5. Retorna lista de chunks com schema padrao.

    Args:
        file_path: Caminho para o documento (PDF, DOCX, PPTX, HTML, imagem).
        chunk_size: Tamanho maximo de cada chunk em caracteres.
        chunk_overlap: Overlap entre chunks adjacentes.
        category: Categoria para metadata dos chunks.

    Returns:
        Lista de dicts com schema:
        {
            'content': str,
            'source_file': str,
            'category': str,
            'chunk_index': int,
            'char_count': int,
            'docling_metadata': dict
        }

    Raises:
        ValueError: Se a extensao do arquivo nao for suportada.
        FileNotFoundError: Se o arquivo nao existir.
        RuntimeError: Se ambas as estrategias (Serve + local) falharem.
    """
    p = Path(file_path)

    if not p.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {p}")

    if not is_docling_compatible(p):
        raise ValueError(
            f"Extensao '{p.suffix}' nao suportada pelo Docling. "
            f"Extensoes validas: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    markdown_text = ""
    conversion_method = ""

    # Tentativa 1: Docling Serve (HTTP API)
    try:
        logger.info("Convertendo %s via Docling Serve (%s)...", p.name, DOCLING_SERVE_URL)
        markdown_text = await _convert_via_serve(p)
        conversion_method = "docling_serve"
        logger.info("Conversao via Docling Serve concluida: %d caracteres", len(markdown_text))
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        logger.warning("Docling Serve indisponivel (%s). Tentando fallback local...", e)
    except httpx.HTTPStatusError as e:
        logger.warning("Docling Serve retornou erro %s. Tentando fallback local...", e.response.status_code)
    except Exception as e:
        logger.warning("Erro inesperado no Docling Serve: %s. Tentando fallback local...", e)

    # Tentativa 2: Docling local (fallback)
    if not markdown_text:
        try:
            logger.info("Convertendo %s via docling local...", p.name)
            markdown_text = _convert_via_local(p)
            conversion_method = "docling_local"
            logger.info("Conversao via docling local concluida: %d caracteres", len(markdown_text))
        except ImportError:
            raise RuntimeError(
                f"Falha ao converter {p.name}: Docling Serve indisponivel em {DOCLING_SERVE_URL} "
                "e pacote 'docling' nao instalado (pip install docling)."
            )
        except Exception as e:
            raise RuntimeError(
                f"Falha ao converter {p.name}: Docling Serve indisponivel e "
                f"docling local falhou: {e}"
            ) from e

    if not markdown_text.strip():
        logger.warning("Docling retornou conteudo vazio para %s", p.name)
        return []

    # Chunking com RecursiveCharacterTextSplitter
    text_chunks = _split_text(markdown_text, chunk_size, chunk_overlap)

    chunks: list[dict] = []
    for i, content in enumerate(text_chunks):
        chunk = {
            "content": content,
            "source_file": p.name,
            "category": category,
            "chunk_index": i,
            "char_count": len(content),
            "docling_metadata": {
                "conversion_method": conversion_method,
                "original_extension": p.suffix.lower(),
                "total_chunks": len(text_chunks),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap,
            },
        }
        chunks.append(chunk)

    logger.info("Extraidos %d chunks de %s (metodo: %s)", len(chunks), p.name, conversion_method)
    return chunks


async def extract_tables(file_path: str | Path) -> list[dict]:
    """
    Extrai tabelas de um documento como dados estruturados.

    Usa Docling Serve com formato de saida focado em tabelas.
    Cada tabela retorna como um chunk separado com metadata de tabela.

    Args:
        file_path: Caminho para o documento.

    Returns:
        Lista de dicts, cada um representando uma tabela:
        {
            'content': str (tabela em Markdown),
            'source_file': str,
            'category': str,
            'chunk_index': int,
            'char_count': int,
            'docling_metadata': dict (inclui 'content_type': 'table')
        }

    Raises:
        ValueError: Se a extensao nao for suportada.
        FileNotFoundError: Se o arquivo nao existir.
        RuntimeError: Se Docling Serve estiver indisponivel.
    """
    p = Path(file_path)

    if not p.exists():
        raise FileNotFoundError(f"Arquivo nao encontrado: {p}")

    if not is_docling_compatible(p):
        raise ValueError(
            f"Extensao '{p.suffix}' nao suportada pelo Docling. "
            f"Extensoes validas: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    # Tenta extrair tabelas via Docling Serve
    url = f"{DOCLING_SERVE_URL}/v1/convert/file"
    tables: list[dict] = []

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            with open(p, "rb") as f:
                files = {"file": (p.name, f, "application/octet-stream")}
                params = {"output_format": "json"}
                response = await client.post(url, files=files, params=params)

            response.raise_for_status()
            data = response.json()

        # Extrai tabelas do JSON de resposta
        raw_tables = []
        if isinstance(data, dict):
            doc = data.get("document", data)
            if isinstance(doc, dict):
                raw_tables = doc.get("tables", [])

        for i, table in enumerate(raw_tables):
            table_content = ""
            if isinstance(table, dict):
                table_content = table.get("markdown", table.get("content", str(table)))
            elif isinstance(table, str):
                table_content = table

            if not table_content.strip():
                continue

            tables.append({
                "content": table_content,
                "source_file": p.name,
                "category": "tables",
                "chunk_index": i,
                "char_count": len(table_content),
                "docling_metadata": {
                    "conversion_method": "docling_serve",
                    "original_extension": p.suffix.lower(),
                    "content_type": "table",
                    "table_index": i,
                },
            })

        logger.info("Extraidas %d tabelas de %s", len(tables), p.name)

    except (httpx.ConnectError, httpx.ConnectTimeout) as e:
        raise RuntimeError(
            f"Docling Serve indisponivel em {DOCLING_SERVE_URL}. "
            f"Extraccao de tabelas requer Docling Serve ativo: {e}"
        ) from e
    except httpx.HTTPStatusError as e:
        raise RuntimeError(
            f"Docling Serve retornou erro {e.response.status_code} "
            f"ao extrair tabelas de {p.name}"
        ) from e

    return tables


async def extract_all_documents(
    search_dir: str | Path,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    category: str = "documents",
) -> list[dict]:
    """
    Busca recursivamente todos os documentos compativeis em um diretorio
    e extrai chunks de cada um.

    Args:
        search_dir: Diretorio para busca recursiva.
        chunk_size: Tamanho maximo de cada chunk.
        chunk_overlap: Overlap entre chunks.
        category: Categoria para metadata.

    Returns:
        Lista consolidada de chunks de todos os documentos.
    """
    search_path = Path(search_dir)
    all_chunks: list[dict] = []

    if not search_path.exists():
        logger.warning("Diretorio nao encontrado: %s", search_path)
        return all_chunks

    for ext in SUPPORTED_EXTENSIONS:
        for doc_file in search_path.rglob(f"*{ext}"):
            if doc_file.name.startswith("._"):
                continue  # Skip macOS resource forks
            try:
                chunks = await extract_with_docling(
                    doc_file,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    category=category,
                )
                all_chunks.extend(chunks)
                logger.info("  %s: %d chunks", doc_file.name, len(chunks))
            except Exception as e:
                logger.warning("Erro ao extrair %s: %s", doc_file, e)

    logger.info("Total: %d chunks extraidos de documentos", len(all_chunks))
    return all_chunks
