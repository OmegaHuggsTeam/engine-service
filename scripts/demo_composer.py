"""
Demo ComposerAgent - Demonstração interativa do ComposerAgent.

Este script permite testar o ComposerAgent localmente sem precisar do Telegram.
Útil para desenvolvimento e debugging.

Uso:
    python scripts/demo_composer.py
    python scripts/demo_composer.py --objective "seu objetivo aqui"
"""

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.neural_link.agents.composer_agent import ComposerAgent

logger = logging.getLogger(__name__)


def print_separator(char="=", length=80):
    """Imprime separador."""
    print(char * length)


def print_workflow_summary(result: dict):
    """Imprime resumo do workflow gerado."""
    if "error" in result:
        print(f"\n❌ Erro: {result['error']}")
        if "suggestion" in result:
            print(f"💡 Sugestão: {result['suggestion']}")
        return

    workflow = result["workflow"]
    templates = result["templates_used"]
    reasoning = result["reasoning"]

    print_separator()
    print("✅ WORKFLOW CRIADO COM SUCESSO!")
    print_separator()
    print()

    print(f"📝 Nome: {workflow['name']}")
    print(f"🔧 Nodes: {len(workflow['nodes'])}")
    print(f"🔗 Conexões: {len(workflow['connections'])}")
    print(f"📚 Templates usados: {len(templates)}")
    print()

    print_separator("-")
    print("🔧 NODES DO WORKFLOW")
    print_separator("-")
    for i, node in enumerate(workflow["nodes"], 1):
        print(f"{i}. {node['name']}")
        print(f"   Tipo: {node['type']}")
        print(f"   Posição: {node['position']}")
        print()

    print_separator("-")
    print("📚 TEMPLATES UTILIZADOS")
    print_separator("-")
    for i, template in enumerate(templates, 1):
        source = template["source"].replace("github/zie619.github.io/", "")
        print(f"{i}. {template['service']} ({template['node_type']})")
        print(f"   Relevância: {template['relevance']:.2f}")
        print(f"   Fonte: {source}")
        print()

    print_separator("-")
    print("💭 RACIOCÍNIO DA COMPOSIÇÃO")
    print_separator("-")
    print(reasoning)
    print()


def save_workflow(workflow: dict, output_dir: str = "data/generated_workflows") -> Path:
    """Salva workflow em arquivo JSON."""
    from datetime import datetime

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"demo_workflow_{timestamp}.json"

    file_path = output_path / filename
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(workflow, f, indent=2, ensure_ascii=False)

    return file_path


def interactive_mode():
    """Modo interativo para testar múltiplos objetivos."""
    print_separator()
    print("🧠 COMPOSER AGENT - MODO INTERATIVO")
    print_separator()
    print()
    print("Digite seus objetivos para criar workflows n8n.")
    print("Digite 'sair' ou 'quit' para encerrar.")
    print()

    agent = ComposerAgent()

    while True:
        print_separator("-")
        objective = input("\n💡 Objetivo: ").strip()

        if objective.lower() in ["sair", "quit", "exit", "q"]:
            print("\n👋 Até logo!")
            break

        if not objective:
            print("⚠️  Objetivo vazio. Tente novamente.")
            continue

        print(f"\n🔄 Processando: {objective}")
        print("⏳ Aguarde...")
        print()

        try:
            result = agent.compose_workflow(objective)
            print_workflow_summary(result)

            if "workflow" in result:
                file_path = save_workflow(result["workflow"])
                print(f"💾 Workflow salvo em: {file_path}")
                print()

        except Exception as e:
            logger.exception("Erro ao compor workflow: %s", e)
            print(f"\n❌ Erro: {e}")
            print()


def single_objective_mode(objective: str):
    """Modo de objetivo único."""
    print_separator()
    print("🧠 COMPOSER AGENT - DEMO")
    print_separator()
    print()
    print(f"💡 Objetivo: {objective}")
    print()
    print("🔄 Processando...")
    print()

    try:
        agent = ComposerAgent()
        result = agent.compose_workflow(objective)

        print_workflow_summary(result)

        if "workflow" in result:
            file_path = save_workflow(result["workflow"])
            print_separator()
            print(f"💾 Workflow salvo em: {file_path}")
            print()
            print("📋 Próximos passos:")
            print("  1. Importe o arquivo JSON no n8n")
            print("  2. Configure as credenciais necessárias")
            print("  3. Ative o workflow")
            print_separator()

    except Exception as e:
        logger.exception("Erro ao compor workflow: %s", e)
        print(f"\n❌ Erro: {e}")
        return 1

    return 0


def demo_examples():
    """Executa exemplos pré-definidos."""
    examples = [
        "Receber webhook e enviar notificação no Telegram",
        "Monitorar Google Sheets e enviar email",
        "Webhook -> Supabase -> Telegram",
    ]

    print_separator()
    print("🧠 COMPOSER AGENT - EXEMPLOS")
    print_separator()
    print()
    print(f"Executando {len(examples)} exemplos...")
    print()

    agent = ComposerAgent()

    for i, objective in enumerate(examples, 1):
        print_separator("=")
        print(f"EXEMPLO {i}/{len(examples)}")
        print_separator("=")
        print()
        print(f"💡 Objetivo: {objective}")
        print()

        try:
            result = agent.compose_workflow(objective, max_templates=3)

            if "error" in result:
                print(f"❌ Erro: {result['error']}")
            else:
                workflow = result["workflow"]
                print(f"✅ Workflow: {workflow['name']}")
                print(f"   Nodes: {len(workflow['nodes'])}")
                print(f"   Templates: {len(result['templates_used'])}")

                file_path = save_workflow(workflow)
                print(f"   Salvo em: {file_path}")

        except Exception as e:
            print(f"❌ Erro: {e}")

        print()

    print_separator()
    print("✅ Exemplos concluídos!")
    print_separator()


def main():
    parser = argparse.ArgumentParser(description="Demonstração do ComposerAgent")
    parser.add_argument(
        "--objective",
        "-o",
        help="Objetivo para criar workflow (modo não-interativo)",
    )
    parser.add_argument(
        "--examples",
        "-e",
        action="store_true",
        help="Executar exemplos pré-definidos",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Modo verbose (mostrar logs)",
    )
    args = parser.parse_args()

    log_level = logging.INFO if args.verbose else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if args.examples:
        demo_examples()
        return 0

    if args.objective:
        return single_objective_mode(args.objective)

    # Modo interativo por padrão
    interactive_mode()
    return 0


if __name__ == "__main__":
    sys.exit(main())
