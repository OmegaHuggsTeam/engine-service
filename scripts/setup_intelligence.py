"""
Setup Intelligence - Pipeline completo de criação de inteligência n8n.

Este script executa todo o pipeline:
1. Ingestão em massa do repositório zie619
2. Geração de arquivos de conhecimento
3. Teste do ComposerAgent
4. Verificação de conectividade

Uso:
    python scripts/setup_intelligence.py [--skip-ingestion] [--test-composer]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


def check_environment():
    """Verifica variáveis de ambiente necessárias."""
    import os

    print("🔍 Verificando ambiente...")
    print("-" * 80)

    checks = {
        "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN"),
        "TELEGRAM_BOT_TOKEN": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "GROQ_API_KEY": os.environ.get("GROQ_API_KEY"),
    }

    all_ok = True
    for key, value in checks.items():
        status = "✅" if value else "⚠️ "
        print(f"{status} {key}: {'configurado' if value else 'não configurado'}")
        if not value and key != "GITHUB_TOKEN":
            all_ok = False

    print()

    if not all_ok:
        print("⚠️  Algumas variáveis de ambiente não estão configuradas.")
        print("   O sistema pode funcionar com limitações.")
        print()

    return all_ok


def run_ingestion():
    """Executa ingestão em massa."""
    print("📥 Executando ingestão em massa...")
    print("-" * 80)

    from src.extractors.github_ingestor import ingest_repository

    ZIE619_REPO = "https://github.com/zie619/zie619.github.io"

    try:
        stats = ingest_repository(ZIE619_REPO, save_to_chromadb=True)

        print(f"✅ Workflows processados: {stats['workflows_processed']}")
        print(f"✅ Chunks salvos: {stats['chunks_saved']}")

        if stats["errors"]:
            print(f"⚠️  Erros: {len(stats['errors'])}")

        print()
        return True

    except Exception as e:
        logger.exception("Falha na ingestão: %s", e)
        print(f"❌ Erro na ingestão: {e}")
        print()
        return False


def generate_knowledge():
    """Gera arquivos de conhecimento."""
    print("🧬 Gerando arquivos de conhecimento...")
    print("-" * 80)

    try:
        from src.processors.n8n_knowledge import (
            generate_capabilities_md,
            generate_master_context,
            generate_recipes_md,
        )
        from src.utils.vector_db import get_all_chunks

        # Carregar chunks
        all_chunks = get_all_chunks()
        external_modules = [c for c in all_chunks if c.get("category") == "external_template"]

        if not external_modules:
            print("⚠️  Nenhum módulo external_template encontrado no ChromaDB")
            print("   Execute a ingestão primeiro: python scripts/mass_ingestion.py")
            print()
            return False

        print(f"📚 Módulos carregados: {len(external_modules)}")

        # Gerar arquivos
        cap_path = generate_capabilities_md(external_modules)
        print(f"✅ Gerado: {cap_path}")

        recipes_path = generate_recipes_md(external_modules)
        print(f"✅ Gerado: {recipes_path}")

        context_path = generate_master_context(external_modules)
        print(f"✅ Gerado: {context_path}")

        print()
        return True

    except Exception as e:
        logger.exception("Falha ao gerar conhecimento: %s", e)
        print(f"❌ Erro ao gerar conhecimento: {e}")
        print()
        return False


def test_composer():
    """Testa o ComposerAgent."""
    print("🧪 Testando ComposerAgent...")
    print("-" * 80)

    try:
        from src.neural_link.agents.composer_agent import ComposerAgent

        agent = ComposerAgent()

        # Teste simples
        test_objective = "Criar workflow que recebe webhook e envia notificação no Telegram"

        print(f"Objetivo de teste: {test_objective}")
        print()

        result = agent.compose_workflow(test_objective, max_templates=3)

        if "error" in result:
            print(f"❌ Erro: {result['error']}")
            print()
            return False

        print(f"✅ Workflow criado: {result['workflow']['name']}")
        print(f"✅ Nodes: {len(result['workflow']['nodes'])}")
        print(f"✅ Templates usados: {len(result['templates_used'])}")
        print()

        # Salvar resultado de teste
        test_output = Path("data/generated_workflows/test_workflow.json")
        test_output.parent.mkdir(parents=True, exist_ok=True)

        with open(test_output, "w", encoding="utf-8") as f:
            json.dump(result["workflow"], f, indent=2, ensure_ascii=False)

        print(f"📁 Workflow de teste salvo em: {test_output}")
        print()

        return True

    except Exception as e:
        logger.exception("Falha no teste do ComposerAgent: %s", e)
        print(f"❌ Erro no teste: {e}")
        print()
        return False


def verify_chromadb():
    """Verifica conectividade com ChromaDB."""
    print("🔌 Verificando ChromaDB...")
    print("-" * 80)

    try:
        from src.utils.vector_db import get_collection_stats

        stats = get_collection_stats()

        print(f"✅ Collection: {stats.get('name', 'unknown')}")
        print(f"✅ Documentos: {stats.get('count', 0)}")
        print()

        return True

    except Exception as e:
        logger.exception("Falha ao verificar ChromaDB: %s", e)
        print(f"❌ Erro ao verificar ChromaDB: {e}")
        print()
        return False


def main():
    parser = argparse.ArgumentParser(description="Setup completo de inteligência n8n")
    parser.add_argument(
        "--skip-ingestion",
        action="store_true",
        help="Pular ingestão (usar dados existentes)",
    )
    parser.add_argument(
        "--test-composer",
        action="store_true",
        help="Executar teste do ComposerAgent",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 80)
    print("🧠 BUNKER INTELLIGENCE SETUP")
    print("=" * 80)
    print()

    # Step 1: Check environment
    check_environment()

    # Step 2: Verify ChromaDB
    if not verify_chromadb():
        print("❌ ChromaDB não está acessível. Verifique a configuração.")
        return 1

    # Step 3: Ingestion (optional)
    if not args.skip_ingestion:
        if not run_ingestion():
            print("❌ Ingestão falhou. Abortando.")
            return 1
    else:
        print("⏭️  Ingestão pulada (usando dados existentes)")
        print()

    # Step 4: Generate knowledge
    if not generate_knowledge():
        print("❌ Geração de conhecimento falhou. Abortando.")
        return 1

    # Step 5: Test composer (optional)
    if args.test_composer:
        if not test_composer():
            print("⚠️  Teste do ComposerAgent falhou, mas o setup continua.")

    # Final summary
    print("=" * 80)
    print("🎯 SETUP COMPLETO!")
    print("=" * 80)
    print()
    print("Próximos passos:")
    print("  1. Inicie o bot Telegram:")
    print("     python -m src.neural_link.telemetry.telegram_command_handler")
    print()
    print("  2. Use os comandos:")
    print("     /explain_workflow <url> - Explica workflows")
    print("     /create_n8n <objetivo> - Cria novo workflow")
    print()
    print("  3. Verifique os arquivos gerados:")
    print("     - vault/Knowledge/n8n_capabilities.md")
    print("     - vault/Knowledge/n8n_recipes.md")
    print("     - data/chunks/n8n_master_context.json")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
