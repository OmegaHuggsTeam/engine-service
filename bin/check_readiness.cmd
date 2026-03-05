@echo off
REM check_readiness.cmd - Verifica se o sistema está pronto para autonomia do Claude
REM Valida dependências, configurações e componentes necessários

echo.
echo ========================================
echo Verificando Prontidão do Bunker
echo ========================================
echo.

set CHECKS_PASSED=0
set CHECKS_FAILED=0
set CHECKS_WARNING=0

echo [1/8] Verificando Python e Ambiente Virtual
echo -------------------------------------------
python --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Python encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] Python não encontrado
    set /a CHECKS_FAILED+=1
)

pip --version >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] pip encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] pip não encontrado
    set /a CHECKS_FAILED+=1
)

if exist .venv (
    echo   [OK] Ambiente virtual encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [AVISO] Ambiente virtual não encontrado
    set /a CHECKS_WARNING+=1
)

echo.
echo [2/8] Verificando Dependências Python
echo --------------------------------------
python -c "import pyautogui" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] pyautogui instalado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] pyautogui não instalado
    set /a CHECKS_FAILED+=1
)

python -c "from PIL import Image" >nul 2>&1
if %errorlevel% equ 0 (
    echo   [OK] Pillow instalado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] Pillow não instalado
    set /a CHECKS_FAILED+=1
)

echo.
echo [3/8] Verificando Estrutura de Diretórios
echo ------------------------------------------
if exist temp (
    echo   [OK] temp/ encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] temp/ não encontrado
    set /a CHECKS_FAILED+=1
)

if exist logs (
    echo   [OK] logs/ encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] logs/ não encontrado
    set /a CHECKS_FAILED+=1
)

if exist macros (
    echo   [OK] macros/ encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] macros/ não encontrado
    set /a CHECKS_FAILED+=1
)

if exist specs (
    echo   [OK] specs/ encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] specs/ não encontrado
    set /a CHECKS_FAILED+=1
)

if exist bin (
    echo   [OK] bin/ encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] bin/ não encontrado
    set /a CHECKS_FAILED+=1
)

echo.
echo [4/8] Verificando Arquivos Essenciais
echo --------------------------------------
if exist bin\capture_view.py (
    echo   [OK] bin/capture_view.py encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] bin/capture_view.py não encontrado
    set /a CHECKS_FAILED+=1
)

if exist bin\jitbit_bridge.py (
    echo   [OK] bin/jitbit_bridge.py encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] bin/jitbit_bridge.py não encontrado
    set /a CHECKS_FAILED+=1
)

if exist specs\ui_map.json (
    echo   [OK] specs/ui_map.json encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] specs/ui_map.json não encontrado
    set /a CHECKS_FAILED+=1
)

if exist tests\mission_zero_autonomy.py (
    echo   [OK] tests/mission_zero_autonomy.py encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] tests/mission_zero_autonomy.py não encontrado
    set /a CHECKS_FAILED+=1
)

echo.
echo [5/8] Testando Scripts
echo ----------------------
python bin\capture_view.py --info > temp\test_capture.log 2>&1
if %errorlevel% equ 0 (
    echo   [OK] capture_view.py funcional
    set /a CHECKS_PASSED+=1
) else (
    echo   [AVISO] capture_view.py retornou erro (pode ser normal)
    set /a CHECKS_WARNING+=1
)

python bin\jitbit_bridge.py --info > temp\test_bridge.log 2>&1
if %errorlevel% equ 0 (
    echo   [OK] jitbit_bridge.py funcional
    set /a CHECKS_PASSED+=1
) else (
    echo   [AVISO] jitbit_bridge.py retornou erro (pode ser normal)
    set /a CHECKS_WARNING+=1
)

echo.
echo [6/8] Verificando Specs (opcional)
echo ----------------------------------
if exist .kiro\specs (
    echo   [OK] Specs Kiro encontrado
    set /a CHECKS_PASSED+=1
) else (
    echo   [AVISO] Specs Kiro nao encontrado
    set /a CHECKS_WARNING+=1
)

echo.
echo [7/8] Verificando Sistema Operacional
echo --------------------------------------
echo   [OK] Windows detectado
set /a CHECKS_PASSED+=1

echo.
echo [8/8] Verificando Permissões
echo ----------------------------
echo test > temp\test_write.tmp 2>nul
if %errorlevel% equ 0 (
    echo   [OK] Permissão de escrita em temp/
    del temp\test_write.tmp >nul 2>&1
    set /a CHECKS_PASSED+=1
) else (
    echo   [ERRO] Sem permissão de escrita em temp/
    set /a CHECKS_FAILED+=1
)

echo.
echo ========================================
echo Resumo da Verificação
echo ========================================
echo.
echo [OK] Checks Passados: %CHECKS_PASSED%
echo [AVISO] Avisos: %CHECKS_WARNING%
echo [ERRO] Checks Falhados: %CHECKS_FAILED%
echo.

if %CHECKS_FAILED% equ 0 (
    if %CHECKS_WARNING% equ 0 (
        echo ========================================
        echo SISTEMA PRONTO PARA AUTONOMIA
        echo ========================================
        echo.
        echo O Bunker está preparado para o Claude assumir o controle.
        echo Execute: python tests\mission_zero_autonomy.py
        echo.
        exit /b 0
    ) else (
        echo ========================================
        echo SISTEMA PARCIALMENTE PRONTO
        echo ========================================
        echo.
        echo Há alguns avisos, mas o sistema pode funcionar.
        echo Revise os avisos acima antes de prosseguir.
        echo.
        exit /b 0
    )
) else (
    echo ========================================
    echo SISTEMA NÃO ESTÁ PRONTO
    echo ========================================
    echo.
    echo Corrija os erros acima antes de prosseguir.
    echo.
    echo Ações sugeridas:
    echo   1. Instalar dependências: pip install -r requirements.txt
    echo   2. Criar diretórios: mkdir temp logs macros
    echo   3. Verificar arquivos essenciais estão presentes
    echo.
    exit /b 1
)
