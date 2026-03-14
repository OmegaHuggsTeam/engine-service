#!/usr/bin/env bash
# check_readiness.sh - Verifica se o sistema está pronto para autonomia do Claude
# Valida dependências, configurações e componentes necessários

set -e

echo "🔍 Verificando Prontidão do Bunker para Autonomia"
echo "=================================================="
echo ""

# Cores
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Contadores
CHECKS_PASSED=0
CHECKS_FAILED=0
CHECKS_WARNING=0

# Função para check
check() {
    local name="$1"
    local command="$2"

    echo -n "  Verificando $name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${RED}✗${NC}"
        ((CHECKS_FAILED++))
        return 1
    fi
}

# Função para warning
check_warn() {
    local name="$1"
    local command="$2"

    echo -n "  Verificando $name... "

    if eval "$command" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC}"
        ((CHECKS_PASSED++))
        return 0
    else
        echo -e "${YELLOW}⚠${NC}"
        ((CHECKS_WARNING++))
        return 1
    fi
}

echo "📦 1. Verificando Python e Ambiente Virtual"
echo "-------------------------------------------"

check "Python 3" "python --version"
check "pip" "pip --version"

if [ -d ".venv" ]; then
    echo -e "  ${GREEN}✓${NC} Ambiente virtual encontrado"
    ((CHECKS_PASSED++))
else
    echo -e "  ${YELLOW}⚠${NC} Ambiente virtual não encontrado"
    echo "    Execute: python -m venv .venv"
    ((CHECKS_WARNING++))
fi

echo ""
echo "📚 2. Verificando Dependências Python"
echo "--------------------------------------"

check "pyautogui" "python -c 'import pyautogui'"
check "Pillow (PIL)" "python -c 'from PIL import Image'"
check_warn "neo4j" "python -c 'import neo4j'"
check_warn "asyncio" "python -c 'import asyncio'"

echo ""
echo "📁 3. Verificando Estrutura de Diretórios"
echo "------------------------------------------"

check "temp/" "test -d temp"
check "logs/" "test -d logs"
check "macros/" "test -d macros"
check "specs/" "test -d specs"
check "bin/" "test -d bin"

echo ""
echo "📄 4. Verificando Arquivos Essenciais"
echo "--------------------------------------"

check "bin/capture_view.py" "test -f bin/capture_view.py"
check "bin/jitbit_bridge.py" "test -f bin/jitbit_bridge.py"
check "specs/ui_map.json" "test -f specs/ui_map.json"
check "tests/mission_zero_autonomy.py" "test -f tests/mission_zero_autonomy.py"
check "bin/test-autonomy" "test -f bin/test-autonomy"

echo ""
echo "🔧 5. Verificando Executabilidade dos Scripts"
echo "----------------------------------------------"

check "capture_view.py executável" "test -x bin/capture_view.py || python bin/capture_view.py --help"
check "jitbit_bridge.py executável" "test -x bin/jitbit_bridge.py || python bin/jitbit_bridge.py --help"
check "test-autonomy executável" "test -x bin/test-autonomy"

echo ""
echo "🎯 6. Verificando Specs (opcional)"
echo "-----------------------------------"
check_warn "Specs Kiro" "test -d .kiro/specs"

echo ""
echo "🖥️  7. Verificando Sistema Operacional"
echo "---------------------------------------"

if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    echo -e "  ${GREEN}✓${NC} Windows detectado"
    ((CHECKS_PASSED++))
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo -e "  ${BLUE}ℹ${NC} Linux detectado (algumas features podem não funcionar)"
    ((CHECKS_WARNING++))
elif [[ "$OSTYPE" == "darwin"* ]]; then
    echo -e "  ${BLUE}ℹ${NC} macOS detectado (algumas features podem não funcionar)"
    ((CHECKS_WARNING++))
else
    echo -e "  ${YELLOW}⚠${NC} Sistema operacional desconhecido: $OSTYPE"
    ((CHECKS_WARNING++))
fi

echo ""
echo "🔐 8. Verificando Permissões"
echo "----------------------------"

check "Permissão de escrita em temp/" "test -w temp"
check "Permissão de escrita em logs/" "test -w logs"
check "Permissão de leitura em specs/" "test -r specs"

echo ""
echo "=================================================="
echo "📊 Resumo da Verificação"
echo "=================================================="
echo ""
echo -e "${GREEN}✓ Checks Passados:${NC} $CHECKS_PASSED"
echo -e "${YELLOW}⚠ Avisos:${NC} $CHECKS_WARNING"
echo -e "${RED}✗ Checks Falhados:${NC} $CHECKS_FAILED"
echo ""

# Determinar status geral
if [ $CHECKS_FAILED -eq 0 ] && [ $CHECKS_WARNING -eq 0 ]; then
    echo -e "${GREEN}✅ SISTEMA PRONTO PARA AUTONOMIA${NC}"
    echo ""
    echo "O Bunker está preparado para o Claude assumir o controle."
    echo "Execute: ./bin/test-autonomy para iniciar a Missão Zero"
    echo ""
    exit 0
elif [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${YELLOW}⚠️  SISTEMA PARCIALMENTE PRONTO${NC}"
    echo ""
    echo "Há alguns avisos, mas o sistema pode funcionar."
    echo "Revise os avisos acima antes de prosseguir."
    echo ""
    exit 0
else
    echo -e "${RED}❌ SISTEMA NÃO ESTÁ PRONTO${NC}"
    echo ""
    echo "Corrija os erros acima antes de prosseguir."
    echo ""
    echo "Ações sugeridas:"
    echo "  1. Instalar dependências: pip install -r requirements.txt"
    echo "  2. Criar diretórios: mkdir -p temp logs macros"
    echo "  3. Verificar arquivos essenciais estão presentes"
    echo ""
    exit 1
fi
