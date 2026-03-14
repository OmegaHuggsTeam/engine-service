# Kiro Cortex - Hub de Automação Cognitiva

Integra: **Nuvem** (Alexa/IFTTT) + **Local** (AHK/PS1) + **Inteligência** (Gemini + RAG).

## Estrutura

```
automation_hub/
├── agents/
│   ├── groq_operator.py     # Turbo: Llama 3 70B (recomendado, rapido)
│   ├── gemini_operator.py   # Gemini decide acao
│   ├── claude_operator.py  # Fallback: regras fixas
│   └── rag_engine.py       # Busca em /knowledge
├── bridge/
│   └── webhook_listener.py  # FastAPI: /webhook com autenticação
├── hardware/
│   ├── ifttt_client.ps1     # Luzes (ligar_quarto_hugo, desligar_quarto_hugo)
│   ├── focus_layout.ahk    # Janelas
│   ├── alert.ahk           # Alerta no monitor (erro)
│   ├── mouse_control.ahk   # Mouse/teclado
│   └── silence_notifications.ps1
├── knowledge/
│   ├── modo_leitura.txt       # Config: luz, apps, layout
│   └── preferencias_gerais.txt # Contexto de erro: vermelho + alert.ahk
├── config/
│   └── credentials.env
├── commands.json
└── requirements.txt
```

## Fluxo: "Alexa, ativar Modo Leitura"

1. **IFTTT** → POST `http://SEU_IP:8765/webhook` com `X-Webhook-Key` ou `?key=IFTTT_KEY`
2. **webhook_listener** → Autentica, extrai comando, enfileira
3. **claude_operator** → RAG em `/knowledge` → decide luz + apps + layout
4. **Execução**: Luz (PS1/IFTTT) + Apps (subprocess) + Layout (AHK) + Silêncio

## Luzes (IFTTT)

- `ligar_quarto_hugo` / `desligar_quarto_hugo`
- `modo_leitura`, `luz_branca`, `vermelho_piscante` (erro)

## Contexto de Erro

Se comando falhar ou IFTTT retornar erro: luz vermelho piscante + `alert.ahk` no monitor. Configure o evento `vermelho_piscante` no IFTTT.

## Como rodar

```powershell
cd automation_hub
pip install -r requirements.txt

# Terminal 1: Webhook (FastAPI)
python bridge/webhook_listener.py 8765

# Terminal 2: Orquestrador (escolha um)
python agents/groq_operator.py    # Turbo: Llama 3 70B (GROQ_API_KEY)
python agents/gemini_operator.py # Gemini
python agents/claude_operator.py # Regras fixas
```

**Groq**: `GROQ_API_KEY` no `.env`. Modelo: `llama3-70b-8192` (ou `GROQ_MODEL`).

**Teste direto**: `python agents/groq_operator.py test "Modo leitura"`

## IFTTT - Configurar Webhook

**Com Tailscale** (recomendado): `https://server.tail1f14ca.ts.net/webhook?key=...`
Ver [docs/TAILSCALE.md](docs/TAILSCALE.md) para setup completo.

**Sem Tailscale** (ngrok ou IP local): `http://SEU_IP:8765/webhook`
- **Method**: POST
- **Headers**: `X-Webhook-Key: haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6`
- **Body** (opcional): `{"event":"modo_leitura","value1":"Modo Leitura"}`

Ou use query: `http://SEU_IP:8765/webhook?key=haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6`

## RAG - Personalizar Modo Leitura

Edite `knowledge/modo_leitura.txt`:

```
luz: leitura
evento_ifttt: modo_leitura
apps:
  - "C:\caminho\para\seu\leitor.pdf"
layout: focus_layout.ahk
silenciar_notificacoes: true
```

## Logs

- `logs/brain.log` - Raciocinio do Gemini antes de cada acao
- `logs/operator.log` - Execucao de scripts

## Requisitos

- Python 3.x + FastAPI + uvicorn + google-generativeai + python-dotenv
- AutoHotkey v2
- PowerShell
