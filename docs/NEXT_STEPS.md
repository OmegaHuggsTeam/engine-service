# Próximos Passos: Sistema de Extração de API Keys

## Status Atual ✅

### Implementado

1. **Sistema de Retry** (`src/utils/retry.py`)
   - Decorator `@retry` com backoff exponencial
   - Configurável por tipo de erro
   - Logging de tentativas

2. **Logging Estruturado** (`src/utils/logger.py`)
   - Níveis: DEBUG, INFO, WARNING, ERROR
   - Saída para console + arquivo
   - Formatação customizável

3. **Validação de API Keys** (`src/extractors/validators.py`)
   - Validação de formato (regex)
   - Teste de conectividade (Groq, OpenAI)
   - Suporte a múltiplas plataformas

4. **Cliente Supabase** (`src/extractors/supabase_client.py`)
   - CRUD completo
   - Teste de conectividade
   - Gestão de status (active, expired, revoked)

5. **Web Extractor Refatorado** (`src/extractors/web_extractor.py`)
   - Tratamento de erros robusto
   - Integração com validators e Supabase
   - Logging detalhado
   - CLI melhorado

6. **Schema Supabase** (`db/supabase_schema.sql`)
   - Tabela `api_keys` com RLS
   - Índices para performance
   - Views e triggers

7. **Documentação**
   - Análise de gaps e riscos
   - Spec completa
   - Guia de uso
   - Script de testes

## Fase 1: Validação e Testes (3-5 dias)

### Objetivos
- Validar implementação atual
- Corrigir bugs encontrados
- Testar em ambiente real

### Tarefas

#### 1.1 Setup do Ambiente
- [ ] Instalar dependências: `pip install -r requirements.txt`
- [ ] Configurar `.env` com credenciais de teste
- [ ] Criar projeto Supabase e executar schema
- [ ] Configurar variáveis Supabase no `.env`

#### 1.2 Testes Unitários
- [ ] Executar: `python scripts/test_extractor.py`
- [ ] Corrigir falhas encontradas
- [ ] Adicionar testes para casos edge

#### 1.3 Testes de Integração
- [ ] Testar extração Groq (modo manual)
- [ ] Testar validação de chave
- [ ] Testar salvamento no Supabase
- [ ] Testar atualização de `.env`

#### 1.4 Testes E2E
- [ ] Fluxo completo: extração → validação → Supabase
- [ ] Testar com chave inválida (deve falhar)
- [ ] Testar com Supabase não configurado (deve funcionar sem Supabase)
- [ ] Testar retry em falhas temporárias

### Critérios de Sucesso
- Todos os testes unitários passam
- Extração de chave Groq funciona em <60s
- Validação detecta chaves inválidas
- Salvamento no Supabase funciona
- Logs são gerados corretamente

## Fase 2: Fluxo Multi-Etapa (5-7 dias)

### Objetivos
- Implementar fluxo Google Groups → GitHub → Groq
- Orquestrar múltiplas etapas com checkpoints
- Suportar resume em caso de falha

### Tarefas

#### 2.1 Pesquisa e Spike
- [ ] Investigar API/automação do Google Groups
- [ ] Testar criação de conta GitHub via Selenium
- [ ] Identificar seletores CSS necessários
- [ ] Documentar fluxo completo

#### 2.2 Implementação
- [ ] Criar `src/extractors/multi_step_flow.py`
- [ ] Implementar state machine para etapas
- [ ] Adicionar sistema de checkpoints
- [ ] Integrar com web_extractor

#### 2.3 Testes
- [ ] Testar cada etapa individualmente
- [ ] Testar fluxo completo
- [ ] Testar resume após falha
- [ ] Testar rollback

### Estrutura Proposta

```python
# src/extractors/multi_step_flow.py

class MultiStepFlow:
    """Orquestrador de fluxos multi-etapa."""

    def __init__(self, flow_name: str):
        self.flow_name = flow_name
        self.state = self._load_checkpoint()

    def execute(self):
        """Executa fluxo completo."""
        steps = [
            self._step_google_groups,
            self._step_github_signup,
            self._step_groq_login,
            self._step_extract_key,
        ]

        for i, step in enumerate(steps):
            if i < self.state.get("last_completed_step", -1):
                continue  # Skip completed steps

            try:
                result = step()
                self._save_checkpoint(i, result)
            except Exception as e:
                self._handle_error(i, e)
                raise

    def _step_google_groups(self):
        """Etapa 1: Obter email do Google Groups."""
        pass

    def _step_github_signup(self):
        """Etapa 2: Criar conta GitHub."""
        pass

    def _step_groq_login(self):
        """Etapa 3: Login no Groq via GitHub."""
        pass

    def _step_extract_key(self):
        """Etapa 4: Extrair API key."""
        pass
```

### Critérios de Sucesso
- Fluxo completo funciona em <5 minutos
- Checkpoints salvam estado corretamente
- Resume funciona após falha
- Logging detalhado de cada etapa

## Fase 3: Dashboard Streamlit (3-5 dias)

### Objetivos
- Interface visual para gestão de chaves
- Integração com dashboard existente
- Visualização de status e logs

### Tarefas

#### 3.1 Design
- [ ] Wireframe da nova aba "API Keys"
- [ ] Definir componentes (formulário, tabela, logs)
- [ ] Planejar integração com dashboard.py

