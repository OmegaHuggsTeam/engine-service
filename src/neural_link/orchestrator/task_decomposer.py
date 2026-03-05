"""
TaskDecomposer - Decompoe requests complexos em DAG de tasks.
Usa Groq function calling (pattern do groq_operator.py).
"""

import json
import logging
import re
import uuid
from typing import TYPE_CHECKING, Optional

from .models import Task, TaskType

if TYPE_CHECKING:
    from ..telemetry.cost_tracker import RequestCostProfile

logger = logging.getLogger(__name__)

# Tool definition para Groq function calling
DECOMPOSE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": (
                "Create a task in the execution plan. Call this function once for each "
                "subtask needed to fulfill the user's request."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "description": {
                        "type": "string",
                        "description": "Clear description of what this task should accomplish",
                    },
                    "type": {
                        "type": "string",
                        "enum": ["query", "automation", "repair", "generation", "analysis"],
                        "description": "Task type: query (search/answer), generation (create content), analysis (analyze data), automation (execute action), repair (fix error)",
                    },
                    "priority": {
                        "type": "integer",
                        "description": "Priority 1-10 (10=highest). Higher priority tasks execute first.",
                        "minimum": 1,
                        "maximum": 10,
                    },
                    "required_capabilities": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Capabilities needed: marketing, social_media, analytics, ai, llm_inference, auto_repair, code_generation, etc.",
                    },
                    "depends_on_index": {
                        "type": "integer",
                        "description": "Index (0-based) of a previous task this depends on. -1 if no dependency.",
                    },
                },
                "required": ["description", "type", "priority", "required_capabilities"],
            },
        },
    }
]


