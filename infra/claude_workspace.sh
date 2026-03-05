#!/usr/bin/env bash
# Claude Workspace - Interface de Comando para o Arquiteto no Terminal
# Iniciado pelo Claude CLI para resumir status do sistema MLOps

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=============================================="
echo "  Kiro Cortex - Status do Sistema (Claude)"
echo "=============================================="
echo ""

# 1. Status dos Containers (Docker)
echo "--- 1. Containers (Docker) ---"
if command -v docker &>/dev/null; then
    docker ps -a 2>/dev/null || echo "Docker nao acessivel"
else
    echo "Docker nao instalado. Stack roda nativamente (Python)."
fi
echo ""

# 2. Status da Rede (Tailscale)
echo "--- 2. Rede (Tailscale) ---"
if command -v tailscale &>/dev/null; then
    TS_IP=$(tailscale ip -4 2>/dev/null || true)
    TS_STATUS=$(tailscale status 2>/dev/null | head -5 || true)
    if [ -n "$TS_IP" ]; then
        echo "IP Tailscale: $TS_IP"
        echo "Webhook IFTTT: http://${TS_IP}:8765/webhook"
    else
        echo "Tailscale nao conectado. Execute: tailscale up"
    fi
    [ -n "$TS_STATUS" ] && echo "$TS_STATUS"
else
    echo "Tailscale nao instalado."
fi
echo ""

# 3. Ultimos Logs de Erro (Groq + Hardware)
echo "--- 3. Ultimos Erros (Groq / Brain / Operator / Hardware) ---"
for log in \
    "automation_hub/logs/brain.log" \
    "automation_hub/logs/operator.log" \
    "rpg_cortex/logs/hardware.log"; do
    full="$PROJECT_ROOT/$log"
    if [ -f "$full" ]; then
        echo ">>> $log (ultimas 5 linhas com erro/warning/ERRO):"
        grep -i -E "erro|error|warning|fail|exception" "$full" 2>/dev/null | tail -5 || echo "  (nenhum)"
    else
        echo ">>> $log: (arquivo nao existe)"
    fi
    echo ""
done

# 4. Resumo de Saude
echo "--- 4. Resumo ---"
echo "Projeto: $PROJECT_ROOT"
echo "Comandos rapidos:"
echo "  bin/docker-up      - Sobe stack (docker-compose up -d)"
echo "  bin/tailscale-up   - Conecta Tailscale"
echo "  bin/workspace     - Reexibe este status"
echo ""
echo "=============================================="
