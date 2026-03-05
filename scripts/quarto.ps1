# Script PowerShell - controle do quarto
# Uso: .\quarto.ps1 on | off | branco | leitura

$KEY = "haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6"

switch ($args[0]) {
    "on" {
        Write-Host "Acendendo o bunker..."
        Invoke-RestMethod -Uri "https://maker.ifttt.com/trigger/ligar_quarto_hugo/with/key/$KEY" -Method Post
        Write-Host "Pronto!"
    }
    "off" {
        Write-Host "Apagando tudo. Boa noite, Hugo."
        Invoke-RestMethod -Uri "https://maker.ifttt.com/trigger/desligar_quarto_hugo/with/key/$KEY" -Method Post
        Write-Host "Feito!"
    }
    "branco" {
        Write-Host "Luz branca..."
        Invoke-RestMethod -Uri "https://maker.ifttt.com/trigger/luz_branca/with/key/$KEY" -Method Post
        Write-Host "Pronto!"
    }
    "leitura" {
        Write-Host "Modo leitura..."
        Invoke-RestMethod -Uri "https://maker.ifttt.com/trigger/modo_leitura/with/key/$KEY" -Method Post
        Write-Host "Pronto!"
    }
    default {
        Write-Host "Uso: .\quarto.ps1 on | off | branco | leitura"
    }
}
