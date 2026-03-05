"""
RAG (Retrieval-Augmented Generation) System for Paladin Grimoire.

Este módulo implementa o sistema de busca e indexação de documentação
estruturada em markdown para o Selum of Persistence.
"""

from .rag_query_system import RAGQuerySystem, RAGResult, RAGIndex, Document, Section
from .abstraction_vow_validator import AbstractionVowValidator, ValidationResult, Violation

__all__ = [
    'RAGQuerySystem',
    'RAGResult',
    'RAGIndex',
    'Document',
    'Section',
    'AbstractionVowValidator',
    'ValidationResult',
    'Violation'
]
