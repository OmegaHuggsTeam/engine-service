"""
NeuralLinkOrchestrator - Entry point principal do Neural Link.

Fluxo:
request -> HybridRAG.query() -> TaskDecomposer.decompose() -> para cada task:
    AgentSelector.select() -> TaskExecutor.execute() -> resultado
-> sintetizar resposta final
"""

import logging
import re
import time
import uuid
from datetime import datetime
from typing import Optional

from src.utils.cost_context import set_cost_profile, clear_cost_profile

from .models import OrchestratorResponse, Task, TaskResult, TaskStatus
from .task_decomposer import TaskDecomposer
from .agent_selector import AgentSelector, AGENT_REGISTRY
from .task_executor import TaskExecutor
from .pipeline_cache import PipelineCache
from .quality_gate import QualityGate
from .model_tier import get_operation_model, get_max_tokens
from .decision_tree import DecisionTree
from ..telemetry.cost_tracker import CostTracker, RequestCostProfile

logger = logging.getLogger(__name__)

# Graph shortcut patterns: regex -> handler name
GRAPH_SHORTCUTS = {
    r"\b(agents?|agentes?)\s+(list|available|registered|disponiveis|todos)\b": "list_agents",
    r"\b(list|show|listar|mostrar)\s+(agents?|agentes?)\b": "list_agents",
    r"\b(roadmap|usecases?|use\s*cases?)\b": "get_roadmap",
    r"\b(coverage|cobertura)\s*(de\s*agentes?)?\b": "get_coverage",
    r"\b(stats?|estatisticas?|status)\s*(do\s*)?(sistema|system|crm)\b": "system_stats",
    r"\bstatus\s+(of\s+)?(UC-[A-Z]+-\d+)\b": "usecase_status",
    r"\b(what can|capabilities of)\s+(\w+_agent)\b": "agent_capabilities",
    r"\b(what is|o que e)\s+(a |an |uma? )?(rag|campaign|campanha|segment|segmento|journey|jornada|lead|flow)\b": "faq_definition",
}

# FAQ definitions for faq_definition shortcut
FAQ_DEFINITIONS = {
    "rag": "Retrieval-Augmented Generation. A technique that enhances LLM responses by retrieving relevant context from a knowledge base before generating answers.",
    "campaign": "A marketing campaign is a coordinated set of actions (emails, SMS, push) targeting a segment of contacts to achieve a specific goal.",
    "campanha": "A marketing campaign is a coordinated set of actions (emails, SMS, push) targeting a segment of contacts to achieve a specific goal.",
    "segment": "A segment is a subset of contacts defined by rules (e.g., active users, high-value customers) used for targeting in campaigns.",
    "segmento": "A segment is a subset of contacts defined by rules (e.g., active users, high-value customers) used for targeting in campaigns.",
    "journey": "A journey is an automated multi-step flow that guides contacts through stages based on their behavior and triggers.",
    "jornada": "A journey is an automated multi-step flow that guides contacts through stages based on their behavior and triggers.",
    "lead": "A lead is a potential customer record in the CRM, with attributes like name, email, company, and interaction history.",
    "flow": "A flow is an automated workflow (e.g., journey, campaign) that executes actions based on triggers and conditions.",
}


