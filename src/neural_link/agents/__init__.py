"""
Neural Link Agents - Knowledge-Powered Specialists.

SpecialistAgent: agente que carrega conhecimento por categoria,
decora prompts com contexto de referência e suporta creative_synthesis.
"""

from .base_agent import BaseAgent
from .specialist_agent import SpecialistAgent

__all__ = ["BaseAgent", "SpecialistAgent"]
