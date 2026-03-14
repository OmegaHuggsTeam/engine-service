"""
Verify Intelligence - Verifica se o sistema de inteligência está funcionando.

Este script executa uma série de testes para garantir que:
1. ChromaDB está acessível e contém templates
2. Arquivos de conhecimento foram gerados
3. ComposerAgent está funcional
4. Telegram bot está configurado (opcional)

Uso:
    python scripts/verify_intelligence.py [--verbose]
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

logger = logging.getLogger(__name__)


class VerificationResult:
    """Resultado de uma verificação."""

    def __init__(self, name: str, passed: bool, message: str, details: dict = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.details = details or {}

    def __str__(self):
        status = "✅" if self.passed else "❌"
        return f"{status} {self.name}: {self.message}"


def verify_chromadb() -> VerificationResult:
    """Verifica se ChromaDB está acessível e contém templates."""
    try:
        from src.utils.vector_db import get_all_chunks, get_collection_stats

        stats = get_collection_stats()
        total_docs = stats.get("count", 0)

        if total_docs == 0:
            return VerificationResult("ChromaDB", False, "ChromaDB está vazio", {"total_docs": 0})

        # Verificar templates external_template
        all_chunks = get_all_chunks()
        external_templates = [c for c in all_chunks if c.get("category") == "external_template"]

        if not external_templates:
            return VerificationResult(
                "ChromaDB",
                False,
                f"ChromaDB tem {total_docs} docs, mas nenhum external_template",
                {"total_docs": total_docs, "external_templates": 0},
            )

        return VerificationResult(
            "ChromaDB",
            True,
            f"{total_docs} documentos, {len(external_templates)} templates",
            {"total_docs": total_docs, "external_templates": len(external_templates)},
        )

    except Exception as e:
        return VerificationResult("ChromaDB", False, f"Erro ao acessar: {e}", {"error": str(e)})


def verify_knowledge_files() -> VerificationResult:
    """Verifica se arquivos de conhecimento foram gerados."""
    required_files = [
        "vault/Knowledge/n8n_capabilities.md",
        "vault/Knowledge/n8n_recipes.md",
        "data/chunks/n8n_master_context.json",
    ]

    missing = []
    found = []

    for file_path in required_files:
        path = Path(file_path)
        if path.exists():
            found.append(file_path)
        else:
            missing.append(file_path)

    if missing:
        return VerificationResult(
            "Knowledge Files",
            False,
            f"{len(found)}/{len(required_files)} arquivos encontrados",
            {"found": found, "missing": missing},
        )

    return VerificationResult(
        "Knowledge Files",
        True,
        f"Todos os {len(required_files)} arquivos encontrados",
        {"files": found},
    )


def verify_composer_agent() -> VerificationResult:
    """Verifica se ComposerAgent está funcional."""
    try:
        from src.neural_link.agents.composer_agent import ComposerAgent

        agent = ComposerAgent()

        # Verificar se master_context foi carregado
        if not agent.master_context:
            return VerificationResult(
                "ComposerAgent",
                False,
                "Master context não foi carregado",
                {"master_context_chunks": 0},
            )

        # Teste simples de composição
        test_objective = "webhook para telegram"
        result = agent.compose_workflow(test_objective, max_templates=2)

        if "error" in result:
            return VerificationResult(
                "ComposerAgent",
                False,
                f"Erro ao compor workflow: {result['error']}",
                {"error": result.get("error"), "suggestion": result.get("suggestion")},
            )

        return VerificationResult(
            "ComposerAgent",
            True,
            f"Funcional ({len(agent.master_context)} context chunks)",
            {
                "master_context_chunks": len(agent.master_context),
                "test_workflow_nodes": len(result["workflow"]["nodes"]),
                "test_templates_used": len(result["templates_used"]),
            },
        )

    except Exception as e:
        return VerificationResult(
            "ComposerAgent", False, f"Erro ao inicializar: {e}", {"error": str(e)}
        )


def verify_telegram_config() -> VerificationResult:
    """Verifica se Telegram bot está configurado."""
    import os

    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()

    if not token:
        return VerificationResult(
            "Telegram Config", False, "TELEGRAM_BOT_TOKEN não configurado", {"configured": False}
        )

    # Tentar verificar conectividade
    try:
        import httpx

        url = f"https://api.telegram.org/bot{token}/getMe"
        with httpx.Client(timeout=10) as client:
            r = client.get(url)

            if r.status_code == 200:
                data = r.json()
                bot_info = data.get("result", {})
                bot_name = bot_info.get("username", "unknown")

                return VerificationResult(
                    "Telegram Config",
                    True,
                    f"Bot @{bot_name} configurado e acessível",
                    {"bot_username": bot_name, "configured": True},
                )
            else:
                return VerificationResult(
                    "Telegram Config",
                    False,
                    f"Token inválido (HTTP {r.status_code})",
                    {"configured": True, "valid": False},
                )

    except Exception as e:
        return VerificationResult(
            "Telegram Config",
            False,
            f"Erro ao verificar conectividade: {e}",
            {"configured": True, "error": str(e)},
        )


def verify_environment() -> VerificationResult:
    """Verifica variáveis de ambiente essenciais."""
    import os

    required = {
        "GROQ_API_KEY": "Obrigatório para LLM",
    }

    optional = {
        "GITHUB_TOKEN": "Recomendado para rate limit maior",
        "TELEGRAM_BOT_TOKEN": "Necessário para bot Telegram",
    }

    missing_required = []
    missing_optional = []
    configured = []

    for key, desc in required.items():
        if os.environ.get(key):
            configured.append(key)
        else:
            missing_required.append(f"{key} ({desc})")

    for key, desc in optional.items():
        if os.environ.get(key):
            configured.append(key)
        else:
            missing_optional.append(f"{key} ({desc})")

    if missing_required:
        return VerificationResult(
            "Environment",
            False,
            f"Variáveis obrigatórias faltando: {', '.join(missing_required)}",
            {
                "configured": configured,
                "missing_required": missing_required,
                "missing_optional": missing_optional,
            },
        )

    message = f"{len(configured)} variáveis configuradas"
    if missing_optional:
        message += f", {len(missing_optional)} opcionais faltando"

    return VerificationResult(
        "Environment",
        True,
        message,
        {"configured": configured, "missing_optional": missing_optional},
    )


def main():
    parser = argparse.ArgumentParser(
        description="Verifica se o sistema de inteligência está funcionando"
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Mostrar detalhes completos de cada verificação",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.WARNING,  # Menos verbose por padrão
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    print("=" * 80)
    print("🔍 BUNKER INTELLIGENCE VERIFICATION")
    print("=" * 80)
    print()

    # Executar verificações
    verifications = [
        ("Environment", verify_environment),
        ("ChromaDB", verify_chromadb),
        ("Knowledge Files", verify_knowledge_files),
        ("ComposerAgent", verify_composer_agent),
        ("Telegram Config", verify_telegram_config),
    ]

    results = []

    for name, verify_func in verifications:
        print(f"Verificando {name}...", end=" ")
        result = verify_func()
        results.append(result)
        print(result.message)

        if args.verbose and result.details:
            print(f"  Detalhes: {json.dumps(result.details, indent=2)}")

        print()

    # Resumo
    print("=" * 80)
    print("📊 RESUMO")
    print("=" * 80)

    passed = sum(1 for r in results if r.passed)
    total = len(results)

    for result in results:
        print(result)

    print()
    print(f"Total: {passed}/{total} verificações passaram")
    print()

    # Recomendações
    if passed < total:
        print("⚠️  AÇÕES RECOMENDADAS:")
        print("-" * 80)

        for result in results:
            if not result.passed:
                if result.name == "ChromaDB":
                    print("• Execute: python scripts/mass_ingestion.py")
                elif result.name == "Knowledge Files":
                    print("• Execute: python scripts/setup_intelligence.py")
                elif result.name == "ComposerAgent":
                    print("• Verifique se ChromaDB e Knowledge Files estão OK primeiro")
                elif result.name == "Telegram Config":
                    print("• Configure TELEGRAM_BOT_TOKEN no ambiente")
                elif result.name == "Environment":
                    print("• Configure as variáveis de ambiente faltando")

        print()
        print("Para setup completo, execute:")
        print("  python scripts/setup_intelligence.py")
        print("=" * 80)
        return 1

    print("🎯 SISTEMA TOTALMENTE FUNCIONAL!")
    print()
    print("Próximos passos:")
    print("  1. Inicie o bot: python -m src.neural_link.telemetry.telegram_command_handler")
    print("  2. Use /create_n8n <objetivo> no Telegram")
    print("  3. Consulte: docs/INTELLIGENCE_SETUP.md")
    print("=" * 80)

    return 0


if __name__ == "__main__":
    sys.exit(main())
