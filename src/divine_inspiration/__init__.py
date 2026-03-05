"""
Divine Inspiration - Sistema de auto-evolução para SelumOfPersistence.

Este módulo implementa um sistema que permite ao Selum aprender automaticamente
novas habilidades quando encontra obstáculos repetitivos.
"""

from .error_detection import ErrorContext, ErrorDetector
from .alchemists_filter import AlchemistsFilter
from .code_validator import CodeValidator
from .divine_inspiration_engine import DivineInspirationEngine
from .hot_patcher import HotPatcher
from .skill_executor import SkillExecutor
from .grimoire_manager import GrimoireManager

__version__ = "1.0.0"

__all__ = [
    'ErrorContext',
    'ErrorDetector',
    'AlchemistsFilter',
    'CodeValidator',
    'DivineInspirationEngine',
    'HotPatcher',
    'SkillExecutor',
    'GrimoireManager',
]
