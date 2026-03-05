# Spec: Sistema de Extração e Gestão de API Keys

## Visão Geral

Sistema automatizado para extrair, validar e gerenciar API keys de múltiplas plataformas (Groq, OpenAI, etc.) com suporte a fluxos complexos de criação de contas e integração com Supabase para armazenamento centralizado.

## Objetivos

1. Automatizar extração de API keys com alta taxa de sucesso (>90%)
2. Suportar fluxo completo: Google Groups → GitHub → Groq
3. Validar chaves antes de salvar (teste de conectividade)
4. Centralizar gestão de chaves no Supabase
5. Fornecer observabilidade e debugging eficiente

## Requisitos Funcionais

### RF1: Extração de API Keys

**Descrição**: Extrair API keys de plataformas web via Selenium.

**Plataformas suportadas**:
- Groq (console.groq.com)
- OpenAI (platform.openai.com)
- Extensível para outras plataformas

**Modos de operação**:
- **Automático**: Login com usuário/senha
- **Manual**: Aguarda OAuth (Google/GitHub)
- **Headless**: Navegador invisível (padrão)
- **Visual**: Navegador visível (debug)

**Critérios de aceitação**:
- [ ] Extrair chave válida em <60s (modo automático)
- [ ] Suportar timeout configurável para modo manual
- [ ] Detectar e reportar falhas de login
- [ ] Salvar chave em `data/raw/api_key.txt`
- [ ] Atualizar `.env` automaticamente (opcional)

### RF2: Fluxo Multi-Etapa (Google Groups → GitHub → Groq)

**Descrição**: Orquestrar criação de conta Groq usando email temporário do Google Groups.

**Etapas**:
1. **Google Groups**: Criar/acessar grupo e obter email temporário
2. **GitHub**: Criar conta usando email do Google Groups
3. **Groq**: Fazer login via GitHub OAuth e extrair API key

**Critérios de aceitação**:
- [ ] Executar 3 etapas em sequência sem intervenção
- [ ] Salvar checkpoint após cada etapa (resume em falha)
- [ ] Timeout total configurável (padrão: 5 minutos)
- [ ] Logging detalhado de cada etapa
- [ ] Rollback em caso de falha crítica

### RF3: Validação de API Keys

**Descrição**: Testar conectividade e permissões antes de salvar.

**Validações**:
- **Formato**: Regex por plataforma (gsk_*, sk-proj-*, etc.)
- **Conectividade**: Request de teste à API
- **Permissões**: Verificar scopes necessários
- **Expiração**: Detectar chaves expiradas

**Critérios de aceitação**:
- [ ] Validar formato em <1s
- [ ] Testar conectividade em <5s
- [ ] Reportar erro específico se falhar
- [ ] Não salvar chaves inválidas
- [ ] Logging de resultado da validação

### RF4: Integração com Supabase

**Descrição**: Armazenar e gerenciar API keys no Supabase.

**Schema da tabela `api_keys`**:
```sql
CREATE TABLE api_keys (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  platform VARCHAR(50) NOT NULL,
  key_value TEXT NOT NULL,
  key_prefix VARCHAR(20),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  validated_at TIMESTAMPTZ,
  last_tested_at TIMESTAMPTZ,
  status VARCHAR(20) DEFAULT 'active',
  metadata JSONB,
  UNIQUE(platform, key_prefix)
);
```

**Operações**:
- **Create**: Salvar nova chave após validação
- **Read**: Buscar chaves por plataforma/status
- **Update**: Atualizar status/metadata
- **Delete**: Revogar chave (soft delete)
- **Test**: Testar conectividade de chave existente

**Critérios de aceitação**:
- [ ] CRUD completo implementado
- [ ] Teste de conectividade antes de salvar
- [ ] Metadata inclui: origem, IP, user-agent
- [ ] Suporte a múltiplas chaves por plataforma
- [ ] Query por status (active, expired, revoked)

