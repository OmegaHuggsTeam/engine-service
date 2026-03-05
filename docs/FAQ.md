# ❓ FAQ - Bunker Intelligence

Perguntas frequentes sobre o sistema de inteligência n8n.

## 🚀 Setup e Instalação

### Como faço o setup inicial?

Execute um único comando:
```bash
python scripts/setup_intelligence.py
```

Este script faz tudo automaticamente: ingestão, geração de conhecimento e verificação.

### Quanto tempo leva o setup completo?

Aproximadamente 5-10 minutos, dependendo da velocidade da internet e do hardware.

### Preciso configurar algo manualmente?

Apenas as variáveis de ambiente no `.env`:
- `GROQ_API_KEY` (obrigatório)
- `TELEGRAM_BOT_TOKEN` (obrigatório para bot)
- `GITHUB_TOKEN` (opcional, mas recomendado)

### O que fazer se o setup falhar?

1. Execute `python scripts/verify_intelligence.py` para diagnóstico
2. Verifique os logs em `logs/bunker.log`
3. Consulte a seção de Troubleshooting em `docs/INTELLIGENCE_SETUP.md`

## 📊 ChromaDB e Dados

### Quantos workflows são ingeridos?

Aproximadamente 4.300+ workflows do repositório zie619/zie619.github.io.

### Quanto espaço em disco é necessário?

- ChromaDB: ~500MB
- Knowledge files: ~5MB
- Generated workflows: ~1MB (cresce com uso)
- Total: ~500-600MB

### Como adiciono mais workflows ao sistema?

Use o comando Telegram:
```
/explain_workflow https://github.com/seu-usuario/seu-repo
```

Ou execute manualmente:
```bash
python -m src.extractors.github_ingestor https://github.com/seu-usuario/seu-repo
```

### Posso limpar o ChromaDB e recomeçar?

Sim, delete a pasta `db/chroma/` e execute novamente:
```bash
rm -rf db/chroma/
python scripts/setup_intelligence.py
```

### Como faço backup do ChromaDB?

Copie a pasta `db/chroma/` para um local seguro:
```bash
cp -r db/chroma/ backup/chroma_$(date +%Y%m%d)/
```

## 🤖 ComposerAgent

### Como o ComposerAgent funciona?

1. Recebe objetivo em linguagem natural
2. Busca templates relevantes no ChromaDB
3. Identifica componentes (trigger, processadores, output)
4. Compõe JSON n8n combinando templates
5. Valida e retorna workflow pronto

### Quais tipos de workflows posso criar?

Qualquer workflow que combine serviços presentes nos templates:
- Webhooks → Processamento → Notificações
- Agendamentos → Consultas → Ações
- Triggers → Transformações → Outputs

### O workflow gerado funciona imediatamente?

Quase sempre, mas pode precisar de ajustes:
- Configure credenciais necessárias
- Ajuste parâmetros específicos do seu caso
- Teste e valide o comportamento

### Como melhoro a qualidade dos workflows gerados?

1. Adicione mais templates via `/explain_workflow`
2. Use objetivos claros e específicos
3. Especifique serviços desejados no objetivo

### Posso customizar o workflow gerado?

Sim! O JSON gerado é um ponto de partida. Importe no n8n e customize conforme necessário.

## 📱 Telegram Bot

### Como inicio o bot Telegram?

```bash
python -m src.neural_link.telemetry.telegram_command_handler
```

### O bot não responde, o que fazer?

1. Verifique se `TELEGRAM_BOT_TOKEN` está configurado
2. Teste conectividade: `curl https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/getMe`
3. Verifique logs do handler

### Posso usar o sistema sem Telegram?

Sim! Use o script de demo:
```bash
python scripts/demo_composer.py
```

Ou via Python:
```python
from src.neural_link.agents.composer_agent import ComposerAgent
agent = ComposerAgent()
result = agent.compose_workflow("seu objetivo aqui")
```

### Quantos comandos o bot suporta?

Atualmente 2:
- `/explain_workflow <url>` - Explica workflows
- `/create_n8n <objetivo>` - Cria workflows

### Posso adicionar novos comandos?

Sim! Edite `src/neural_link/telemetry/telegram_command_handler.py` e adicione na função `_handle_command()`.

## 🔍 Busca e RAG

### Como funciona a busca híbrida?

O HybridRAG combina três motores:
1. **ChromaDB** - Busca semântica por embeddings
2. **Neo4j** - Busca por grafo de conceitos (Fase 3)
3. **TF-IDF** - Busca exata por keywords

### Por que alguns templates não aparecem na busca?

Possíveis razões:
- Template não está no ChromaDB (execute ingestão)
- Objetivo muito específico (reformule de forma mais genérica)
- Relevância baixa (templates existem mas não são relevantes)

### Como melhoro a relevância da busca?

1. Use termos específicos dos serviços (ex: "Telegram", "Webhook")
2. Especifique o fluxo desejado (ex: "receber → processar → enviar")
3. Adicione mais templates similares ao que procura

## 📁 Arquivos e Estrutura

### Onde ficam os workflows gerados?

Em `data/generated_workflows/` com timestamp no nome.

### Onde fica o conhecimento gerado?

- `vault/Knowledge/n8n_capabilities.md`
- `vault/Knowledge/n8n_recipes.md`
- `data/chunks/n8n_master_context.json`

### Posso deletar arquivos gerados?

