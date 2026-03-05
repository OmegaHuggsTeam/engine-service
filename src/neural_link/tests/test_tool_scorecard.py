"""
Tests for ToolScorecard — Multi-tool sprint review tracker for KPI Intelligence.

Covers calculate_nota_geral, validate_tool_name, VALID_TOOLS,
submit_review (validation, clamping, nota_geral), and graph-less query fallbacks.
"""

import pytest

from src.neural_link.telemetry.tool_scorecard import (
    ToolScorecard,
    VALID_TOOLS,
)


# ==================================================================
# TestCalculateNotaGeral
# ==================================================================


class TestCalculateNotaGeral:
    """ToolScorecard.calculate_nota_geral weighted formula."""

    def test_all_100(self):
        result = ToolScorecard.calculate_nota_geral(100, 100, 100)
        assert result == 100.0

    def test_all_zero(self):
        result = ToolScorecard.calculate_nota_geral(0, 0, 0)
        assert result == 0.0

    def test_weighted_formula(self):
        # 80*0.4 + 90*0.3 + 70*0.3 = 32 + 27 + 21 = 80
        result = ToolScorecard.calculate_nota_geral(80, 90, 70)
        assert result == 80.0

    def test_fractional_result(self):
        # 85*0.4 + 75*0.3 + 65*0.3 = 34 + 22.5 + 19.5 = 76.0
        result = ToolScorecard.calculate_nota_geral(85, 75, 65)
        assert result == 76.0

    def test_asymmetric_scores(self):
        # 100*0.4 + 0*0.3 + 0*0.3 = 40
        result = ToolScorecard.calculate_nota_geral(100, 0, 0)
        assert result == 40.0


# ==================================================================
# TestValidateToolName
# ==================================================================


class TestValidateToolName:
    """ToolScorecard.validate_tool_name and VALID_TOOLS."""

    def test_kiro_valid(self):
        assert ToolScorecard.validate_tool_name("kiro") is True

    def test_cursor_valid(self):
        assert ToolScorecard.validate_tool_name("cursor") is True

    def test_anti_gravity_valid(self):
        assert ToolScorecard.validate_tool_name("anti_gravity") is True

    def test_claude_code_valid(self):
        assert ToolScorecard.validate_tool_name("claude_code") is True

    def test_notepad_invalid(self):
        assert ToolScorecard.validate_tool_name("notepad") is False

    def test_empty_invalid(self):
        assert ToolScorecard.validate_tool_name("") is False

    def test_valid_tools_count(self):
        assert len(VALID_TOOLS) == 4

    def test_valid_tools_exact_set(self):
        assert VALID_TOOLS == {"kiro", "cursor", "anti_gravity", "claude_code"}


# ==================================================================
# TestSubmitReview
# ==================================================================


class TestSubmitReview:
    """ToolScorecard.submit_review behavior."""

    def test_submit_no_graph_returns_dict(self):
        sc = ToolScorecard(graph_manager=None)
        result = sc.submit_review(
            tool_name="kiro",
            sprint_date="2026-03-04",
            score_correto=90,
            score_completo=85,
            score_qualidade=80,
        )
        assert isinstance(result, dict)
        assert result["tool_name"] == "kiro"
        assert result["sprint_date"] == "2026-03-04"

    def test_submit_invalid_tool_raises(self):
        sc = ToolScorecard(graph_manager=None)
        with pytest.raises(ValueError, match="Invalid tool"):
            sc.submit_review(
                tool_name="notepad",
                sprint_date="2026-03-04",
                score_correto=90,
                score_completo=85,
                score_qualidade=80,
            )

    def test_submit_clamps_high_scores(self):
        sc = ToolScorecard(graph_manager=None)
        result = sc.submit_review(
            tool_name="cursor",
            sprint_date="2026-03-04",
            score_correto=150,
            score_completo=200,
            score_qualidade=300,
        )
        assert result["score_correto"] == 100.0
        assert result["score_completo"] == 100.0
        assert result["score_qualidade"] == 100.0

    def test_submit_clamps_negative_scores(self):
        sc = ToolScorecard(graph_manager=None)
        result = sc.submit_review(
            tool_name="anti_gravity",
            sprint_date="2026-03-04",
            score_correto=-10,
            score_completo=-20,
            score_qualidade=-5,
        )
        assert result["score_correto"] == 0.0
        assert result["score_completo"] == 0.0
        assert result["score_qualidade"] == 0.0

    def test_submit_computes_nota_geral(self):
        sc = ToolScorecard(graph_manager=None)
        result = sc.submit_review(
            tool_name="claude_code",
            sprint_date="2026-03-04",
            score_correto=80,
            score_completo=90,
            score_qualidade=70,
        )
        # 80*0.4 + 90*0.3 + 70*0.3 = 80
        assert result["nota_geral"] == 80.0

    def test_submit_includes_optional_fields(self):
        sc = ToolScorecard(graph_manager=None)
        result = sc.submit_review(
            tool_name="kiro",
            sprint_date="2026-03-04",
            score_correto=90,
            score_completo=85,
            score_qualidade=80,
            deliverables_done=5,
            deliverables_total=6,
            issues_critical=1,
            issues_medium=2,
            issues_low=3,
            reviewer="human",
            notes="Good sprint",
        )
        assert result["deliverables_done"] == 5
        assert result["deliverables_total"] == 6
        assert result["issues_critical"] == 1
        assert result["reviewer"] == "human"
        assert result["notes"] == "Good sprint"

    def test_submit_id_format(self):
        sc = ToolScorecard(graph_manager=None)
        result = sc.submit_review(
            tool_name="cursor",
            sprint_date="2026-03-04",
            score_correto=50,
            score_completo=50,
            score_qualidade=50,
        )
        assert result["id"].startswith("tr_cursor_2026-03-04_")


# ==================================================================
# TestQueryMethods
# ==================================================================


class TestQueryMethods:
    """ToolScorecard query methods with no graph."""

    def test_get_all_reviews_no_graph(self):
        sc = ToolScorecard(graph_manager=None)
        assert sc.get_all_reviews() == []

    def test_get_tool_history_no_graph(self):
        sc = ToolScorecard(graph_manager=None)
        assert sc.get_tool_history("kiro") == []

    def test_get_comparison_no_graph(self):
        sc = ToolScorecard(graph_manager=None)
        assert sc.get_comparison() == []
