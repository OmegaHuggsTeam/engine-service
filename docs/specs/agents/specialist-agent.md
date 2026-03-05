# SpecialistAgent - Especificação Técnica

## 📋 Metadados

| Campo | Valor |
|-------|-------|
| **Nome** | SpecialistAgent |
| **Tipo** | Specialist |
| **Versão** | 1.0.0 |
| **Status** | Active |
| **Módulo** | `src.neural_link.agents.specialist_agent` |
| **Criado em** | 2026-03-03 |
| **Última Atualização** | 2026-03-03 |

---

## 🎯 Função Core

O SpecialistAgent é um agente alimentado por conhecimento (chunks) que injeta automaticamente contexto relevante em cada tarefa. Ele funciona como um especialista que consulta sua base de conhecimento antes de responder, garantindo respostas precisas e fundamentadas em documentação real.

### Responsabilidades Primárias
- **Prompt Decoration**: Injeta automaticamente os top 5 chunks mais relevantes como "Contexto de Referência" antes de cada tarefa
- **Knowledge Loading**: Carrega e filtra chunks por categoria (chunk_type) de múltiplas fontes (ChromaDB, JSON files)
- **Creative Synthesis**: Propõe conexões inteligentes entre dois chunks (Trigger + Action) para criar automações
- **Pod Log Analysis**: Analisa logs de Pods Kubernetes em CrashLoopBackOff e sugere correções baseadas em padrões conhecidos
- **Workflow Adaptation**: Baixa, analisa e adapta workflows n8n, substituindo credenciais por variáveis de ambiente

### Responsabilidades Secundárias
- **Jitbit Macro Error Analysis**: Analisa erros de macros Jitbit (sanitização, delays, coordenadas) e sugere correções
- Busca híbrida de chunks (TF-IDF + keyword fallback)
- Extração de expressões n8n entre nodes
- Conversão de credenciais CamelCase para UPPER_SNAKE_CASE
- Formatação de respostas em Telegram Markdown

---

## 🧠 Skills Necessárias

### Skills Obrigatórias
1. **KnowledgeRetrieval**
   - Descrição: Busca e ranking de chunks relevantes usando TF-IDF ou keyword matching
   - Prioridade: Alta
   - Status: Implementada

2. **PromptEngineering**
   - Descrição: Decoração de prompts com contexto relevante antes da execução
   - Prioridade: Alta
   - Status: Implementada

3. **LLMInvocation**
   - Descrição: Invocação do LLM (Groq/Gemini/Claude) com prompts decorados
   - Prioridade: Alta
   - Status: Implementada

4. **K8sLogAnalysis**
   - Descrição: Análise de logs de Pods Kubernetes e identificação de padrões de erro
   - Prioridade: Alta
   - Status: Implementada

5. **WorkflowAdaptation**
   - Descrição: Download, parsing e adaptação de workflows n8n com substituição de credenciais
   - Prioridade: Alta
   - Status: Implementada

### Skills Opcionais
1. **CreativeSynthesis**
   - Descrição: Propõe conexões entre chunks para criar automações inovadoras
   - Prioridade: Média
   - Status: Implementada

2. **ExpressionExtraction**
   - Descrição: Extrai expressões n8n ({{ $('Node').item.json.field }}) de workflows
   - Prioridade: Média
   - Status: Implementada

---

## 📥 Input / Output

### Input Esperado

```python
# Modo Default
agent.execute(
    task="Como configurar Selenium com perfil Chrome?",
    chunk_type="selenium_docs",  # Opcional: carrega conhecimento
    query="selenium chrome profile",  # Opcional: override para busca
    model="llama3-70b-8192"  # Opcional: modelo LLM
)

# Modo Creative Synthesis
agent.execute(
    task="Propor automação",
    mode="creative_synthesis",
    chunk_a={"content": "Webhook recebe dados...", "source_file": "trigger.json"},
    chunk_b={"content": "Telegram envia mensagem...", "source_file": "action.json"}
)

# Análise de Logs K8s
agent.analyze_pod_logs(
    logs="Error: connection refused to neo4j:7687...",
    pod_name="neo4j-0",
    namespace="neural-link",
    chunk_type="k8s_error_patterns"
)

# Adaptação de Workflow n8n
agent.explain_and_adapt(
    url="https://raw.githubusercontent.com/user/repo/workflow.json"
)
```

