"""
Hot-Patcher - Sistema de hot-patching para executar código gerado dinamicamente.

Este módulo implementa o sistema que compila e registra skills dinamicamente
sem reiniciar a aplicação.
"""

import time
import typing
from typing import Callable, Dict

from selenium.webdriver.common.by import By


class HotPatcher:
    """Sistema de hot-patching para executar código gerado dinamicamente."""

    @staticmethod
    def patch_skill(skill_name: str, skill_code: str, skill_registry: Dict[str, Callable]) -> bool:
        """
        Compila e registra uma skill no registry.

        Args:
            skill_name: Nome da skill
            skill_code: Código Python da skill
            skill_registry: Registry onde registrar a skill

        Returns:
            True se bem-sucedido, False caso contrário
        """
        try:
            # Importar SelumOfPersistence dinamicamente para evitar circular import
            from src.utils.selum_of_persistence import SelumOfPersistence

            # Criar namespace isolado
            namespace = {
                "SelumOfPersistence": SelumOfPersistence,
                "By": By,
                "time": time,
                "typing": typing,
            }

            # Compilar código
            exec(skill_code, namespace)

            # Extrair função do namespace
            if skill_name not in namespace:
                raise ValueError(f"Function {skill_name} not found in compiled code")

            skill_function = namespace[skill_name]

            # Registrar no registry
            skill_registry[skill_name] = skill_function

            return True

        except Exception:
            # Log será feito pelo chamador
            return False
