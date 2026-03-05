# IFTTT Client - Controle de luzes Positivo via Maker Webhooks
# Uso: .\ifttt_client.ps1 on | off | branco | leitura
# Chave: IFTTT_WEBHOOK_KEY ou IFTTT_KEY do .env

$KEY = $env:IFTTT_WEBHOOK_KEY
if (-not $KEY) { $KEY = $env:IFTTT_KEY }
if (-not $KEY) {
    $envFile = Join-Path (Split-Path $PSScriptRoot -Parent) "config\credentials.env"
    if (Test-Path $envFile) {
        Get-Content $envFile | ForEach-Object {
            if ($_ -match '^IFTTT_WEBHOOK_KEY=(.+)$') { $KEY = $matches[1].Trim() }
            elseif ($_ -match '^IFTTT_KEY=(.+)$') { $KEY = $matches[1].Trim() }
        }
    }
}
if (-not $KEY) {
    $KEY = "haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6"
}

$mode = $args[0]
$events = @{
    "on"                = "ligar_quarto_hugo"
    "off"               = "desligar_quarto_hugo"
    "branco"            = "luz_branca"
    "leitura"           = "modo_leitura"
    "vermelho_piscante" = "vermelho_piscante"
}

$event = $events[$mode]
if ($event) {
    try {
        Invoke-RestMethod -Uri "https://maker.ifttt.com/trigger/$event/with/key/$KEY" -Method Post -ErrorAction Stop
        exit 0
    } catch {
        Write-Host "ERRO IFTTT: $_"
        exit 1
    }
} else {
    Write-Host "Uso: .\ifttt_client.ps1 on | off | branco | leitura | vermelho_piscante"
    exit 1
}
