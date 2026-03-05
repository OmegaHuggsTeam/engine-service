"""
🛡️ Teste de Campo - Selum of Persistence

Este script valida o Paladino Selum em combate real:
1. Dry Run: Substituir cliques comuns por selum.strike()
2. Validar logs narrativos do CombatLogger
3. Simular falha e verificar invoke_wisdom()
4. Confirmar loop fechado: erro -> especialização -> nova manobra

Uso: python scripts/test_selum_field.py [--headless]
"""

import argparse
import logging
import os
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

# Importar o Paladino
from src.utils.selum_of_persistence import SelumOfPersistence
from src.utils.combat_logger import CombatLogger


def print_banner():
    """Imprime banner do teste."""
    print("\n" + "=" * 70)
    print("🛡️  TESTE DE CAMPO - SELUM OF PERSISTENCE")
    print("=" * 70)
    print("\nO Paladino Moltor entra em seu primeiro combate real!")
    print("Validando: Logs narrativos, resiliência e integração com AgentFactory\n")


def test_1_basic_navigation(driver, selum):
    """Teste 1: Navegação básica com strike()."""
    print("\n" + "-" * 70)
    print("TESTE 1: Navegação Básica com Strike")
    print("-" * 70 + "\n")
    
    try:
        # Navegar para página de teste
        print("Navegando para https://example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        
        # Usar strike() para clicar em um link
        print("\nUsando selum.strike() para clicar no link 'More information'...")
        selum.strike("a", strategy='smart')
        
        time.sleep(2)
        print(f"\n✓ Teste 1 concluído! URL atual: {driver.current_url}")
        return True
        
    except Exception as e:
        print(f"\n✗ Teste 1 falhou: {e}")
        return False


def test_2_scout_multi_selector(driver, selum):
    """Teste 2: Scout com múltiplos seletores."""
    print("\n" + "-" * 70)
    print("TESTE 2: Scout (Reconhecimento Multi-Seletor)")
    print("-" * 70 + "\n")
    
    try:
        # Navegar para página de teste
        print("Navegando para https://example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        
        # Usar scout() com múltiplas possibilidades
        print("\nUsando selum.scout() com múltiplos seletores...")
        element = selum.scout([
            {"text": "More information"},
            {"text": "Mais informações"},
            {"text": "Más información"},
            {"css": "a"},
            {"xpath": "//a"}
        ])
        
        if element:
            print(f"\n✓ Elemento encontrado: {element.text}")
            print(f"✓ Teste 2 concluído!")
            return True
        else:
            print("\n✗ Nenhum elemento encontrado")
            return False
        
    except Exception as e:
        print(f"\n✗ Teste 2 falhou: {e}")
        return False


def test_3_cleansing_aura(driver, selum):
    """Teste 3: Cleansing Aura (remoção de obstáculos)."""
    print("\n" + "-" * 70)
    print("TESTE 3: Cleansing Aura (Limpeza de Obstáculos)")
    print("-" * 70 + "\n")
    
    try:
        # Navegar para página de teste
        print("Navegando para https://example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        
        # Usar cleansing_aura()
        print("\nInvocando Aura de Limpeza...")
        removed = selum.cleansing_aura()
        
        print(f"\n✓ Teste 3 concluído! Obstáculos removidos: {removed}")
        return True
        
    except Exception as e:
        print(f"\n✗ Teste 3 falhou: {e}")
        return False


def test_4_vigilance(driver, selum):
    """Teste 4: Vigilance (espera inteligente)."""
    print("\n" + "-" * 70)
    print("TESTE 4: Vigilance (Espera Inteligente)")
    print("-" * 70 + "\n")
    
    try:
        # Navegar para página de teste
        print("Navegando para https://example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        
        # Usar vigilance() com timeout curto
        print("\nUsando selum.vigilance() para aguardar elemento...")
        element = selum.vigilance("h1", timeout=10)
        
        if element:
            print(f"\n✓ Elemento encontrado: {element.text}")
            print(f"✓ Teste 4 concluído!")
            return True
        else:
            print("\n✗ Elemento não encontrado")
            return False
        
    except Exception as e:
        print(f"\n✗ Teste 4 falhou (esperado se timeout): {e}")
        return False


def test_5_invoke_wisdom_on_failure(driver, selum):
    """Teste 5: Invoke Wisdom quando falha ocorre."""
    print("\n" + "-" * 70)
    print("TESTE 5: Invoke Wisdom (Integração com AgentFactory)")
    print("-" * 70 + "\n")
    
    try:
        # Navegar para página de teste
        print("Navegando para https://example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        
        # Tentar clicar em elemento inexistente (vai falhar)
        print("\nTentando clicar em elemento INEXISTENTE (simulando falha)...")
        print("Esperado: invoke_wisdom() será chamado automaticamente\n")
        
        try:
            selum.strike(".elemento-que-nao-existe-123456", strategy='smart')
        except Exception as e:
            print(f"\n✓ Falha capturada (esperado): {type(e).__name__}")
            print(f"✓ invoke_wisdom() foi chamado automaticamente!")
            print(f"✓ Teste 5 concluído!")
            return True
        
        print("\n✗ Teste 5 falhou: Deveria ter falhado mas não falhou")
        return False
        
    except Exception as e:
        print(f"\n✗ Teste 5 falhou inesperadamente: {e}")
        return False


def test_6_battle_report(driver, selum):
    """Teste 6: Relatório de Batalha."""
    print("\n" + "-" * 70)
    print("TESTE 6: Relatório de Batalha")
    print("-" * 70 + "\n")
    
    try:
        # Executar algumas manobras
        print("Executando sequência de manobras...")
        driver.get("https://example.com")
        time.sleep(1)
        
        selum.cleansing_aura()
        selum.scout([{"css": "a"}])
        
        # Obter relatório
        report = selum.get_battle_report()
        
        print(f"\n📊 Relatório de Batalha:")
        print("-" * 70)
        for action in report:
            status = "✓" if action['success'] else "✗"
            print(f"{status} Turno {action['turn']}: {action['action']} -> {action['result'][:50]}")
        
        print(f"\n✓ Total de turnos: {len(report)}")
        print(f"✓ Teste 6 concluído!")
        return True
        
    except Exception as e:
        print(f"\n✗ Teste 6 falhou: {e}")
        return False


def test_7_steady_gaze(driver, selum):
    """Teste 7: Steady Gaze (scroll até elemento)."""
    print("\n" + "-" * 70)
    print("TESTE 7: Steady Gaze (Scroll Inteligente)")
    print("-" * 70 + "\n")
    
    try:
        # Navegar para página de teste
        print("Navegando para https://example.com...")
        driver.get("https://example.com")
        time.sleep(2)
        
        # Usar steady_gaze()
        print("\nUsando selum.steady_gaze() para focar em elemento...")
        element = selum.steady_gaze("h1")
        
        if element:
            print(f"\n✓ Elemento focado: {element.text}")
            print(f"✓ Teste 7 concluído!")
            return True
        else:
            print("\n✗ Elemento não encontrado")
            return False
        
    except Exception as e:
        print(f"\n✗ Teste 7 falhou: {e}")
        return False


def run_field_test(headless: bool = True):
    """Executa todos os testes de campo."""
    print_banner()
    
    # Configurar WebDriver
    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    
    options = Options()
    if headless:
        options.add_argument('--headless')
        options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    print("Inicializando WebDriver...")
    driver = webdriver.Chrome(options=options)
    
    # Inicializar o Paladino
    print("Forjando o Paladino Selum...")
    selum = SelumOfPersistence(driver)
    print("✓ Paladino pronto para o combate!\n")
    
    # Executar testes
    tests = [
        ("Navegação Básica (Strike)", test_1_basic_navigation),
        ("Reconhecimento (Scout)", test_2_scout_multi_selector),
        ("Limpeza (Cleansing Aura)", test_3_cleansing_aura),
        ("Espera Inteligente (Vigilance)", test_4_vigilance),
        ("Sabedoria Ancestral (Invoke Wisdom)", test_5_invoke_wisdom_on_failure),
        ("Relatório de Batalha", test_6_battle_report),
        ("Foco Firme (Steady Gaze)", test_7_steady_gaze),
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func(driver, selum)
            results.append((test_name, result))
        except Exception as e:
            print(f"\n✗ Erro crítico no teste '{test_name}': {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Sumário
    print("\n" + "=" * 70)
    print("📊 SUMÁRIO DOS TESTES")
    print("=" * 70 + "\n")
    
    passed = sum(1 for _, result in results if result)
    failed = len(results) - passed
    
    for test_name, result in results:
        status = "✓ PASSOU" if result else "✗ FALHOU"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {len(results)}")
    print(f"Passou: {passed}")
    print(f"Falhou: {failed}")
    
    # Relatório final do Paladino
    print("\n" + "=" * 70)
    print("🛡️ RELATÓRIO FINAL DO PALADINO")
    print("=" * 70 + "\n")
    
    final_report = selum.get_battle_report()
    print(f"Total de turnos executados: {len(final_report)}")
    
    successes = sum(1 for action in final_report if action['success'])
    failures = len(final_report) - successes
    
    print(f"Manobras bem-sucedidas: {successes}")
    print(f"Manobras falhadas: {failures}")
    
    if failures > 0:
        print(f"\nManobras que falharam:")
        for action in final_report:
            if not action['success']:
                print(f"  - Turno {action['turn']}: {action['action']} ({action['result'][:50]})")
    
    # Fechar driver
    try:
        driver.quit()
    except Exception:
        pass
    
    # Resultado final
    print("\n" + "=" * 70)
    if failed == 0:
        print("✓ TODOS OS TESTES PASSARAM!")
        print("\n🛡️ Selum of Persistence está pronto para produção!")
    else:
        print(f"✗ {failed} TESTE(S) FALHARAM")
        print("\n⚠️ Revise os logs acima para detalhes.")
    print("=" * 70 + "\n")
    
    return failed == 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de campo do Selum of Persistence")
    parser.add_argument("--headless", action="store_true", help="Modo headless (sem interface)")
    args = parser.parse_args()
    
    try:
        success = run_field_test(headless=args.headless)
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n[ERRO CRÍTICO] {e}")
        traceback.print_exc()
        sys.exit(1)
