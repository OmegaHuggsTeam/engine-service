# Plano MVP: Chunk Generator → Plataforma de Treinamento de Agentes

**Objetivo**: Transformar o projeto em uma plataforma de treinamento e acompanhamento de agentes, pronta para GitHub, CI/CD, SonarQube e distribuição entre amigos. Timeline: 5 anos de evolução em 5 meses.

**Status**: Planejamento (não executar ainda)

---

## Índice

1. [Visão Macro](#1-visão-macro)
2. [Estrutura de Branches e Workflow](#2-estrutura-de-branches-e-workflow)
3. [CI/CD e Integrações Automáticas](#3-cicd-e-integrações-automáticas)
4. [Onboarding e Documentação](#4-onboarding-e-documentação)
5. [MVP da Plataforma de Treinamento](#5-mvp-da-plataforma-de-treinamento)
6. [Requisitos e Bootstrap](#6-requisitos-e-bootstrap)
7. [SonarQube e Qualidade](#7-sonarqube-e-qualidade)
8. [Timeline Evolutiva (5 anos em 5 meses)](#8-timeline-evolutiva-5-anos-em-5-meses)
9. [Commits Semânticos e Organização](#9-commits-semânticos-e-organização)
10. [Rebase e Merge para Main](#10-rebase-e-merge-para-main)

---

## 1. Visão Macro

### O que o projeto se tornará

- **Plataforma de treinamento de agentes**: usuários (amigos) criam, treinam e avaliam seus próprios agentes
- **Visão macro liberada**: documentação e ferramentas para que qualquer pessoa entenda como criar agentes
- **Ambiente colaborativo**: branches por agente, avaliação de prompts, feedback entre usuários
- **Qualidade garantida**: testes automáticos, SonarQube, CI/CD como “equipe virtual” validando o código

### Princípios

- **JK (Joga no Kolho)**: acelerar 5 anos de roadmap em 5 meses
- **Validação contínua**: testes rodando em todo push/PR
- **Bootstrap validado**: `run_init.py` como porta de entrada única e confiável

---

## 2. Estrutura de Branches e Workflow

### Branches principais

| Branch | Propósito |
|--------|-----------|
| `main` | Código estável, validado, pronto para produção |
| `develop` | Integração contínua, base para features |
| `release/*` | Preparação de releases (ex: `release/v0.1.0`) |

### Branches por agente / feature

| Padrão | Exemplo | Uso |
|--------|---------|-----|
| `agent/<nome>` | `agent/marketing`, `agent/social-media` | Desenvolvimento de um agente específico |
| `prompt/<agente>-<versao>` | `prompt/marketing-v2` | Experimentação de prompts |
| `feature/<descricao>` | `feature/onboarding-flow` | Features da plataforma |
| `fix/<descricao>` | `fix/chroma-connection` | Correções |
| `docs/<descricao>` | `docs/onboarding-guide` | Documentação |

### Fluxo de trabalho

```
main ← develop ← agent/marketing
              ← agent/social-media
              ← feature/onboarding-flow
              ← prompt/marketing-v2
```

- Cada agente em sua branch
- PRs para `develop` com revisão (manual ou automática)
- Merge de `develop` → `main` após validação completa

---

## 3. CI/CD e Integrações Automáticas

### GitHub Actions (a criar)

| Workflow | Trigger | Ações |
|----------|---------|-------|
| `ci-tests.yml` | push, PR em qualquer branch | pytest, cobertura, lint (black, flake8, mypy) |
| `ci-frontend.yml` | push, PR em `frontend/` | npm run build, npm test |
| `ci-sonar.yml` | push em `develop`, `main` | Análise SonarQube |
| `ci-docker.yml` | push em `main` | Build e push de imagens Docker (opcional) |
| `ci-bootstrap.yml` | push em `main`, `develop` | Valida `run_init.py` em ambiente limpo |

### Integrações “como equipe”

- **Dependabot**: atualização automática de dependências
- **CodeQL**: análise de segurança
- **SonarQube**: qualidade, duplicação, cobertura, bugs
- **Status checks**: PRs só mergeáveis se todos os checks passarem

### Ambiente de testes

- Python 3.10, 3.11, 3.12 (matrix)
- Serviços mockados (ChromaDB, Neo4j, Groq) para CI
- Variáveis de ambiente via GitHub Secrets

---

## 4. Onboarding e Documentação

### Documentos a criar/atualizar

| Documento | Conteúdo |
|-----------|----------|
| `docs/ONBOARDING.md` | Passo a passo para novos usuários (clone, run_init, primeiro agente) |
| `docs/COMO_TREINAR_AGENTES.md` | Conceitos: prompts, RAG, avaliação de respostas |
| `docs/COMO_AVALIAR_RESPOSTAS.md` | Critérios de qualidade, exemplos de validação |
| `docs/VISAO_MACRO.md` | Arquitetura, agentes, fluxo de dados, roadmap |
| `docs/BOOTSTRAP_VALIDACAO.md` | O que o `run_init.py` faz e como validar |
| `README.md` (atualizar) | Links para onboarding, badges de CI, SonarQube |

### Fluxo de onboarding sugerido

1. Clone do repositório
2. Executar `python run_init.py`
3. Ler `docs/ONBOARDING.md`
4. Seguir tutorial “Criar seu primeiro agente”
5. Rodar testes locais: `pytest src/neural_link/tests/ -v`
6. Fazer primeiro PR (ex: ajuste de doc ou prompt)

---

## 5. MVP da Plataforma de Treinamento

### Funcionalidades mínimas

| Feature | Descrição | Prioridade |
|---------|-----------|------------|
| **Registro de agentes** | Cadastro de agentes customizados (nome, capabilities, prompts) | P0 |
| **Treinamento** | Interface para enviar exemplos e ajustar prompts | P0 |
| **Avaliação** | Marcar respostas como corretas/incorretas, feedback | P0 |
| **Dashboard** | Visão de agentes, métricas básicas (acurácia, uso) | P1 |
| **Comparação de prompts** | A/B entre versões de prompt | P2 |

### Componentes técnicos

- **API**: endpoints em `sovereign_gateway` ou novo serviço para CRUD de agentes
- **Storage**: persistência de agentes customizados (JSON, SQLite ou Neo4j)
- **Frontend**: páginas no Next.js para onboarding, treinamento e dashboard
- **Integração**: agentes customizados plugáveis no `AgentSelector`

### Validação do bootstrap

- Script `scripts/validate_bootstrap.py` que:
  - Cria ambiente limpo (venv temporário)
  - Executa `run_init.py`
  - Verifica se ChromaDB, Neo4j (ou mocks) respondem
  - Roda suite de testes
  - Gera relatório de sucesso/falha

---

## 6. Requisitos e Bootstrap

### Arquivos de requisitos

| Arquivo | Propósito |
|---------|-----------|
| `requirements.txt` | Dependências principais (já existe) |
| `requirements-dev.txt` | Dev: pytest, black, flake8, mypy, hypothesis, pytest-cov |
| `requirements-docker.txt` | Build Docker (já existe) |
| `pyproject.toml` | Metadados, configs de ferramentas (black, pytest, mypy) |

### Bootstrap (`run_init.py`)

- Manter como ponto de entrada único
- Adicionar etapa opcional: “Validar testes” (rodar pytest)
- Documentar todas as etapas em `docs/BOOTSTRAP_VALIDACAO.md`
- Garantir idempotência (rodar várias vezes sem quebrar)

---

## 7. SonarQube e Qualidade

### Configuração SonarQube

| Item | Configuração |
|------|--------------|
| **Projeto** | `chunk-generator` (ou nome do repo no GitHub) |
| **Linguagens** | Python, TypeScript/JavaScript |
| **Exclusões** | `node_modules/`, `.venv/`, `db/`, `data/` |
| **Cobertura** | Integrar com pytest-cov (formato Cobertura XML) |
| **Quality Gates** | Definir thresholds (ex: cobertura > 60%, 0 bugs críticos) |

### Arquivos a criar

- `sonar-project.properties` na raiz
- Configuração no GitHub Actions para enviar análise ao SonarCloud (ou SonarQube self-hosted)

### Exemplo `sonar-project.properties`

```properties
sonar.projectKey=chunk-generator
sonar.organization=seu-org
sonar.sources=src,frontend/src,automation_hub
sonar.exclusions=**/node_modules/**,**/.venv/**,**/db/**,**/data/**,**/__pycache__/**
sonar.python.coverage.reportPaths=coverage.xml
sonar.javascript.lcov.reportPaths=frontend/coverage/lcov.info
```

---

## 8. Timeline Evolutiva (5 anos em 5 meses)

### Mapeamento conceitual: 5 anos → 5 meses

| Ano (conceitual) | Mês | Foco |
|------------------|-----|------|
| **Ano 1** | Mês 1 | Fundação: CI/CD, testes automáticos, bootstrap validado, onboarding |
| **Ano 2** | Mês 2 | Plataforma: MVP de treinamento, registro de agentes, avaliação de respostas |
| **Ano 3** | Mês 3 | Qualidade: SonarQube, cobertura, refatoração, documentação completa |
| **Ano 4** | Mês 4 | Colaboração: branches por agente, avaliação de prompts, feedback entre usuários |
| **Ano 5** | Mês 5 | Escala: distribuição, melhorias contínuas, preparação para produção |

### Marcos por mês

**Mês 1 – Fundação**
- GitHub Actions: testes, lint, cobertura
- `pyproject.toml` e `conftest.py` na raiz
- Onboarding + docs de treinamento
- Bootstrap validado em CI

**Mês 2 – Plataforma**
- API de agentes customizados
- Interface de treinamento (Streamlit ou Next.js)
- Fluxo de avaliação de respostas

**Mês 3 – Qualidade**
- SonarQube integrado
- Cobertura > 60%
- Refatoração de código crítico

**Mês 4 – Colaboração**
- Workflow de branches por agente
- Sistema de avaliação de prompts (A/B)
- Documentação de contribuição atualizada

**Mês 5 – Escala**
- Distribuição para amigos
- Coleta de feedback
- Ajustes e preparação para evolução contínua

---

## 9. Commits Semânticos e Organização

### Padrão Conventional Commits

```
<tipo>(<escopo>): <descrição>

[corpo opcional]

[footer opcional]
```

### Tipos e escopos por timeline

| Tipo | Uso | Exemplo |
|------|-----|---------|
| `feat` | Nova funcionalidade | `feat(agent): adiciona MarketingAgent com RAG` |
| `fix` | Correção de bug | `fix(chroma): corrige conexão em ambiente CI` |
| `docs` | Documentação | `docs(onboarding): guia de primeiro agente` |
| `test` | Testes | `test(orchestrator): testes E2E do pipeline` |
| `ci` | CI/CD | `ci(gh-actions): workflow de testes Python` |
| `chore` | Manutenção | `chore(deps): atualiza pytest para 8.x` |
| `refactor` | Refatoração | `refactor(agent-selector): simplifica seleção` |

### Associação ao core e timeline

- **Escopos de core**: `orchestrator`, `agents`, `graph`, `rag`, `api`, `bootstrap`
- **Escopos de plataforma**: `training`, `evaluation`, `dashboard`, `onboarding`
- **Escopos de infra**: `ci`, `docker`, `sonar`, `k8s`

### Exemplos de mensagens por marco

```
# Mês 1 - Fundação
ci(gh-actions): adiciona workflow de testes e cobertura
docs(onboarding): guia completo para novos usuários
test(bootstrap): valida run_init em ambiente limpo

# Mês 2 - Plataforma
feat(training): API para registro de agentes customizados
feat(evaluation): endpoint para marcar resposta correta/incorreta

# Mês 3 - Qualidade
ci(sonar): integra análise SonarQube no pipeline
refactor(orchestrator): reduz complexidade ciclomática

# Mês 4 - Colaboração
feat(prompts): sistema de A/B para avaliação de prompts
docs(contributing): workflow de branches por agente

# Mês 5 - Escala
docs(distribution): guia para distribuição e feedback
chore(release): prepara v0.1.0 para main
```

---

## 10. Rebase e Merge para Main

### Pré-condições para merge em `main`

- [ ] Todos os testes passando (CI verde)
- [ ] SonarQube sem bugs críticos
- [ ] Cobertura mínima atingida
- [ ] Bootstrap validado
- [ ] Documentação de onboarding completa
- [ ] README atualizado com badges e links

### Processo de rebase

1. Garantir que `develop` está estável
2. Criar branch `release/v0.1.0` a partir de `develop`
3. Rodar testes finais e validação manual
4. Rebase interativo para organizar commits (squash se necessário)
5. Merge de `release/v0.1.0` em `main`
6. Tag `v0.1.0` em `main`
7. Merge de `main` de volta em `develop` (sync)

### Comandos sugeridos

```bash
# Após validação completa
git checkout develop
git pull origin develop
git checkout -b release/v0.1.0
# ... validações finais ...
git rebase -i main   # opcional: organizar commits
git checkout main
git merge --no-ff release/v0.1.0
git tag -a v0.1.0 -m "MVP: plataforma de treinamento de agentes"
git push origin main --tags
git checkout develop
git merge main
git push origin develop
```

---

## Resumo Executivo

| Área | Ação principal |
|------|----------------|
| **GitHub** | CI/CD com testes, lint, cobertura, SonarQube |
| **Branches** | `main`, `develop`, `agent/*`, `prompt/*`, `feature/*` |
| **Onboarding** | `ONBOARDING.md`, `COMO_TREINAR_AGENTES.md`, `COMO_AVALIAR_RESPOSTAS.md` |
| **MVP** | Registro de agentes, treinamento, avaliação, dashboard básico |
| **Bootstrap** | Validar `run_init.py` em CI e documentar |
| **SonarQube** | `sonar-project.properties`, integração no pipeline |
| **Timeline** | 5 meses = 5 anos conceituais (fundação → escala) |
| **Commits** | Conventional Commits com escopos alinhados ao core |
| **Merge** | Rebase em `release/*`, merge em `main`, tag `v0.1.0` |

---

**Próximo passo**: Validar este plano e, em seguida, executar fase por fase (Mês 1 primeiro).
