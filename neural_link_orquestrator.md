╭───────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ Plan to implement                                                                                     │
│                                                                                                       │
│ Neural Link Orchestrator - Plano de Implementacao                                                     │
│                                                                                                       │
│ Contexto                                                                                              │
│                                                                                                       │
│ O projeto mcp-engine-service possui uma infraestrutura rica mas fragmentada: ChromaDB para vetores,      │
│ TF-IDF manual para grimoire, RAG baseado em keywords no automation_hub, 4 agentes de dominio, 3       │
│ operadores LLM, sistema de auto-evolucao (Divine Inspiration), e automacao de interface. O          │
│ problema: esses sistemas nao se comunicam, nao aprendem entre si, e nao tem uma camada de             │
│ orquestracao inteligente. O objetivo e criar um Neural Link - uma camada de orquestracao com Neo4j    │
│ como grafo de conhecimento, RAG hibrido, e feedback loop que transforma cada interacao em             │
│ aprendizado.                                                                                          │
│                                                                                                       │
│ ---                                                                                                   │
│ Fase 1: Neo4j Foundation + Schema + Migracao                                                          │
│                                                                                                       │
│ Objetivo                                                                                              │
│                                                                                                       │
│ Subir Neo4j, criar schema do grafo, migrar dados existentes do ChromaDB.                              │
│                                                                                                       │
│ Arquivos a criar                                                                                      │
│                                                                                                       │
│ src/neural_link/__init__.py                                                                           │
│ src/neural_link/config.py                  -- NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD do .env           │
│ src/neural_link/graph/__init__.py                                                                     │
│ src/neural_link/graph/manager.py           -- GraphManager: wrapper thread-safe do driver Neo4j       │
│ src/neural_link/graph/schema.py            -- Criacao de constraints, indexes, fulltext indexes       │
│ src/neural_link/graph/migrations.py        -- Migra chunks do ChromaDB para nodes no grafo            │
│ src/neural_link/graph/queries.py           -- Cypher query templates como constantes                  │
│                                                                                                       │
│ Arquivos a modificar                                                                                  │
│                                                                                                       │
│ - infra/docker-compose.yml -- Adicionar servico neo4j (5.16.0-community, portas 7474/7687, APOC       │
│ plugin)                                                                                               │
│ - .env -- Adicionar NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD                                             │
│                                                                                                       │
│ Schema Neo4j (Nodes)                                                                                  │
│                                                                                                       │
│ - Chunk: id, content, source_file, chunk_index, category, agent_specialty, created_at, access_count   │
│ - Concept: id, name, domain, description, confidence (0-1), source (extracted|manual|inferred)        │
│ - Agent: id, name, type (domain|operator|specialist), module_path, capabilities[], status,            │
│ success_rate                                                                                          │
│ - Skill: id, name, code, source (divine_inspiration|manual), target_error, success_count,             │
│ failure_count                                                                                         │
│ - Task: id, description, type (query|automation|repair|generation), status, priority, input/output    │
│ JSON                                                                                                  │
│ - Error: id, error_type, message, library, frequency, resolved (boolean)                              │
│ - Session: id, source (webhook|cli|api), started_at, task_count, success_count                        │
│                                                                                                       │
│ Schema Neo4j (Relationships)                                                                          │
│                                                                                                       │
│ - (:Chunk)-[:MENTIONS {confidence}]->(:Concept)                                                       │
│ - (:Chunk)-[:NEXT_CHUNK]->(:Chunk) e (:Chunk)-[:SAME_SOURCE]->(:Chunk)                                │
│ - (:Concept)-[:RELATED_TO {weight, type}]->(:Concept)                                                 │
│ - (:Agent)-[:SPECIALIZES_IN]->(:Concept) e (:Agent)-[:OWNS]->(:Skill)                                 │
│ - (:Task)-[:ASSIGNED_TO]->(:Agent) e (:Task)-[:USED_CHUNK {relevance}]->(:Chunk)                      │
│ - (:Error)-[:RESOLVED_BY]->(:Skill) e (:Error)-[:SIMILAR_TO]->(:Error)                                │
│                                                                                                       │
│ Migracao                                                                                              │
│                                                                                                       │
│ migrations.py le todos os chunks via vector_db.get_all(), cria nodes Chunk no Neo4j, e cria           │
│ relationships NEXT_CHUNK (por chunk_index dentro do mesmo source_file) e SAME_SOURCE. Tambem semeia   │
│ Agent nodes para os 4 agentes de dominio + 3 operadores.                                              │
│                                                                                                       │
│ Como testar                                                                                           │
│                                                                                                       │
│ docker compose -f infra/docker-compose.yml up neo4j -d                                                │
│ python -c "from src.neural_link.graph.schema import create_schema; create_schema()"                   │
│ python -c "from src.neural_link.graph.migrations import migrate_chromadb; migrate_chromadb()"         │
│ pytest src/neural_link/tests/test_graph_manager.py -v                                                 │
│                                                                                                       │
│ ---                                                                                                   │
│ Fase 2: RAG Hibrido (ChromaDB + Neo4j + TF-IDF)                                                       │
│                                                                                                       │
│ Objetivo                                                                                              │
│                                                                                                       │
│ Combinar os 3 motores de busca existentes com roteamento inteligente e reranking unificado.           │
│                                                                                                       │
│ Arquivos a criar                                                                                      │
│                                                                                                       │
│ src/neural_link/rag/__init__.py                                                                       │
│ src/neural_link/rag/hybrid_rag.py          -- HybridRAG: orquestra os 3 motores                       │
│ src/neural_link/rag/query_router.py        -- QueryRouter: classifica query e define pesos            │
│ src/neural_link/rag/result_merger.py       -- ResultMerger: normaliza scores + merge + boost          │
│ multi-engine                                                                                          │
│ src/neural_link/rag/graph_retriever.py     -- GraphRetriever: busca por conceitos, resolucao de       │
│ erros, expansao de contexto                                                                           │
│ src/neural_link/rag/concept_extractor.py   -- ConceptExtractor: extrai conceitos (rule-based + LLM    │
│ fallback)                                                                                             │
│                                                                                                       │
│ Arquivos a modificar                                                                                  │
│                                                                                                       │
│ - src/utils/vector_db.py -- Adicionar metodo search_with_scores() que retorna distancias/scores junto │
│  aos resultados                                                                                       │
│ - src/rag/rag_query_system.py -- Adicionar metodo query_with_scores() que retorna dicts normalizados  │
│                                                                                                       │
│ Arquitetura do Router                                                                                 │
│                                                                                                       │
│ ┌──────────┬────────────────────────┬──────────────────────────────────────────────────┐              │
│ │  Motor   │         Forca          │                   Quando usar                    │              │
│ ├──────────┼────────────────────────┼──────────────────────────────────────────────────┤              │
│ │ ChromaDB │ Similaridade semantica │ Perguntas abertas, conceituais                   │              │
│ ├──────────┼────────────────────────┼──────────────────────────────────────────────────┤              │
│ │ Neo4j    │ Traversal de relacoes  │ "Como X se relaciona com Y?", resolucao de erros │              │
│ ├──────────┼────────────────────────┼──────────────────────────────────────────────────┤              │
│ │ TF-IDF   │ Match exato de termos  │ Lookups de documentacao, procedimentos           │              │
│ └──────────┴────────────────────────┴──────────────────────────────────────────────────┘              │
│                                                                                                       │
│ Pesos default: chroma=0.4, neo4j=0.3, tfidf=0.3. O router ajusta baseado em sinais da query (palavras │
│  relacionais, tipos de erro, termos tecnicos).                                                        │
│                                                                                                       │
│ Result Merger                                                                                         │
│                                                                                                       │
│ 1. Normaliza scores de cada motor para [0, 1]                                                         │
│ 2. Aplica pesos do router                                                                             │
│ 3. Deduplica por ID do chunk                                                                          │
│ 4. Boost de +15% para itens encontrados por multiplos motores (cross-engine confirmation)             │
│                                                                                                       │
│ Concept Extractor                                                                                     │
│                                                                                                       │
│ - Primeiro tenta rule-based: match contra conceitos ja conhecidos no grafo                            │
│ - Se < 2 conceitos encontrados, faz LLM extraction via chat_completion() existente                    │
│ - Cache de conceitos para evitar chamadas LLM redundantes                                             │
│                                                                                                       │
│ Como testar                                                                                           │
│                                                                                                       │
│ python -c "                                                                                           │
│ from src.neural_link.rag.hybrid_rag import HybridRAG                                                  │
│ rag = HybridRAG.from_env()                                                                            │
│ results = rag.query('Como configurar Selenium com perfil Chrome?')                                    │
│ for r in results[:5]:                                                                                 │
│     print(f'{r[\"score\"]:.3f} | {r[\"content\"][:80]}...')                                           │
│ "                                                                                                     │
│                                                                                                       │
│ ---                                                                                                   │
│ Fase 3: Orchestrator Core                                                                             │
│                                                                                                       │
│ Objetivo                                                                                              │
│                                                                                                       │
│ Motor central de orquestracao: decomposicao de tarefas, selecao de agentes, pipeline de execucao.     │
│                                                                                                       │
│ Arquivos a criar                                                                                      │
│                                                                                                       │
│ src/neural_link/orchestrator/__init__.py                                                              │
│ src/neural_link/orchestrator/models.py     -- Pydantic: Task, TaskResult, TaskType, TaskStatus,       │
│ OrchestratorResponse                                                                                  │
│ src/neural_link/orchestrator/core.py       -- NeuralLinkOrchestrator: entry point principal           │
│ src/neural_link/orchestrator/task_decomposer.py  -- TaskDecomposer: decomposicao via Groq function    │
│ calling                                                                                               │
│ src/neural_link/orchestrator/agent_selector.py   -- AgentSelector: selecao baseada no grafo           │
│ src/neural_link/orchestrator/task_executor.py    -- TaskExecutor: invoca agentes + gerencia estado    │
│                                                                                                       │
│ Fluxo do Orchestrator                                                                                 │
│                                                                                                       │
│ request -> HybridRAG.query() -> TaskDecomposer.decompose() -> para cada task:                         │
│     AgentSelector.select() -> TaskExecutor.execute() -> resultado                                     │
│ -> sintetizar resposta final                                                                          │
│                                                                                                       │
│ TaskDecomposer                                                                                        │
│                                                                                                       │
│ Usa Groq function calling (pattern do groq_operator.py) com tool create_task para decompor requests   │
│ complexos em DAG de tasks.                                                                            │
│                                                                                                       │
│ AgentSelector                                                                                         │
│                                                                                                       │
│ Consulta Neo4j para encontrar o melhor agente baseado em:                                             │
│ - Capabilities match com required_capabilities da task                                                │
│ - Success rate historico do agente (rolling average)                                                  │
│ - Especializacao em conceitos relevantes                                                              │
│                                                                                                       │
│ Registry de agentes existentes:                                                                       │
│ - marketing_agent, social_media_agent, analytics_agent, ai_engineer_agent                             │
│ - groq_operator, gemini_operator, claude_operator                                                     │
│ - divine_inspiration, evolutionary_orchestrator                                                       │
│                                                                                                       │
│ TaskExecutor                                                                                          │
│                                                                                                       │
│ Wraps chamadas aos modulos existentes:                                                                │
│ - Agentes de dominio: ask_agent()                                                                     │
│ - Operadores: process_command()                                                                       │
│ - Repair: AgentFactory.handle_exception()                                                             │
│ - Automacao: autonomous_repair_loop()                                                                 │
│                                                                                                       │
│ Toda execucao registra Task node no grafo com status transitions.                                     │
│                                                                                                       │
│ Como testar                                                                                           │
│                                                                                                       │
│ python -c "                                                                                           │
│ from src.neural_link.orchestrator.core import NeuralLinkOrchestrator                                  │
│ orch = NeuralLinkOrchestrator.from_env()                                                              │
│ r = orch.process('Crie uma estrategia de marketing e gere prompts para cada post')                    │
│ print(r.answer)                                                                                       │
│ print(f'Tasks: {len(r.tasks)}, Success: {sum(1 for t in r.results if t.success)}/{len(r.results)}')   │
│ "                                                                                                     │
│                                                                                                       │
│ ---                                                                                                   │
│ Fase 4: Knowledge Evolution + Feedback Loop                                                           │
│                                                                                                       │
│ Objetivo                                                                                              │
│                                                                                                       │
│ Cada interacao enriquece automaticamente o grafo com conceitos, relacoes e scores de confianca.       │
│                                                                                                       │
│ Arquivos a criar                                                                                      │
│                                                                                                       │
│ src/neural_link/orchestrator/feedback.py   -- FeedbackLoop: registra outcomes, extrai conceitos,      │
│ atualiza scores                                                                                       │
│ src/neural_link/rag/concept_linker.py      -- ConceptLinker: descobre relacoes entre conceitos        │
│ src/neural_link/graph/enrichment.py        -- Batch enrichment operations                             │
│                                                                                                       │
│ Arquivos a modificar                                                                                  │
│                                                                                                       │
│ - src/agents/agent_factory.py -- Adicionar logging opcional no grafo (wrap em try/except ImportError  │
│ para nao quebrar nada)                                                                                │
│                                                                                                       │
│ Mecanismos de Evolucao                                                                                │
│                                                                                                       │
│ 1. Extracao de conceitos: Apos cada task, extrai conceitos da query + resposta                        │
│ 2. Linking de conceitos: Para cada conceito novo, busca relacionados no grafo via similaridade        │
│ 3. Confidence decay: Conceitos nao acessados por 30+ dias decaem 5% por semana                        │
│ 4. Error pattern learning: Agrupa erros similares com SIMILAR_TO edges; resolucoes propagam           │
│ 5. Agent performance tracking: Success rate como rolling average; flag se < 50%                       │
│                                                                                                       │
│ Seguranca                                                                                             │
│                                                                                                       │
│ Todo import de src.neural_link em codigo existente e wrapped em try/except ImportError. Se Neo4j nao  │
│ esta rodando, o sistema continua funcionando normalmente.                                             │
│                                                                                                       │
│ Como testar                                                                                           │
│                                                                                                       │
│ # Executa 4 queries e verifica crescimento do grafo                                                   │
│ python -c "                                                                                           │
│ from src.neural_link.orchestrator.core import NeuralLinkOrchestrator                                  │
│ orch = NeuralLinkOrchestrator.from_env()                                                              │
│ for q in ['O que e RAG?', 'Como usar ChromaDB?', 'Selenium best practices', 'Marketing digital']:     │
│     r = orch.process(q)                                                                               │
│     print(f'Nodes added: {r.knowledge_enrichment[\"nodes_added\"]}')                                  │
│ "                                                                                                     │
│                                                                                                       │
│ ---                                                                                                   │
│ Fase 5: Interface Unificada + Integracao Webhook                                                      │
│                                                                                                       │
│ Objetivo                                                                                              │
│                                                                                                       │
│ Ponto de entrada unico para Claude e webhook system.                                                  │
│                                                                                                       │
│ Arquivos a criar                                                                                      │
│                                                                                                       │
│ src/neural_link/api/__init__.py                                                                       │
│ src/neural_link/api/interface.py           -- UnifiedInterface: singleton,                            │
│ process/search/status/stats                                                                           │
│ src/neural_link/api/webhook_integration.py -- Integracao com FastAPI existente                        │
│                                                                                                       │
│ Arquivos a modificar                                                                                  │
│                                                                                                       │
│ - automation_hub/bridge/webhook_listener.py -- Adicionar endpoint POST /neural-link                   │
│                                                                                                       │
│ UnifiedInterface                                                                                      │
│                                                                                                       │
│ class UnifiedInterface:                                                                               │
│     def process(query, context) -> OrchestratorResponse  # Orquestracao completa                      │
│     def search(query, top_k) -> list[dict]               # RAG hibrido direto                         │
│     def get_agent_status() -> list[dict]                  # Status de todos os agentes                │
│     def get_graph_stats() -> dict                         # Estatisticas do grafo                     │
│                                                                                                       │
│ Como testar                                                                                           │
│                                                                                                       │
│ # Terminal 1: iniciar webhook                                                                         │
│ python automation_hub/bridge/webhook_listener.py 8765                                                 │
│                                                                                                       │
│ # Terminal 2: testar endpoint                                                                         │
│ curl -X POST http://localhost:8765/neural-link \                                                      │
│   -H "Content-Type: application/json" \                                                               │
│   -d '{"query": "Analise o funil de conversao e sugira melhorias"}'                                   │
│                                                                                                       │
│ ---                                                                                                   │
│ Fase 6 (Opcional): Dashboard + Monitoramento                                                          │
│                                                                                                       │
│ Adicionar tab "Neural Link" ao dashboard.py com:                                                      │
│ - Contagem de nodes por tipo                                                                          │
│ - Success rate dos agentes                                                                            │
│ - Tasks recentes e status                                                                             │
│ - Nuvem de conceitos mais conectados                                                                  │
│ - Cobertura de resolucao de erros                                                                     │
│                                                                                                       │
│ ---                                                                                                   │
│ Resumo de Impacto nos Arquivos Existentes                                                             │
│                                                                                                       │
│ ┌───────────────────────────────────────────┬───────────────────────────────────┬──────────────────┐  │
│ │                  Arquivo                  │              Mudanca              │      Risco       │  │
│ ├───────────────────────────────────────────┼───────────────────────────────────┼──────────────────┤  │
│ │ src/utils/vector_db.py                    │ +1 metodo search_with_scores()    │ Nenhum (aditivo) │  │
│ ├───────────────────────────────────────────┼───────────────────────────────────┼──────────────────┤  │
│ │ src/rag/rag_query_system.py               │ +1 metodo query_with_scores()     │ Nenhum (aditivo) │  │
│ ├───────────────────────────────────────────┼───────────────────────────────────┼──────────────────┤  │
│ │ src/agents/agent_factory.py               │ +5 linhas de logging opcional com │ Nenhum           │  │
│ │                                           │  try/except                       │ (graceful)       │  │
│ ├───────────────────────────────────────────┼───────────────────────────────────┼──────────────────┤  │
│ │ automation_hub/bridge/webhook_listener.py │ +1 endpoint /neural-link          │ Nenhum (aditivo) │  │
│ ├───────────────────────────────────────────┼───────────────────────────────────┼──────────────────┤  │
│ │ infra/docker-compose.yml                  │ +servico neo4j                    │ Nenhum (novo     │  │
│ │                                           │                                   │ servico)         │  │
│ ├───────────────────────────────────────────┼───────────────────────────────────┼──────────────────┤  │
│ │ .env                                      │ +3 variaveis NEO4J_*              │ Nenhum           │  │
│ └───────────────────────────────────────────┴───────────────────────────────────┴──────────────────┘  │
│                                                                                                       │
│ Nenhum arquivo existente tem codigo removido ou comportamento alterado.                               │
│                                                                                                       │
│ ---                                                                                                   │
│ Arquivos Criticos de Referencia                                                                       │
│                                                                                                       │
│ - src/utils/llm_client.py -- Todas as chamadas LLM passam por aqui (reusar chat_completion() e        │
│ KeyManager)                                                                                           │
│ - src/utils/vector_db.py -- Motor de busca vetorial principal (reusar get_all(), search(), count())   │
│ - src/agents/agent_factory.py -- Pattern de criacao/evolucao de agentes (template para orchestrator)  │
│ - automation_hub/agents/groq_operator.py -- Pattern de function calling (template para                │
│ TaskDecomposer)                                                                                       │
│ - src/rag/rag_query_system.py -- TF-IDF existente (reusar como motor de busca #3)                     │
╰───────────────────────────────────────────────────────────────────────────────────────────────────────