class NeuralLinkOrchestrator:
    """
    Motor central de orquestracao.
    Decompoe requests, seleciona agentes, executa tasks, e sintetiza respostas.
    """

    def __init__(
        self,
        graph_manager=None,
        hybrid_rag=None,
        decomposer: TaskDecomposer | None = None,
        selector: AgentSelector | None = None,
        pipeline_cache: PipelineCache | None = None,
        quality_gate: QualityGate | None = None,
        cost_tracker: CostTracker | None = None,
        metrics_timeseries=None,
        model_benchmark=None,
    ):
        self._graph = graph_manager
        self._rag = hybrid_rag
        self._decomposer = decomposer or TaskDecomposer()
        self._selector = selector or AgentSelector(graph_manager)
        self._pipeline_cache = pipeline_cache or PipelineCache()
        self._quality_gate = quality_gate or QualityGate()
        self._cost_tracker = cost_tracker or CostTracker()
        self._decision_tree = DecisionTree()
        self._metrics_timeseries = metrics_timeseries
        self._model_benchmark = model_benchmark

    @property
    def cost_stats(self) -> dict:
        """Aggregate cost statistics across all tracked requests."""
        return self._cost_tracker.stats

    @classmethod
    def from_env(cls) -> "NeuralLinkOrchestrator":
        """Cria orchestrator a partir do ambiente."""
        graph_manager = None
        hybrid_rag = None

        try:
            from ..graph.manager import GraphManager
            gm = GraphManager.from_env()
            if gm.verify_connectivity():
                graph_manager = gm
        except Exception as e:
            logger.warning(f"Neo4j not available: {e}")

        try:
            from ..rag.hybrid_rag import HybridRAG
            hybrid_rag = HybridRAG(
                graph_manager=graph_manager,
                graph_retriever=None,
            )
            # Inicializa graph_retriever se graph disponivel
            if graph_manager:
                from ..rag.graph_retriever import GraphRetriever
                hybrid_rag._graph_retriever = GraphRetriever(graph_manager)
                hybrid_rag._neo4j_available = True
        except Exception as e:
            logger.warning(f"HybridRAG init failed: {e}")

        return cls(
            graph_manager=graph_manager,
            hybrid_rag=hybrid_rag,
        )

    def process(
        self,
        query: str,
        context: Optional[dict] = None,
        session_source: str = "api",
    ) -> OrchestratorResponse:
        """
        Processa um request completo.

        Args:
            query: Texto do request
            context: Contexto adicional
            session_source: Origem (webhook, cli, api)

        Returns:
            OrchestratorResponse com answer, tasks, results, etc.
        """
        start = time.time()
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        profile = self._cost_tracker.start_request(session_id)
        set_cost_profile(profile)

        try:
            return self._process_impl(query, context, session_source, session_id, start, profile)
        finally:
            clear_cost_profile()
            self._cost_tracker.finish_request(profile)
            # Enqueue to KPI subsystems
            if self._metrics_timeseries:
                try:
                    self._metrics_timeseries.enqueue(profile)
                except Exception as e:
                    logger.debug("MetricsTimeSeries enqueue failed: %s", e)
            if self._model_benchmark:
                try:
                    self._model_benchmark.record_from_profile(profile)
                except Exception as e:
                    logger.debug("ModelBenchmark record failed: %s", e)

    def _process_impl(
        self,
        query: str,
        context: Optional[dict],
        session_source: str,
        session_id: str,
        start: float,
        profile: RequestCostProfile,
    ) -> OrchestratorResponse:
        """Internal process implementation with cost profile tracking."""
        logger.info(f"[{session_id}] Processing: {query[:100]}...")

        # Layer 0: Deterministic resolution (cache + graph shortcuts)
        cached = self._pipeline_cache.get(query)
        if cached is not None:
            profile.cache_hit = True
            profile.layers_reached = 0
            logger.info(f"[{session_id}] Cache HIT - resolved at Layer 0")
            return OrchestratorResponse(
                answer=cached,
                tasks=[],
                results=[],
                rag_results=[],
                session_id=session_id,
                processing_time_ms=(time.time() - start) * 1000,
            )

        # DecisionTree advisory classification (before graph shortcut)
        decision = self._decision_tree.classify(query)
        profile.decision_layer = decision.layer

        graph_answer = self._try_graph_shortcut(query)
        if graph_answer is not None:
            profile.graph_shortcut = True
            profile.layers_reached = 0
            self._pipeline_cache.put(query, graph_answer)
            logger.info(f"[{session_id}] Graph shortcut - resolved at Layer 0")
            return OrchestratorResponse(
                answer=graph_answer,
                tasks=[],
                results=[],
                rag_results=[],
                session_id=session_id,
                processing_time_ms=(time.time() - start) * 1000,
            )

        profile.layers_reached = max(profile.layers_reached, 2)

        # 1. RAG hibrido para buscar contexto
        rag_results = []
        rag_context = ""
        if self._rag:
            try:
                rag_results = self._rag.query(query, top_k=5, context=context)
                rag_context = "\n".join(
                    f"[{r.get('score', 0):.2f}] {r.get('content', '')[:200]}"
                    for r in rag_results[:3]
                )
            except Exception as e:
                logger.warning(f"RAG query failed: {e}")

        # 2. Decompor em tasks (DecisionTree layer 1: skip LLM decompose)
        if decision.layer == 1:
            profile.triage_resolved = True
            profile.layers_reached = max(profile.layers_reached, 1)
            tasks = [self._decomposer._create_simple_task(query)]
            logger.info(f"[{session_id}] DecisionTree layer 1 - simple task (no decompose)")
        else:
            tasks = self._decomposer.decompose(query, rag_context=rag_context, cost_profile=profile)
        logger.info(f"[{session_id}] Decomposed into {len(tasks)} tasks")

        # 3. Executar tasks em ordem (respeitando dependencias)
        executor = TaskExecutor(
            graph_manager=self._graph,
            rag_context=rag_context,
        )
        results = []
        completed_ids = set()

        # Ordenar por prioridade (maior primeiro)
        tasks_sorted = sorted(tasks, key=lambda t: t.priority, reverse=True)

        for task in tasks_sorted:
            # Verificar dependencias
            if task.depends_on:
                unmet = [d for d in task.depends_on if d not in completed_ids]
                if unmet:
                    logger.warning(f"Task {task.id} has unmet dependencies: {unmet}")
                    # Executa mesmo assim (best effort)

            # Selecionar agente
            agent_id = self._selector.select(task)
            logger.info(f"[{session_id}] Task '{task.description[:50]}...' -> Agent: {agent_id}")

            # Executar
            result = executor.execute(task, agent_id)

            # Layer 4: Quality gate - smart evaluation
            if result.success:
                agent_rate = self._get_agent_success_rate(agent_id)
                should_eval = self._quality_gate.should_evaluate(
                    task_type=task.type.value,
                    success=result.success,
                    agent_success_rate=agent_rate,
                )
                if not should_eval:
                    profile.evaluation_skipped = True
                if should_eval:
                    profile.layers_reached = max(profile.layers_reached, 4)
                    try:
                        from ..graph.evaluator import TaskEvaluator
                        evaluator = TaskEvaluator(
                            graph_manager=self._graph, threshold=7, max_refinements=1,
                        )
                        summary = evaluator.evaluate_and_refine(task, result, executor, agent_id)
                        if summary.final_output:
                            result = TaskResult(
                                task_id=task.id,
                                success=True,
                                output=summary.final_output,
                                agent_used=agent_id,
                                execution_time_ms=result.execution_time_ms,
                            )
                    except Exception as e:
                        logger.warning(f"Evaluation failed for task {task.id}: {e}")
                else:
                    logger.debug(f"[{session_id}] Evaluation SKIPPED for task {task.id} (agent_rate={agent_rate:.2f})")

            results.append(result)

            if result.success:
                completed_ids.add(task.id)

        # 4. Sintetizar resposta final + cache
        answer = self._synthesize_answer(query, tasks, results, rag_context)
        self._pipeline_cache.put(query, answer)

        # 5. Feedback loop (enriquecimento)
        enrichment = self._run_feedback_loop(query, answer, tasks, results, rag_results)

        # 6. Registrar sessao
        self._record_session(session_id, session_source, tasks, results)

        elapsed = (time.time() - start) * 1000

        response = OrchestratorResponse(
            answer=answer,
            tasks=tasks,
            results=results,
            rag_results=rag_results,
            knowledge_enrichment=enrichment,
            session_id=session_id,
            processing_time_ms=elapsed,
        )

        logger.info(
            f"[{session_id}] Done in {elapsed:.0f}ms: "
            f"{len(tasks)} tasks, {sum(1 for r in results if r.success)}/{len(results)} success"
        )

        return response

    def _try_graph_shortcut(self, query: str) -> Optional[str]:
        """Layer 0: Try to resolve query via direct graph/registry lookup."""
        query_stripped = query.strip()

        for pattern, handler in GRAPH_SHORTCUTS.items():
            match = re.search(pattern, query_stripped, re.IGNORECASE)
            if match:
                try:
                    return self._handle_graph_shortcut(handler, query, match)
                except Exception as e:
                    logger.debug("Graph shortcut '%s' failed: %s", handler, e)
                    return None
        return None

    def _handle_graph_shortcut(
        self, handler: str, query: str = "", match: Optional[re.Match] = None
    ) -> Optional[str]:
        """Execute a graph shortcut handler."""
        if handler == "list_agents":
            agents = sorted(AGENT_REGISTRY.keys())
            lines = [f"**{len(agents)} agents registered:**\n"]
            for aid in agents:
                info = AGENT_REGISTRY[aid]
                lines.append(f"- **{info['name']}** ({info['type']}) - {', '.join(sorted(info['capabilities'])[:5])}")
            return "\n".join(lines)

        if handler == "get_roadmap":
            try:
                from ..api.usecase_registry import UseCaseRegistry
                registry = UseCaseRegistry(self._graph)
                return registry.export_roadmap_md()
            except Exception:
                return None

        if handler == "get_coverage":
            try:
                from ..api.usecase_registry import UseCaseRegistry
                registry = UseCaseRegistry(self._graph)
                coverage = registry.get_agent_coverage()
                if coverage:
                    lines = ["**Agent Coverage:**\n"]
                    for c in coverage:
                        lines.append(f"- {c.get('agent_name', '?')}: {c.get('usecase_count', 0)} use cases")
                    return "\n".join(lines)
            except Exception:
                pass
            return None

        if handler == "usecase_status" and match:
            usecase_id = match.group(2) if match.lastindex >= 2 else None
            if usecase_id:
                return self._handle_usecase_status(usecase_id)
            return None

        if handler == "agent_capabilities" and match:
            agent_id = match.group(2) if match.lastindex >= 2 else None
            if agent_id:
                return self._handle_agent_capabilities(agent_id)
            return None

        if handler == "faq_definition" and match:
            # Group 2 is optional (a |an |uma? ), group 3 is the term
            term = (match.group(3) if match.lastindex >= 3 else match.group(2)).lower()
            if term:
                return self._handle_faq_definition(term)
            return None

        return None

    def _handle_usecase_status(self, usecase_id: str) -> Optional[str]:
        """Query Neo4j :UseCase {id: $id}, return status+name."""
        if not self._graph:
            return f"UseCase {usecase_id}: (Neo4j unavailable)"
        try:
            results = self._graph.execute_read(
                "MATCH (u:UseCase {id: $id}) RETURN u.name AS name, u.status AS status",
                {"id": usecase_id},
            )
            if results:
                name = results[0].get("name", "?")
                status = results[0].get("status", "?")
                return f"**{usecase_id}**: {name} — status: {status}"
            return f"UseCase {usecase_id} not found."
        except Exception as e:
            logger.debug("usecase_status failed: %s", e)
            return None

    def _handle_agent_capabilities(self, agent_id: str) -> Optional[str]:
        """Lookup AGENT_REGISTRY, return capabilities list."""
        info = AGENT_REGISTRY.get(agent_id)
        if not info:
            return f"Agent '{agent_id}' not found in registry."
        caps = sorted(info.get("capabilities", set()))
        lines = [f"**{info.get('name', agent_id)}** capabilities:\n"]
        lines.extend(f"- {c}" for c in caps[:15])
        if len(caps) > 15:
            lines.append(f"- ... and {len(caps) - 15} more")
        return "\n".join(lines)

    def _handle_faq_definition(self, term: str) -> Optional[str]:
        """Return hardcoded FAQ definition."""
        definition = FAQ_DEFINITIONS.get(term)
        if definition:
            return f"**{term.upper()}**: {definition}"
        return None

    def _get_agent_success_rate(self, agent_id: str) -> float:
        """Get agent success rate from graph or default."""
        if not self._graph:
            return 0.5
        try:
            from ..graph import queries
            results = self._graph.execute_read(
                "MATCH (a:Agent {id: $agent_id}) RETURN a.success_rate AS rate",
                {"agent_id": agent_id},
            )
            if results and results[0].get("rate") is not None:
                return float(results[0]["rate"])
        except Exception:
            pass
        return 0.5

    def _synthesize_answer(
        self,
        query: str,
        tasks: list[Task],
        results: list[TaskResult],
        rag_context: str,
    ) -> str:
        """Sintetiza resposta final a partir dos resultados das tasks."""
        if len(results) == 1 and results[0].success:
            return str(results[0].output or "")

        # Multiplos resultados: sintetiza via LLM
        if any(r.success for r in results):
            successful_outputs = [
                f"[Task: {t.description[:80]}]\n{r.output}"
                for t, r in zip(tasks, results)
                if r.success and r.output
            ]

            if not successful_outputs:
                return "Tasks executadas mas sem output significativo."

            if len(successful_outputs) == 1:
                return successful_outputs[0].split("\n", 1)[-1]

            try:
                from src.utils.llm_client import chat_completion

                synthesis_prompt = (
                    f"The user asked: {query}\n\n"
                    f"Here are the results from different agents:\n\n"
                    + "\n\n---\n\n".join(successful_outputs[:5])
                    + "\n\nSynthesize a coherent, complete answer. Be concise."
                )

                return chat_completion(
                    [
                        {"role": "system", "content": "Synthesize multiple agent outputs into one coherent answer."},
                        {"role": "user", "content": synthesis_prompt},
                    ],
                    model=get_operation_model("synthesis"),
                    max_tokens=get_max_tokens("synthesis"),
                )
            except Exception as e:
                logger.warning(f"Synthesis failed: {e}")
                return "\n\n".join(str(r.output) for r in results if r.success and r.output)

        # Todos falharam
        errors = [r.error for r in results if r.error]
        return f"Nao foi possivel processar o request. Erros: {'; '.join(errors[:3])}"

    def _run_feedback_loop(
        self,
        query: str,
        answer: str,
        tasks: list[Task],
        results: list[TaskResult],
        rag_results: list[dict],
    ) -> dict:
        """Executa feedback loop para enriquecer o grafo."""
        enrichment = {"nodes_added": 0, "relationships_added": 0, "concepts_extracted": 0}

        if not self._graph:
            return enrichment

        try:
            from .feedback import FeedbackLoop
            fb = FeedbackLoop(self._graph)
            enrichment = fb.process_interaction(
                query=query,
                answer=answer,
                tasks=tasks,
                results=results,
                rag_results=rag_results,
            )
        except ImportError:
            logger.debug("FeedbackLoop not available yet")
        except Exception as e:
            logger.warning(f"Feedback loop failed: {e}")

        return enrichment

    def _record_session(
        self,
        session_id: str,
        source: str,
        tasks: list[Task],
        results: list[TaskResult],
    ):
        """Registra sessao no grafo."""
        if not self._graph:
            return

        try:
            from ..graph import queries

            self._graph.execute_write(queries.UPSERT_SESSION, {
                "id": session_id,
                "source": source,
                "started_at": datetime.now().isoformat(),
                "task_count": len(tasks),
                "success_count": sum(1 for r in results if r.success),
            })
        except Exception as e:
            logger.debug(f"Failed to record session: {e}")
