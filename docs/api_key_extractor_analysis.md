# Análise: Automação de Extração de API Keys

## Contexto Atual

O projeto possui um extrator web (`src/extractors/web_extractor.py`) que automatiza login e extração de API keys usando Selenium. O objetivo é expandir para suportar fluxos complexos (Google Groups → GitHub → Groq) e integração com Supabase.

## Pontos Fortes da Implementação Atual

1. **Arquitetura modular** - Funções separadas para driver, extração, salvamento
2. **Suporte a múltiplos modos** - Login automático e manual (OAuth)
3. **Padrões de validação** - Regex para diferentes tipos de API keys
4. **Configuração via .env** - Credenciais não hardcoded
5. **Webdriver-manager** - Instalação automática do ChromeDriver

## Gaps e Riscos Identificados

### 1. Tratamento de Erros Insuficiente

**Problema**: Falta tratamento específico para cenários comuns de falha.

**Riscos**:
- Timeout em páginas lentas
- Elementos não encontrados (seletores CSS dinâmicos)
- Captchas e verificações de segurança
- Rate limiting
- Mudanças no layout da página

**Impacto**: Falhas silenciosas ou mensagens genéricas que dificultam debug.

### 2. Fluxo Multi-Etapa Não Implementado

**Problema**: O código atual não suporta o fluxo Google Groups → GitHub → Groq.

**Requisitos não atendidos**:
- Criar/trocar email no Google Groups
- Usar esse email para criar conta GitHub
- Usar login GitHub para acessar Groq
- Orquestrar as 3 etapas em sequência

**Impacto**: Não é possível automatizar a criação gratuita de contas Groq.

### 3. Ausência de Retry e Resiliência

**Problema**: Sem mecanismo de retry para falhas temporárias.

**Cenários não cobertos**:
- Timeout de rede
- Elementos carregando lentamente
- Falhas intermitentes de API

**Impacto**: Baixa taxa de sucesso em ambientes instáveis.

### 4. Validação de API Keys Limitada

**Problema**: Apenas validação por regex, sem teste de conectividade.

**Riscos**:
- Extrair chave inválida ou expirada
- Salvar chave sem permissões adequadas
- Não detectar chaves revogadas

**Impacto**: Chaves salvas podem não funcionar.

### 5. Integração com Supabase Ausente

**Problema**: Não há código para salvar/gerenciar chaves no Supabase.

**Requisitos não atendidos**:
- Salvar chaves com metadata (plataforma, data, status)
- Testar conectividade antes de salvar
- Gerenciar múltiplas chaves por plataforma
- Rotação e expiração de chaves

**Impacto**: Não é possível centralizar gestão de chaves.

### 6. Logging e Observabilidade

**Problema**: Apenas prints, sem logging estruturado.

**Gaps**:
- Sem rastreamento de execução
- Difícil debug em produção
- Sem métricas de sucesso/falha

**Impacto**: Dificulta troubleshooting e monitoramento.

### 7. Segurança de Credenciais

**Problema**: Credenciais em .env sem criptografia.

**Riscos**:
- Exposição acidental em repositório
- Sem rotação automática
- Sem auditoria de acesso

**Impacto**: Risco de vazamento de credenciais.

### 8. Seletores CSS Hardcoded

**Problema**: Seletores podem quebrar com mudanças no site.

**Riscos**:
- Manutenção constante necessária
- Falhas após updates dos sites
- Sem fallback para seletores alternativos

**Impacto**: Código frágil e alto custo de manutenção.

## Melhorias Propostas

### Prioridade Alta (P0)

1. **Sistema de Retry com Backoff Exponencial**
   - Decorator `@retry` para funções críticas
   - Configurável por tipo de erro
   - Logging de tentativas

2. **Tratamento de Erros Robusto**
   - Try-catch específicos por tipo de erro
   - Mensagens de erro descritivas
   - Fallback para modo manual quando automático falha

3. **Validação de API Keys com Teste de Conectividade**
   - Fazer request de teste após extração
   - Validar permissões necessárias
   - Salvar apenas se validação passar

4. **Logging Estruturado**
   - Usar `logging` module do Python
   - Níveis: DEBUG, INFO, WARNING, ERROR
   - Logs em arquivo + console

### Prioridade Média (P1)

5. **Fluxo Multi-Etapa (Google Groups → GitHub → Groq)**
   - Classe `MultiStepFlow` para orquestrar
   - State machine para gerenciar etapas
   - Checkpoint/resume em caso de falha

6. **Integração com Supabase**
   - Tabela `api_keys` com schema definido
   - CRUD operations
   - Teste de conectividade antes de salvar
   - Metadata: plataforma, criado_em, testado_em, status

7. **Seletores Dinâmicos com Fallback**
   - Lista de seletores alternativos
   - Tentar múltiplos seletores em ordem
   - Configuração externa (JSON/YAML)

### Prioridade Baixa (P2)

8. **Detecção de Captcha**
   - Identificar quando captcha aparece
   - Pausar e notificar usuário
   - Integração com serviços de resolução (opcional)

9. **Dashboard de Monitoramento**
   - Visualizar chaves ativas
   - Status de validação
   - Histórico de extrações

10. **Criptografia de Credenciais**
    - Usar `cryptography` para .env
    - Chave mestra em variável de ambiente
    - Rotação automática

## Arquitetura Proposta

```
src/extractors/
├── web_extractor.py          # Código atual (refatorado)
├── multi_step_flow.py        # Orquestrador de fluxos complexos
├── validators.py             # Validação e teste de API keys
├── selectors.py              # Gerenciamento de seletores CSS
└── supabase_client.py        # Integração com Supabase

src/utils/
├── retry.py                  # Decorator de retry
├── logger.py                 # Logging estruturado
└── crypto.py                 # Criptografia de credenciais
```

## Próximos Passos

1. **Spike**: Prototipar fluxo Google Groups → GitHub → Groq (2-3 dias)
2. **Spec**: Documentar requisitos detalhados e casos de uso (1 dia)
3. **Implementação**: Desenvolver melhorias P0 e P1 (1-2 semanas)
4. **Testes**: Validar em ambiente real com múltiplas plataformas (3-5 dias)
5. **Integração Supabase**: Schema, CRUD, testes de conectividade (3-5 dias)
6. **Documentação**: Guias de uso e troubleshooting (2 dias)

## Estimativa de Esforço

- **Spike + Spec**: 3-4 dias
- **Desenvolvimento**: 2-3 semanas
- **Testes + Validação**: 1 semana
- **Total**: 4-5 semanas

## Riscos do Projeto

1. **Mudanças nos sites** - Seletores podem quebrar frequentemente
2. **Captchas** - Podem bloquear automação
3. **Rate limiting** - Limites de requisições podem atrasar testes
4. **Políticas de uso** - Alguns sites proíbem automação (verificar ToS)
