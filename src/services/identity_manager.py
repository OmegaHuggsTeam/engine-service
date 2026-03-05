"""
Identity Manager - Core do modulo de orquestracao de identidade.
Processa configuracoes de provisionamento e gera fila de tarefas no Neo4j.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional

from src.services.models import (
    IdentityConfig,
    ProviderType,
    ProvisioningStep,
    ProvisioningTask,
)

logger = logging.getLogger(__name__)

# Ordenacao padrao de providers (dependencia sequencial)
PROVIDER_ORDER = [ProviderType.GOOGLE, ProviderType.GITHUB, ProviderType.GROQ]


class IdentityManager:
    """
    Orquestra provisionamento de identidade.
    Carrega config, gera task queue, persiste no Neo4j.
    """

    def __init__(self, graph_manager=None, router=None):
        """
        Args:
            graph_manager: GraphManager opcional. Se None, opera sem Neo4j.
            router: GroqRouter opcional. Se fornecido, classifica tarefas antes da execucao.
        """
        self._graph = graph_manager
        self._router = router

    def load_config(self, path: str) -> IdentityConfig:
        """Carrega e valida identity_config.json via Pydantic."""
        config_path = Path(path)
        if not config_path.exists():
            raise FileNotFoundError(f"Config nao encontrado: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return IdentityConfig(**data)

    def generate_task_queue(self, config: IdentityConfig) -> list[ProvisioningTask]:
        """
        Gera tarefas com dependencias seguindo ordering: Google -> GitHub -> Groq.
        Cada step de um provider depende do step anterior.
        Primeiro step de um provider depende do ultimo step do provider anterior.
        """
        tasks: list[ProvisioningTask] = []
        prev_provider_last_task_id: Optional[str] = None

        # Ordena providers conforme PROVIDER_ORDER
        enabled_providers = [
            pc for pc in config.providers if pc.enabled
        ]
        enabled_providers.sort(
            key=lambda pc: (
                PROVIDER_ORDER.index(pc.provider)
                if pc.provider in PROVIDER_ORDER
                else len(PROVIDER_ORDER)
            )
        )

        for provider_config in enabled_providers:
            prev_step_task_id: Optional[str] = None

            for step_idx, step_config in enumerate(provider_config.steps):
                task_id = f"{config.identity_name}_{provider_config.provider.value}_{step_idx:02d}_{step_config.step.value}"

                depends_on = []
                if prev_step_task_id:
                    depends_on.append(prev_step_task_id)
                elif prev_provider_last_task_id:
                    depends_on.append(prev_provider_last_task_id)

                input_data = {
                    "base_url": provider_config.base_url,
                    "selector": step_config.selector,
                    "value_field": step_config.value_field,
                    "timeout_ms": step_config.timeout_ms,
                    "form_fields": provider_config.form_fields,
                }

                task = ProvisioningTask(
                    id=task_id,
                    provider=provider_config.provider,
                    step=step_config.step,
                    depends_on=depends_on,
                    input_data=input_data,
                )
                task.checksum = task.compute_checksum()
                tasks.append(task)
                prev_step_task_id = task_id

            if prev_step_task_id:
                prev_provider_last_task_id = prev_step_task_id

        return tasks

    def persist_tasks(self, tasks: list[ProvisioningTask]) -> None:
        """Persiste tarefas no Neo4j via GraphManager usando UPSERT_TASK."""
        if not self._graph:
            logger.warning("GraphManager nao disponivel - tasks nao persistidas")
            return

        from src.neural_link.graph.queries import UPSERT_TASK

        for task in tasks:
            params = {
                "id": task.id,
                "description": f"Provisioning: {task.provider.value} - {task.step.value}",
                "type": task.provider.value,
                "status": task.status,
                "priority": 5,
                "input": json.dumps(task.input_data),
                "output": json.dumps({"checksum": task.checksum, "depends_on": task.depends_on}),
                "created_at": task.created_at,
            }
            self._graph.execute_write(UPSERT_TASK, params)

        logger.info(f"Persistidas {len(tasks)} tasks no Neo4j")

    def get_pending_tasks(self, provider: str = None) -> list[dict]:
        """Busca tasks pendentes no grafo, opcionalmente filtradas por provider."""
        if not self._graph:
            logger.warning("GraphManager nao disponivel")
            return []

        if provider:
            from src.neural_link.graph.queries import GET_TASK_QUEUE_BY_PROVIDER
            tasks = self._graph.execute_read(
                GET_TASK_QUEUE_BY_PROVIDER, {"provider": provider}
            )
        else:
            from src.neural_link.graph.queries import GET_PENDING_TASKS_BY_TYPE
            tasks = self._graph.execute_read(
                GET_PENDING_TASKS_BY_TYPE, {"task_type": "provisioning"}
            )

        if self._router and tasks:
            from src.middleware.groq_router import RouterRequest
            req = RouterRequest(
                task_description=f"Triage {len(tasks)} pending tasks",
                task_type="task_triage",
                context={"count": len(tasks), "provider": provider or "all"},
                source="identity_manager",
            )
            resp = self._router.route(req)
            if not resp.escalate and resp.result:
                logger.info(f"Router triaged tasks: {resp.reason}")
                for task in tasks:
                    task_data = task.get("t", task)
                    task_data["_router_triage"] = resp.result

        return tasks

    def update_task_status(self, task_id: str, status: str, output: dict = None) -> None:
        """Atualiza status de uma task no grafo."""
        if not self._graph:
            logger.warning("GraphManager nao disponivel")
            return

        from src.neural_link.graph.queries import UPDATE_TASK_STATUS
        self._graph.execute_write(
            UPDATE_TASK_STATUS,
            {
                "task_id": task_id,
                "status": status,
                "output": json.dumps(output) if output else None,
            },
        )

        if self._router:
            from src.middleware.groq_router import RouterRequest
            req = RouterRequest(
                task_description=f"Task {task_id} completed with status={status}, check follow-ups",
                task_type="follow_up_check",
                context={"task_id": task_id, "status": status, "output": output},
                source="identity_manager",
            )
            resp = self._router.route(req)
            if not resp.escalate and resp.result:
                logger.info(f"Router follow-up suggestion: {resp.reason}")

    def process_config(self, path: str) -> list[ProvisioningTask]:
        """Pipeline completo: load -> generate -> persist."""
        config = self.load_config(path)

        if self._router:
            from src.middleware.groq_router import RouterRequest
            req = RouterRequest(
                task_description=f"Process config for {config.identity_name} with {len(config.providers)} providers",
                task_type="config_processing",
                context={"providers": [p.provider.value for p in config.providers if p.enabled]},
                source="identity_manager",
            )
            resp = self._router.route(req)
            if not resp.escalate and resp.result:
                logger.info(f"Router enriched config processing: {resp.reason}")

        tasks = self.generate_task_queue(config)
        self.persist_tasks(tasks)
        logger.info(
            f"Pipeline completo: {len(tasks)} tasks para '{config.identity_name}'"
        )
        return tasks
