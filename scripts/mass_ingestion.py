"""
Mass Ingestion Script - Executa ingestão completa do repositório zie619.

Este script:
1. Executa github_ingestor no repositório zie619/zie619.github.io
2. Gera n8n_capabilities.md e n8n_recipes.md
3. Gera n8n_master_context.json para o SpecialistAgent
4. Reporta estatísticas completas

Uso:
    python scripts/mass_ingestion.py [--no-chromadb] [--token GITHUB_TOKEN]
"""

import argparse
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extractors.github_ingestor import ingest_repository
from src.processors.n8n_knowledge import (
    generate_capabilities_md,
    generate_master_context,
    generate_recipes_md,
)
from src.utils.vector_db import get_collection_stats

logger = logging.getLogger(__name__)

ZIE619_REPO = "https://github.com/zie619/zie619.github.io"


def main():
    parser = argparse.ArgumentParser(
        description="Ingestão em massa de workflows n8n do repositório zie619"
    )
    parser.add_argument(
        "--no-chromadb",
        action="store_true",
        help="Não salvar chunks no ChromaDB (apenas gerar arquivos)",
    )
    parser.add_argument(
        "--token",
        "-t",
        help="GitHub token para rate limit maior (ou use GITHUB_TOKEN env var)",
    )
    parser.add_argument(
        "--branch",
        "-b",
        default=None,
        help="Branch específico (default: branch padrão do repo)",
    )
    parser.add_argument(
        "--vault",
        default="vault",
        help="Caminho do vault Obsidian (default: vault)",
    )
    parser.add_argument(
        "--output",
        default="data/chunks",
        help="Diretório de saída para n8n_master_context.json (default: data/chunks)",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 80)
    print("🧠 BUNKER MASS INGESTION - Criação de Inteligência n8n")
    print("=" * 80)
    print(f"Repositório: {ZIE619_REPO}")
    print(f"Branch: {args.branch or 'default'}")
    print(f"ChromaDB: {'disabled' if args.no_chromadb else 'enabled'}")
    print(f"Vault: {args.vault}")
    print(f"Output: {args.output}")
    print("=" * 80)
    print()

    # Step 1: GitHub Ingestion
    print("📥 STEP 1: Ingestão do GitHub...")
    print("-" * 80)

    stats = ingest_repository(
        ZIE619_REPO,
        branch=args.branch,
        token=args.token,
        save_to_chromadb=not args.no_chromadb,
    )

    print(f"✅ Arquivos JSON encontrados: {stats['total_files']}")
    print(f"✅ Workflows n8n processados: {stats['workflows_processed']}")
    print(f"✅ Chunks salvos no ChromaDB: {stats['chunks_saved']}")

    if stats["errors"]:
        print(f"⚠️  Erros encontrados: {len(stats['errors'])}")
        for err in stats["errors"][:5]:  # Show first 5 errors
            print(f"   - {err.get('path', 'unknown')}: {err.get('error', 'unknown error')}")

    print()

    # Step 2: Load modules from ChromaDB for knowledge generation
    print("📚 STEP 2: Carregando módulos do ChromaDB...")
    print("-" * 80)

    try:
        from src.utils.vector_db import get_all_chunks

        all_chunks = get_all_chunks()
        external_modules = [c for c in all_chunks if c.get("category") == "external_template"]

        print(f"✅ Total de chunks no ChromaDB: {len(all_chunks)}")
        print(f"✅ Módulos external_template: {len(external_modules)}")
        print()

    except Exception as e:
        logger.error(f"Falha ao carregar chunks do ChromaDB: {e}")
        print(f"❌ Erro ao carregar chunks: {e}")
        print("   Continuando sem geração de conhecimento...")
        external_modules = []
        print()

    # Step 3: Generate Knowledge Files
    if external_modules:
        print("🧬 STEP 3: Gerando arquivos de conhecimento...")
        print("-" * 80)

        try:
            # Generate n8n_capabilities.md
            cap_path = generate_capabilities_md(external_modules, vault_path=args.vault)
            print(f"✅ Gerado: {cap_path}")

            # Generate n8n_recipes.md
            recipes_path = generate_recipes_md(external_modules, vault_path=args.vault)
            print(f"✅ Gerado: {recipes_path}")

            # Generate n8n_master_context.json
            context_path = generate_master_context(external_modules, output_dir=args.output)
            print(f"✅ Gerado: {context_path}")
            print()

        except Exception as e:
            logger.error(f"Falha ao gerar arquivos de conhecimento: {e}")
            print(f"❌ Erro na geração de conhecimento: {e}")
            print()
    else:
        print("⚠️  STEP 3: Pulado (nenhum módulo external_template encontrado)")
        print()

    # Step 4: Final Statistics
    print("📊 STEP 4: Estatísticas Finais")
    print("=" * 80)

    if not args.no_chromadb:
        try:
            collection_stats = get_collection_stats()
            print(f"ChromaDB Collection: {collection_stats.get('name', 'unknown')}")
            print(f"Total de documentos: {collection_stats.get('count', 0)}")
            print()
        except Exception as e:
            logger.warning(f"Não foi possível obter stats do ChromaDB: {e}")

    print("🎯 INGESTÃO COMPLETA!")
    print()
    print("Próximos passos:")
    print("  1. Verifique os arquivos gerados em vault/Knowledge/")
    print("  2. Use o ComposerAgent via Telegram: /create_n8n <objetivo>")
    print("  3. O SpecialistAgent agora tem acesso a 4.300+ workflows de referência")
    print("=" * 80)


if __name__ == "__main__":
    main()