### Output Esperado

```python
# Modo Default - String com resposta fundamentada
"""
## Contexto de Referência

[Referência 1 - selenium_docs.json]
Para usar perfil Chrome customizado, configure ChromeOptions...

---

## Resposta
Para configurar Selenium com perfil Chrome, siga estes passos:
1. Importe ChromeOptions
2. Configure user-data-dir...
"""

# Modo Creative Synthesis - String com proposta de automação
"""
Com base nos chunks fornecidos, proponha esta automação:

**Fluxo**: Webhook -> Processamento -> Telegram
1. Webhook recebe dados de formulário
2. Valida e enriquece com dados externos
3. Envia notificação formatada no Telegram

**Implementação sugerida**:
- Use n8n Webhook node para receber
- HTTP Request para enriquecer dados
- Telegram node para notificar
"""

# analyze_pod_logs - String com análise estruturada
"""
**Pod**: neo4j-0 (namespace: neural-link)

## Análise Requerida
1. **Identificar Padrão de Erro**: Conexão/Rede
   - connection refused to neo4j:7687

2. **Causa Raiz**: Service neo4j não está acessível ou Pod não iniciou

3. **Sugestão de Correção**:
   - Verificar se Service existe: `kubectl get svc neo4j -n neural-link`
   - Verificar logs do Pod neo4j: `kubectl logs neo4j-0 -n neural-link`
   - Verificar se porta 7687 está exposta no Service
"""

# explain_and_adapt - String em Telegram Markdown
"""
*Workflow de Notificação Telegram*
_Categoria: Communication_

*Objetivo do Fluxo*
Fluxo com 3 nodes operacionais.
Cadeia: `Webhook -> HTTP Request -> Telegram`

*Servicos Necessarios*
- Telegram
- Webhook

*Credenciais*
- `telegramApi` -> `TELEGRAM_API`

*Variaveis .env necessarias:*
```
TELEGRAM_API_ID=<seu-id-aqui>
TELEGRAM_API_NAME=<seu-nome-aqui>
```

*JSON Adaptado:*
```json
{
  "nodes": [
    {
      "type": "n8n-nodes-base.telegram",
      "credentials": {
        "telegramApi": {
          "id": "{{ $env.TELEGRAM_API_ID }}",
          "name": "{{ $env.TELEGRAM_API_NAME }}"
        }
      }
    }
  ]
}
```
"""
```

---

## 🔗 Contexto de Memória (Obsidian/Neo4j)

### Nodes Relacionados
- **Concepts**: 
  - Knowledge Retrieval
  - Prompt Engineering
  - Kubernetes Troubleshooting
  - n8n Workflow Automation
  - Credential Management
  - TF-IDF Ranking
  - Creative Synthesis

- **Skills**: 
  - KnowledgeRetrieval
  - PromptEngineering
  - LLMInvocation
  - K8sLogAnalysis
  - WorkflowAdaptation
  - CreativeSynthesis
  - ExpressionExtraction

- **Tasks**: 
  - Query answering with context injection
  - Pod log analysis and troubleshooting
  - Workflow download and adaptation
  - Creative automation proposals

### Relationships
- `(:SpecialistAgent)-[:SPECIALIZES_IN]->(:Concept {name: "Knowledge Retrieval"})`
- `(:SpecialistAgent)-[:SPECIALIZES_IN]->(:Concept {name: "Kubernetes Troubleshooting"})`
- `(:SpecialistAgent)-[:OWNS]->(:Skill {name: "KnowledgeRetrieval"})`
- `(:SpecialistAgent)-[:OWNS]->(:Skill {name: "K8sLogAnalysis"})`
- `(:SpecialistAgent)-[:EXECUTES]->(:Task {type: "query"})`
- `(:SpecialistAgent)-[:EXECUTES]->(:Task {type: "automation"})`

### Queries Cypher Relevantes

