# Silencia notificacoes do sistema (Windows Focus Assist)
# Modo Leitura = ativa "Nao perturbe"

try {
    # Windows 10/11: Ativa Focus Assist via registro
    $path = "HKCU:\Software\Microsoft\Windows\CurrentVersion\CloudStore\Store\DefaultAccount\Current\default$windows.data.focusassist.focusassiststate\windows.data.focusassist.focusassiststate"
    if (Test-Path (Split-Path $path -Parent)) {
        Set-ItemProperty -Path (Split-Path $path -Parent) -Name (Split-Path $path -Leaf) -Value ([byte[]](1,0,0,0)) -ErrorAction SilentlyContinue
    }
} catch {
    # Fallback: apenas loga - usuario pode implementar via Settings ou outra API
    Write-Host "Focus Assist: ajuste manualmente se necessario"
}
