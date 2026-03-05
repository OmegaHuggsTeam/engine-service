"""
CRM Repo Ingestor - Importa codigo dos repos CRM SendSpeed/UserIn.

Segue o padrao do github_ingestor.py mas para arquivos .ts/.tsx/.js/.jsx
nas branches pedro-crm. Usa GitHub Trees API para listar arquivos e
crm_code_extractor para extrair chunks estruturados.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

import httpx

from .crm_code_extractor import detect_and_extract, sync_crm_modules_to_graph

logger = logging.getLogger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"

# Repos CRM com branches pedro-crm
CRM_REPOS = [
    {
        "url": "https://github.com/sendspeed0/platform-backend",
        "branch": "pedro-crm",
        "description": "Backend: Kafka, Journey Builder, Campaigns, Ontology, MCP",
    },
    {
        "url": "https://github.com/sendspeed0/sendspeed-engage-ai-flow-08",
        "branch": "pedro-crm",
        "description": "Frontend: React+Vite, 45 paginas, Journey Canvas, Segments",
    },
    {
        "url": "https://github.com/sendspeed0/segment-engine",
        "branch": "pedro-crm",
        "description": "Segmentacao: ClickHouse, Kafka workers, profiling comportamental",
    },
    {
        "url": "https://github.com/sendspeed0/smarttrack.userin.ai",
        "branch": "pedro-crm",
        "description": "Tracker SDK: eventos, WebSocket, minigames, rules engine",
    },
    {
        "url": "https://github.com/sendspeed0/userin-integrations",
        "branch": "pedro-crm",
        "description": "Integracoes: SMS (SendSpeed), Email (Resend), Smartico",
    },
    {
        "url": "https://github.com/sendspeed0/ingestion-service",
        "branch": "pedro-crm",
        "description": "Ingestao iGaming: SevenX, Databricks, Redis dedup",
    },
]

# Extensions to download
CODE_EXTENSIONS = {".js", ".ts", ".tsx", ".jsx"}

# Directories to skip
SKIP_DIRS = {"node_modules", "dist", "build", ".next", ".cache", ".git",
             "coverage", "__pycache__", ".turbo"}


def _parse_repo_url(url: str) -> tuple[str, str]:
    """Extrai owner e repo de uma URL GitHub."""
    from urllib.parse import urlparse
    url = url.strip().rstrip("/")
    parsed = urlparse(url)
    if "github.com" in parsed.netloc:
        parts = parsed.path.strip("/").split("/")
        if len(parts) >= 2:
            return parts[0], parts[1].removesuffix(".git")
    raise ValueError(f"URL de repositorio GitHub invalida: {url}")


def _list_code_files(
    owner: str,
    repo: str,
    branch: str,
    token: Optional[str] = None,
) -> list[str]:
    """Lista todos os arquivos de codigo do repositorio via Git Trees API."""
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

    files = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item["path"]
        # Check extension
        suffix = Path(path).suffix.lower()
        if suffix not in CODE_EXTENSIONS:
            continue
        # Skip directories
        parts = Path(path).parts
        if any(d in SKIP_DIRS for d in parts):
            continue
        files.append(path)

    return files


def _download_file(
    owner: str,
    repo: str,
    branch: str,
    path: str,
    token: Optional[str] = None,
) -> str:
    """Baixa conteudo de um arquivo via raw URL."""
    url = f"{GITHUB_RAW}/{owner}/{repo}/{branch}/{path}"
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(url, headers=headers)
        r.raise_for_status()
        return r.text


def ingest_crm_repository(
    repo_url: str,
    *,
    branch: str = "pedro-crm",
    token: Optional[str] = None,
    save_to_chromadb: bool = True,
) -> dict:
    """
    Ingere codigo CRM de um repositorio GitHub.

    Args:
        repo_url: URL do repositorio (ex: https://github.com/sendspeed0/platform-backend)
        branch: Branch a usar (default: pedro-crm)
        token: GITHUB_TOKEN opcional
        save_to_chromadb: Se True, salva chunks no ChromaDB

    Returns:
        Dict com stats: total_files, files_processed, chunks_extracted, chunks_saved, errors
    """
    token = token or os.environ.get("GITHUB_TOKEN")
    owner, repo = _parse_repo_url(repo_url)

    stats = {
        "repo": f"{owner}/{repo}",
        "branch": branch,
        "total_files": 0,
        "files_processed": 0,
        "chunks_extracted": 0,
        "chunks_saved": 0,
        "errors": [],
        "by_category": {},
    }

    logger.info("Ingerindo %s/%s branch=%s ...", owner, repo, branch)

    try:
        code_paths = _list_code_files(owner, repo, branch, token)
    except httpx.HTTPStatusError as e:
        stats["errors"].append({"stage": "list_files", "error": str(e)})
        logger.error("Falha ao listar arquivos de %s/%s: %s", owner, repo, e)
        return stats

    stats["total_files"] = len(code_paths)
    logger.info("Encontrados %d arquivos de codigo em %s/%s", len(code_paths), owner, repo)

    all_chunks: list[dict] = []

    with tempfile.TemporaryDirectory(prefix=f"crm_ingestor_{repo}_") as tmpdir:
        tmp = Path(tmpdir)

        for path in code_paths:
            try:
                content = _download_file(owner, repo, branch, path, token)
                local_path = tmp / path
                local_path.parent.mkdir(parents=True, exist_ok=True)
                local_path.write_text(content, encoding="utf-8")

                chunks = detect_and_extract(local_path)
                if not chunks:
                    continue

                # Enrich with repo metadata
                for chunk in chunks:
                    chunk["repo"] = repo
                    chunk["source_file"] = f"crm/{repo}/{path}"

                all_chunks.extend(chunks)
                stats["files_processed"] += 1

                # Track by category
                for c in chunks:
                    cat = c.get("category", "unknown")
                    stats["by_category"][cat] = stats["by_category"].get(cat, 0) + 1

            except Exception as e:
                stats["errors"].append({"path": path, "error": str(e)})
                logger.debug("Erro ao processar %s: %s", path, e)

    stats["chunks_extracted"] = len(all_chunks)

    # Save to ChromaDB
    if save_to_chromadb and all_chunks:
        try:
            from src.utils.vector_db import add_chunks
            n = add_chunks(all_chunks)
            stats["chunks_saved"] = n
        except Exception as e:
            stats["errors"].append({"stage": "chromadb", "error": str(e)})
            logger.error("Falha ao salvar no ChromaDB: %s", e)

    # Sync to Neo4j graph
    if all_chunks:
        try:
            graph_stats = sync_crm_modules_to_graph(all_chunks)
            stats["graph_sync"] = graph_stats
        except Exception as e:
            stats["graph_sync"] = {"skipped": True, "error": str(e)}
            logger.debug("Graph sync falhou (non-blocking): %s", e)

    logger.info(
        "CRM Ingestor [%s]: %d files -> %d chunks extraidos, %d salvos, %d erros",
        repo, stats["files_processed"], stats["chunks_extracted"],
        stats["chunks_saved"], len(stats["errors"]),
    )
    return stats


def ingest_all_crm_repos(
    *,
    token: Optional[str] = None,
    save_to_chromadb: bool = True,
) -> dict:
    """
    Ingere todos os 6 repos CRM em sequencia.

    Returns:
        Dict com stats agregados e detalhes por repo.
    """
    token = token or os.environ.get("GITHUB_TOKEN")

    results = {
        "total_repos": len(CRM_REPOS),
        "repos_processed": 0,
        "total_chunks": 0,
        "total_saved": 0,
        "total_errors": 0,
        "repos": [],
    }

    for repo_config in CRM_REPOS:
        logger.info("=" * 60)
        logger.info("Processando: %s", repo_config["url"])
        logger.info("Descricao: %s", repo_config["description"])

        stats = ingest_crm_repository(
            repo_config["url"],
            branch=repo_config["branch"],
            token=token,
            save_to_chromadb=save_to_chromadb,
        )

        results["repos"].append(stats)
        results["repos_processed"] += 1
        results["total_chunks"] += stats.get("chunks_extracted", 0)
        results["total_saved"] += stats.get("chunks_saved", 0)
        results["total_errors"] += len(stats.get("errors", []))

    logger.info("=" * 60)
    logger.info(
        "CRM Ingestor COMPLETO: %d repos, %d chunks, %d salvos, %d erros",
        results["repos_processed"], results["total_chunks"],
        results["total_saved"], results["total_errors"],
    )
    return results


def main():
    """CLI: python -m src.extractors.crm_repo_ingestor [--repo URL] [--all]"""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="Ingere codigo CRM dos repos SendSpeed")
    parser.add_argument("--repo", help="URL de um repo especifico")
    parser.add_argument("--branch", "-b", default="pedro-crm", help="Branch (default: pedro-crm)")
    parser.add_argument("--all", action="store_true", help="Ingere todos os 6 repos CRM")
    parser.add_argument("--no-chromadb", action="store_true", help="Nao salvar no ChromaDB")
    parser.add_argument("--list-repos", action="store_true", help="Lista repos configurados")
    args = parser.parse_args()

    if args.list_repos:
        for r in CRM_REPOS:
            print(f"  {r['url']} (branch: {r['branch']})")
            print(f"    {r['description']}")
        return

    if args.all:
        stats = ingest_all_crm_repos(save_to_chromadb=not args.no_chromadb)
    elif args.repo:
        stats = ingest_crm_repository(
            args.repo,
            branch=args.branch,
            save_to_chromadb=not args.no_chromadb,
        )
    else:
        parser.print_help()
        return

    print(json.dumps(stats, indent=2, default=str))


if __name__ == "__main__":
    main()
