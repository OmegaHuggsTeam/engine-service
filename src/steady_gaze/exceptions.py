"""
Exceções customizadas para o sistema Steady Gaze Recon.

Define hierarquia de exceções para tratamento de erros específicos.
"""


class SteadyGazeError(Exception):
    """Erro base do Steady Gaze."""
    pass


class CDPConnectionError(SteadyGazeError):
    """Erro de conexão CDP."""
    pass


class AnalysisTimeoutError(SteadyGazeError):
    """Timeout durante análise."""
    pass


class DimensionAnalysisError(SteadyGazeError):
    """Erro em dimensão específica."""
    
    def __init__(self, dimension: str, original_error: Exception):
        """
        Inicializa erro de dimensão.
        
        Args:
            dimension: Nome da dimensão que falhou
            original_error: Exceção original
        """
        self.dimension = dimension
        self.original_error = original_error
        super().__init__(f"Erro ao analisar {dimension}: {original_error}")


class PageNotLoadedError(SteadyGazeError):
    """Página não carregada."""
    pass