#### 3.2 Implementação
- [ ] Adicionar aba "API Keys" no dashboard.py
- [ ] Formulário de extração
- [ ] Tabela de chaves ativas (Supabase)
- [ ] Botão de validação
- [ ] Logs de execução

#### 3.3 Testes
- [ ] Testar extração via dashboard
- [ ] Testar visualização de chaves
- [ ] Testar validação via botão
- [ ] Testar responsividade

### Estrutura Proposta

```python
# Adicionar ao dashboard.py

with tab_api_keys:
    st.header("Gestão de API Keys")

    # Seção 1: Extração
    with st.expander("Extrair Nova Chave", expanded=True):
        platform = st.selectbox("Plataforma", ["groq", "openai"])
        manual = st.checkbox("Modo Manual (OAuth)", value=True)

        if st.button("Extrair Chave"):
            with st.spinner("Extraindo..."):
                # Chamar web_extractor
                pass

    # Seção 2: Chaves Ativas
    st.subheader("Chaves Ativas")
    # Buscar do Supabase e exibir tabela

    # Seção 3: Validação
    if st.button("Testar Todas as Chaves"):
        # Chamar supabase_client.test_all_keys()
        pass

    # Seção 4: Logs
    with st.expander("Logs de Execução"):
        # Ler logs/extractor.log
        pass
```

### Critérios de Sucesso
- Dashboard funcional e intuitivo
- Extração via UI funciona
- Chaves são exibidas corretamente
- Validação via botão funciona

## Fase 4: Melhorias e Otimizações (3-5 dias)

### Objetivos
- Seletores CSS em arquivo externo
- Detecção de captcha
- Notificações
- Criptografia de credenciais

### Tarefas

#### 4.1 Seletores Externos
- [ ] Criar `config/selectors.yaml`
- [ ] Migrar seletores hardcoded
- [ ] Implementar fallback para múltiplos seletores
- [ ] Adicionar suporte a XPath

#### 4.2 Detecção de Captcha
- [ ] Identificar padrões de captcha
- [ ] Pausar execução quando detectado
- [ ] Notificar usuário
- [ ] Aguardar resolução manual

#### 4.3 Notificações
- [ ] Integração com email (SMTP)
- [ ] Integração com Slack (webhook)
- [ ] Notificar quando chaves expirarem
- [ ] Relatório diário de status

#### 4.4 Criptografia
- [ ] Implementar `src/utils/crypto.py`
- [ ] Criptografar `.env`
- [ ] Chave mestra em variável de ambiente
- [ ] Documentar processo

### Critérios de Sucesso
- Seletores configuráveis externamente
- Captcha detectado e tratado
- Notificações funcionando
- Credenciais criptografadas

## Fase 5: Documentação e Deploy (2-3 dias)

### Objetivos
- Documentação completa
- Vídeo demo
- Deploy em produção

### Tarefas

#### 5.1 Documentação
- [ ] README principal atualizado
- [ ] Guia de troubleshooting expandido
- [ ] Exemplos de uso
- [ ] FAQ

#### 5.2 Vídeo Demo
- [ ] Gravar extração simples
- [ ] Gravar fluxo multi-etapa
- [ ] Gravar uso do dashboard
- [ ] Publicar no YouTube/Loom

#### 5.3 Deploy
- [ ] Configurar ambiente de produção
- [ ] Migrar schema Supabase
- [ ] Configurar cron jobs
- [ ] Monitoramento e alertas

### Critérios de Sucesso
- Documentação completa e clara
- Vídeo demo publicado
- Sistema em produção
- Monitoramento ativo

## Estimativa Total

| Fase | Duração | Prioridade |
|------|---------|------------|
| Fase 1: Validação e Testes | 3-5 dias | P0 (Crítica) |
| Fase 2: Fluxo Multi-Etapa | 5-7 dias | P1 (Alta) |
| Fase 3: Dashboard Streamlit | 3-5 dias | P1 (Alta) |
| Fase 4: Melhorias | 3-5 dias | P2 (Média) |
| Fase 5: Documentação | 2-3 dias | P1 (Alta) |

**Total**: 16-25 dias (~4-5 semanas)

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Seletores CSS mudam | Alta | Médio | Seletores externos + fallback |
| Captchas bloqueiam | Alta | Alto | Detecção + modo manual |
| Supabase indisponível | Baixa | Médio | Fallback para salvamento local |
| Fluxo multi-etapa complexo | Média | Alto | Spike detalhado antes de implementar |

## Métricas de Sucesso

- Taxa de sucesso de extração: >90%
- Tempo médio de extração: <60s
- Cobertura de testes: >80%
- Uptime do sistema: >99%
- Chaves válidas após validação: 100%

## Próxima Ação Imediata

**Começar pela Fase 1: Validação e Testes**

1. Instalar dependências
2. Configurar `.env` e Supabase
3. Executar `python scripts/test_extractor.py`
4. Testar extração manual do Groq
5. Validar salvamento no Supabase

**Comando para começar:**

```bash
# 1. Instalar dependências
pip install -r requirements.txt

# 2. Configurar .env
copy .env.example .env
# Editar .env com suas credenciais

# 3. Executar testes
python scripts/test_extractor.py

# 4. Testar extração (modo visual para debug)
python -m src.extractors.web_extractor --platform groq --manual --no-headless

# 5. Listar chaves no Supabase (se configurado)
python -m src.extractors.supabase_client --list
```