### RF5: Sistema de Retry e Resiliência

**Descrição**: Retry automático para falhas temporárias.

**Configuração**:
- **Max retries**: 3 (padrão)
- **Backoff**: Exponencial (1s, 2s, 4s)
- **Erros retriáveis**: Timeout, ConnectionError, ElementNotFound
- **Erros não retriáveis**: InvalidCredentials, Captcha

**Critérios de aceitação**:
- [ ] Decorator `@retry` aplicável a qualquer função
- [ ] Configurável por tipo de erro
- [ ] Logging de cada tentativa
- [ ] Não retry em erros permanentes
- [ ] Timeout total respeitado

## Requisitos Não Funcionais

### RNF1: Performance

- Extração de chave: <60s (modo automático)
- Validação de chave: <5s
- Fluxo multi-etapa: <5 minutos
- Timeout configurável por operação

### RNF2: Confiabilidade

- Taxa de sucesso: >90% (sem captcha)
- Retry automático em falhas temporárias
- Checkpoint/resume em fluxos longos
- Graceful degradation (fallback para modo manual)

### RNF3: Segurança

- Credenciais apenas em .env (nunca hardcoded)
- Suporte a criptografia de .env (opcional)
- Logging sem expor credenciais/chaves
- Conexão HTTPS com Supabase
- Row Level Security (RLS) no Supabase

### RNF4: Observabilidade

- Logging estruturado (JSON)
- Níveis: DEBUG, INFO, WARNING, ERROR
- Logs em arquivo + console
- Métricas: taxa de sucesso, tempo médio, erros

### RNF5: Manutenibilidade

- Seletores CSS em arquivo de configuração
- Fallback para múltiplos seletores
- Código modular e testável
- Documentação inline (docstrings)

## Arquitetura

### Componentes

```
src/extractors/
├── web_extractor.py          # Extrator base (refatorado)
├── multi_step_flow.py        # Orquestrador de fluxos
├── validators.py             # Validação de API keys
├── selectors.py              # Gerenciamento de seletores
└── supabase_client.py        # Cliente Supabase

src/utils/
├── retry.py                  # Decorator de retry
├── logger.py                 # Logging estruturado
└── crypto.py                 # Criptografia (opcional)

config/
└── selectors.yaml            # Seletores CSS por plataforma
```

### Fluxo de Dados

```
1. Usuário → CLI/Dashboard
2. CLI → WebExtractor
3. WebExtractor → Selenium (navegação)
4. Selenium → Página web (extração)
5. WebExtractor → Validator (validação)
6. Validator → API da plataforma (teste)
7. WebExtractor → SupabaseClient (salvamento)
8. SupabaseClient → Supabase (persistência)
9. WebExtractor → .env (atualização local)
```

### State Machine (Fluxo Multi-Etapa)

```
[START] → [GOOGLE_GROUPS] → [GITHUB] → [GROQ] → [VALIDATE] → [SAVE] → [END]
           ↓                  ↓          ↓         ↓            ↓
        [RETRY]            [RETRY]    [RETRY]   [FAIL]      [FAIL]
           ↓                  ↓          ↓
        [MANUAL]           [MANUAL]   [MANUAL]
```

## Casos de Uso

### UC1: Extração Simples (Groq com OAuth)

**Ator**: Desenvolvedor

**Pré-condições**:
- Conta Groq existente
- Credenciais GitHub configuradas

**Fluxo**:
1. Executar: `python -m src.extractors.web_extractor --platform groq --manual`
2. Sistema abre navegador em console.groq.com/login
3. Usuário faz login via GitHub OAuth
4. Sistema aguarda 60s
5. Sistema navega para /keys
6. Sistema extrai chave do HTML
7. Sistema valida chave (request de teste)
8. Sistema salva em Supabase e .env
9. Sistema exibe: "Chave extraída e validada com sucesso"

