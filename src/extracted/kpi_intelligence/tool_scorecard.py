"""
ToolScorecard — Multi-tool sprint review tracker for KPI Intelligence.

Manages :ToolReview nodes in Neo4j following the REVIEW_TEMPLATE.md formula:
    Correto(40%) + Completo(30%) + Qualidade(30%) = nota_geral (0-100)

Valid tool names: kiro, cursor, anti_gravity, claude_code

EXTRACTED: migrated from src/neural_link/telemetry/ for separate repo.
"""

import logging
import uuid
from typing import Any

from . import queries_kpi as q

logger = logging.getLogger(__name__)

VALID_TOOLS = {"kiro", "cursor", "anti_gravity", "claude_code"}


class ToolScorecard:
    """CRUD operations for :ToolReview nodes."""

    def __init__(self, graph_manager=None):
        self._graph = graph_manager

    @staticmethod
    def calculate_nota_geral(
        score_correto: float,
        score_completo: float,
        score_qualidade: float,
    ) -> float:
        """
        Compute weighted score following REVIEW_TEMPLATE.md formula.
        Each input is 0-100. Output is 0-100.
        """
        return round(
            score_correto * 0.40 + score_completo * 0.30 + score_qualidade * 0.30,
            1,
        )

    @staticmethod
    def validate_tool_name(tool_name: str) -> bool:
        """Check if tool name is valid."""
        return tool_name in VALID_TOOLS

    def submit_review(
        self,
        tool_name: str,
        sprint_date: str,
        score_correto: float,
        score_completo: float,
        score_qualidade: float,
        deliverables_done: int = 0,
        deliverables_total: int = 0,
        issues_critical: int = 0,
        issues_medium: int = 0,
        issues_low: int = 0,
        reviewer: str = "claude_code",
        notes: str = "",
    ) -> dict | None:
        """
        Submit a tool review. Validates inputs and persists to Neo4j.
        Returns the review dict or None on failure.
        """
        if not self.validate_tool_name(tool_name):
            raise ValueError(f"Invalid tool: {tool_name}. Must be one of: {VALID_TOOLS}")

        score_correto = max(0.0, min(100.0, score_correto))
        score_completo = max(0.0, min(100.0, score_completo))
        score_qualidade = max(0.0, min(100.0, score_qualidade))

        nota_geral = self.calculate_nota_geral(score_correto, score_completo, score_qualidade)

        review_id = f"tr_{tool_name}_{sprint_date}_{uuid.uuid4().hex[:6]}"
        params = {
            "id": review_id,
            "tool_name": tool_name,
            "sprint_date": sprint_date,
            "score_correto": score_correto,
            "score_completo": score_completo,
            "score_qualidade": score_qualidade,
            "nota_geral": nota_geral,
            "deliverables_done": deliverables_done,
            "deliverables_total": deliverables_total,
            "issues_critical": issues_critical,
            "issues_medium": issues_medium,
            "issues_low": issues_low,
            "reviewer": reviewer,
            "notes": notes,
        }

        if self._graph:
            try:
                self._graph.execute_write(q.UPSERT_TOOL_REVIEW, params)
            except Exception as e:
                logger.warning("ToolScorecard.submit_review failed: %s", e)
                return None

        return params

    def get_all_reviews(self, limit: int = 50) -> list[dict]:
        """Get all tool reviews, newest first."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(q.GET_TOOL_REVIEWS, {"limit": limit})
        except Exception as e:
            logger.warning("ToolScorecard.get_all_reviews failed: %s", e)
            return []

    def get_tool_history(self, tool_name: str, limit: int = 20) -> list[dict]:
        """Get sprint-by-sprint reviews for a specific tool."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(
                q.GET_TOOL_REVIEW_HISTORY, {"tool_name": tool_name, "limit": limit}
            )
        except Exception as e:
            logger.warning("ToolScorecard.get_tool_history failed: %s", e)
            return []

    def get_comparison(self) -> list[dict]:
        """Compare all tools side-by-side."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(q.GET_TOOL_COMPARISON)
        except Exception as e:
            logger.warning("ToolScorecard.get_comparison failed: %s", e)
            return []
