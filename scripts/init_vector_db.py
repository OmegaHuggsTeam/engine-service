"""
Inicializa o ChromaDB migrando chunks existentes dos JSONs para o banco vetorial.
Execute após o pipeline de processamento para popular o ChromaDB.
"""

import json
import sys
from pathlib import Path

# Adiciona raiz ao path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

CHUNKS_DIR = PROJECT_ROOT / "data" / "chunks"


def main():
    print("Inicializando ChromaDB...")

    try:
        from src.utils.vector_db import add_chunks, count
    except ImportError as e:
        print(f"[ERRO] {e}")
        print("Instale: pip install chromadb")
        return 1

    if not CHUNKS_DIR.exists():
        print(f"Pasta {CHUNKS_DIR} nao existe.")
        print("Execute o pipeline primeiro para gerar chunks.")
        return 1

    json_files = list(CHUNKS_DIR.glob("*.json"))
    if not json_files:
        print("Nenhum arquivo .json em data/chunks.")
        print("Execute o pipeline primeiro.")
        return 1

    total = 0
    for jf in json_files:
        try:
            data = json.loads(jf.read_text(encoding="utf-8"))
            chunks = data if isinstance(data, list) else [data]
            added = add_chunks(chunks)
            total += added
            print(f"  [OK] {jf.name}: {added} chunks")
        except Exception as e:
            print(f"  [ERRO] {jf.name}: {e}")

    print(f"\n[OK] Total: {total} chunks no ChromaDB (db/chroma)")
    print(f"     Verificacao: {count()} chunks na colecao")
    return 0


if __name__ == "__main__":
    sys.exit(main())
