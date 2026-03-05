# 🗺️ Neural Link CRM - Mapa de Estrutura Documental

## Visão Geral da Reorganização

Este documento apresenta a nova arquitetura de documentação do projeto Neural Link CRM, seguindo princípios de Clean Architecture e separação de responsabilidades.

---

## 📁 Nova Estrutura de Pastas

```
docs/
├── architecture/           # Desenhos do sistema, fluxos e diagramas
│   ├── neural-link-graph.md
│   ├── k8s-deployment.md
│   ├── tailscale-network.md
│   ├── rag-hybrid-flow.md
│   └── agent-orchestration.md
│
├── api/                   # Especificações de endpoints e contratos
│   ├── gateway-openapi.yaml
│   ├── webhook-integration.md
│   ├── neural-link-api.md
│   └── authentication.md
│
├── product/              # Visão de produto e regras de negócio
│   ├── vision.md
│   ├── agent-taxonomy.md
│   ├── business-rules.md
│   ├── use-cases.md
│   └── roadmap.md
│
├── ops/                  # Manuais operacionais e manutenção
│   ├── deployment-guide.md
│   ├── kubectl-commands.md
│   ├── cluster-maintenance.md
│   ├── monitoring.md
│   └── troubleshooting.md
│
├── specs/                # Especificações técnicas detalhadas
│   ├── agents/          # Specs de cada agente
│   │   ├── TEMPLATE.md
│   │   ├── specialist-agent.md
│   │   ├── marketing-agent.md
│   │   └── ...
│   │
│   └── skills/          # Specs de skills reutilizáveis
│       ├── TEMPLATE.md
│       ├── social-media-scraper.md
│       ├── lead-scorer.md
│       └── ...
│
└── guides/              # Guias práticos e tutoriais
    ├── quickstart.md
    ├── development.md
    ├── testing.md
    └── contributing.md
```

---

## 🔄 Mapeamento de Arquivos Existentes

### Arquivos na Raiz (a serem movidos)

| Arquivo Atual | Novo Local | Categoria |
|--------------|------------|-----------|
| `README.md` | `docs/guides/quickstart.md` | Guia |
| `neural_link_orquestrator.md` | `docs/architecture/neural-link-graph.md` | Arquitetura |
| `INFRASTRUCTURE_STATUS.md` | `docs/ops/cluster-maintenance.md` | Ops |
| `README_INFRASTRUCTURE.md` | `docs/ops/deployment-guide.md` | Ops |
| `QUICKSTART_INTELLIGENCE.md` | `docs/guides/intelligence-setup.md` | Guia |
| `EVOLUTION.md` | `docs/product/roadmap.md` | Produto |
| `DOCKER.md` | `docs/ops/docker-guide.md` | Ops |
| `SELUM_QUICKSTART.md` | `docs/guides/selum-guide.md` | Guia |
| `SETUP_QUICK_START.md` | `docs/guides/development.md` | Guia |
| `TODO_CLAUDE.md` | `docs/product/backlog.md` | Produto |

### Arquivos em docs/ (a serem reorganizados)

| Arquivo Atual | Novo Local | Categoria |
|--------------|------------|-----------|
| `docs/EXECUTIVE_SUMMARY.md` | `docs/product/vision.md` | Produto |
| `docs/INFRASTRUCTURE_SETUP.md` | `docs/ops/deployment-guide.md` | Ops |
| `docs/INTELLIGENCE_SETUP.md` | `docs/guides/intelligence-setup.md` | Guia |
| `docs/WORKFLOW_DIAGRAMS.md` | `docs/architecture/workflow-flows.md` | Arquitetura |
| `docs/CALIBRATION_GUIDE.md` | `docs/guides/calibration.md` | Guia |
| `docs/SELUM_GUIDE.md` | `docs/guides/selum-guide.md` | Guia |
| `docs/api_key_extractor_*.md` | `docs/guides/api-key-extraction.md` | Guia |

---

## 🤖 Agentes Identificados (19 Total)

### Agentes de Domínio (4)
1. **MarketingAgent** - Estratégias de marketing e ROI
2. **SocialMediaAgent** - Conteúdo para redes sociais
3. **AnalyticsAgent** - Métricas e análise de dados
4. **AIEngineerAgent** - Automação e prompts

### Agentes Especializados (11)
5. **SpecialistAgent** - Coordenação e especialização
6. **WorkflowAgent** - Criação de workflows n8n
7. **FrontendAgent** - Desenvolvimento frontend
8. **DevOpsAgent** - Infraestrutura e deploy
9. **DataEngineeringAgent** - Pipelines de dados
10. **SecurityAuditAgent** - Auditoria de segurança
11. **TestingAgent** - Testes automatizados
12. **DocumentationAgent** - Documentação técnica
13. **NLPAgent** - Processamento de linguagem natural
14. **APIGatewayAgent** - Gestão de APIs
15. **CloudProvisioningAgent** - Provisionamento cloud

### Agentes Operadores (3)
16. **GroqOperator** - LLM Llama 3 70B (turbo)
17. **GeminiOperator** - LLM Gemini
18. **ClaudeOperator** - Regras fixas (fallback)

### Agentes de Sistema (1)
19. **ComputerUseAgent** - Automação de interface

---

## 🎯 Skills Prioritárias (Top 5)

### 1. SocialMediaScraper
- **Função**: Extração de dados de redes sociais
- **Agentes**: SocialMediaAgent, AnalyticsAgent
- **Tecnologias**: Selenium, BeautifulSoup, APIs

### 2. LeadScorer
- **Função**: Pontuação e qualificação de leads
- **Agentes**: MarketingAgent, AnalyticsAgent
- **Tecnologias**: ML, RAG, ChromaDB

### 3. WorkflowDeployer
- **Função**: Deploy automatizado de workflows n8n
- **Agentes**: WorkflowAgent, DevOpsAgent
- **Tecnologias**: n8n API, K8s, Docker

### 4. ContentGenerator
- **Função**: Geração de conteúdo otimizado
- **Agentes**: SocialMediaAgent, MarketingAgent
- **Tecnologias**: LLM, RAG, Templates

### 5. ErrorRecovery
- **Função**: Recuperação automática de erros
- **Agentes**: Todos (cross-cutting)
- **Tecnologias**: Divine Inspiration, Neo4j, Pattern Matching

---

## 📊 Estatísticas do Projeto

- **Total de Agentes**: 19
- **Agentes de Domínio**: 4
- **Agentes Especializados**: 11
- **Agentes Operadores**: 3
- **Agentes de Sistema**: 1
- **Skills Prioritárias**: 5
- **Arquivos a Reorganizar**: ~25
- **Novas Pastas**: 6 principais

---

## 🚀 Próximos Passos

1. ✅ Criar estrutura de pastas
2. ⏳ Mover arquivos existentes
3. ⏳ Criar specs de agentes
4. ⏳ Criar specs de skills
5. ⏳ Criar CONTRIBUTING.md
6. ⏳ Atualizar referências cruzadas

---

**Última Atualização**: 2026-03-03  
**Responsável**: Chief Documentation Officer (Kiro)