```cypher
// Buscar especialização do agente
MATCH (a:Agent {name: "SpecialistAgent"})-[:SPECIALIZES_IN]->(c:Concept)
RETURN c.name, c.domain, c.confidence
ORDER BY c.confidence DESC

// Buscar skills do agente
MATCH (a:Agent {name: "SpecialistAgent"})-[:OWNS]->(s:Skill)
RETURN s.name, s.success_count, s.failure_count, 
       (s.success_count * 1.0 / (s.success_count + s.failure_count)) as success_rate
ORDER BY success_rate DESC

// Buscar histórico de tasks de análise de logs
MATCH (a:Agent {name: "SpecialistAgent"})<-[:ASSIGNED_TO]-(t:Task {type: "k8s_log_analysis"})
WHERE t.created_at > datetime() - duration('P7D')
RETURN t.description, t.status, t.priority, t.output
ORDER BY t.created_at DESC
LIMIT 10

// Buscar chunks mais utilizados pelo agente
MATCH (a:Agent {name: "SpecialistAgent"})<-[:ASSIGNED_TO]-(t:Task)-[:USED_CHUNK]->(c:Chunk)
WITH c, count(t) as usage_count
RETURN c.id, c.source_file, c.category, usage_count
ORDER BY usage_count DESC
LIMIT 20
```

---

## 🔧 Dependências Técnicas

### Bibliotecas Python
```txt
# Core
httpx>=0.24.0              # HTTP client para download de workflows
scikit-learn>=1.3.0        # TF-IDF vectorization

# LLM Integration (via src.utils.llm_client)
groq>=0.4.0                # Groq API
google-generativeai>=0.3.0 # Gemini API

# Data Storage (via src.utils.vector_db)
chromadb>=0.4.0            # Vector database

# Optional (Neo4j integration)
neo4j>=5.0.0               # Graph database
```

### Serviços Externos
- **ChromaDB**: Busca vetorial de chunks (fallback para JSON se indisponível)
- **Groq API**: LLM primário (llama3-70b-8192)
- **Gemini API**: LLM alternativo
- **Neo4j**: Grafo de conhecimento (opcional, graceful degradation)

### Variáveis de Ambiente
```bash
# LLM APIs
GROQ_API_KEY=gsk_...
GEMINI_API_KEY=...
CLAUDE_API_KEY=...

# ChromaDB (opcional, usa JSON fallback)
CHROMA_HOST=localhost
CHROMA_PORT=8000

# Neo4j (opcional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=...
```

---

## 📊 Métricas de Performance

### KPIs
- **Success Rate**: > 95% (alta confiabilidade com context injection)
- **Response Time**: < 3s (p95) incluindo busca de chunks + LLM
- **Token Efficiency**: < 800 tokens/query (contexto focado com top 5 chunks)
- **Context Relevance**: > 0.85 (TF-IDF scoring)
- **Knowledge Coverage**: > 90% das queries encontram chunks relevantes

### Monitoramento
```python
# Exemplo de logging de métricas
{
  "agent": "SpecialistAgent",
  "timestamp": "2026-03-03T10:00:00Z",
  "metrics": {
    "success_rate": 0.97,
    "avg_response_time_ms": 2100,
    "avg_tokens_used": 650,
    "context_relevance": 0.88,
    "chunks_loaded": 1247,
    "chunk_type": "k8s_error_patterns"
  },
  "operation": "analyze_pod_logs"
}
```

---

## 🧪 Testes

### Casos de Teste Unitários

1. **Teste de Load Knowledge**
   - Input: `chunk_type="n8n_templates"`
   - Output esperado: Lista de chunks filtrados por categoria

2. **Teste de Prompt Decoration**
   - Input: `task="Como usar Selenium?"`, `knowledge=[chunks]`
   - Output esperado: Prompt com seção "Contexto de Referência" + top 5 chunks

3. **Teste de Creative Synthesis**
   - Input: `chunk_a={trigger}`, `chunk_b={action}`
   - Output esperado: Proposta de automação conectando A e B

4. **Teste de Credential Conversion**
   - Input: `"groqApi"`, `"googleSheetsOAuth2Api"`
   - Output esperado: `"GROQ_API"`, `"GOOGLE_SHEETS_OAUTH2_API"`

5. **Teste de Expression Extraction**
   - Input: JSON com `{{ $('Node').item.json.field }}`
   - Output esperado: `[{"node": "Node", "field": "field"}]`

### Casos de Teste de Integração

1. **Integração com ChromaDB**
   - Cenário: Buscar chunks por categoria via vector_db
   - Validação: Retorna chunks corretos ou fallback para JSON