class TaskDecomposer:
    """Decompoe requests em tasks usando LLM function calling."""

    def decompose(
        self,
        request: str,
        rag_context: str = "",
        max_tasks: int = 5,
        cost_profile: "RequestCostProfile | None" = None,
    ) -> list[Task]:
        """
        Decompoe um request em lista de Tasks.

        Para requests simples, retorna 1 task.
        Para complexos, usa LLM para decompor.
        """
        # Heuristica: requests simples = 1 task
        if self._is_simple_request(request):
            if cost_profile:
                cost_profile.triage_resolved = True
                cost_profile.layers_reached = max(cost_profile.layers_reached, 1)
            return [self._create_simple_task(request)]

        # Requests complexos: usa LLM
        try:
            return self._decompose_with_llm(request, rag_context, max_tasks)
        except Exception as e:
            logger.warning(f"LLM decomposition failed ({e}), falling back to single task")
            return [self._create_simple_task(request)]

    # Single-intent patterns: questions that are inherently single-task
    _SINGLE_INTENT_PATTERNS = [
        r'^(what|how|why|when|where|who|which|explain|describe|list|show|get|tell)\b',
        r'^(o que|como|por que|quando|onde|quem|qual|explique|descreva|liste|mostre|me\s+(diga|fale|conte))\b',
    ]

    def _is_simple_request(self, request: str) -> bool:
        """Heuristica: request simples se < 50 palavras e sem conectivos de composicao."""
        words = request.split()
        if len(words) > 50:
            return False
        composite_signals = [
            r'\be\s+(depois|tambem|alem)\b',
            r'\band\s+(then|also)\b',
            r'\bprimeiro\b.*\bdepois\b',
            r'\bfirst\b.*\bthen\b',
            r'\b\d+\)\s',  # numbered lists
        ]
        request_lower = request.lower().strip()

        has_composite = any(re.search(p, request_lower) for p in composite_signals)
        if has_composite:
            return False

        # Single-intent question words → always simple
        if any(re.match(p, request_lower) for p in self._SINGLE_INTENT_PATTERNS):
            return True

        # Short requests without composite signals → simple
        return len(words) <= 50

    def _create_simple_task(self, request: str) -> Task:
        """Cria uma unica task para requests simples."""
        task_type = self._infer_task_type(request)
        capabilities = self._infer_capabilities(request)

        return Task(
            id=f"task_{uuid.uuid4().hex[:8]}",
            description=request,
            type=task_type,
            priority=5,
            required_capabilities=capabilities,
        )

    def _decompose_with_llm(
        self, request: str, rag_context: str, max_tasks: int
    ) -> list[Task]:
        """Usa Groq function calling para decompor o request."""
        from src.utils.llm_client import chat_completion

        system_prompt = (
            "You are a task decomposition engine. Break down the user's request into "
            f"subtasks (maximum {max_tasks}). Call create_task() for each subtask. "
            "Order tasks by dependency and priority.\n\n"
            "Available capabilities: marketing, social_media, analytics, ai, "
            "llm_inference, function_calling, automation, auto_repair, "
            "code_generation, copywriting, branding, funnel, content_creation, "
            "engagement, metrics, reporting, data_analysis, embeddings, rag, "
            "crm_backend, crm_frontend, crm_data, crm_integration, "
            "campaigns, journeys, contacts, segmentation, clickhouse, "
            "kafka, sms, email, tracker_sdk, ontology, "
            "real_time_analytics, card_analytics, acquisition_analytics, "
            "ai_recommendations, cohort_analysis, campaign_analytics, weekly_kpis, "
            "profiling, dynamic_fields, weekly_stats, ml_scoring, feature_buckets, "
            "audience_queries, event_collection, fingerprinting, rules_engine, "
            "smart_modals, minigames, buyer_agent, form_capture, "
            "sms_delivery, supplier_routing, campaign_execution, credit_management, "
            "rabbitmq, webhook_processing, status_normalization, batch_processing, "
            "supplier_management, billing, client_management, pricing, lost_list, "
            "blacklist_management, fraud_detection, phone_maturation, "
            "message_delivery, circuit_breaker, dlq, retry_patterns, "
            "rest_api, multi_tenant, authentication, rate_limiting_api, "
            "contact_management, template_engine, api_logging.\n\n"
            f"Context from knowledge base:\n{rag_context[:500] if rag_context else '(none)'}"
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": request},
        ]

        # Usar Groq com function calling
        try:
            from groq import Groq
            import os

            api_key = os.getenv("GROQ_API_KEY")
            if not api_key:
                raise ValueError("GROQ_API_KEY not set")

            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
                messages=messages,
                tools=DECOMPOSE_TOOLS,
                tool_choice="auto",
            )

            # Record token usage for cost profiling
            try:
                from src.utils.cost_context import get_cost_profile
                profile = get_cost_profile()
                model_used = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")
                if profile and hasattr(profile, "record_llm_call") and hasattr(completion, "usage") and completion.usage:
                    profile.record_llm_call(
                        model_used,
                        getattr(completion.usage, "prompt_tokens", 0),
                        getattr(completion.usage, "completion_tokens", 0),
                    )
            except ImportError:
                pass

            msg = completion.choices[0].message
            tool_calls = getattr(msg, "tool_calls", None) or []

            if not tool_calls:
                # LLM nao chamou funcoes - cria task simples
                return [self._create_simple_task(request)]

            tasks = []
            for tc in tool_calls:
                fn = getattr(tc, "function", tc)
                raw_args = getattr(fn, "arguments", "{}") or "{}"
                try:
                    args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
                except json.JSONDecodeError:
                    continue

                task_id = f"task_{uuid.uuid4().hex[:8]}"
                depends_on_idx = args.get("depends_on_index", -1)

                task = Task(
                    id=task_id,
                    description=args.get("description", ""),
                    type=TaskType(args.get("type", "query")),
                    priority=min(10, max(1, args.get("priority", 5))),
                    required_capabilities=args.get("required_capabilities", []),
                    depends_on=[tasks[depends_on_idx].id]
                    if isinstance(depends_on_idx, int) and 0 <= depends_on_idx < len(tasks)
                    else [],
                )
                tasks.append(task)

            return tasks[:max_tasks] if tasks else [self._create_simple_task(request)]

        except ImportError:
            # Fallback sem Groq: usa chat_completion generico
            response = chat_completion(messages)
            return [self._create_simple_task(request)]

    def _infer_task_type(self, text: str) -> TaskType:
        """Infere o tipo de task a partir do texto."""
        text_lower = text.lower()
        if any(w in text_lower for w in ["erro", "error", "fix", "bug", "corrigir"]):
            return TaskType.REPAIR
        if any(w in text_lower for w in ["crie", "create", "gere", "generate", "escreva", "write"]):
            return TaskType.GENERATION
        if any(w in text_lower for w in ["analise", "analyze", "metricas", "metrics", "relatorio"]):
            return TaskType.ANALYSIS
        if any(w in text_lower for w in ["execute", "automatize", "rode", "run"]):
            return TaskType.AUTOMATION
        return TaskType.QUERY

    def _infer_capabilities(self, text: str) -> list[str]:
        """Infere capabilities necessarias a partir do texto."""
        text_lower = text.lower()
        caps = []
        mapping = {
            "marketing": ["marketing", "campanha", "campaign", "branding", "marca"],
            "social_media": ["social", "instagram", "twitter", "linkedin", "post"],
            "analytics": ["analytics", "metricas", "metrics", "dados", "data", "relatorio",
                          "real-time", "real time", "active users", "engagement score",
                          "kpi", "weekly stats", "cohort", "retention", "funnel",
                          "bounce rate", "scroll depth", "acquisition", "card analytics",
                          "campaign stats", "heatmap", "tier distribution"],
            "ai": ["ai", "inteligencia artificial", "machine learning", "ml", "modelo"],
            "llm_inference": ["llm", "gpt", "groq", "prompt", "gerar texto"],
            "auto_repair": ["erro", "error", "fix", "bug", "repair", "corrigir"],
            "code_generation": ["codigo", "code", "script", "funcao", "function"],
            "rag": ["rag", "busca", "search", "documento", "knowledge"],
            "crm_backend": ["campaign", "campanha", "journey", "jornada", "contact", "contato",
                            "ontology", "ontologia", "crm", "lead", "template",
                            "journey engine", "campaign scheduler", "tag rules"],
            "crm_frontend": ["component", "componente", "dashboard", "canvas", "react flow",
                             "widget", "ui", "pagina", "page", "sidebar",
                             "funnel chart", "cohort chart", "kpi card", "stage funnel",
                             "d3", "recharts", "ai recommendations ui"],
            "crm_data": ["segment", "segmento", "clickhouse", "behavioral", "comportamental",
                         "ingestion", "ingestao", "kafka", "worker", "profiling", "perfil",
                         "dynamic fields", "weekly stats", "ml scoring", "feature bucket",
                         "audience", "peerdb", "cdc"],
            "crm_integration": ["tracker", "smartico", "sdk",
                                "resend", "buyer agent", "fingerprint",
                                "rules engine", "smart modal", "minigame", "form capture",
                                "event collection"],
            "sms_delivery": ["sms", "supplier", "fornecedor", "pushfy", "sona", "infobip",
                             "mex10", "plugni", "yup", "envio sms", "send sms", "multi-supplier",
                             "message delivery", "entrega mensagem"],
            "supplier_management": ["supplier config", "supplier health", "rate limit",
                                     "priority routing", "lost list", "phone blocking"],
            "billing": ["credito", "credit", "billing", "fatura", "invoice", "pricing",
                         "plano", "plan", "pagamento", "payment", "saldo", "balance"],
            "campaign_execution": ["campanha sms", "sms campaign", "campaign wizard",
                                    "phone list", "lista telefone", "agendamento",
                                    "scheduling", "batch send", "envio massa"],
            "webhook_processing": ["webhook", "callback", "delivery status", "dlr",
                                    "status queue", "status update"],
            "blacklist_management": ["blacklist", "bloqueio", "block", "maturation",
                                      "cooling", "strike", "fraud", "fraude",
                                      "anti-fraud", "opt out", "complaint", "reclamacao"],
            "rest_api": ["api rest", "rest api", "endpoint", "multi-tenant",
                          "api key", "portal cliente", "portal api"],
            "rabbitmq": ["rabbitmq", "fila", "queue", "consumer", "producer",
                          "message broker", "amqp"],
        }
        for cap, keywords in mapping.items():
            if any(kw in text_lower for kw in keywords):
                caps.append(cap)
        return caps or ["llm_inference"]
