# Hozana modo sexo - Luzes + YouTube Music
# Uso: .\hozana_modo_sexo.ps1
#
# IFTTT: If Maker Event "hoza_modo_sexo", then activate hozana modo sexo

$KEY = "haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6"
$CENA_EVENT = "hoza_modo_sexo"  # Maker Event no IFTTT

# URL do YouTube Music - inicia em 1:27 (t=87)
$YOUTUBE_MUSIC = "https://music.youtube.com/watch?v=_u0zg4p9cV4&si=yj5klKe5ZQ_vUwHd&t=87"

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
