"""
ComposerAgent - Cria workflows n8n combinando templates do ChromaDB.

Este agente:
1. Recebe um objetivo em linguagem natural
2. Busca templates relevantes no ChromaDB (categoria: external_template)
3. Usa o HybridRAG para encontrar padrões similares
4. Compõe um JSON n8n válido combinando lógica de diferentes templates
5. Retorna o workflow pronto para importação no n8n

Comando Telegram: /create_n8n <objetivo>
"""

import json
import logging
from typing import Optional

from ..rag.hybrid_rag import HybridRAG
from .base_agent import BaseAgent

logger = logging.getLogger(__name__)


class ComposerAgent(BaseAgent):
    """
    Agente especializado em compor workflows n8n a partir de templates.
    """

    def __init__(self, rag: Optional[HybridRAG] = None):
        super().__init__(
            name="ComposerAgent",
            specialty="n8n_workflow_composition",
            description="Compõe workflows n8n combinando templates do ChromaDB",
        )
        self.rag = rag or HybridRAG.from_env()
        self._load_master_context()

    def _load_master_context(self):
        """Carrega n8n_master_context.json para best practices."""
        try:
            from pathlib import Path

            context_path = Path("data/chunks/n8n_master_context.json")

            if context_path.exists():
                with open(context_path, "r", encoding="utf-8") as f:
                    self.master_context = json.load(f)
                logger.info(f"ComposerAgent: Loaded {len(self.master_context)} context chunks")
            else:
                self.master_context = []
                logger.warning("ComposerAgent: n8n_master_context.json not found")
        except Exception as e:
            logger.error(f"ComposerAgent: Failed to load master context: {e}")
            self.master_context = []

    def compose_workflow(self, objective: str, max_templates: int = 5) -> dict:
        """
        Compõe um workflow n8n a partir de um objetivo.

        Args:
            objective: Descrição do que o workflow deve fazer
            max_templates: Número máximo de templates a considerar

        Returns:
            Dict com:
                - workflow: JSON do workflow n8n
                - templates_used: Lista de templates utilizados
                - reasoning: Explicação da composição
                - metadata: Metadados do workflow
        """
        logger.info(f"ComposerAgent: Composing workflow for '{objective}'")

        # Step 1: Buscar templates relevantes
        templates = self._search_templates(objective, top_k=max_templates)

        if not templates:
            return {
                "error": "Nenhum template relevante encontrado",
                "suggestion": "Tente reformular o objetivo ou adicione mais workflows ao ChromaDB",
            }

        # Step 2: Analisar objetivo e identificar componentes necessários
        components = self._identify_components(objective, templates)

        # Step 3: Compor workflow combinando templates
        workflow = self._build_workflow(objective, components, templates)

        # Step 4: Validar e enriquecer
        workflow = self._validate_and_enrich(workflow)

        # Step 5: Gerar explicação
        reasoning = self._generate_reasoning(objective, templates, components)

        return {
            "workflow": workflow,
            "templates_used": [
                {
                    "source": t.get("source_file", "unknown"),
                    "service": t.get("service", "unknown"),
                    "node_type": t.get("node_type", "unknown"),
                    "relevance": t.get("score", 0.0),
                }
                for t in templates
            ],
            "reasoning": reasoning,
            "metadata": {
                "objective": objective,
                "composer_version": "1.0",
                "templates_count": len(templates),
            },
        }

    def _search_templates(self, objective: str, top_k: int = 5) -> list[dict]:
        """Busca templates relevantes no ChromaDB."""
        try:
            # Buscar usando HybridRAG
            results = self.rag.query(
                query_text=objective,
                top_k=top_k,
                context={"category": "external_template"},
            )

            # Filtrar apenas external_template
            templates = [r for r in results if r.get("category") == "external_template"]

            logger.info(f"ComposerAgent: Found {len(templates)} relevant templates")
            return templates

        except Exception as e:
            logger.error(f"ComposerAgent: Template search failed: {e}")
            return []

    def _identify_components(self, objective: str, templates: list[dict]) -> dict:
        """
        Identifica componentes necessários baseado no objetivo e templates.

        Returns:
            Dict com:
                - trigger: Tipo de trigger necessário
                - processors: Lista de processadores
                - output: Tipo de output
                - credentials: Credenciais necessárias
        """
        components = {
            "trigger": None,
            "processors": [],
            "output": None,
            "credentials": set(),
        }

        # Analisar objetivo para identificar trigger
        objective_lower = objective.lower()

        if any(kw in objective_lower for kw in ["webhook", "api", "http"]):
            components["trigger"] = "Webhook"
        elif any(kw in objective_lower for kw in ["schedule", "cron", "diário", "horário"]):
            components["trigger"] = "Schedule"
        elif any(kw in objective_lower for kw in ["telegram", "mensagem"]):
            components["trigger"] = "Telegram"
        elif any(kw in objective_lower for kw in ["email", "mail"]):
            components["trigger"] = "Email"
        else:
            # Default: usar trigger mais comum dos templates
            triggers = [
                t.get("node_type", "")
                for t in templates
                if "trigger" in t.get("node_type", "").lower()
            ]
            components["trigger"] = triggers[0] if triggers else "Webhook"

        # Identificar processadores dos templates
        for template in templates:
            node_type = template.get("node_type", "")
            service = template.get("service", "")

            if "trigger" not in node_type.lower():
                components["processors"].append(
                    {
                        "node_type": node_type,
                        "service": service,
                        "parameters": template.get("parameters", {}),
                    }
                )

            # Coletar credenciais
            creds = template.get("credential_types", [])
            components["credentials"].update(creds)

        # Identificar output baseado no objetivo
        if any(kw in objective_lower for kw in ["telegram", "enviar mensagem"]):
            components["output"] = "Telegram"
        elif any(kw in objective_lower for kw in ["email", "enviar email"]):
            components["output"] = "Email"
        elif any(kw in objective_lower for kw in ["sheets", "planilha"]):
            components["output"] = "GoogleSheets"
        elif any(kw in objective_lower for kw in ["database", "banco", "supabase"]):
            components["output"] = "Database"
        else:
            # Default: usar output mais comum dos templates
            components["output"] = templates[0].get("service", "HTTP") if templates else "HTTP"

        components["credentials"] = list(components["credentials"])
        return components

    def _build_workflow(self, objective: str, components: dict, templates: list[dict]) -> dict:
        """
        Constrói o JSON do workflow n8n.

        Estrutura básica:
        {
            "name": "...",
            "nodes": [...],
            "connections": {...},
            "settings": {...}
        }
        """
        workflow = {
            "name": self._generate_workflow_name(objective),
            "nodes": [],
            "connections": {},
            "settings": {"executionOrder": "v1"},
            "staticData": None,
            "tags": [],
            "triggerCount": 0,
            "updatedAt": None,
            "versionId": None,
        }

        node_id = 0
        prev_node_name = None

        # Add trigger node
        trigger_node = self._create_trigger_node(components["trigger"], node_id)
        workflow["nodes"].append(trigger_node)
        prev_node_name = trigger_node["name"]
        node_id += 1

        # Add processor nodes
        for processor in components["processors"][:3]:  # Limit to 3 processors
            proc_node = self._create_processor_node(processor, node_id)
            workflow["nodes"].append(proc_node)

            # Connect to previous node
            if prev_node_name:
                if prev_node_name not in workflow["connections"]:
                    workflow["connections"][prev_node_name] = {
                        "main": [[{"node": proc_node["name"], "type": "main", "index": 0}]]
                    }

            prev_node_name = proc_node["name"]
            node_id += 1

        # Add output node
        output_node = self._create_output_node(components["output"], node_id)
        workflow["nodes"].append(output_node)

        # Connect to previous node
        if prev_node_name:
            if prev_node_name not in workflow["connections"]:
                workflow["connections"][prev_node_name] = {
                    "main": [[{"node": output_node["name"], "type": "main", "index": 0}]]
                }

        return workflow

    def _create_trigger_node(self, trigger_type: str, node_id: int) -> dict:
        """Cria um nó de trigger."""
        trigger_map = {
            "Webhook": "n8n-nodes-base.webhook",
            "Schedule": "n8n-nodes-base.scheduleTrigger",
            "Telegram": "n8n-nodes-base.telegramTrigger",
            "Email": "n8n-nodes-base.emailReadImap",
        }

        node_type = trigger_map.get(trigger_type, "n8n-nodes-base.webhook")

        return {
            "parameters": {},
            "name": f"{trigger_type} Trigger",
            "type": node_type,
            "typeVersion": 1,
            "position": [250, 300],
            "id": str(node_id),
            "webhookId": None,
        }

    def _create_processor_node(self, processor: dict, node_id: int) -> dict:
        """Cria um nó processador."""
        return {
            "parameters": processor.get("parameters", {}),
            "name": processor.get("service", f"Process {node_id}"),
            "type": processor.get("node_type", "n8n-nodes-base.function"),
            "typeVersion": 1,
            "position": [450 + (node_id * 200), 300],
            "id": str(node_id),
        }

    def _create_output_node(self, output_type: str, node_id: int) -> dict:
        """Cria um nó de output."""
        output_map = {
            "Telegram": "n8n-nodes-base.telegram",
            "Email": "n8n-nodes-base.emailSend",
            "GoogleSheets": "n8n-nodes-base.googleSheets",
            "Database": "n8n-nodes-base.postgres",
            "HTTP": "n8n-nodes-base.httpRequest",
        }

        node_type = output_map.get(output_type, "n8n-nodes-base.httpRequest")

        return {
            "parameters": {},
            "name": f"{output_type} Output",
            "type": node_type,
            "typeVersion": 1,
            "position": [850, 300],
            "id": str(node_id),
        }

    def _generate_workflow_name(self, objective: str) -> str:
        """Gera um nome para o workflow baseado no objetivo."""
        # Limitar a 50 caracteres e remover caracteres especiais
        name = objective[:50].strip()
        name = "".join(c for c in name if c.isalnum() or c in " -_")
        return name or "Generated Workflow"

    def _validate_and_enrich(self, workflow: dict) -> dict:
        """Valida e enriquece o workflow com metadados."""
        # Adicionar tags baseadas nos nodes
        services = {node.get("type", "").split(".")[-1] for node in workflow["nodes"]}
        workflow["tags"] = [{"name": svc} for svc in services if svc]

        # Contar triggers
        workflow["triggerCount"] = sum(
            1 for node in workflow["nodes"] if "trigger" in node.get("type", "").lower()
        )

        return workflow

    def _generate_reasoning(self, objective: str, templates: list[dict], components: dict) -> str:
        """Gera explicação da composição."""
        lines = [
            f"Workflow composto para: {objective}",
            "",
            "Componentes selecionados:",
            f"- Trigger: {components['trigger']}",
            f"- Processadores: {len(components['processors'])}",
            f"- Output: {components['output']}",
            "",
            "Templates utilizados:",
        ]

        for i, t in enumerate(templates, 1):
            source = t.get("source_file", "unknown").replace("github/zie619.github.io/", "")
            service = t.get("service", "unknown")
            score = t.get("score", 0.0)
            lines.append(f"{i}. {service} (relevância: {score:.2f}) - {source}")

        if components["credentials"]:
            lines.append("")
            lines.append("Credenciais necessárias:")
            for cred in components["credentials"]:
                lines.append(f"- {cred}")

        return "\n".join(lines)

    def execute(self, task: dict) -> dict:
        """
        Executa tarefa de composição de workflow.

        Args:
            task: Dict com 'objective' (obrigatório) e 'max_templates' (opcional)

        Returns:
            Resultado da composição
        """
        objective = task.get("objective")
        if not objective:
            return {"error": "Campo 'objective' é obrigatório"}

        max_templates = task.get("max_templates", 5)
        return self.compose_workflow(objective, max_templates=max_templates)
