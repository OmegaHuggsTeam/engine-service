# Reset Git History - Remove todo o histórico semântico do GitHub
# Uso: .\scripts\reset_git_history.ps1
# ATENÇÃO: Isso apaga o histórico. Faça backup do .zip antes.

$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $root

Write-Host "=== Reset Git History ===" -ForegroundColor Yellow
Write-Host ""

# 1. Criar branch órfã (sem histórico)
Write-Host "1. Criando branch órfã (sem parent)..." -ForegroundColor Cyan
git checkout --orphan fresh-main

# 2. Adicionar todos os arquivos do estado atual
Write-Host "2. Adicionando arquivos..." -ForegroundColor Cyan
git add -A

# 3. Commit único
Write-Host "3. Criando commit único..." -ForegroundColor Cyan
git commit -m "chore: initial commit (history reset)"

# 4. Deletar branch main local e renomear fresh-main para main
Write-Host "4. Substituindo main..." -ForegroundColor Cyan
git branch -D main 2>$null
git branch -m fresh-main main

# 5. Force push para origin
Write-Host "5. Force push para origin/main..." -ForegroundColor Cyan
git push -f origin main

# 6. (Opcional) Atualizar feat/extract-kpi-intelligence para apontar ao mesmo commit
Write-Host "6. Atualizando feat/extract-kpi-intelligence..." -ForegroundColor Cyan
git push -f origin main:feat/extract-kpi-intelligence

Write-Host ""
Write-Host "=== Concluído ===" -ForegroundColor Green
Write-Host "Histórico removido. O repositório agora tem apenas 1 commit."
Write-Host "Outras branches no remoto podem ser deletadas manualmente no GitHub."
