# Guia de Uso: Sistema de Extração de API Keys

## Visão Geral

Sistema automatizado para extrair, validar e gerenciar API keys de plataformas como Groq e OpenAI usando Selenium + Supabase.

## Instalação

### 1. Instalar Dependências

```bash
pip install -r requirements.txt
```

### 2. Configurar Variáveis de Ambiente

Copie `.env.example` para `.env` e configure:

```bash
copy .env.example .env  # Windows
```

Edite `.env`:

```bash
# Extração de API Keys
EXTRACTOR_URL=https://console.groq.com
EXTRACTOR_HEADLESS=true
EXTRACTOR_KEYS_URL=https://console.groq.com/keys

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/extractor.log

# Supabase (opcional)
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=eyJxxx
```

### 3. Configurar Supabase (Opcional)

Se quiser salvar chaves no Supabase:

1. Crie um projeto no [Supabase](https://supabase.com)
2. Execute o script SQL em `db/supabase_schema.sql` no SQL Editor
3. Configure `SUPABASE_URL` e `SUPABASE_KEY` no `.env`

## Uso

### Extração Simples (Modo Manual - OAuth)

Recomendado para Groq com login GitHub:

```bash
python -m src.extractors.web_extractor --platform groq --manual --no-headless
```

O navegador abrirá e você terá 60 segundos para fazer login via GitHub OAuth.

### Extração com Validação

Valida a chave antes de salvar:

```bash
python -m src.extractors.web_extractor --platform groq --manual
```

### Extração e Salvamento no Supabase

```bash
python -m src.extractors.web_extractor --platform groq --manual --supabase
```

### Validar Chave Existente

```bash
python -m src.extractors.validators --key gsk_xxx --platform groq
```

### Gerenciar Chaves no Supabase

Listar todas as chaves:

```bash
python -m src.extractors.supabase_client --list
```

Testar todas as chaves ativas:

```bash
python -m src.extractors.supabase_client --test-all
```

Filtrar por plataforma:

```bash
python -m src.extractors.supabase_client --list --platform groq
```

## Fluxos de Uso

### Fluxo 1: Extração Rápida (Groq)

1. Execute: `python -m src.extractors.web_extractor --platform groq --manual --no-headless`
2. Faça login via GitHub OAuth no navegador
3. Aguarde extração automática
4. Chave salva em `data/raw/api_key.txt` e `.env`

### Fluxo 2: Extração com Supabase

1. Configure Supabase no `.env`
2. Execute: `python -m src.extractors.web_extractor --platform groq --manual --supabase`
3. Chave validada e salva no Supabase
4. Verifique no dashboard do Supabase

### Fluxo 3: Validação Periódica

Configure um cron job para testar chaves diariamente:

```bash
# Windows Task Scheduler ou cron (Linux/Mac)
python -m src.extractors.supabase_client --test-all
```

## Parâmetros CLI

### web_extractor.py

```
--url              URL da plataforma (padrão: .env)
--manual           Modo manual (aguarda OAuth)
--no-headless      Mostrar navegador (útil para debug)
--wait             Segundos para login manual (padrão: 60)
--platform         Plataforma: groq, openai (padrão: groq)
--no-validate      Não validar chave após extração
--supabase         Salvar no Supabase
```

### validators.py

```
--key              API key a validar (obrigatório)
--platform         Plataforma: groq, openai, anthropic, generic
```

### supabase_client.py

```
--list             Listar chaves
--test-all         Testar todas as chaves ativas
--platform         Filtrar por plataforma
```

## Estrutura de Arquivos

```
src/extractors/
├── web_extractor.py          # Extrator principal
├── validators.py             # Validação de chaves
└── supabase_client.py        # Cliente Supabase

src/utils/
├── retry.py                  # Sistema de retry
└── logger.py                 # Logging estruturado

db/
└── supabase_schema.sql       # Schema do banco

data/raw/
└── api_key.txt               # Chave extraída

logs/
└── extractor.log             # Logs de execução
```

## Troubleshooting

### Erro: "FFmpeg não encontrado"

Instale FFmpeg e adicione ao PATH:
1. Baixe em https://ffmpeg.org/download.html
2. Extraia e adicione pasta `bin` ao PATH do Windows

### Erro: "Elemento não encontrado"

Os seletores CSS podem ter mudado. Configure seletores customizados no `.env`:

```bash
EXTRACTOR_USER_SELECTOR=input[name='email']
EXTRACTOR_PASS_SELECTOR=input[name='password']
EXTRACTOR_BTN_SELECTOR=button[type='submit']
```

### Erro: "Nenhuma API key encontrada"

1. Verifique se está na página correta (configure `EXTRACTOR_KEYS_URL`)
2. Aumente o tempo de espera: `--wait 120`
3. Use modo visual para debug: `--no-headless`

### Erro: "Chave inválida ou expirada"

A chave foi extraída mas falhou na validação. Possíveis causas:
- Chave sem permissões
- Rate limit excedido
- Chave revogada

### Erro: "Configure SUPABASE_URL e SUPABASE_KEY"

Configure as variáveis no `.env` ou não use `--supabase`.

## Logs

Logs são salvos em `logs/extractor.log` (configurável via `LOG_FILE`).

Níveis de log:
- `DEBUG`: Detalhes de execução
- `INFO`: Operações principais
- `WARNING`: Avisos não críticos
- `ERROR`: Erros que impedem execução

Altere o nível no `.env`:

```bash
LOG_LEVEL=DEBUG  # Para debug detalhado
```

## Segurança

1. **Nunca commite o .env** - Já está no `.gitignore`
2. **Use RLS no Supabase** - Row Level Security configurado no schema
3. **Rotacione chaves periodicamente** - Use `--test-all` para detectar expiradas
4. **Limite acesso ao Supabase** - Configure políticas de acesso adequadas

## Próximos Passos

- [ ] Implementar fluxo multi-etapa (Google Groups → GitHub → Groq)
- [ ] Adicionar suporte a mais plataformas (Anthropic, Cohere, etc.)
- [ ] Dashboard Streamlit para gestão visual
- [ ] Notificações por email/Slack quando chaves expirarem
- [ ] Seletores CSS em arquivo YAML externo

## Suporte

Para problemas ou dúvidas:
1. Verifique os logs em `logs/extractor.log`
2. Execute com `LOG_LEVEL=DEBUG` para mais detalhes
3. Use `--no-headless` para ver o navegador em ação
4. Consulte a documentação das plataformas para mudanças em seletores