**Pós-condições**:
- Chave salva em `data/raw/api_key.txt`
- `.env` atualizado com `GROQ_API_KEY=gsk_...`
- Registro criado no Supabase com status `active`

### UC2: Fluxo Completo (Google Groups → GitHub → Groq)

**Ator**: Desenvolvedor

**Pré-condições**:
- Acesso ao Google Groups
- Nenhuma conta GitHub/Groq

**Fluxo**:
1. Executar: `python -m src.extractors.multi_step_flow --flow groq_free`
2. **Etapa 1**: Sistema acessa Google Groups
3. Sistema cria/acessa grupo temporário
4. Sistema obtém email: `temp123@groups.google.com`
5. Sistema salva checkpoint
6. **Etapa 2**: Sistema acessa github.com/signup
7. Sistema preenche formulário com email temporário
8. Sistema aguarda verificação de email (manual)
9. Sistema completa cadastro GitHub
10. Sistema salva checkpoint
11. **Etapa 3**: Sistema acessa console.groq.com/login
12. Sistema clica em "Login with GitHub"
13. Sistema autoriza OAuth
14. Sistema navega para /keys
15. Sistema extrai chave
16. **Validação**: Sistema testa chave
17. **Salvamento**: Sistema salva em Supabase e .env
18. Sistema exibe: "Fluxo completo! Chave Groq criada e validada"

**Pós-condições**:
- Conta GitHub criada
- Conta Groq criada via GitHub
- Chave Groq extraída e validada
- Registros salvos no Supabase

### UC3: Validação de Chave Existente

**Ator**: Sistema (cron job)

**Pré-condições**:
- Chaves salvas no Supabase

**Fluxo**:
1. Sistema busca chaves com `last_tested_at` > 24h
2. Para cada chave:
   - Fazer request de teste à API
   - Atualizar `last_tested_at`
   - Se falhar: atualizar `status` para `expired`
3. Sistema envia relatório por email/Slack

**Pós-condições**:
- Chaves testadas
- Status atualizado
- Relatório enviado

## Interface

### CLI

```bash
# Extração simples (modo manual)
python -m src.extractors.web_extractor --platform groq --manual

# Extração automática (usuário/senha)
python -m src.extractors.web_extractor --platform groq --user user@example.com --password secret

# Fluxo completo
python -m src.extractors.multi_step_flow --flow groq_free

# Validar chave existente
python -m src.extractors.validators --platform groq --key gsk_xxx

# Testar todas as chaves no Supabase
python -m src.extractors.supabase_client --test-all
```

### Dashboard (Streamlit)

Nova aba: "API Keys"

**Seções**:
1. **Extração**: Formulário para extrair nova chave
2. **Chaves Ativas**: Tabela com chaves do Supabase
3. **Validação**: Botão para testar todas as chaves
4. **Logs**: Histórico de extrações

## Testes

### Testes Unitários

- `test_web_extractor.py`: Mocks do Selenium
- `test_validators.py`: Validação de formato e conectividade
- `test_supabase_client.py`: CRUD operations
- `test_retry.py`: Decorator de retry

### Testes de Integração

- `test_groq_extraction.py`: Extração real (modo manual)
- `test_multi_step_flow.py`: Fluxo completo (sandbox)
- `test_supabase_integration.py`: Salvamento e query

### Testes E2E

- Extração de chave Groq via GitHub OAuth
- Fluxo completo Google Groups → GitHub → Groq
- Validação de chave e salvamento no Supabase

## Configuração

### Variáveis de Ambiente (.env)

```bash
# Extração de API Keys
EXTRACTOR_URL=https://console.groq.com
EXTRACTOR_USER=user@example.com
EXTRACTOR_PASS=secret
EXTRACTOR_HEADLESS=true
EXTRACTOR_KEYS_URL=https://console.groq.com/keys

# Seletores CSS (opcional, fallback para config/selectors.yaml)
EXTRACTOR_USER_SELECTOR=input[name='email']
EXTRACTOR_PASS_SELECTOR=input[name='password']
EXTRACTOR_BTN_SELECTOR=button[type='submit']

# Retry
RETRY_MAX_ATTEMPTS=3
RETRY_BACKOFF_FACTOR=2

# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx
SUPABASE_TABLE=api_keys

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/extractor.log
```

