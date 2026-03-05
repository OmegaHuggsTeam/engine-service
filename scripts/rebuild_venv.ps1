# Reconstrucao do ambiente virtual - Chunk Generator
# Execute com: .\scripts\rebuild_venv.ps1
# IMPORTANTE: Feche o Cursor/IDE e terminais que usam o .venv antes de rodar.

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
Set-Location $ProjectRoot

Write-Host "`n=== Reconstrucao do .venv ===" -ForegroundColor Cyan

# 1. Verificar Python 3.12 ou 3.11
$py312 = Get-Command python3.12 -ErrorAction SilentlyContinue
$py311 = Get-Command python3.11 -ErrorAction SilentlyContinue
$pyLauncher = Get-Command py -ErrorAction SilentlyContinue

$pythonExe = $null
if ($py312) { $pythonExe = "python3.12" }
elseif ($py311) { $pythonExe = "python3.11" }
elseif ($pyLauncher) {
    # Tenta py -3.12 ou py -3.11
    $v = & py -3.12 -c "import sys; print(sys.executable)" 2>$null
    if ($v) { $pythonExe = "py -3.12" }
    else {
        $v = & py -3.11 -c "import sys; print(sys.executable)" 2>$null
        if ($v) { $pythonExe = "py -3.11" }
    }
}
if (-not $pythonExe) {
    $pythonExe = "python"  # Fallback
    Write-Host "[AVISO] Python 3.12/3.11 nao encontrado. Usando: $(python --version)" -ForegroundColor Yellow
    Write-Host "Instale Python 3.12 em: https://www.python.org/downloads/" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Usando: $pythonExe" -ForegroundColor Green
}

# 2. Remover .venv antigo
if (Test-Path ".venv") {
    Write-Host "`nRemovendo .venv antigo..." -ForegroundColor Yellow
    try {
        Remove-Item -Recurse -Force .venv
        Write-Host "[OK] .venv removido" -ForegroundColor Green
    } catch {
        Write-Host "[ERRO] Nao foi possivel remover .venv. Feche o Cursor e terminais." -ForegroundColor Red
        Write-Host $_.Exception.Message -ForegroundColor Red
        exit 1
    }
} else {
    Write-Host "[OK] Nenhum .venv existente" -ForegroundColor Green
}

# 3. Criar novo venv
Write-Host "`nCriando novo .venv com $pythonExe..." -ForegroundColor Cyan
if ($pythonExe -match "py -") {
    Invoke-Expression "$pythonExe -m venv .venv"
} else {
    & $pythonExe -m venv .venv
}
if ($LASTEXITCODE -ne 0) { exit 1 }
Write-Host "[OK] .venv criado" -ForegroundColor Green

# 4. Ativar e instalar
$pip = ".venv\Scripts\pip.exe"
$python = ".venv\Scripts\python.exe"

Write-Host "`nAtualizando pip..." -ForegroundColor Cyan
& $python -m pip install --upgrade pip -q
Write-Host "[OK] pip atualizado" -ForegroundColor Green

# Tenta requirements.txt completo primeiro
Write-Host "`nInstalando dependencias (requirements.txt)..." -ForegroundColor Cyan
$r = & $pip install -r requirements.txt 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[AVISO] Falha no requirements.txt completo. Tentando minimal (sem ChromaDB)..." -ForegroundColor Yellow
    & $pip install -r requirements-minimal.txt -q
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERRO] Instalacao falhou" -ForegroundColor Red
        exit 1
    }
    Write-Host "[OK] Dependencias minimas instaladas (Selenium + Bot)" -ForegroundColor Green
} else {
    Write-Host "[OK] Todas as dependencias instaladas" -ForegroundColor Green
}

# 5. Validar
Write-Host "`nValidando..." -ForegroundColor Cyan
& $python -c "import selenium; import telegram; print('Selenium + Telegram: OK')"
& $python -c "import groq; print('Groq: OK')"
try {
    & $python -c "import chromadb; print('ChromaDB: OK')"
} catch {
    Write-Host "ChromaDB: nao instalado (use requirements.txt completo se precisar)" -ForegroundColor Yellow
}

Write-Host "`n=== Concluido ===" -ForegroundColor Green
Write-Host "Ative com: .venv\Scripts\activate" -ForegroundColor Cyan
Write-Host "Rode: python run_init.py" -ForegroundColor Cyan
Write-Host ""
