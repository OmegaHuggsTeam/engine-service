"""
KPI Intelligence — Extracted package for migration to separate repo.

Modules:
- ToolScorecard: Multi-tool sprint review (Correto 40% + Completo 30% + Qualidade 30%)
- ModelBenchmark: Per-model performance tracking, leaderboard
- CostQualityAnalyzer: $/quality-point analysis, recommend_model()
- MetricsTimeSeries: RequestMetric persistence, DailyAggregate, anomaly detection

Dependencies: Neo4j GraphManager (execute_read, execute_write).
Profile interface: objects with to_request_metric_params() for MetricsTimeSeries.enqueue().
"""

from .tool_scorecard import ToolScorecard, VALID_TOOLS
from .model_benchmark import ModelBenchmark, ModelCallRecord, _estimate_cost
from .cost_quality_analyzer import CostQualityAnalyzer
from .metrics_timeseries import MetricsTimeSeries

__all__ = [
    "ToolScorecard",
    "VALID_TOOLS",
    "ModelBenchmark",
    "ModelCallRecord",
    "_estimate_cost",
    "CostQualityAnalyzer",
    "MetricsTimeSeries",
]
