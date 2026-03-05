"""
Workflow Scrapper - Baixa workflows n8n do repositório Zie619/n8n-workflows.

Acessa https://github.com/Zie619/n8n-workflows, lista todos os .json em workflows/,
baixa e salva em data/workflows/ preservando a estrutura de pastas.

Uso:
  python tools/workflow_scrapper.py
  python tools/workflow_scrapper.py --limit 50
  python tools/workflow_scrapper.py --output data/workflows

Importação no n8n: Settings > Import from File > selecione os JSONs em data/workflows/
"""

import argparse
import json
import sys
from pathlib import Path

import httpx

REPO = "Zie619/n8n-workflows"
BRANCH = "main"
GITHUB_API = "https://api.github.com"
GITHUB_RAW = "https://raw.githubusercontent.com"
WORKFLOWS_PREFIX = "workflows/"


def list_workflow_paths(token: str | None = None) -> list[str]:
    """Lista todos os paths de arquivos .json em workflows/ via Git Trees API."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    with httpx.Client(timeout=60) as client:
        r = client.get(
            f"{GITHUB_API}/repos/{REPO}/git/trees/{BRANCH}?recursive=1",
            headers=headers,
        )
        r.raise_for_status()
        data = r.json()
        tree = data.get("tree", [])
        return [
            item["path"]
            for item in tree
            if item.get("type") == "blob"
            and item["path"].startswith(WORKFLOWS_PREFIX)
            and item["path"].lower().endswith(".json")
        ]


def download_workflow(path: str) -> str:
    """Baixa conteúdo de um arquivo via raw URL."""
    url = f"{GITHUB_RAW}/{REPO}/{BRANCH}/{path}"
    with httpx.Client(timeout=30, follow_redirects=True) as client:
        r = client.get(url)
        r.raise_for_status()
        return r.text


def main() -> int:
    parser = argparse.ArgumentParser(description="Baixa workflows n8n do Zie619/n8n-workflows")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "data" / "workflows",
        help="Pasta de destino (default: data/workflows)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limitar quantidade de workflows (0 = todos)",
    )
    parser.add_argument(
        "--token",
        type=str,
        default=None,
        help="GITHUB_TOKEN para rate limit maior",
    )
    args = parser.parse_args()

    token = args.token or __import__("os").environ.get("GITHUB_TOKEN")
    output_dir = args.output
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Listando workflows em {REPO}...")
    try:
        paths = list_workflow_paths(token)
    except Exception as e:
        print(f"Erro ao listar: {e}")
        return 1

    if args.limit:
        paths = paths[: args.limit]
        print(f"Limitando a {args.limit} workflows")
    print(f"Encontrados {len(paths)} arquivos .json")

    ok = 0
    fail = 0
    for i, path in enumerate(paths, 1):
        rel_path = path[len(WORKFLOWS_PREFIX) :] if path.startswith(WORKFLOWS_PREFIX) else path
        dest = output_dir / rel_path
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            content = download_workflow(path)
            # Valida se é JSON válido (workflow n8n)
            try:
                data = json.loads(content)
                if not isinstance(data, dict):
                    raise ValueError("Não é um objeto JSON")
            except json.JSONDecodeError:
                raise ValueError("JSON inválido")
            dest.write_text(content, encoding="utf-8")
            ok += 1
            if i % 50 == 0 or i == len(paths):
                print(f"  [{i}/{len(paths)}] OK: {path}")
        except Exception as e:
            fail += 1
            print(f"  [FALHA] {path}: {e}")

    print(f"\nConcluído: {ok} salvos, {fail} falhas")
    print(f"Workflows em: {output_dir.absolute()}")
    print("\nImportação no n8n: Settings > Import from File > selecione os JSONs")
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
