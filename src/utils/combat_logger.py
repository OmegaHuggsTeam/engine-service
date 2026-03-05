"""
Combat Logger - Sistema de Logs Narrativos para Selum of Persistence

Este módulo fornece um sistema de logging com narrativa de RPG para o Paladino Selum.
Todos os logs seguem um formato consistente que conta a história das batalhas contra o DOM.
"""


class CombatLogger:
    """
    Sistema de logs com narrativa de RPG para o Paladino Selum.
    
    Responsável por formatar e exibir logs de todas as ações do Paladino,
    transformando operações técnicas em narrativas épicas de combate.
    """
    
    @staticmethod
    def turn_action(turn: int, action: str, target: str) -> None:
        """
        Registra o início de uma ação de combate.
        
        Args:
            turn: Número do turno atual
            action: Nome da ação sendo executada (ex: "Empunhando 'strike'")
            target: Alvo da ação (seletor, texto, etc.)
        
        Example:
            >>> CombatLogger.turn_action(1, "Empunhando 'strike'", ".settings-button")
            [Turno 1 - Selum of Persistence]: Empunhando 'strike' contra '.settings-button'...
        """
        print(f"[Turno {turn} - Selum of Persistence]: {action} contra '{target}'...")
    
    @staticmethod
    def result(success: bool, message: str) -> None:
        """
        Registra o resultado de uma ação de combate.
        
        Args:
            success: Se a ação foi bem-sucedida
            message: Mensagem descritiva do resultado
        
        Example:
            >>> CombatLogger.result(True, "O caminho está livre.")
            [Resultado]: ✓ Golpe certeiro! O caminho está livre.
        """
        status = "✓ Golpe certeiro!" if success else "✗ Bloqueado!"
        print(f"[Resultado]: {status} {message}")
    
    @staticmethod
    def progress(message: str) -> None:
        """
        Registra progresso durante uma ação prolongada.
        
        Args:
            message: Mensagem de progresso
        
        Example:
            >>> CombatLogger.progress("Ainda em vigília... (5s de 30s)")
            [Progresso]: Ainda em vigília... (5s de 30s)
        """
        print(f"[Progresso]: {message}")
    
    @staticmethod
    def wisdom(message: str) -> None:
        """
        Registra sabedoria ancestral recebida do AgentFactory.
        
        Args:
            message: Mensagem de sabedoria/solução sugerida
        
        Example:
            >>> CombatLogger.wisdom("Use JS click para elementos interceptados")
            [Sabedoria Ancestral]: Use JS click para elementos interceptados
        """
        print(f"[Sabedoria Ancestral]: {message}")
    
    @staticmethod
    def warning(message: str) -> None:
        """
        Registra um aviso durante o combate.
        
        Args:
            message: Mensagem de aviso
        
        Example:
            >>> CombatLogger.warning("Elemento não encontrado, tentando próximo caminho...")
            [Aviso]: Elemento não encontrado, tentando próximo caminho...
        """
        print(f"[Aviso]: {message}")
    
    @staticmethod
    def error(message: str) -> None:
        """
        Registra um erro crítico durante o combate.
        
        Args:
            message: Mensagem de erro
        
        Example:
            >>> CombatLogger.error("Todas as estratégias falharam!")
            [Erro Crítico]: Todas as estratégias falharam!
        """
        print(f"[Erro Crítico]: {message}")
