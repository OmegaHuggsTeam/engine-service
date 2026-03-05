# Tailscale Funnel - Expõe o webhook para a internet
# Execute APÓS iniciar o webhook_listener (porta 8765)
#
# Uso: .\tailscale_funnel.ps1
# Para parar: tailscale funnel localhost:8765 off

Write-Host "Expondo webhook (porta 8765) via Tailscale Funnel..."
Write-Host "URL publica: https://server.tail1f14ca.ts.net/webhook"
Write-Host ""
Write-Host "IFTTT: POST https://server.tail1f14ca.ts.net/webhook?key=haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6"
Write-Host ""
Write-Host "Ctrl+C para parar"
Write-Host ""

tailscale funnel localhost:8765
