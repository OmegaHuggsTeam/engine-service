"""
Triage Middleware — Classifica queries por dominio antes do pipeline.

Uso no gateway:
    from src.middleware.triage_middleware import TriageMiddleware

    triage_mw = TriageMiddleware()
    result = triage_mw.classify(query)
    if result.routed:
        context["domain"] = result.domain
    # segue pro pipeline com dominio informado
"""

import logging

from src.triage.domain_router import DomainRouter, TriageResult

log = logging.getLogger(__name__)


class TriageMiddleware:
    """Middleware que classifica queries por dominio."""

    def __init__(self, rules_path: str = None):
        self.router = DomainRouter(rules_path=rules_path)
        log.info("[TRIAGE MW] Triage middleware inicializado")

    def classify(self, query: str) -> TriageResult:
        """Classifica a query e retorna o resultado."""
        return self.router.classify(query)

    def get_domains(self) -> list[str]:
        """Lista dominios disponiveis."""
        return self.router.get_domains()

    def reload(self, rules_path: str = None) -> None:
        """Recarrega regras sem reiniciar."""
        self.router.reload_rules(rules_path)
