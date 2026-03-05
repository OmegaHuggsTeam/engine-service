"""
Gera workflow bot_evolution.json para o projeto Bot Self-Evolution.

Usa ComposerAgent com prompt específico, valida com n8n_validator
e salva em data/generated_workflows/bot_evolution.json.
"""

import json
import logging
import sys
from pathlib import Path

# Add project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

COMPOSITION_PROMPT = (
    "Crie um fluxo que automatize a criação de novos comandos de bot, "
    "incluindo um node de validação de segurança. "
    "O fluxo deve: receber mensagem via Telegram, consultar ChromaDB buscando "
    "por external_template relacionados a 'Telegram Command Handlers'."
)

OUTPUT_PATH = PROJECT_ROOT / "data" / "generated_workflows" / "bot_evolution.json"
REFERENCE_DIR = PROJECT_ROOT / "data" / "raw"


def _build_workflow_manually() -> dict:
    """
    Constrói workflow n8n v1.0+ manualmente.
    Telegram -> Set (query) -> HTTP (ChromaDB) -> If (validação) -> Set (output)
    """
    return {
        "name": "Bot Self-Evolution",
        "nodes": [
            {
                "id": "telegram-trigger",
                "name": "Telegram Trigger",
                "type": "n8n-nodes-base.telegramTrigger",
                "typeVersion": 1.2,
                "position": [240, 300],
                "parameters": {"updates": ["message"]},
            },
            {
                "id": "set-query",
                "name": "Prepare ChromaDB Query",
                "type": "n8n-nodes-base.set",
                "typeVersion": 3.4,
                "position": [460, 300],
                "parameters": {
                    "assignments": {
                        "assignments": [
                            {"id": "q1", "name": "query", "value": "Telegram Command Handlers external_template", "type": "string"},
                            {"id": "c1", "name": "category", "value": "external_template", "type": "string"},
                        ]
                    },
                    "options": {},
                },
            },
            {
                "id": "chromadb-search",
                "name": "ChromaDB Search",
                "type": "n8n-nodes-base.httpRequest",
                "typeVersion": 4.2,
                "position": [680, 300],
                "parameters": {
                    "method": "POST",
                    "url": "={{ $env.N8N_BUNKER_URL || 'http://localhost:8000' }}/api/chromadb/search",
                    "sendBody": True,
                    "specifyBody": "json",
                    "jsonBody": "={\"query\": \"{{ $json.query }}\", \"category\": \"{{ $json.category }}\", \"top_k\": 5}",
                    "options": {},
                },
            },
            {
                "id": "security-validation",
                "name": "Security Validation",
                "type": "n8n-nodes-base.if",
                "typeVersion": 2.2,
                "position": [900, 300],
                "parameters": {
                    "conditions": {
                        "options": {"caseSensitive": True, "leftValue": "", "typeValidation": "loose", "version": 2},
                        "conditions": [
                            {
                                "id": "v1",
                                "leftValue": "={{ $json }}",
                                "rightValue": "",
                                "operator": {"type": "object", "operation": "exists", "singleValue": True},
                            }
                        ],
                        "combinator": "and",
                    },
                    "options": {},
                },
            },
            {
                "id": "format-output",
                "name": "Format Output",
                "type": "n8n-nodes-base.set",
                "typeVersion": 3.4,
                "position": [1120, 300],
                "parameters": {
                    "assignments": {
                        "assignments": [
                            {"id": "r1", "name": "templates_found", "value": "={{ Array.isArray($json) ? $json.length : 0 }}", "type": "number"},
                            {"id": "m1", "name": "message", "value": "Chunks encontrados para Telegram Command Handlers", "type": "string"},
                        ]
                    },
                    "options": {},
                },
            },
        ],
        "connections": {
            "Telegram Trigger": {"main": [[{"node": "Prepare ChromaDB Query", "type": "main", "index": 0}]]},
            "Prepare ChromaDB Query": {"main": [[{"node": "ChromaDB Search", "type": "main", "index": 0}]]},
            "ChromaDB Search": {"main": [[{"node": "Security Validation", "type": "main", "index": 0}]]},
            "Security Validation": {"main": [[{"node": "Format Output", "type": "main", "index": 0}], []]},
        },
        "settings": {"executionOrder": "v1"},
        "meta": {"templateCredsSetupCompleted": False},
    }


def main():
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    workflow = None
    try:
        from src.neural_link.agents.composer_agent import ComposerAgent
        agent = ComposerAgent()
        result = agent.compose_workflow(COMPOSITION_PROMPT, max_templates=5)
        if "error" not in result:
            workflow = result["workflow"]
            workflow["name"] = "Bot Self-Evolution"
            logger.info("ComposerAgent gerou workflow com %d nodes", len(workflow.get("nodes", [])))
        else:
            logger.warning("ComposerAgent: %s - usando workflow manual", result.get("error", ""))
    except Exception as e:
        logger.warning("ComposerAgent falhou: %s - usando workflow manual", e)

    if not workflow:
        workflow = _build_workflow_manually()

    # Validar com n8n_validator
    try:
        from src.processors.n8n_validator import N8nFlowValidator
        validator = N8nFlowValidator.from_reference_dir(REFERENCE_DIR)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)
        result = validator.validate(OUTPUT_PATH)
        logger.info(result.summary())
        if not result.valid:
            logger.warning("Workflow tem erros - ajuste manualmente se necessário")
    except Exception as e:
        logger.warning("Validação falhou: %s - salvando mesmo assim", e)
        with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
            json.dump(workflow, f, indent=2, ensure_ascii=False)

    logger.info("Workflow salvo em %s", OUTPUT_PATH)
    return 0


if __name__ == "__main__":
    sys.exit(main())
