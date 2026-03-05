"""
UseCase Registry - Interface de consulta para :UseCase nodes no Neo4j.

Fornece queries estruturadas para roadmap, cobertura de agentes,
gaps de skills e exportacao em Markdown.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class UseCaseRegistry:
    """Query interface para UseCase nodes no Neo4j."""

    def __init__(self, graph_manager=None):
        self._graph = graph_manager

    def _ensure_graph(self):
        """Lazy init do GraphManager."""
        if self._graph is None:
            from src.neural_link.graph.manager import GraphManager
            self._graph = GraphManager.from_env()

    def get_by_domain(self, domain: str) -> list[dict]:
        """Retorna use cases por dominio."""
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.GET_USECASES_BY_DOMAIN,
                {"domain": domain},
            )
        except Exception as e:
            logger.warning("Failed to get usecases by domain: %s", e)
            return []

    def get_by_status(self, status: str) -> list[dict]:
        """Retorna use cases por status."""
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.GET_USECASES_BY_STATUS,
                {"status": status},
            )
        except Exception as e:
            logger.warning("Failed to get usecases by status: %s", e)
            return []

    def get_by_id(self, usecase_id: str) -> Optional[dict]:
        """Retorna use case com contexto completo."""
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            results = self._graph.execute_read(
                queries.GET_USECASE_BY_ID,
                {"usecase_id": usecase_id},
            )
            return results[0] if results else None
        except Exception as e:
            logger.warning("Failed to get usecase %s: %s", usecase_id, e)
            return None

    def get_roadmap(self) -> list[dict]:
        """
        Retorna todos use cases organizados por priority e dependencia.
        Formato otimizado para visualizacao e exportacao.
        """
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.GET_USECASE_ROADMAP,
                {},
            )
        except Exception as e:
            logger.warning("Failed to get roadmap: %s", e)
            return []

    def get_agent_coverage(self) -> list[dict]:
        """
        Matriz agente x use cases.
        Retorna para cada agente quantos use cases ele cobre.
        """
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.GET_USECASE_COVERAGE,
                {},
            )
        except Exception as e:
            logger.warning("Failed to get coverage: %s", e)
            return []

    def get_skill_gaps(self) -> list[dict]:
        """
        Retorna use cases cujas skills nao possuem agente owner.
        Indica onde precisamos criar ou treinar agentes.
        """
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.GET_USECASE_SKILL_GAPS,
                {},
            )
        except Exception as e:
            logger.warning("Failed to get skill gaps: %s", e)
            return []

    def search(self, query: str, limit: int = 10) -> list[dict]:
        """Busca fulltext em use cases."""
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.FULLTEXT_SEARCH_USECASES,
                {"query": query, "limit": limit},
            )
        except Exception as e:
            logger.warning("Failed to search usecases: %s", e)
            return []

    def get_all(self, limit: int = 100) -> list[dict]:
        """Retorna todos os use cases."""
        try:
            self._ensure_graph()
            from src.neural_link.graph import queries
            return self._graph.execute_read(
                queries.GET_ALL_USECASES,
                {"limit": limit},
            )
        except Exception as e:
            logger.warning("Failed to get all usecases: %s", e)
            return []

    def export_roadmap_md(self, output_path: Optional[str | Path] = None) -> str:
        """
        Exporta roadmap como Markdown formatado.

        Returns:
            Conteudo Markdown do roadmap.
        """
        roadmap = self.get_roadmap()
        coverage = self.get_agent_coverage()
        gaps = self.get_skill_gaps()

        lines = [
            "# ROADMAP AI-First: CRM UserIn/SendSpeed",
            "",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "## Use Cases por Dominio",
            "",
        ]

        # Group by domain
        domains: dict[str, list[dict]] = {}
        for uc in roadmap:
            d = uc.get("domain", "general")
            domains.setdefault(d, []).append(uc)

        for domain, usecases in sorted(domains.items()):
            lines.append(f"### {domain.title()}")
            lines.append("")
            lines.append("| ID | Nome | Priority | Complexity | Status | Agents | Dependencies |")
            lines.append("|---|---|---|---|---|---|---|")
            for uc in usecases:
                agents = ", ".join(uc.get("agents", []))
                deps = ", ".join(uc.get("depends_on", []))
                lines.append(
                    f"| {uc['id']} | {uc['name']} | P{uc.get('priority', '?')} "
                    f"| {uc.get('complexity', '?')} | {uc.get('status', '?')} "
                    f"| {agents or '-'} | {deps or '-'} |"
                )
            lines.append("")

        # Agent Coverage
        if coverage:
            lines.append("## Cobertura de Agentes")
            lines.append("")
            lines.append("| Agent | Use Cases | Count |")
            lines.append("|---|---|---|")
            for c in coverage:
                ucs = ", ".join(c.get("usecase_ids", []))
                lines.append(
                    f"| {c.get('agent_name', c.get('agent_id', '?'))} "
                    f"| {ucs or '-'} | {c.get('usecase_count', 0)} |"
                )
            lines.append("")

        # Skill Gaps
        if gaps:
            lines.append("## Skill Gaps (sem agente owner)")
            lines.append("")
            lines.append("| UseCase | Skill | Criticality |")
            lines.append("|---|---|---|")
            for g in gaps:
                lines.append(
                    f"| {g.get('usecase_name', g.get('usecase_id', '?'))} "
                    f"| {g.get('skill_name', g.get('skill_id', '?'))} "
                    f"| {g.get('criticality', '?')} |"
                )
            lines.append("")

        content = "\n".join(lines)

        if output_path:
            p = Path(output_path)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content, encoding="utf-8")
            logger.info("Roadmap exported to %s", p)

        return content
