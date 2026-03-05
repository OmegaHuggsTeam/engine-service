"""
Error Detection System - Detecta e rastreia erros estruturais.

Este módulo implementa o sistema de detecção de erros estruturais que
identifica quando o Selum deve invocar a Inspiração Divina.
"""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Set
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    ElementNotInteractableException,
    StaleElementReferenceException
)


@dataclass
class ErrorContext:
    """Contexto completo de um erro estrutural."""
    
    error_type: str              # Tipo da exceção
    selector: str                # Seletor que falhou
    by_type: str                # Tipo de seletor (CSS, XPATH, etc.)
    html_context: str           # HTML da área problemática
    attempt_count: int          # Número de tentativas
    timestamp: float            # Timestamp da última tentativa
    maneuver_history: List[str] = field(default_factory=list)  # Histórico de manobras
    
    def to_description(self) -> str:
        """Converte para descrição textual para Groq."""
        return f"{self.error_type} on {self.selector} after {self.attempt_count} attempts"


class ErrorDetector:
    """Detecta e rastreia erros estruturais."""
    
    def __init__(self, driver=None):
        """
        Inicializa o detector de erros.
        
        Args:
            driver: WebDriver do Selenium (opcional, usado para extrair HTML)
        """
        self.driver = driver
        self.error_contexts: Dict[str, ErrorContext] = {}
        self.structural_errors: Set[type] = {
            NoSuchElementException,
            TimeoutException,
            ElementNotInteractableException,
            StaleElementReferenceException
        }
    
    def is_structural_error(self, exception: Exception) -> bool:
        """
        Verifica se é um erro estrutural.
        
        Args:
            exception: Exceção a verificar
            
        Returns:
            True se for erro estrutural, False caso contrário
        """
        return type(exception) in self.structural_errors
    
    def track_error(
        self, 
        exception: Exception, 
        selector: str, 
        by_type: str,
        maneuver_name: str = None
    ) -> ErrorContext:
        """
        Rastreia um erro e retorna o contexto atualizado.
        
        Args:
            exception: Exceção que ocorreu
            selector: Seletor que falhou
            by_type: Tipo de seletor (CSS_SELECTOR, XPATH, etc.)
            maneuver_name: Nome da manobra que falhou (opcional)
            
        Returns:
            ErrorContext atualizado
        """
        context_key = f"{type(exception).__name__}:{selector}"
        
        if context_key not in self.error_contexts:
            self.error_contexts[context_key] = ErrorContext(
                error_type=type(exception).__name__,
                selector=selector,
                by_type=by_type,
                html_context=self._extract_html_context(selector),
                attempt_count=1,
                timestamp=time.time(),
                maneuver_history=[maneuver_name] if maneuver_name else []
            )
        else:
            ctx = self.error_contexts[context_key]
            ctx.attempt_count += 1
            ctx.timestamp = time.time()
            if maneuver_name and maneuver_name not in ctx.maneuver_history:
                ctx.maneuver_history.append(maneuver_name)
        
        return self.error_contexts[context_key]
    
    def should_invoke_divine_inspiration(self, context: ErrorContext) -> bool:
        """
        Verifica se deve invocar Divine Inspiration.
        
        Args:
            context: Contexto do erro
            
        Returns:
            True se deve invocar, False caso contrário
        """
        return context.attempt_count >= 3
    
    def _extract_html_context(self, selector: str) -> str:
        """
        Extrai HTML da área problemática.
        
        Args:
            selector: Seletor para extrair contexto
            
        Returns:
            HTML da área (limitado a 5000 chars)
        """
        if not self.driver:
            return ""
        
        try:
            # Tentar pegar HTML do body
            body_html = self.driver.find_element("tag name", "body").get_attribute('outerHTML')
            
            # Limitar a 5000 caracteres
            if len(body_html) > 5000:
                return body_html[:5000]
            
            return body_html
        except Exception:
            # Se falhar, retornar string vazia
            return ""
    
    def reset_context(self, selector: str, error_type: str = None):
        """
        Reseta o contexto de erro para um seletor específico.
        
        Args:
            selector: Seletor para resetar
            error_type: Tipo de erro específico (opcional)
        """
        if error_type:
            context_key = f"{error_type}:{selector}"
            if context_key in self.error_contexts:
                del self.error_contexts[context_key]
        else:
            # Resetar todos os contextos para este seletor
            keys_to_delete = [
                key for key in self.error_contexts.keys() 
                if key.endswith(f":{selector}")
            ]
            for key in keys_to_delete:
                del self.error_contexts[key]
