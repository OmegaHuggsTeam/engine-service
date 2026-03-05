# Integração Tailscale - Alexa + Groq

Use seu hostname Tailscale (`server.tail1f14ca.ts.net`) como conexão web para o IFTTT alcançar seu PC.

## Pré-requisitos

- Tailscale instalado e logado
- Plano Tailscale com **Funnel** (Personal Plus, Premium ou Enterprise)
- [Verificar Funnel](https://tailscale.com/kb/1223/funnel): Admin Console → Access Controls → habilitar Funnel

## Passo a passo

### 1. Inicie o webhook (Terminal 1)

```powershell
cd automation_hub
python bridge/webhook_listener.py 8765
```

### 2. Inicie o Groq operator (Terminal 2)

```powershell
cd automation_hub
python agents/groq_operator.py
```

### 3. Exponha via Tailscale Funnel (Terminal 3)

```powershell
cd automation_hub\scripts
.\tailscale_funnel.ps1
```

Ou direto:

```powershell
tailscale funnel localhost:8765
```

O comando exibirá a URL pública. Seu hostname: `https://server.tail1f14ca.ts.net`

**Para adicionar o webhook ao Funnel existente**, rode (com webhook na 8765):
```powershell
tailscale funnel --set-path=/webhook localhost:8765
```
Se der "listener already exists", o path pode precisar ser configurado no Admin Console do Tailscale.

### 4. Configure o IFTTT

**URL do Webhook:**
```
https://server.tail1f14ca.ts.net/webhook?key=haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6
```

**Ou com header:** `X-Webhook-Key: haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6`

**Method:** POST  
**Body:** `{"event":"modo_leitura","value1":"Modo leitura"}`

### 5. Para desligar o Funnel

```powershell
tailscale funnel localhost:8765 off
```

## Funnel em background

```powershell
tailscale funnel --bg localhost:8765
```

Persiste após reiniciar o PC (se Tailscale estiver configurado para iniciar com o sistema).

## Resumo do fluxo

```
Alexa → IFTTT → https://tail1f14ca.ts.net/webhook → seu PC (8765) → commands.json → Groq
```
