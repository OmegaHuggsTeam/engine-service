#!/usr/bin/env bash
# Hozana modo sexo - Luzes + YouTube Music
# Uso: ./scripts/hozana_modo_sexo.sh
#
# IFTTT: If Maker Event "hoza_modo_sexo", then activate hozana modo sexo
# Requer: IFTTT_KEY no ambiente ou .env

set -e

CENA_EVENT="hoza_modo_sexo"
YOUTUBE_MUSIC="https://music.youtube.com/watch?v=_u0zg4p9cV4&si=yj5klKe5ZQ_vUwHd&t=87"

# Carregar .env se existir (na raiz do projeto)
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
if [ -f "$ROOT/.env" ]; then
  set -a
  source "$ROOT/.env"
  set +a
fi

KEY="${IFTTT_KEY:-}"
if [ -z "$KEY" ]; then
  echo "Erro: IFTTT_KEY não definida. Defina no .env ou export IFTTT_KEY=..."
  exit 1
fi

echo "Hozana modo sexo ativado... "
echo "Acendendo a cena..."

if curl -sS -X POST "https://maker.ifttt.com/trigger/${CENA_EVENT}/with/key/${KEY}" > /dev/null; then
  echo "Luzes prontas!"
else
  echo "Aviso: cena não disparou. Verifique o applet '$CENA_EVENT' no IFTTT."
fi

echo "Abrindo YouTube Music..."
if command -v xdg-open &>/dev/null; then
  xdg-open "$YOUTUBE_MUSIC"
elif command -v open &>/dev/null; then
  open "$YOUTUBE_MUSIC"
else
  echo "Abra manualmente: $YOUTUBE_MUSIC"
fi

echo ""
echo "Pronto! Aproveita."
