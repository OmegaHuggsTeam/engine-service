"""
GitHub Ingestor - Importa workflows n8n de repositórios GitHub.

Recebe URL de repositório, baixa apenas arquivos .json de workflows,
dispara n8n_extractor em cada um e salva chunks no ChromaDB com
categoria 'external_template' e metadado source_url para citação.
"""

import json
import logging
import os
import re
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from .n8n_extractor import extract_operation_modules, is_n8n_workflow, sync_modules_to_graph

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"


def _parse_repo_url(url: str) -> tuple[str, str]:
    """
    Extrai owner e repo de uma URL GitHub.

    Suporta:
      - https://github.com/owner/repo
      - https://github.com/owner/repo/
      - git@github.com:owner/repo.git
    """
    url = url.strip().rstrip("/")
    # SSH
    m = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if m:
        return m.group(1), m.group(2).removesuffix(".git")

    # HTTPS
    parsed = urlparse(url)
    if "github.com" in parsed.netloc:
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1].removesuffix(".git")

    raise ValueError(f"URL de repositório GitHub inválida: {url}")


def _get_default_branch(owner: str, repo: str, token: Optional[str] = None) -> str:
    """Obtém o branch padrão do repositório (main ou master)."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30) as client:
        r = client.get(f"{GITHUB_API}/repos/{owner}/{repo}", headers=headers)
        r.raise_for_status()
        data = r.json()
        return data.get("default_branch", "main")


def _list_json_files(owner: str, repo: str, branch: str, token: Optional[str] = None) -> list[str]:
    """
    Lista todos os arquivos .json do repositório via Git Trees API.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30) as client:
        r = client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/git/trees/{branch}?recursive=1",
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
        tree = data.get("tree", [])
        return [item["path"] for item in tree if item.get("type") == "blob" and item["path"].lower().endswith(".json")]


def _download_file(owner: str, repo: str, branch: str, path: str) -> str:
    """Baixa conteúdo de um arquivo via raw URL."""
    url = f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{path}"
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def ingest_repository(
    repo_url: str,
    *,
    branch: Optional[str] = None,
    token: Optional[str] = None,
    save_to_chromadb: bool = True,
) -> dict:
    """
    Ingere workflows n8n de um repositório GitHub.

    Args:
        repo_url: URL do repositório (ex: https://github.com/zie619/zie619.github.io)
        branch: Branch a usar (default: branch padrão do repo)
        token: GITHUB_TOKEN opcional para rate limit maior
        save_to_chromadb: Se True, salva chunks no ChromaDB

    Returns:
        Dict com stats: total_files, workflows_processed, chunks_saved, errors
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    owner, repo = _parse_repo_url(repo_url)
    branch = branch or _get_default_branch(owner, repo, token)

    base_url = f"https://github.com/{owner}/{repo}/blob/{branch}"
    stats = {"total_files": 0, "workflows_processed": 0, "chunks_saved": 0, "errors": []}

    json_paths = _list_json_files(owner, repo, branch, token)
    stats["total_files"] = len(json_paths)

    if not json_paths:
        logger.info("Nenhum arquivo .json encontrado em %s", repo_url)
        return stats

    all_chunks: list[dict] = []

    with tempfile.TemporaryDirectory(prefix="github_ingestor_") as tmpdir:
        tmp = Path(tmpdir)

        for path in json_paths:
            try:
                content = _download_file(owner, repo, branch, path)
                local_path = tmp / path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(content, encoding="utf-8")

                if not is_n8n_workflow(local_path):
                    continue

                source_url = f"{base_url}/{path}"
                modules = extract_operation_modules(local_path)

                for mod in modules:
                    mod["category"] = "external_template"
                    mod["source_url"] = source_url
                    mod["source_file"] = f"github/{repo}/{path}"
                    all_chunks.append(mod)

                stats["workflows_processed"] += 1
                logger.info("  %s: %d módulos (n8n workflow)", path, len(modules))

            except Exception as e:
                stats["errors"].append({"path": path, "error": str(e)})
                logger.warning("Erro ao processar %s: %s", path, e)

    if save_to_chromadb and all_chunks:
        try:
            from src.utils.vector_db import add_chunks
            n = add_chunks(all_chunks)
            stats["chunks_saved"] = n
        except Exception as e:
            stats["errors"].append({"stage": "chromadb", "error": str(e)})
            logger.error("Falha ao salvar no ChromaDB: %s", e)

    # GraphSynergy: sync Service/N8nNode graph (graceful — never blocks ingestion)
    if all_chunks:
        try:
            graph_stats = sync_modules_to_graph(all_chunks)
            stats["graph_sync"] = graph_stats
        except Exception as e:
            stats["graph_sync"] = {"skipped": True, "error": str(e)}
            logger.debug("Graph sync falhou (non-blocking): %s", e)

    logger.info(
        "GitHub Ingestor: %d workflows, %d chunks salvos, %d erros",
        stats["workflows_processed"],
        stats["chunks_saved"],
        len(stats["errors"]),
    )
    return stats


def main():
    """CLI: python -m src.extractors.github_ingestor <repo_url>"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Ingere workflows n8n de repositório GitHub")
    parser.add_argument("repo_url", help="URL do repositório (ex: https://github.com/zie619/zie619.github.io)")
    parser.add_argument("--branch", "-b", help="Branch (default: branch padrão)")
    parser.add_argument("--no-chromadb", action="store_true", help="Não salvar no ChromaDB")
    args = parser.parse_args()

    stats = ingest_repository(
        args.repo_url,
        branch=args.branch,
        save_to_chromadb=not args.no_chromadb,
    )

    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