### Seletores (config/selectors.yaml)

```yaml
groq:
  login_url: https://console.groq.com/login
  keys_url: https://console.groq.com/keys
  selectors:
    github_btn:
      - button[data-provider='github']
      - a[href*='github']
    api_key:
      - code[data-key]
      - pre.api-key
      - span.key-value

openai:
  login_url: https://platform.openai.com/login
  keys_url: https://platform.openai.com/api-keys
  selectors:
    email:
      - input[name='email']
      - input[type='email']
    password:
      - input[name='password']
      - input[type='password']
    submit:
      - button[type='submit']
      - input[type='submit']
```

## Dependências

```txt
# Já existentes
selenium>=4.15.0
webdriver-manager>=4.0.0
python-dotenv>=1.0.0

# Novas
supabase>=2.0.0           # Cliente Supabase
tenacity>=8.2.0           # Retry com backoff
pyyaml>=6.0.0             # Config de seletores
cryptography>=41.0.0      # Criptografia (opcional)
```

## Cronograma

### Fase 1: Spike (3 dias)

- [ ] Prototipar fluxo Google Groups → GitHub → Groq
- [ ] Identificar seletores CSS necessários
- [ ] Testar viabilidade de cada etapa
- [ ] Documentar descobertas e bloqueios

### Fase 2: Refatoração (5 dias)

- [ ] Implementar sistema de retry
- [ ] Adicionar logging estruturado
- [ ] Refatorar tratamento de erros
- [ ] Criar validators.py
- [ ] Testes unitários

### Fase 3: Multi-Step Flow (5 dias)

- [ ] Implementar multi_step_flow.py
- [ ] State machine com checkpoints
- [ ] Integração com web_extractor
- [ ] Testes de integração

### Fase 4: Integração Supabase (5 dias)

- [ ] Criar schema no Supabase
- [ ] Implementar supabase_client.py
- [ ] CRUD operations
- [ ] Teste de conectividade
- [ ] Testes E2E

### Fase 5: Dashboard (3 dias)

- [ ] Nova aba "API Keys" no Streamlit
- [ ] Formulário de extração
- [ ] Tabela de chaves ativas
- [ ] Botão de validação
- [ ] Logs de execução

### Fase 6: Documentação (2 dias)

- [ ] README com guias de uso
- [ ] Troubleshooting
- [ ] Exemplos de configuração
- [ ] Vídeo demo

**Total**: 23 dias (~5 semanas)

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Captchas bloqueiam automação | Alta | Alto | Fallback para modo manual, notificar usuário |
| Seletores CSS mudam | Média | Médio | Múltiplos seletores, config externa, testes frequentes |
| Rate limiting | Média | Baixo | Backoff exponencial, respeitar limites |
| Políticas de uso proíbem automação | Baixa | Alto | Verificar ToS, usar apenas para uso pessoal |
| Falhas no Supabase | Baixa | Médio | Fallback para salvamento local, retry |

## Métricas de Sucesso

- Taxa de sucesso de extração: >90%
- Tempo médio de extração: <60s
- Uptime do sistema: >99%
- Chaves válidas após validação: 100%
- Cobertura de testes: >80%

## Próximos Passos

1. **Aprovação da spec** - Review com stakeholders
2. **Setup do ambiente** - Supabase, config, dependências
3. **Spike** - Prototipar fluxo completo
4. **Desenvolvimento** - Seguir cronograma
5. **Testes** - Validação em ambiente real
6. **Deploy** - Integração com dashboard
7. **Monitoramento** - Métricas e alertas
