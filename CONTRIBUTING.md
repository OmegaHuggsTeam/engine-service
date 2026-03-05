# 🤝 Guia de Contribuição - Neural Link CRM

## Bem-vindo ao Time Neural Link!

Este documento estabelece as regras e padrões para desenvolvimento colaborativo no projeto Neural Link CRM. Seguir estas diretrizes garante que os agentes (Claude, Gemini, Groq) consigam ler e modificar o código uns dos outros sem conflitos.

---

## 📋 Índice

1. [Estrutura do Projeto](#estrutura-do-projeto)
2. [Convenções de Nomenclatura](#convenções-de-nomenclatura)
3. [Padrões de Código](#padrões-de-código)
4. [Workflow de Desenvolvimento](#workflow-de-desenvolvimento)
5. [Documentação](#documentação)
6. [Testes](#testes)
7. [Git e Commits](#git-e-commits)
8. [Revisão de Código](#revisão-de-código)

---

## 🏗️ Estrutura do Projeto

### Organização de Pastas

```
neural-link-crm/
├── .kiro/                      # Configurações Kiro (specs, agents)
│   ├── agents/                 # Definições de agentes customizados
│   └── specs/                  # Especificações de features
│
├── automation_hub/             # Hub de automação (Alexa, IFTTT, Hardware)
│   ├── agents/                 # Operadores LLM (Groq, Gemini, Claude)
│   ├── bridge/                 # Webhook listener e integrações
│   ├── hardware/               # Scripts AHK, PS1 para automação física
│   └── knowledge/              # Base de conhecimento para RAG
│
├── data/                       # Dados do sistema
│   ├── chunks/                 # Chunks processados (JSON)
│   ├── processed/              # Dados processados
│   ├── raw/                    # Dados brutos
│   └── workflows/              # Workflows n8n salvos
│
├── db/                         # Bancos de dados
│   ├── chroma/                 # ChromaDB (vector store)
│   └── supabase_schema.sql     # Schema Supabase
│
├── docs/                       # Documentação organizada
│   ├── architecture/           # Diagramas e arquitetura
│   ├── api/                    # Especificações de API
│   ├── product/                # Visão de produto
│   ├── ops/                    # Manuais operacionais
│   ├── specs/                  # Specs técnicas (agents, skills)
│   └── guides/                 # Guias práticos
│
├── frontend/                   # Frontend Next.js
│   ├── src/
│   │   ├── app/               # App Router (Next.js 13+)
│   │   ├── components/        # Componentes React
│   │   └── lib/               # Utilitários frontend
│   └── public/                # Assets estáticos
│
├── infra/                      # Infraestrutura
│   ├── k8s/                   # Manifests Kubernetes
│   ├── docker-compose.yml     # Compose local
│   └── Dockerfile             # Container principal
│
├── src/                        # Código fonte Python
│   ├── agents/                # Agentes de domínio
│   ├── extractors/            # Extratores de dados
│   ├── neural_link/           # Neural Link core
│   │   ├── agents/           # Agentes especializados
│   │   ├── graph/            # Neo4j graph manager
│   │   ├── orchestrator/     # Orquestrador central
│   │   └── rag/              # RAG híbrido
│   ├── processors/            # Processadores de dados
│   ├── rag/                   # Sistema RAG legado
│   ├── sentinela/             # Sentinela (Selenium automation)
│   └── utils/                 # Utilitários compartilhados
│
├── tests/                      # Testes
│   ├── unit/                  # Testes unitários
│   ├── integration/           # Testes de integração
│   ├── property/              # Property-based tests
│   └── sentinela/             # Testes Sentinela
│
├── scripts/                    # Scripts utilitários
├── tools/                      # Ferramentas CLI
└── vault/                      # Obsidian vault (knowledge base)
```

### Regras de Organização

1. **Não criar pastas soltas na raiz**: Use as pastas existentes
2. **Código Python**: Sempre em `src/` ou `automation_hub/`
3. **Documentação**: Sempre em `docs/` (nunca na raiz)
4. **Testes**: Sempre em `tests/` com estrutura espelhada
5. **Scripts temporários**: Use `temp/` (gitignored)

---

## 🏷️ Convenções de Nomenclatura

### Arquivos e Pastas

| Tipo | Convenção | Exemplo |
|------|-----------|---------|
| **Pastas** | `kebab-case` | `neural-link/`, `k8s-monitoring/` |
| **Python files** | `snake_case` | `specialist_agent.py`, `vector_db.py` |
| **Test files** | `test_*.py` | `test_specialist_agent.py` |
| **Config files** | `kebab-case` | `docker-compose.yml`, `.env.example` |
| **Markdown docs** | `UPPER_CASE` ou `kebab-case` | `README.md`, `contributing-guide.md` |

### Python

#### Classes
```python
# PascalCase para classes
class SpecialistAgent:
    pass

class NeuralLinkOrchestrator:
    pass
```

#### Funções e Métodos
```python
# snake_case para funções e métodos
def load_knowledge(chunk_type: str) -> list[dict]:
    pass

def _build_context_block(chunks: list[dict]) -> str:  # _ para privado
    pass
```

#### Variáveis
```python
# snake_case para variáveis
chunk_type = "k8s_error_patterns"
top_k_results = 5

# UPPER_CASE para constantes
TOP_K_CONTEXT = 5
CHUNKS_DIR = Path("data/chunks")
```

#### Módulos e Pacotes
```python
# snake_case para módulos
import specialist_agent
from neural_link.graph import manager
```

### TypeScript/JavaScript (Frontend)

#### Componentes React
```typescript
// PascalCase para componentes
export function AgentDashboard() {}
export const WorkflowCard = () => {}
```

#### Funções e Variáveis
```typescript
// camelCase para funções e variáveis
const fetchAgentStatus = async () => {}
const agentList = []
```

#### Tipos e Interfaces
```typescript
// PascalCase para tipos e interfaces
interface AgentConfig {
  name: string;
  capabilities: string[];
}

type TaskStatus = "pending" | "running" | "completed";
```

### Variáveis de Ambiente

```bash
# UPPER_SNAKE_CASE para env vars
GROQ_API_KEY=gsk_...
NEO4J_URI=bolt://localhost:7687
CHROMA_HOST=localhost
```

### Neo4j (Cypher)

```cypher
// PascalCase para nodes
(:Agent), (:Chunk), (:Concept)

// UPPER_CASE para relationships
(:Agent)-[:SPECIALIZES_IN]->(:Concept)
(:Task)-[:ASSIGNED_TO]->(:Agent)

// snake_case para propriedades
{name: "SpecialistAgent", success_rate: 0.95}
```

---

## 💻 Padrões de Código

### Python

#### Type Hints (Obrigatório)
```python
# ✅ BOM
def search_chunks(chunks: list[dict], query: str, top_k: int = 5) -> list[dict]:
    pass

# ❌ RUIM
def search_chunks(chunks, query, top_k=5):
    pass
```

#### Docstrings (Obrigatório para funções públicas)
```python
# ✅ BOM
def analyze_pod_logs(logs: str, pod_name: str = "", namespace: str = "") -> str:
    """
    Analisa logs de Pod em CrashLoopBackOff.
    
    Args:
        logs: Conteúdo dos logs do Pod
        pod_name: Nome do Pod (opcional)
        namespace: Namespace (opcional)
        
    Returns:
        Análise estruturada com causa raiz e sugestões
    """
    pass
```

#### Imports
```python
# Ordem: stdlib -> third-party -> local
import json
import logging
from pathlib import Path
from typing import Any, Optional

import httpx
from sklearn.feature_extraction.text import TfidfVectorizer

from .base_agent import BaseAgent
from src.utils.vector_db import get_by_category
```

#### Error Handling
```python
# ✅ BOM - Específico e com logging
try:
    result = risky_operation()
except ValueError as e:
    logger.error("Invalid value: %s", e)
    return default_value
except Exception as e:
    logger.exception("Unexpected error in risky_operation")
    raise

# ❌ RUIM - Genérico e silencioso
try:
    result = risky_operation()
except:
    pass
```

#### Logging
```python
import logging

logger = logging.getLogger(__name__)

# Níveis apropriados
logger.debug("Detailed info for debugging")
logger.info("General informational messages")
logger.warning("Warning messages")
logger.error("Error messages")
logger.exception("Error with full traceback")
```

### TypeScript/React

#### Componentes Funcionais
```typescript
// ✅ BOM
interface AgentCardProps {
  name: string;
  status: "active" | "inactive";
  onSelect: (name: string) => void;
}

export function AgentCard({ name, status, onSelect }: AgentCardProps) {
  return (
    <div onClick={() => onSelect(name)}>
      <h3>{name}</h3>
      <span>{status}</span>
    </div>
  );
}
```

#### Hooks Customizados
```typescript
// ✅ BOM - Prefixo "use"
function useAgentStatus(agentName: string) {
  const [status, setStatus] = useState<AgentStatus | null>(null);
  
  useEffect(() => {
    fetchAgentStatus(agentName).then(setStatus);
  }, [agentName]);
  
  return status;
}
```

---

## 🔄 Workflow de Desenvolvimento

### 1. Antes de Começar

```bash
# 1. Atualizar branch principal
git checkout main
git pull origin main

# 2. Criar branch de feature
git checkout -b feature/nome-da-feature

# 3. Verificar ambiente
python --version  # Python 3.10+
node --version    # Node 18+
```

### 2. Durante o Desenvolvimento

```bash
# 1. Fazer mudanças incrementais
# 2. Testar localmente
pytest tests/unit/test_meu_modulo.py -v

# 3. Verificar linting
ruff check src/
black src/ --check

# 4. Commit frequente
git add .
git commit -m "feat: adiciona funcionalidade X"
```

### 3. Antes de Submeter

```bash
# 1. Rodar todos os testes
pytest tests/ -v

# 2. Verificar cobertura
pytest --cov=src tests/

# 3. Atualizar documentação se necessário
# 4. Push para remote
git push origin feature/nome-da-feature
```

### 4. Code Review

1. Criar Pull Request no GitHub
2. Preencher template de PR
3. Aguardar review de pelo menos 1 pessoa
4. Aplicar feedback
5. Merge após aprovação

---

## 📚 Documentação

### Quando Documentar

- **Sempre**: Funções públicas, classes, módulos
- **Recomendado**: Funções privadas complexas
- **Opcional**: Código auto-explicativo

### Onde Documentar

| Tipo | Local |
|------|-------|
| **Arquitetura** | `docs/architecture/` |
| **API** | `docs/api/` + docstrings |
| **Guias** | `docs/guides/` |
| **Specs de Agentes** | `docs/specs/agents/` |
| **Specs de Skills** | `docs/specs/skills/` |
| **README de módulo** | Dentro da pasta do módulo |

### Formato

```markdown
# Título Claro

## Objetivo
[O que este documento explica]

## Conteúdo
[Conteúdo estruturado]

## Exemplos
[Exemplos práticos]

## Referências
[Links relacionados]
```

---

## 🧪 Testes

### Estrutura de Testes

```
tests/
├── unit/                    # Testes unitários (isolados)
│   ├── test_specialist_agent.py
│   └── test_vector_db.py
│
├── integration/             # Testes de integração (múltiplos componentes)
│   ├── test_orchestrator_integration.py
│   └── test_rag_pipeline.py
│
├── property/                # Property-based tests (Hypothesis)
│   └── test_chunk_search_property.py
│
└── conftest.py             # Fixtures compartilhadas
```

### Convenções de Testes

```python
# test_specialist_agent.py

import pytest
from src.neural_link.agents.specialist_agent import SpecialistAgent

class TestSpecialistAgent:
    """Testes para SpecialistAgent."""
    
    def test_load_knowledge_returns_list(self):
        """load_knowledge deve retornar lista de chunks."""
        agent = SpecialistAgent()
        chunks = agent.load_knowledge("test_category")
        assert isinstance(chunks, list)
    
    def test_execute_with_invalid_mode_raises_error(self):
        """execute com mode inválido deve levantar ValueError."""
        agent = SpecialistAgent()
        with pytest.raises(ValueError):
            agent.execute("task", mode="invalid")
```

### Cobertura Mínima

- **Código novo**: 80% de cobertura
- **Código crítico**: 90% de cobertura
- **Código legado**: Melhorar gradualmente

### Comandos

```bash
# Rodar todos os testes
pytest tests/ -v

# Rodar testes específicos
pytest tests/unit/test_specialist_agent.py -v

# Rodar com cobertura
pytest --cov=src tests/

# Rodar apenas testes rápidos
pytest -m "not slow" tests/
```

---

## 🔀 Git e Commits

### Branches

| Tipo | Formato | Exemplo |
|------|---------|---------|
| **Feature** | `feature/descricao` | `feature/specialist-agent` |
| **Bugfix** | `fix/descricao` | `fix/chunk-loading-error` |
| **Hotfix** | `hotfix/descricao` | `hotfix/critical-security-patch` |
| **Docs** | `docs/descricao` | `docs/update-contributing` |
| **Refactor** | `refactor/descricao` | `refactor/simplify-rag-pipeline` |

### Commits (Conventional Commits)

```bash
# Formato: <tipo>(<escopo>): <descrição>

# Tipos:
feat: nova funcionalidade
fix: correção de bug
docs: documentação
style: formatação (sem mudança de lógica)
refactor: refatoração
test: adicionar/modificar testes
chore: tarefas de manutenção

# Exemplos:
git commit -m "feat(specialist-agent): adiciona analyze_pod_logs"
git commit -m "fix(vector-db): corrige busca por categoria vazia"
git commit -m "docs(contributing): atualiza convenções de nomenclatura"
git commit -m "test(specialist-agent): adiciona testes de integração"
```

### Mensagens de Commit

```bash
# ✅ BOM
feat(specialist-agent): adiciona suporte a creative synthesis

Implementa modo creative_synthesis que conecta chunk A (Trigger)
e chunk B (Action) para propor automações.

- Adiciona parâmetro mode="creative_synthesis"
- Cria método _creative_synthesis()
- Adiciona testes unitários

Closes #123

# ❌ RUIM
fix stuff
update code
wip
```

---

## 👀 Revisão de Código

### Checklist do Revisor

- [ ] Código segue convenções de nomenclatura
- [ ] Type hints presentes (Python)
- [ ] Docstrings presentes para funções públicas
- [ ] Testes cobrem casos principais
- [ ] Sem código comentado ou debug prints
- [ ] Sem secrets ou credenciais hardcoded
- [ ] Documentação atualizada se necessário
- [ ] Commits seguem Conventional Commits

### Checklist do Autor

Antes de submeter PR:

- [ ] Todos os testes passam localmente
- [ ] Código formatado (black, ruff)
- [ ] Documentação atualizada
- [ ] Changelog atualizado (se aplicável)
- [ ] PR description clara e completa

---

## 🚀 Protocolo de Aceleração

### Time de Front (Frontend)

**Responsabilidades**:
- Componentes React em `frontend/src/components/`
- Páginas Next.js em `frontend/src/app/`
- Integração com APIs backend
- UI/UX e acessibilidade

**Stack**:
- Next.js 13+ (App Router)
- TypeScript
- Tailwind CSS
- React Query (data fetching)

**Padrões**:
- Componentes funcionais com hooks
- Props tipadas com interfaces
- Fetch via API routes (`/api/*`)
- Testes com Jest + React Testing Library

### Time de Back (Backend)

**Responsabilidades**:
- Agentes em `src/agents/` e `src/neural_link/agents/`
- APIs em `automation_hub/bridge/`
- Processamento de dados em `src/processors/`
- Integrações externas

**Stack**:
- Python 3.10+
- FastAPI (APIs)
- Neo4j (grafo)
- ChromaDB (vetores)
- Groq/Gemini (LLMs)

**Padrões**:
- Type hints obrigatórios
- Docstrings em funções públicas
- Logging estruturado
- Testes com pytest

### Comunicação Entre Times

**Contratos de API**:
- Documentar em `docs/api/` usando OpenAPI
- Versionar endpoints (`/api/v1/`)
- Validar com Pydantic (backend) e Zod (frontend)

**Exemplo**:
```yaml
# docs/api/agents-api.yaml
/api/v1/agents/{agent_name}/execute:
  post:
    summary: Executa tarefa em agente específico
    parameters:
      - name: agent_name
        in: path
        required: true
        schema:
          type: string
    requestBody:
      content:
        application/json:
          schema:
            type: object
            properties:
              task:
                type: string
              context:
                type: object
    responses:
      200:
        description: Tarefa executada com sucesso
```

---

## 🎯 Boas Práticas Gerais

### DRY (Don't Repeat Yourself)
```python
# ✅ BOM - Reutilizar código
def format_agent_response(data: dict) -> str:
    return json.dumps(data, indent=2)

# Usar em múltiplos lugares
response1 = format_agent_response(agent1_data)
response2 = format_agent_response(agent2_data)

# ❌ RUIM - Duplicar código
response1 = json.dumps(agent1_data, indent=2)
response2 = json.dumps(agent2_data, indent=2)
```

### KISS (Keep It Simple, Stupid)
```python
# ✅ BOM - Simples e direto
def is_valid_email(email: str) -> bool:
    return "@" in email and "." in email.split("@")[1]

# ❌ RUIM - Complexo desnecessariamente
def is_valid_email(email: str) -> bool:
    import re
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

### YAGNI (You Aren't Gonna Need It)
```python
# ✅ BOM - Implementar apenas o necessário
class Agent:
    def execute(self, task: str) -> str:
        return self._process(task)

# ❌ RUIM - Implementar features "por precaução"
class Agent:
    def execute(self, task: str) -> str:
        return self._process(task)
    
    def execute_async(self, task: str):  # Não usado ainda
        pass
    
    def execute_batch(self, tasks: list):  # Não usado ainda
        pass
```

---

## 📞 Contato e Suporte

### Dúvidas sobre Código
- Abrir issue no GitHub com label `question`
- Perguntar no canal #dev do Discord/Slack

### Reportar Bugs
- Abrir issue no GitHub com label `bug`
- Incluir: steps to reproduce, expected vs actual, logs

### Sugerir Features
- Abrir issue no GitHub com label `enhancement`
- Descrever: problema, solução proposta, alternativas

---

## 📜 Licença e Código de Conduta

- **Licença**: [MIT License](LICENSE)
- **Código de Conduta**: Seja respeitoso, colaborativo e construtivo

---

**Última Atualização**: 2026-03-03  
**Mantido por**: Neural Link Team

---

## 🎉 Agradecimentos

Obrigado por contribuir para o Neural Link CRM! Juntos estamos construindo um sistema de orquestração de agentes de classe mundial. 🚀
