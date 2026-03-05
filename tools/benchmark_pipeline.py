"""
Benchmark pipeline ROI - runs N queries and collects cost stats.

Fully offline: mocks all LLM and Neo4j calls.
Run: python tools/benchmark_pipeline.py [--json]
"""

import argparse
import json
import logging
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root in path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Suppress noisy logs during benchmark
logging.getLogger("src.neural_link").setLevel(logging.WARNING)
logging.getLogger("src.utils").setLevel(logging.WARNING)

BENCHMARK_QUERIES = [
    # Layer 0 - cache/shortcut (cost $0.00)
    {"query": "list agents", "expected_layer": 0, "category": "shortcut"},
    {"query": "list agents", "expected_layer": 0, "category": "cache"},  # repeat
    {"query": "show roadmap", "expected_layer": 0, "category": "shortcut"},
    {"query": "status of UC-CAM-001", "expected_layer": 0, "category": "shortcut"},
    {"query": "what can crm_backend_agent do", "expected_layer": 0, "category": "shortcut"},
    # Layer 1 - triage (cost ~$0.0001) — "what is RAG?" is layer 0 via faq_definition
    {"query": "what is RAG?", "expected_layer": 0, "category": "simple"},
    {"query": "explain campaigns", "expected_layer": 1, "category": "simple"},
    {"query": "how does the pipeline work?", "expected_layer": 1, "category": "simple"},
    {"query": "o que e um segmento?", "expected_layer": 0, "category": "simple"},  # faq_definition
    {"query": "describe the Journey Builder", "expected_layer": 1, "category": "simple"},
    # Layer 2 - domain (cost ~$0.0003)
    {"query": "create a segment for active users", "expected_layer": 2, "category": "domain"},
    {"query": "build a campaign for Black Friday", "expected_layer": 2, "category": "domain"},
    {"query": "analyze SMS delivery rates", "expected_layer": 2, "category": "domain"},
    # Layer 3 - complex (cost ~$0.005)
    {
        "query": "first analyze the metrics then generate a report and deploy",
        "expected_layer": 3,
        "category": "complex",
    },
    {
        "query": "redesign the Journey Builder engine for better performance",
        "expected_layer": 3,
        "category": "complex",
    },
    {
        "query": "1) audit security 2) fix vulnerabilities 3) generate report",
        "expected_layer": 3,
        "category": "complex",
    },
]


def _make_mock_graph():
    """Create a mock graph manager that never connects to Neo4j."""
    mock = MagicMock()
    mock.verify_connectivity.return_value = False  # Pretend offline
    mock.execute_read.return_value = []
    mock.execute_write.return_value = None
    return mock


def run_benchmark(use_json: bool = False) -> dict:
    """Run benchmark with all LLM and Neo4j mocked. Returns stats dict."""
    from src.neural_link.orchestrator.core import NeuralLinkOrchestrator
    from src.neural_link.orchestrator.pipeline_cache import PipelineCache

    cache = PipelineCache()
    cache._encoder = False  # disable semantic (no sentence-transformers)

    mock_graph = _make_mock_graph()

    orch = NeuralLinkOrchestrator(
        graph_manager=mock_graph,  # mock - no real Neo4j
        hybrid_rag=None,  # offline - no RAG
        pipeline_cache=cache,
        cost_tracker=None,  # use default
    )

    mock_response = "Mocked LLM response for benchmark."

    per_query = []
    with patch("src.utils.llm_client.chat_completion", return_value=mock_response):
        for i, item in enumerate(BENCHMARK_QUERIES):
            q = item["query"]
            expected = item["expected_layer"]
            category = item["category"]
            try:
                resp = orch.process(q)
                stats = orch.cost_stats
                last_profile = orch._cost_tracker._profiles[-1] if orch._cost_tracker._profiles else None
                decision_layer = last_profile.decision_layer if last_profile else -1
                layers_reached = last_profile.layers_reached if last_profile else -1
                cache_hit = last_profile.cache_hit if last_profile else False
                graph_shortcut = last_profile.graph_shortcut if last_profile else False
                per_query.append({
                    "query": q[:50] + ("..." if len(q) > 50 else ""),
                    "expected_layer": expected,
                    "category": category,
                    "decision_layer": decision_layer,
                    "layers_reached": layers_reached,
                    "cache_hit": cache_hit,
                    "graph_shortcut": graph_shortcut,
                    "answer_len": len(resp.answer) if resp.answer else 0,
                })
            except Exception as e:
                per_query.append({
                    "query": q[:50],
                    "expected_layer": expected,
                    "category": category,
                    "error": str(e),
                })

    stats = orch.cost_stats

    # Layer distribution
    total = len(BENCHMARK_QUERIES)
    layer_counts = {0: 0, 1: 0, 2: 0, 3: 0}
    for pq in per_query:
        dl = pq.get("decision_layer", -1)
        if dl >= 0:
            layer_counts[min(dl, 3)] = layer_counts.get(min(dl, 3), 0) + 1

    result = {
        "total_queries": total,
        "layer_distribution": {
            f"layer_{k}": round(v / total * 100, 1) for k, v in layer_counts.items()
        },
        "avg_tokens_per_request": stats.get("avg_tokens_per_request", 0),
        "cache_hit_rate": stats.get("cache_hit_rate", 0),
        "graph_shortcut_rate": stats.get("graph_shortcut_rate", 0),
        "total_estimated_cost_usd": stats.get("total_cost_usd", 0),
        "per_query_breakdown": per_query,
    }
    return result


def main():
    parser = argparse.ArgumentParser(description="Benchmark Neural Link pipeline (offline)")
    parser.add_argument("--json", action="store_true", help="Output JSON for CI")
    args = parser.parse_args()

    result = run_benchmark(use_json=args.json)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("=== Pipeline Benchmark (Offline) ===\n")
        print(f"Total queries: {result['total_queries']}")
        print(f"Layer distribution: {result['layer_distribution']}")
        print(f"Avg tokens/request: {result['avg_tokens_per_request']}")
        print(f"Cache hit rate: {result['cache_hit_rate']}")
        print(f"Graph shortcut rate: {result['graph_shortcut_rate']}")
        print(f"Total estimated cost: ${result['total_estimated_cost_usd']:.6f}")
        print("\nPer-query breakdown:")
        for pq in result["per_query_breakdown"][:8]:
            err = f" ERROR: {pq['error']}" if "error" in pq else ""
            print(f"  [{pq.get('decision_layer', '?')}] {pq['query']}{err}")


if __name__ == "__main__":
    main()
