# Hozana modo sexo - Luzes + YouTube Music
# Uso: .\scripts\hozana_modo_sexo.ps1
#
# IFTTT: If Maker Event "hoza_modo_sexo", then activate hozana modo sexo
# Requer: IFTTT_KEY ou IFTTT_WEBHOOK_KEY no .env ou ambiente

$ErrorActionPreference = "Stop"
$CENA_EVENT = "hoza_modo_sexo"
$YOUTUBE_MUSIC = "https://music.youtube.com/watch?v=_u0zg4p9cV4&si=yj5klKe5ZQ_vUwHd&t=87"

# Carregar .env se existir
$root = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$envFile = Join-Path $root ".env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match '^IFTTT_WEBHOOK_KEY=(.+)$') { $env:IFTTT_WEBHOOK_KEY = $matches[1].Trim() }
        elseif ($_ -match '^IFTTT_KEY=(.+)$') { $env:IFTTT_KEY = $matches[1].Trim() }
    }
}

$KEY = $env:IFTTT_WEBHOOK_KEY
if (-not $KEY) { $KEY = $env:IFTTT_KEY }
if (-not $KEY) {
    Write-Host "Erro: IFTTT_KEY ou IFTTT_WEBHOOK_KEY nao definida. Adicione no .env"
    exit 1
}

Write-Host "Hozana modo sexo ativado... "
Write-Host "Acendendo a cena..."
try {
    Invoke-RestMethod -Uri "https://maker.ifttt.com/trigger/$CENA_EVENT/with/key/$KEY" -Method Post
    Write-Host "Luzes prontas!"
} catch {
    Write-Host "Aviso: cena nao disparou. Verifique o applet '$CENA_EVENT' no IFTTT."
}

Write-Host "Abrindo YouTube Music..."
Start-Process $YOUTUBE_MUSIC

Write-Host "`nPronto! Aproveita."
