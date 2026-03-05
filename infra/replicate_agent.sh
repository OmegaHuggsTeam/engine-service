#!/usr/bin/env bash
# Replicate Agent - Clonagem da estrutura base do agente
# Gera novo hostname Tailscale e sobe container
# Uso: ./infra/replicate_agent.sh [novo_hostname]

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
AGENT_BASE="$PROJECT_ROOT"
REPLICAS_DIR="${REPLICAS_DIR:-$PROJECT_ROOT/replicas}"

# Novo hostname (padrao: kiro-agent-YYYYMMDD-HHMM)
NEW_HOST="${1:-kiro-agent-$(date +%Y%m%d-%H%M)}"
DEST="$REPLICAS_DIR/$NEW_HOST"

echo "=============================================="
echo "  Replicate Agent - Clonagem"
echo "=============================================="
echo "Origem: $AGENT_BASE"
echo "Destino: $DEST"
echo "Hostname Tailscale: $NEW_HOST"
echo ""

# 1. Copiar estrutura base
mkdir -p "$REPLICAS_DIR"
if [ -d "$DEST" ]; then
    echo "AVISO: $DEST ja existe. Sobrescrevendo..."
fi

echo "1. Copiando estrutura..."
if command -v rsync &>/dev/null; then
    rsync -a --exclude='.git' --exclude='__pycache__' --exclude='*.pyc' \
        --exclude='replicas' --exclude='node_modules' \
        "$AGENT_BASE/" "$DEST/"
else
    mkdir -p "$DEST"
    for dir in automation_hub rpg_cortex infra bin; do
        [ -d "$AGENT_BASE/$dir" ] && cp -r "$AGENT_BASE/$dir" "$DEST/"
    done
    [ -f "$AGENT_BASE/requirements.txt" ] && cp "$AGENT_BASE/requirements.txt" "$DEST/" 2>/dev/null || true
fi

# 2. Gerar .env para replica (copia do original, sem sobrescrever)
if [ -f "$AGENT_BASE/.env" ] && [ ! -f "$DEST/.env" ]; then
    cp "$AGENT_BASE/.env" "$DEST/.env"
    echo "2. .env copiado (edite $DEST/.env se necessario)"
else
    echo "2. .env: usar existente ou criar manualmente"
fi

# 3. Configurar hostname Tailscale (se tailscale disponivel)
echo "3. Tailscale hostname: $NEW_HOST"
if command -v tailscale &>/dev/null; then
    tailscale set --hostname "$NEW_HOST" 2>/dev/null && echo "   Hostname aplicado." || echo "   (Execute manualmente: tailscale set --hostname $NEW_HOST)"
else
    echo "   Tailscale nao instalado. Apos instalar: tailscale set --hostname $NEW_HOST"
fi

# 4. Docker Compose (se disponivel)
echo "4. Subindo container..."
cd "$DEST"
if [ -f "infra/docker-compose.yml" ] && command -v docker &>/dev/null; then
    docker compose -f infra/docker-compose.yml up -d 2>/dev/null || docker-compose -f infra/docker-compose.yml up -d
    echo "   Container iniciado."
else
    echo "   Docker nao disponivel ou compose nao encontrado."
    echo "   Execute manualmente: cd $DEST && python automation_hub/bridge/webhook_listener.py 8765"
fi

echo ""
echo "=============================================="
echo "Replica criada: $DEST"
echo "Webhook: http://\$(tailscale ip -4):8765/webhook"
echo "=============================================="