Sim, workflows em `data/generated_workflows/` podem ser deletados sem afetar o sistema.

Não delete:
- `vault/Knowledge/` - Conhecimento estruturado
- `data/chunks/n8n_master_context.json` - Contexto mestre
- `db/chroma/` - Base de dados

### Como organizo workflows gerados?

Crie subpastas em `data/generated_workflows/`:
```bash
mkdir -p data/generated_workflows/telegram
mkdir -p data/generated_workflows/webhooks
```

## 🐛 Troubleshooting

### "Nenhum template relevante encontrado"

**Causa:** ChromaDB vazio ou sem templates para o objetivo.

**Solução:**
```bash
python scripts/mass_ingestion.py
```

### "ChromaDB não está acessível"

**Causa:** ChromaDB não foi inicializado ou está corrompido.

**Solução:**
```bash
# Reconstruir ChromaDB
rm -rf db/chroma/
python scripts/setup_intelligence.py
```

### "ComposerAgent falhou ao inicializar"

**Causa:** `n8n_master_context.json` não existe.

**Solução:**
```bash
python scripts/setup_intelligence.py --skip-ingestion
```

### "Workflow gerado não funciona no n8n"

**Causa:** Versões incompatíveis ou credenciais faltando.

**Solução:**
1. Verifique versões dos nodes no n8n
2. Configure credenciais necessárias
3. Ajuste parâmetros manualmente
4. Use como base e customize

### Erro: "GROQ_API_KEY não configurado"

**Solução:**
```bash
# Adicione ao .env
echo "GROQ_API_KEY=sua_chave_aqui" >> .env
```

## 🔧 Desenvolvimento

### Como adiciono um novo agente?

1. Crie arquivo em `src/neural_link/agents/seu_agent.py`
2. Herde de `BaseAgent`
3. Implemente método `execute()`
4. Adicione testes em `tests/`

### Como adiciono um novo comando Telegram?

Edite `src/neural_link/telemetry/telegram_command_handler.py`:

```python
def _handle_command(chat_id: int, command: str, args: str) -> None:
    if command == "seu_comando":
        # Sua lógica aqui
        _send_message(chat_id, "Resposta")
```

### Como contribuo com o projeto?

1. Fork o repositório
2. Crie branch para sua feature
3. Implemente e teste
4. Abra Pull Request

### Onde reporto bugs?

Crie issue no GitHub com:
- Descrição do problema
- Passos para reproduzir
- Logs relevantes
- Ambiente (OS, Python version)

## 📈 Performance

### Quanto tempo leva para criar um workflow?

Tipicamente 2-5 segundos, dependendo da complexidade.

### Quantos workflows posso criar por dia?

Sem limite! O sistema é stateless e não tem rate limiting.

### O sistema consome muita memória?

Uso típico:
- ChromaDB: ~200MB RAM
- ComposerAgent: ~100MB RAM
- Total: ~300-400MB RAM

### Como otimizo a performance?

1. Use SSD para ChromaDB
2. Aumente RAM disponível
3. Use cache de embeddings (já implementado)

## 🔐 Segurança

### Minhas chaves de API estão seguras?

Sim, desde que:
- `.env` não seja commitado no Git (já está no `.gitignore`)
- Permissões do arquivo sejam restritas: `chmod 600 .env`

### Posso usar em produção?

Sim, mas recomendamos:
- Usar Docker (Fase 2)
- Configurar backups automáticos
- Monitorar logs e métricas
- Implementar rate limiting no bot

### Como rotaciono secrets?

1. Gere novas chaves nas plataformas
2. Atualize `.env`
3. Reinicie o bot

## 🌐 Integração

### Posso integrar com outros sistemas?

Sim! O ComposerAgent pode ser usado via:
- API REST (implemente endpoint)
- Python SDK (importe diretamente)
- Telegram Bot (já implementado)
- CLI (use `demo_composer.py`)

### Como integro com CI/CD?

```yaml
# .github/workflows/generate-workflow.yml
- name: Generate n8n workflow
  run: |
    python scripts/demo_composer.py --objective "seu objetivo"
```

### Posso usar com outros LLMs além do Groq?

Sim! Edite `src/neural_link/agents/composer_agent.py` e configure o LLM desejado.

## 📚 Aprendizado

### Onde aprendo mais sobre n8n?

- [Documentação oficial n8n](https://docs.n8n.io/)
- [Repositório zie619](https://github.com/zie619/zie619.github.io)
- `vault/Knowledge/n8n_recipes.md` (exemplos práticos)

### Como entendo melhor o sistema?

1. Leia `docs/INTELLIGENCE_SETUP.md`
2. Execute `python scripts/demo_composer.py`
3. Explore `vault/Knowledge/`
4. Veja diagramas em `docs/WORKFLOW_DIAGRAMS.md`

### Há tutoriais em vídeo?

Ainda não, mas você pode:
1. Seguir o Quick Start
2. Usar o modo interativo do demo
3. Experimentar comandos Telegram

---

## 🆘 Ainda tem dúvidas?

1. Consulte a documentação completa em `docs/`
2. Verifique os logs em `logs/bunker.log`
3. Execute `python scripts/verify_intelligence.py --verbose`
4. Abra issue no GitHub com detalhes

---

**Última atualização:** 2026-03-03
**Autor:** Hugo (Bunker Intelligence Team)
