"""
TaskExecutor - Invoca agentes e gerencia estado de execucao.

Wraps chamadas aos modulos existentes:
- Agentes de dominio: ask_agent() ou modulo direto
- Operadores: process_command()
- Repair: AgentFactory.handle_exception()
- LLM generico: chat_completion()
"""

import logging
import time
import uuid
from datetime import datetime
from typing import Optional

from .models import Task, TaskResult, TaskStatus, TaskType
from .agent_selector import AGENT_REGISTRY

logger = logging.getLogger(__name__)


class TaskExecutor:
    """Executa tasks delegando para os agentes/operadores corretos."""

    def __init__(self, graph_manager=None, rag_context: str = ""):
        self._graph = graph_manager
        self._rag_context = rag_context

    def execute(self, task: Task, agent_id: str) -> TaskResult:
        """
        Executa uma task usando o agente selecionado.

        Args:
            task: A task para executar
            agent_id: ID do agente selecionado

        Returns:
            TaskResult com output ou error
        """
        start = time.time()
        task.status = TaskStatus.IN_PROGRESS
        task.assigned_agent = agent_id

        try:
            output = self._invoke_agent(task, agent_id)

            elapsed = (time.time() - start) * 1000
            task.status = TaskStatus.COMPLETED

            result = TaskResult(
                task_id=task.id,
                success=True,
                output=output,
                agent_used=agent_id,
                execution_time_ms=elapsed,
            )

            # Registra no grafo se disponivel
            self._record_task_in_graph(task, result)

            return result

        except Exception as e:
            elapsed = (time.time() - start) * 1000
            task.status = TaskStatus.FAILED
            logger.error(f"Task {task.id} failed with agent {agent_id}: {e}")

            result = TaskResult(
                task_id=task.id,
                success=False,
                error=str(e),
                agent_used=agent_id,
                execution_time_ms=elapsed,
            )

            self._record_task_in_graph(task, result)

            return result

    def _invoke_agent(self, task: Task, agent_id: str) -> str:
        """Invoca o agente correto baseado no tipo."""
        agent_info = AGENT_REGISTRY.get(agent_id)

        if not agent_info:
            # Fallback: LLM generico
            return self._invoke_llm(task)

        agent_type = agent_info["type"]

        if agent_type == "domain" and agent_info.get("agent_class") and agent_info.get("module_path"):
            return self._invoke_domain_agent_class(task, agent_id, agent_info)
        if agent_type == "domain":
            return self._invoke_domain_agent(task, agent_id, agent_info)
        elif agent_type == "operator":
            return self._invoke_operator(task, agent_id, agent_info)
        elif agent_type == "specialist":
            return self._invoke_specialist(task, agent_id, agent_info)
        else:
            return self._invoke_llm(task)

    def _invoke_domain_agent_class(self, task: Task, agent_id: str, agent_info: dict) -> str:
        """Invoca Domain Agent via agent_class/module_path (Marketing, Social, AI Engineer)."""
        try:
            import importlib
            module_path = agent_info["module_path"]
            class_name = agent_info.get("agent_class", "")
            mod = importlib.import_module(module_path)
            agent_class = getattr(mod, class_name)
            agent = agent_class()
            result = agent.execute(task.description, **task.input_data)
            return str(result)
        except Exception as e:
            logger.warning("Domain agent %s failed: %s, falling back to domain agent", agent_id, e)
            return self._invoke_domain_agent(task, agent_id, agent_info)

    def _invoke_domain_agent(self, task: Task, agent_id: str, agent_info: dict) -> str:
        """Invoca agente de dominio via LLM com system prompt especializado."""
        from src.utils.llm_client import chat_completion

        agent_name = agent_info["name"]
        capabilities = ", ".join(agent_info["capabilities"])

        system_prompt = (
            f"You are the {agent_name}, specialized in: {capabilities}. "
            f"Answer the following task accurately and concisely.\n\n"
            f"Context from knowledge base:\n{self._rag_context[:1000] if self._rag_context else '(none)'}"
        )

        response = chat_completion([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": task.description},
        ])

        return response

    def _invoke_operator(self, task: Task, agent_id: str, agent_info: dict) -> str:
        """Invoca operador LLM."""
        # Operadores usam chat_completion diretamente com suas especialidades
        from src.utils.llm_client import chat_completion

        capabilities = ", ".join(agent_info["capabilities"])

        response = chat_completion([
            {
                "role": "system",
                "content": (
                    f"You are {agent_info['name']} with capabilities: {capabilities}. "
                    f"Execute this task.\n\nContext:\n{self._rag_context[:800] if self._rag_context else '(none)'}"
                ),
            },
            {"role": "user", "content": task.description},
        ])

        return response

    def _invoke_specialist(self, task: Task, agent_id: str, agent_info: dict) -> str:
        """Invoca agente especialista."""
        if agent_id == "divine_inspiration" and task.type == TaskType.REPAIR:
            try:
                from src.agents.agent_factory import AgentFactory

                error_data = task.input_data
                exception = Exception(error_data.get("error_message", task.description))
                traceback_str = error_data.get("traceback", str(exception))

                result = AgentFactory.handle_exception(exception, traceback_str)
                return str(result.get("suggested_solution") or result)
            except Exception as e:
                logger.warning(f"Divine Inspiration failed: {e}, falling back to LLM")

        if agent_id == "specialist_agent":
            try:
                from src.neural_link.agents.specialist_agent import SpecialistAgent
                agent = SpecialistAgent(capabilities=agent_info.get("capabilities", set()))
                chunk_type = task.input_data.get("chunk_type") or task.required_capabilities
                if chunk_type:
                    ct = chunk_type if isinstance(chunk_type, str) else next(iter(chunk_type), None)
                    if ct:
                        agent.load_knowledge(ct)
                result = agent.execute(task.description, **task.input_data)
                return str(result)
            except Exception as e:
                logger.warning(f"SpecialistAgent failed: {e}, falling back to LLM")

        # Fallback
        return self._invoke_llm(task)

    def _invoke_llm(self, task: Task) -> str:
        """Fallback: invoca LLM generico para qualquer task."""
        from src.utils.llm_client import chat_completion

        response = chat_completion([
            {
                "role": "system",
                "content": (
                    "You are a helpful AI assistant. Complete the following task. "
                    f"Context:\n{self._rag_context[:800] if self._rag_context else '(none)'}"
                ),
            },
            {"role": "user", "content": task.description},
        ])

        return response

    def _record_task_in_graph(self, task: Task, result: TaskResult):
        """Registra task e resultado no grafo Neo4j."""
        if not self._graph:
            return

        try:
            from ..graph import queries

            self._graph.execute_write(queries.UPSERT_TASK, {
                "id": task.id,
                "description": task.description[:500],
                "type": task.type.value,
                "status": task.status.value,
                "priority": task.priority,
                "input": str(task.input_data)[:500] if task.input_data else "",
                "output": str(result.output)[:500] if result.output else "",
                "created_at": task.created_at,
            })

            if task.assigned_agent:
                self._graph.execute_write(queries.CREATE_TASK_ASSIGNED, {
                    "task_id": task.id,
                    "agent_id": task.assigned_agent,
                })

            # CRM: if task references a lead, record an Interaction node
            lead_id = task.input_data.get("lead_id") if task.input_data else None
            if lead_id:
                try:
                    interaction_id = f"interaction_{task.id}"
                    now = datetime.now().isoformat()
                    self._graph.execute_write(queries.UPSERT_INTERACTION, {
                        "id": interaction_id,
                        "lead_id": lead_id,
                        "agent_id": task.assigned_agent,
                        "channel": "agent",
                        "action": task.type.value,
                        "detail": task.description[:200],
                        "timestamp": now,
                    })
                    self._graph.execute_write(queries.CREATE_INTERACTION_FOR_LEAD, {
                        "interaction_id": interaction_id,
                        "lead_id": lead_id,
                    })
                    if task.assigned_agent:
                        self._graph.execute_write(queries.CREATE_INTERACTION_BY_AGENT, {
                            "interaction_id": interaction_id,
                            "agent_id": task.assigned_agent,
                        })
                    self._graph.execute_write(queries.INCREMENT_LEAD_INTERACTION_COUNT, {
                        "lead_id": lead_id,
                        "updated_at": now,
                    })
                except Exception as crm_err:
                    logger.debug(f"CRM interaction recording skipped: {crm_err}")

        except Exception as e:
            logger.debug(f"Failed to record task in graph: {e}")
