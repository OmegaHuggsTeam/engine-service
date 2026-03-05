# Hub Hibrido - Groq + Tailscale + IFTTT

## Regra de Seguranca

**NUNCA exponha portas no roteador fisico.** Toda comunicacao externa passa pelo tunel Tailscale.

## Arquitetura

```
Alexa (voz) -> IFTTT -> Tailscale (100.x.y.z:8765) -> Webhook -> commands.json -> Groq -> Hardware
```

## Configuracao

### 1. .env (raiz do projeto)

```
GROQ_API_KEY=gsk_...
IFTTT_WEBHOOK_KEY=haB9jt-...   # Maker IFTTT para luz Positivo
GROQ_TAILSCALE_ACESS=tskey-... # Opcional
GROQ_TAILSCALE_AUTH_KEY=tskey-... # Opcional
```

### 2. Iniciar servicos

**Terminal 1 - Webhook (porta 8765)**
```powershell
cd automation_hub
python bridge/webhook_listener.py 8765
```
Exibe o IP Tailscale para configurar no IFTTT.

**Terminal 2 - Groq Operator**
```powershell
python agents/groq_operator.py
```

### 3. IFTTT Webhook

URL: `http://SEU_IP_TAILSCALE:8765/webhook?key=IFTTT_WEBHOOK_KEY`
Body: `{"event":"voice_command","value1":"Modo leitura"}`

O value1 e o comando de voz da Alexa, enviado direto ao Groq.

### 4. Comandos complexos

Ex: "Prepare o quarto para leitura e feche o VS Code"
-> Groq chama simultaneamente: ifttt_luz(leitura), ahk_script(focus_layout.ahk), fechar_app(Code)

## Teste

```powershell
python tests/test_voice.py "Modo leitura"
python tests/test_voice.py "Prepare o quarto para leitura e feche o VS Code"
```
