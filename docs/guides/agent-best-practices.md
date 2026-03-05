# Agent Best Practices Guide

## Agent Taxonomy

The system has **29 agents** organized in 4 categories:

### 1. Domain Agents (12)
Business-logic specialists bound to specific product domains.

| Agent | Domain | Key Capabilities |
|-------|--------|-----------------|
| marketing_agent | Marketing | Copywriting, campaign strategy, A/B testing |
| social_media_agent | Social | Social posting, engagement analysis, content calendar |
| analytics_agent | Analytics | ClickHouse, weekly KPIs, cohort analysis |
| ai_engineer_agent | AI/ML | Model evaluation, pipeline design, RAG architecture |
| crm_backend_agent | CRM Backend | Express, MongoDB, Kafka, campaigns, journeys |
| crm_frontend_agent | CRM Frontend | React, React Flow, Tailwind, dashboards |
| crm_data_agent | CRM Data | Segmentation, ClickHouse, behavioral analysis |
| crm_integration_agent | CRM Integration | Event collection, fingerprinting, rules engine |
| sendspeed_sms_agent | SendSpeed SMS | SMS delivery, supplier routing, RabbitMQ |
| sendspeed_admin_agent | SendSpeed Admin | Billing, fraud detection, blacklist |
| sendspeed_pipeline_agent | SendSpeed Pipeline | Message delivery, circuit breaker, DLQ |
| sendspeed_api_agent | SendSpeed API | REST API, multi-tenant, DDD, rate limiting |

### 2. Operator Agents (3)
LLM provider wrappers with fallback chains.

| Agent | Provider | Specialization |
|-------|----------|---------------|
| groq_operator | Groq | Fast inference, function calling |
| gemini_operator | Gemini | Multimodal, long context |
| claude_operator | Claude | Deep reasoning, code generation |

### 3. Specialist Agents (14)
Technical capability agents for cross-cutting concerns.

| Agent | Focus | Key Skills |
|-------|-------|-----------|
| divine_inspiration | Self-healing | Auto-repair, skill generation |
| evolutionary_orchestrator | Evolution | Self-improvement, adaptation |
| devops_agent | Infrastructure | Monitoring, health check, observability |
| computer_use_agent | UI Automation | Screenshot, typing, mouse control |
| cloud_provisioning_agent | Cloud/IaC | Terraform, Kubernetes |
| security_audit_agent | Security | Vulnerability, compliance, pentesting |
| testing_agent | QA | Unit/integration testing, automation |
| documentation_agent | Documentation | Technical writing, API docs |
| data_engineering_agent | Data | ETL, Spark, Airflow |
| frontend_agent | Frontend | React, CSS, accessibility |
| api_gateway_agent | API Gateway | Rate limiting, versioning |
| workflow_agent | Workflows | Task scheduling, cron, event-driven |
| nlp_agent | NLP | Text classification, sentiment, NER |
| specialist_agent | Knowledge | Chunks, creative synthesis, n8n templates |

## 5 Initialization Patterns

### Pattern 1: No-arg Constructor
Most specialists use direct instantiation.

```python
from src.agents.specialist_agent import SpecialistAgent
agent = SpecialistAgent()
result = agent.execute(query="Explain the RAG pipeline")
```

### Pattern 2: Dynamic Import via AGENT_REGISTRY
Domain agents use `agent_class` + `module_path` for lazy loading.

```python
from src.neural_link.orchestrator.agent_selector import AgentSelector

selector = AgentSelector(graph_manager)
agent = selector.select_agent(task)  # Returns best match by capabilities
```

Registry fields:
- `module_path`: Python import path (e.g., `src.neural_link.agents.crm_domain_agent`)
- `agent_class`: Class name (e.g., `CrmBackendAgent`)
- `invoke`: Method to call (e.g., `execute`)

### Pattern 3: LLM Fallback Chain
Operator agents implement provider fallback: Groq -> Gemini -> Claude.

```python
from src.utils.llm_client import LLMClient

client = LLMClient()  # Auto-selects provider from env
response = client.ask(prompt, model_tier="fast")  # 8b for triage
response = client.ask(prompt, model_tier="standard")  # 70b for generation
```

### Pattern 4: Exception-Driven (AgentFactory)
The AgentFactory handles failures by delegating to DivineInspiration.

```python
from src.agents.agent_factory import AgentFactory

factory = AgentFactory()
try:
    result = factory.execute_with_agent(agent_name, task)
except AgentError:
    result = factory.handle_exception(error, task)  # Auto-repair
```

### Pattern 5: Self-Healing Poll (SentinelBridge)
Active anomaly detection via Neo4j polling.

```python
from src.neural_link.services.sentinel_bridge import SentinelBridge

bridge = SentinelBridge(graph_manager, telemetry_hub)
bridge.start_polling(interval_seconds=60)  # Background thread
# Emits CRITICAL_ANOMALY events when quality drops
```

## Agent Creation Workflow

1. **Define capabilities** in AGENT_REGISTRY (`agent_selector.py` lines 18-280)
2. **Implement class** following the invoke pattern (execute/ask_agent/process_command)
3. **Add knowledge_categories** for RAG chunk injection
4. **Write spec** using `docs/specs/agents/TEMPLATE.md`
5. **Add tests** following `tests/test_{agent_name}.py` convention
6. **Register in schema** if agent needs Neo4j :Agent node

## Testing Strategy

### Unit Tests
- Test each capability independently
- Mock LLM calls (no real API in unit tests)
- Verify Pydantic model serialization
- Test error handling paths

### Integration Tests
- Test agent selection via AgentSelector
- Verify graph persistence (mock GraphManager)
- Test fallback chains end-to-end
- Verify telemetry recording

### Acceptance Tests
- UseCase-driven: each UC-* spec defines agent acceptance criteria
- ToolScorecard scoring: Correto 40% + Completo 30% + Qualidade 30%

## Common Pitfalls

1. **Missing knowledge_categories** — Agent won't receive RAG chunks
2. **Wrong invoke method** — Must match registry entry exactly
3. **No fallback** — Always handle LLM provider failures gracefully
4. **Unbounded context** — Use adaptive truncation (max_chars = 500 * score)
5. **No telemetry** — Wrap execute() with CostTracker profiling
