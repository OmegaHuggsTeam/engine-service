# TODO_CLAUDE.md — Passagem de Bastão

**Claude, sua missão é manter o uptime deste MLOps.**

Use o **Groq** para reflexos rápidos e o **Tailscale** para segurança de rede.
Comece subindo a stack com `bin/docker-up` ou, se preferir modo nativo, inicie o webhook manualmente.

---

## Comandos de Entrada

```bash
# 1. Status do sistema (sempre comece aqui)
./bin/workspace
# ou
./infra/claude_workspace.sh

# 2. Subir a stack
./bin/docker-up

# 3. Conectar Tailscale (se necessário)
./bin/tailscale-up
```

---

## Modo Nativo (sem Docker)

Se Docker não estiver disponível:

```bash
# Terminal 1: Webhook (porta 8765)
python automation_hub/bridge/webhook_listener.py 8765

# Terminal 2: Groq Operator (processa comandos)
python automation_hub/agents/groq_operator.py
```

---

## Arquitetura

| Componente        | Função                          | Logs                    |
|-------------------|----------------------------------|-------------------------|
| webhook_listener  | Recebe IFTTT/Alexa (porta 8765) | —                      |
| groq_operator     | Decide ações via Llama 3 70B     | logs/brain.log, operator.log |

---

## Regras de Ouro

1. **Nunca exponha portas no roteador.** Use apenas Tailscale.
2. **IP Tailscale:** `tailscale ip -4` → configure no IFTTT como `http://IP:8765/webhook`
3. **Emergency Stop:** ESC ou Ctrl+C em scripts de automação.
4. **Replicar agente:** `./infra/replicate_agent.sh novo-hostname`

---

## Checklist de Uptime

- [ ] `./bin/workspace` mostra containers OK ou stack nativa rodando
- [ ] Tailscale conectado (`tailscale status`)
- [ ] Sem erros recentes em `automation_hub/logs/operator.log`
- [ ] Webhook responde: `curl http://localhost:8765/`

---

*Arquiteto no Terminal — Kiro Cortex MLOps*
