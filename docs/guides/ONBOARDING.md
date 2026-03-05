# Onboarding — Zero to First Agent

## 1. O que é Bunker Intelligence?

Bunker Intelligence é uma plataforma multi-agente para treinamento e avaliação de agentes de IA. Combina RAG (ChromaDB), grafo de conhecimento (Neo4j) e um pipeline de 5 camadas que otimiza custo e qualidade. O Sovereign Gateway expõe 47 endpoints REST e 5 WebSockets para integração com dashboards, webhooks e automações.

O sistema permite criar agentes especializados por domínio (CRM, Marketing, n8n), injetar conhecimento via chunks e conceitos no grafo, e avaliar respostas com a fórmula Correto 40% + Completo 30% + Qualidade 30%.

---

## 2. Pré-requisitos

- [ ] **Python 3.11+**
- [ ] **Docker** (para Neo4j)
- [ ] **Git**
- [ ] **Chave Groq** gratuita em [console.groq.com](https://console.groq.com)
- [ ] (Opcional) Node.js 20+ para o frontend

---

## 3. Setup Passo a Passo

```bash
# 1. Clone
git clone https://github.com/OmegaHuggsTeam/engine-service.git
cd engine-service

# 2. Ambiente virtual
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate   # Linux/Mac

# 3. Instalação
make install
# ou: pip install -r requirements.txt

# 4. Self-bootstrap (configura tudo)
python run_init.py

# 5. Docker (Neo4j)
make docker-up
# ou: docker compose up -d
```

---

## 4. Verificar se Funcionou

```bash
# Health check do Gateway
curl http://localhost:8766/api/v1/cluster/health

# Listar agentes
curl http://localhost:8766/api/v1/agents

# Teste de query
curl -X POST http://localhost:8766/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "O que é um workflow n8n?"}'
```

---

## 5. Primeira Interação com um Agente

1. Inicie o Gateway: `make gateway` (porta 8766)
2. Envie uma query via API ou use o frontend (`make gateway` + acesse a UI)
3. Leia a resposta e verifique os metadados (agent_used, confidence, sources)

---

## 6. Criar Seu Primeiro Agente Customizado

1. **Fork** o `TEMPLATE.md` em `docs/templates/`
2. **Registre** o agente no `AGENT_REGISTRY` (ver `COMO_TREINAR_AGENTES.md`)
3. **Escreva testes** em `src/neural_link/tests/` ou `tests/`
4. **Submeta um PR** com o novo agente

---

## 7. Entendendo o Score

- **Correto (40%)**: A resposta está factualmente correta?
- **Completo (30%)**: Cobre todos os aspectos da pergunta?
- **Qualidade (30%)**: Clareza, estrutura, sem alucinações?

Ver `COMO_AVALIAR_RESPOSTAS.md` para o rubric detalhado.

---

## 8. Ajuda

- **Issues**: Abra um issue no GitHub para bugs ou dúvidas
- **Discussions**: Use Discussions para ideias e perguntas gerais
- **Docs**: `docs/guides/` contém guias técnicos granulares
