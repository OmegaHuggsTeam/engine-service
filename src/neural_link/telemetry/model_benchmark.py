"""
ModelBenchmark — Proxy para src.extracted.kpi_intelligence.

Mantido para compatibilidade. Implementação migrada para extracted/kpi_intelligence/.
Ver docs/MIGRATION_KPI.md.
"""

from src.extracted.kpi_intelligence import ModelBenchmark, ModelCallRecord, _estimate_cost

__all__ = ["ModelBenchmark", "ModelCallRecord", "_estimate_cost"]
