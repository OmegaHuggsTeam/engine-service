"""
DevOps Agent - Agente de Operacoes e Observabilidade.

Lacuna identificada pelo NeuralLinkOrchestrator:
  Nenhum dos 9 agentes existentes cobre monitoring, health checks,
  data pipeline, ou observabilidade. O ecossistema nao se auto-monitora.

Este agente preenche as lacunas:
  - monitoring:     Health checks de todos os servicos (Neo4j, ChromaDB, LLM keys)
  - data_pipeline:  Ingestao de sources -> chunks -> ChromaDB + Neo4j
  - observability:  Performance dos agentes, graph stats, alertas
  - maintenance:    Confidence decay, error grouping, agent flagging

Capabilities: monitoring, data_pipeline, observability, maintenance, health_check
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent.parent


class DevOpsAgent:
    """
    Agente de Operacoes - o sistema nervoso do ecossistema.
    Monitora, diagnostica e mantem a infraestrutura funcionando.
    """

    def __init__(self):
        self._graph = None
        self._neo4j_available = False
        self._init_graph()

    def _init_graph(self):
        """Tenta conectar ao Neo4j (graceful se indisponivel)."""
        try:
            from src.neural_link.graph.manager import GraphManager
            self._graph = GraphManager.from_env()
            self._neo4j_available = self._graph.verify_connectivity()
        except (ImportError, Exception) as e:
            logger.info(f"DevOpsAgent: Neo4j not available ({e}), running in limited mode")

    # ================================================================
    # HEALTH CHECKS
    # ================================================================

    def full_health_check(self) -> dict:
        """
        Executa health check completo de todos os servicos.
        Retorna dict com status por componente e overall status.
        """
        checks = {}
        start = time.time()

        # 1. Neo4j
        checks["neo4j"] = self._check_neo4j()

        # 2. ChromaDB
        checks["chromadb"] = self._check_chromadb()

        # 3. LLM Keys (Groq)
        checks["groq_keys"] = self._check_groq_keys()

        # 4. TF-IDF / Grimoire
        checks["tfidf_grimoire"] = self._check_tfidf()

        # 5. Filesystem (logs, data dirs)
        checks["filesystem"] = self._check_filesystem()

        # Overall
        statuses = [c["status"] for c in checks.values()]
        if all(s == "healthy" for s in statuses):
            overall = "HEALTHY"
        elif any(s == "critical" for s in statuses):
            overall = "CRITICAL"
        else:
            overall = "DEGRADED"

        elapsed = (time.time() - start) * 1000

        result = {
            "overall": overall,
            "timestamp": datetime.now().isoformat(),
            "check_time_ms": round(elapsed, 1),
            "components": checks,
        }

        # Persist to graph if available
        if self._neo4j_available:
            self._record_health_check(result)

        return result

    def _check_neo4j(self) -> dict:
        if not self._neo4j_available:
            return {"status": "critical", "message": "Not connected"}
        try:
            start = time.time()
            res = self._graph.execute_read("RETURN 1 AS pulse")
            latency = (time.time() - start) * 1000
            node_count = self._graph.execute_read(
                "MATCH (n) RETURN count(n) AS count"
            )
            return {
                "status": "healthy",
                "latency_ms": round(latency, 1),
                "total_nodes": node_count[0]["count"],
            }
        except Exception as e:
            return {"status": "critical", "message": str(e)}

    def _check_chromadb(self) -> dict:
        try:
            from src.utils.vector_db import count
            n = count()
            return {"status": "healthy", "chunks": n}
        except Exception as e:
            err = str(e)
            if "unable to infer type" in err or "pydantic" in err.lower():
                return {
                    "status": "degraded",
                    "message": "Python 3.14 pydantic v1 incompatibility",
                    "impact": "ChromaDB search unavailable, Neo4j+TF-IDF compensate",
                }
            return {"status": "critical", "message": err[:200]}

    def _check_groq_keys(self) -> dict:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
        keys = []
        for i in range(1, 11):
            k = os.getenv(f"GROQ_KEY_{i}", "").strip()
            if k:
                keys.append(i)
        fallback = os.getenv("GROQ_API_KEY", "").strip()
        total = len(keys) if keys else (1 if fallback else 0)
        if total == 0:
            return {"status": "critical", "message": "No Groq API keys configured"}
        return {
            "status": "healthy",
            "keys_available": total,
            "pool_keys": keys if keys else ["fallback"],
        }

    def _check_tfidf(self) -> dict:
        grimoire_path = PROJECT_ROOT / "docs" / "paladin_grimoire"
        if not grimoire_path.exists():
            return {"status": "degraded", "message": "Grimoire directory not found"}
        try:
            from src.rag.rag_query_system import RAGQuerySystem
            rag = RAGQuerySystem(str(grimoire_path))
            files = rag.get_indexed_files()
            return {
                "status": "healthy",
                "indexed_files": len(files),
            }
        except Exception as e:
            return {"status": "degraded", "message": str(e)[:200]}

    def _check_filesystem(self) -> dict:
        dirs = {
            "data": PROJECT_ROOT / "data",
            "logs": PROJECT_ROOT / "logs",
            "db": PROJECT_ROOT / "db",
            "docs": PROJECT_ROOT / "docs",
        }
        result = {"status": "healthy"}
        for name, path in dirs.items():
            result[name] = "exists" if path.exists() else "MISSING"
            if not path.exists():
                result["status"] = "degraded"
        return result

    def _record_health_check(self, result: dict):
        """Registra health check no grafo como node."""
        try:
            self._graph.execute_write(
                "CREATE (h:HealthCheck {"
                "  timestamp: $ts, overall: $overall, "
                "  check_time_ms: $time, details: $details"
                "})",
                {
                    "ts": result["timestamp"],
                    "overall": result["overall"],
                    "time": result["check_time_ms"],
                    "details": json.dumps(result["components"], default=str)[:2000],
                },
            )
        except Exception as e:
            logger.debug(f"Failed to record health check: {e}")

    # ================================================================
    # AGENT PERFORMANCE MONITORING
    # ================================================================

    def get_agent_performance_report(self) -> dict:
        """
        Relatorio de performance de todos os agentes.
        Identifica underperformers e recomendacoes.
        """
        if not self._neo4j_available:
            return {"error": "Neo4j not available"}

        agents = self._graph.execute_read(
            "MATCH (a:Agent) "
            "RETURN a.id AS id, a.name AS name, a.type AS type, "
            "       a.success_rate AS rate, a.status AS status, "
            "       a.capabilities AS caps "
            "ORDER BY a.success_rate ASC"
        )

        # Contar tasks por agente
        task_counts = self._graph.execute_read(
            "MATCH (t:Task)-[:ASSIGNED_TO]->(a:Agent) "
            "RETURN a.id AS agent_id, count(t) AS tasks, "
            "       sum(CASE WHEN t.status = 'completed' THEN 1 ELSE 0 END) AS completed "
            "ORDER BY tasks DESC"
        )
        task_map = {r["agent_id"]: r for r in task_counts}

        report = {
            "timestamp": datetime.now().isoformat(),
            "total_agents": len(agents),
            "agents": [],
            "warnings": [],
            "recommendations": [],
        }

        for agent in agents:
            aid = agent["id"]
            rate = float(agent.get("rate") or 1.0)
            tasks = task_map.get(aid, {})

            entry = {
                "id": aid,
                "name": agent["name"],
                "type": agent["type"],
                "success_rate": round(rate, 3),
                "status": agent["status"],
                "total_tasks": tasks.get("tasks", 0),
                "completed_tasks": tasks.get("completed", 0),
            }
            report["agents"].append(entry)

            if rate < 0.5:
                report["warnings"].append(
                    f"ALERT: {agent['name']} success_rate={rate:.1%} (below 50% threshold)"
                )
            if tasks.get("tasks", 0) == 0:
                report["recommendations"].append(
                    f"Agent '{agent['name']}' has never been assigned a task. "
                    f"Consider routing relevant queries to test it."
                )

        return report

    # ================================================================
    # GRAPH MAINTENANCE
    # ================================================================

    def run_maintenance(self) -> dict:
        """
        Executa ciclo completo de manutencao do grafo.
        - Confidence decay em conceitos antigos
        - Agrupamento de erros similares
        - Propagacao de resolucoes
        - Flagging de agentes underperforming
        """
        if not self._neo4j_available:
            return {"error": "Neo4j not available"}

        try:
            from src.neural_link.graph.enrichment import run_maintenance
            return run_maintenance(self._graph)
        except Exception as e:
            return {"error": str(e)}

    # ================================================================
    # DATA PIPELINE
    # ================================================================

    def discover_unprocessed_sources(self) -> list[dict]:
        """
        Descobre arquivos de dados que ainda nao foram processados.
        Compara data/raw/ e data/processed/ com o que ja esta no ChromaDB/Neo4j.
        """
        raw_dir = PROJECT_ROOT / "data" / "raw"
        processed_dir = PROJECT_ROOT / "data" / "processed"
        chunks_dir = PROJECT_ROOT / "data" / "chunks"

        sources = []

        for directory in [raw_dir, processed_dir, chunks_dir]:
            if not directory.exists():
                continue
            for f in directory.rglob("*"):
                if f.is_file() and f.suffix in (".txt", ".md", ".json", ".csv"):
                    sources.append({
                        "path": str(f.relative_to(PROJECT_ROOT)),
                        "size_kb": round(f.stat().st_size / 1024, 1),
                        "modified": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
                        "directory": directory.name,
                    })

        # Check which are already in Neo4j
        if self._neo4j_available:
            known_sources = self._graph.execute_read(
                "MATCH (c:Chunk) RETURN DISTINCT c.source_file AS source"
            )
            known = {r["source"] for r in known_sources if r.get("source")}
            for s in sources:
                s["in_graph"] = s["path"] in known
        else:
            for s in sources:
                s["in_graph"] = None

        return sources

    def get_pipeline_status(self) -> dict:
        """Retorna status do pipeline de dados."""
        sources = self.discover_unprocessed_sources()

        in_graph = sum(1 for s in sources if s.get("in_graph"))
        not_in_graph = sum(1 for s in sources if s.get("in_graph") is False)

        graph_stats = {}
        if self._neo4j_available:
            node_counts = self._graph.execute_read(
                "MATCH (n) WITH labels(n) AS lbls, count(n) AS cnt "
                "UNWIND lbls AS label RETURN label, sum(cnt) AS count "
                "ORDER BY count DESC"
            )
            graph_stats = {r["label"]: r["count"] for r in node_counts}

        return {
            "total_source_files": len(sources),
            "in_graph": in_graph,
            "pending_ingestion": not_in_graph,
            "graph_nodes": graph_stats,
        }

    # ================================================================
    # UNIFIED COMMAND INTERFACE
    # ================================================================

    def execute(self, command: str) -> dict:
        """
        Entry point para o orchestrator.
        Aceita comandos: health, performance, maintenance, pipeline, status.
        """
        cmd = command.lower().strip()

        if cmd in ("health", "health_check", "check"):
            return self.full_health_check()
        elif cmd in ("performance", "perf", "agents"):
            return self.get_agent_performance_report()
        elif cmd in ("maintenance", "maintain", "cleanup"):
            return self.run_maintenance()
        elif cmd in ("pipeline", "sources", "data"):
            return self.get_pipeline_status()
        elif cmd in ("status", "full", "report"):
            return {
                "health": self.full_health_check(),
                "performance": self.get_agent_performance_report(),
                "pipeline": self.get_pipeline_status(),
            }
        else:
            return {
                "error": f"Unknown command: {cmd}",
                "available": ["health", "performance", "maintenance", "pipeline", "status"],
            }


# Funcao para integracao com o orchestrator
def ask_agent(query: str) -> str:
    """Entry point compativel com o pattern dos domain agents."""
    agent = DevOpsAgent()
    result = agent.execute(query)
    return json.dumps(result, indent=2, ensure_ascii=False, default=str)