2. **Integração com LLM (Groq)**
   - Cenário: Invocar chat_completion com prompt decorado
   - Validação: Resposta coerente baseada no contexto injetado

3. **Integração com n8n Workflows**
   - Cenário: Download e adaptação de workflow público
   - Validação: JSON adaptado com credenciais substituídas por $env

### Comandos de Teste
```bash
# Testes unitários
pytest tests/unit/test_specialist_agent.py -v

# Testes de integração
pytest tests/integration/test_specialist_agent_integration.py -v

# Teste manual - Load Knowledge
python -c "
from src.neural_link.agents.specialist_agent import SpecialistAgent
agent = SpecialistAgent()
chunks = agent.load_knowledge('k8s_error_patterns')
print(f'Loaded {len(chunks)} chunks')
"

# Teste manual - Analyze Pod Logs
python -c "
from src.neural_link.agents.specialist_agent import SpecialistAgent
agent = SpecialistAgent()
logs = 'Error: connection refused to neo4j:7687'
result = agent.analyze_pod_logs(logs, pod_name='neo4j-0', namespace='neural-link')
print(result)
"

# Teste manual - Explain and Adapt Workflow
python -c "
from src.neural_link.agents.specialist_agent import SpecialistAgent
agent = SpecialistAgent()
url = 'https://raw.githubusercontent.com/zie619/zie619.github.io/main/workflows/telegram_notification.json'
result = agent.explain_and_adapt(url)
print(result)
"
```

---

## 🔄 Integração com Outros Agentes

### Agentes Upstream (fornecem input)
- **NeuralLinkOrchestrator**: Delega tasks que requerem conhecimento especializado
- **TaskDecomposer**: Identifica tasks que precisam de context injection
- **AgentSelector**: Seleciona SpecialistAgent quando task requer conhecimento de domínio

### Agentes Downstream (recebem output)
- **TaskExecutor**: Recebe resultados e registra no grafo Neo4j
- **FeedbackLoop**: Extrai conceitos das respostas para enriquecer o grafo
- **DevOpsAgent**: Usa análises de logs para aplicar correções em K8s

### Padrões de Comunicação
- **Síncrono**: Chamada direta via método `execute()` ou `analyze_pod_logs()`
- **Assíncrono**: Tasks enfileiradas no Neo4j com status tracking
- **Event-driven**: Webhook triggers para `explain_and_adapt()`

---

## 📝 Exemplos de Uso

### Exemplo 1: Query com Context Injection
```python
from src.neural_link.agents.specialist_agent import SpecialistAgent

agent = SpecialistAgent()

# Carrega conhecimento de Selenium
agent.load_knowledge("selenium_docs")

# Executa query - automaticamente injeta top 5 chunks relevantes
result = agent.execute(
    task="Como configurar Selenium com perfil Chrome customizado?",
    model="llama3-70b-8192"
)

print(result)
# Output: Resposta detalhada baseada nos chunks de documentação Selenium
```

### Exemplo 2: Análise de Logs K8s
```python
from src.neural_link.agents.specialist_agent import SpecialistAgent

agent = SpecialistAgent()

# Logs de um Pod em CrashLoopBackOff
logs = """
Error: connect ECONNREFUSED 10.96.0.10:7687
    at TCPConnectWrap.afterConnect [as oncomplete] (net.js:1148:16)
Failed to connect to Neo4j at bolt://neo4j:7687
"""

# Analisa e sugere correção
analysis = agent.analyze_pod_logs(
    logs=logs,
    pod_name="neural-link-api-0",
    namespace="neural-link",
    chunk_type="k8s_error_patterns"
)

print(analysis)
# Output: Análise estruturada com padrão de erro, causa raiz e comandos kubectl
```

### Exemplo 3: Creative Synthesis
```python
from src.neural_link.agents.specialist_agent import SpecialistAgent

agent = SpecialistAgent()
agent.load_knowledge("n8n_templates")

# Dois chunks: Trigger e Action
chunk_a = {
    "content": "Webhook node recebe dados de formulário com campos: nome, email, telefone",
    "source_file": "webhook_trigger.json"
}

chunk_b = {
    "content": "Telegram node envia mensagem formatada para canal específico",
    "source_file": "telegram_action.json"
}

# Propõe automação conectando os dois
proposal = agent.execute(
    task="Criar automação para notificar equipe de vendas",
    mode="creative_synthesis",
    chunk_a=chunk_a,
    chunk_b=chunk_b
)

print(proposal)
# Output: Proposta de workflow n8n conectando webhook -> processamento -> telegram
```

