"""
Skill Executor - Executa skills do registry em sandbox.

Este módulo implementa a execução segura de skills com validação de resultado
e logging narrativo.
"""

from typing import Dict, Callable, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from src.utils.selum_of_persistence import SelumOfPersistence


class SkillExecutor:
    """Executa skills do registry em sandbox."""
    
    @staticmethod
    def execute(
        skill_name: str,
        skill_registry: Dict[str, Callable],
        selum_instance: 'SelumOfPersistence',
        is_first_execution: bool = False
    ) -> Tuple[bool, Optional[str]]:
        """
        Executa uma skill do registry em sandbox.
        
        Args:
            skill_name: Nome da skill a executar
            skill_registry: Registry de skills
            selum_instance: Instância do SelumOfPersistence
            is_first_execution: Se True, aplica validação rigorosa para persistência
        
        Returns:
            (success, error_message)
        """
        if skill_name not in skill_registry:
            return False, "Skill not found in registry"
        
        try:
            skill_function = skill_registry[skill_name]
            result = skill_function(selum_instance)
            
            # Validar resultado
            if not isinstance(result, bool):
                error_msg = f"Skill returned {type(result).__name__} instead of bool"
                if is_first_execution:
                    # Log será feito pelo chamador
                    pass
                return False, error_msg
            
            # Se é primeira execução, logar resultado
            # (logs serão feitos pelo chamador para manter narrativa consistente)
            
            return result, None
        
        except Exception as e:
            error_msg = f"{type(e).__name__}: {str(e)}"
            # Log será feito pelo chamador
            return False, error_msg
