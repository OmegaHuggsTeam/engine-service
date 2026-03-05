"""
The Alchemist's Filter - Validação robusta com compile() e feedback iterativo.

Este módulo implementa o sistema de validação de sintaxe que usa compile()
para detectar erros antes da execução, com sistema de recuperação iterativa.
"""

from typing import Optional, Tuple
from .error_detection import ErrorContext


class AlchemistsFilter:
    """Sistema de validação robusta com compile() e feedback iterativo."""
    
    MAX_RECOVERY_ATTEMPTS = 2
    
    @staticmethod
    def validate_syntax(code: str) -> Tuple[bool, Optional[str]]:
        """
        Valida sintaxe do código usando compile().
        
        Args:
            code: Código Python a validar
            
        Returns:
            (is_valid, error_message)
        """
        try:
            compile(code, '<divine_inspiration>', 'exec')
            return True, None
        except SyntaxError as e:
            error_msg = f"SyntaxError at line {e.lineno}: {e.msg}"
            # Log será feito pelo chamador
            return False, error_msg
    
    @staticmethod
    def build_recovery_prompt(
        original_context: ErrorContext,
        failed_code: str,
        error_message: str,
        error_type: str,  # "syntax" ou "execution"
        attempt_number: int
    ) -> str:
        """
        Constrói prompt de recuperação com feedback do erro.
        
        Args:
            original_context: Contexto do erro original
            failed_code: Código que falhou
            error_message: Mensagem de erro
            error_type: Tipo de erro ("syntax" ou "execution")
            attempt_number: Número da tentativa atual
            
        Returns:
            Prompt formatado para Groq
        """
        error_context = {
            "syntax": f"O código gerado tem um erro de sintaxe:\n```\n{error_message}\n```\n",
            "execution": f"O código executou mas falhou com erro:\n```\n{error_message}\n```\n"
        }
        
        return f"""
The previous code I generated failed. Here's what happened:

**Original Problem:**
- Error Type: {original_context.error_type}
- Selector: {original_context.selector}
- HTML Context: {original_context.html_context[:2000]}

**Failed Code:**
```python
{failed_code}
```

**Error:**
{error_context[error_type]}

**Recovery Attempt {attempt_number}/{AlchemistsFilter.MAX_RECOVERY_ATTEMPTS}:**
Please generate a DIFFERENT approach using alternative Selum commands. 

**Available Selum Commands:**
- selum.strike(selector, by=By.CSS_SELECTOR, strategy='smart') - Click with fallback
- selum.scout(possibilities_list) - Find first matching element from multiple options
- selum.steady_gaze(selector, by=By.CSS_SELECTOR) - Scroll to element
- selum.vigilance(selector, timeout=20, by=By.CSS_SELECTOR) - Wait for element
- selum.cleansing_aura() - Remove overlays and modals

**Requirements:**
1. Function signature: `def skill_<descriptive_name>(selum: SelumOfPersistence) -> bool:`
2. Use ONLY Selum commands (no direct Selenium calls)
3. Return True if successful, False otherwise
4. Include try-except for error handling
5. Fix the error from the previous attempt
6. Try a different strategy if possible

Generate the corrected function now:
"""