### Exemplo 4: Adaptação de Workflow n8n
```python
from src.neural_link.agents.specialist_agent import SpecialistAgent

agent = SpecialistAgent()

# URL de workflow público no GitHub
url = "https://raw.githubusercontent.com/zie619/zie619.github.io/main/workflows/lead_scoring.json"

# Baixa, analisa e adapta
explanation = agent.explain_and_adapt(url)

print(explanation)
# Output: Markdown formatado com:
# - Objetivo do fluxo
# - Serviços necessários
# - Credenciais (convertidas para $env)
# - Variáveis .env
# - JSON adaptado
```

---

## 🐛 Troubleshooting

### Problema Comum 1: Chunks não encontrados
- **Sintoma**: `load_knowledge()` retorna lista vazia
- **Causa**: ChromaDB indisponível e arquivos JSON não existem em `data/chunks/`
- **Solução**: 
  1. Verificar se ChromaDB está rodando: `docker ps | grep chroma`
  2. Verificar se arquivos JSON existem: `ls data/chunks/*.json`
  3. Rodar pipeline de chunking: `python scripts/mass_ingestion.py`

### Problema Comum 2: LLM invocation failed
- **Sintoma**: `[Erro ao invocar LLM: ...]`
- **Causa**: API key inválida ou serviço indisponível
- **Solução**:
  1. Verificar `.env`: `echo $GROQ_API_KEY`
  2. Testar API manualmente: `curl https://api.groq.com/openai/v1/models -H "Authorization: Bearer $GROQ_API_KEY"`
  3. Verificar logs: `tail -f logs/orchestrator_run.json`

### Problema Comum 3: Workflow download timeout
- **Sintoma**: `explain_and_adapt()` falha com timeout
- **Causa**: URL inacessível ou rede lenta
- **Solução**:
  1. Testar URL manualmente: `curl -I <url>`
  2. Aumentar timeout: Modificar `httpx.Client(timeout=60)` em `specialist_agent.py`
  3. Usar arquivo local: Salvar JSON e usar `file://` URL

### Problema Comum 4: TF-IDF import error
- **Sintoma**: Fallback para keyword matching sempre ativo
- **Causa**: scikit-learn não instalado
- **Solução**:
  1. Instalar: `pip install scikit-learn>=1.3.0`
  2. Verificar: `python -c "from sklearn.feature_extraction.text import TfidfVectorizer"`

---

## 🗺️ Roadmap

### Versão Atual (1.0.0)
- ✅ Prompt decoration com top 5 chunks
- ✅ Load knowledge de ChromaDB + JSON fallback
- ✅ Creative synthesis entre chunks
- ✅ Pod log analysis com padrões K8s
- ✅ Workflow adaptation com credential substitution
- ✅ TF-IDF ranking com keyword fallback

### Próxima Versão (1.1.0)
- ⏳ Cache de chunks em memória para performance
- ⏳ Suporte a múltiplos chunk_types simultâneos
- ⏳ Ranking híbrido (TF-IDF + embeddings)
- ⏳ Feedback loop: registrar chunks utilizados no Neo4j
- ⏳ Métricas de relevância de contexto (precision@5)

### Futuro (2.0.0)
- 💡 Auto-learning: ajustar pesos de ranking baseado em feedback
- 💡 Multi-modal: suporte a imagens e diagramas em chunks
- 💡 Streaming responses: retornar chunks progressivamente
- 💡 Collaborative filtering: recomendar chunks baseado em histórico
- 💡 A/B testing: comparar diferentes estratégias de context injection

---

## 📚 Referências

- [BaseAgent Abstract Class](src/neural_link/agents/base_agent.py)
- [ChromaDB Integration](src/utils/vector_db.py)
- [LLM Client](src/utils/llm_client.py)
- [n8n Extractor](src/extractors/n8n_extractor.py)
- [Kubernetes Error Patterns](data/chunks/k8s_error_patterns.json)
- [Test Suite](tests/unit/test_specialist_agent.py)

---

**Mantido por**: Neural Link Team  
**Última Revisão**: 2026-03-03
