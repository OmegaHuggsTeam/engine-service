"""
BaseAgent - Interface base para agentes do Neural Link.

Define o contrato mínimo: execute() e capabilities.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseAgent(ABC):
    """
    Classe base abstrata para agentes especializados.
    """

    @property
    def capabilities(self) -> set[str]:
        """Capacidades do agente (ex: workflow, n8n_templates, automation)."""
        return set()

    @abstractmethod
    def execute(self, task: str, **kwargs: Any) -> Any:
        """
        Executa uma tarefa.

        Args:
            task: Descrição ou comando da tarefa.
            **kwargs: Argumentos adicionais (query, chunk_a, chunk_b, etc.).

        Returns:
            Resultado da execução (str, dict, etc.).
        """
        ...
