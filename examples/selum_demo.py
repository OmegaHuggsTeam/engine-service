"""
Demonstração do Selum of Persistence - O Paladino do Selenium

Este script demonstra como usar o Paladino Selum para interações
resilientes e narrativas com Selenium.

NOTA: Este é um exemplo demonstrativo. Para executar, você precisa:
1. Um WebDriver configurado (Chrome, Firefox, etc.)
2. Uma página web de teste
"""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options

from src.utils.selum_of_persistence import SelumOfPersistence


def demo_basic_strike():
    """Demonstra o uso básico do strike (clique resiliente)."""
    print("\n" + "=" * 70)
    print("DEMO 1: Strike (Clique Resiliente)")
    print("=" * 70 + "\n")

    # Configurar WebDriver (headless para demo)
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        # Inicializar o Paladino
        selum = SelumOfPersistence(driver)

        # Navegar para uma página de teste
        driver.get("https://example.com")

        # Tentar clicar em um link (estratégia smart)
        print("Tentando clicar com estratégia 'smart'...")
        selum.strike("a", strategy="smart")

        print("\n✓ Demo 1 concluída!")

    except Exception as e:
        print(f"\n✗ Erro na demo: {e}")
    finally:
        driver.quit()


def demo_scout():
    """Demonstra o uso do scout (reconhecimento multi-seletor)."""
    print("\n" + "=" * 70)
    print("DEMO 2: Scout (Reconhecimento Multi-Seletor)")
    print("=" * 70 + "\n")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        selum = SelumOfPersistence(driver)
        driver.get("https://example.com")

        # Buscar elemento com múltiplas possibilidades
        print("Buscando elemento com múltiplos seletores...")
        element = selum.scout(
            [
                {"text": "More information"},
                {"text": "Mais informações"},
                {"css": "a"},
                {"xpath": "//a"},
            ]
        )

        if element:
            print(f"\n✓ Elemento encontrado: {element.text}")
        else:
            print("\n✗ Nenhum elemento encontrado")

        print("\n✓ Demo 2 concluída!")

    except Exception as e:
        print(f"\n✗ Erro na demo: {e}")
    finally:
        driver.quit()


def demo_cleansing_aura():
    """Demonstra o uso do cleansing_aura (remoção de obstáculos)."""
    print("\n" + "=" * 70)
    print("DEMO 3: Cleansing Aura (Remoção de Obstáculos)")
    print("=" * 70 + "\n")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        selum = SelumOfPersistence(driver)
        driver.get("https://example.com")

        # Limpar obstáculos
        print("Invocando Aura de Limpeza...")
        removed = selum.cleansing_aura()

        print(f"\n✓ {removed} obstáculos removidos")
        print("\n✓ Demo 3 concluída!")

    except Exception as e:
        print(f"\n✗ Erro na demo: {e}")
    finally:
        driver.quit()


def demo_battle_report():
    """Demonstra o relatório de batalha."""
    print("\n" + "=" * 70)
    print("DEMO 4: Relatório de Batalha")
    print("=" * 70 + "\n")

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")

    driver = webdriver.Chrome(options=options)

    try:
        selum = SelumOfPersistence(driver)
        driver.get("https://example.com")

        # Executar várias manobras
        selum.cleansing_aura()
        selum.scout([{"css": "a"}])
        selum.strike("a", strategy="smart")

        # Obter relatório
        report = selum.get_battle_report()

        print("\nRelatório de Batalha:")
        print("-" * 70)
        for action in report:
            print(f"Turno {action['turn']}: {action['action']} -> {action['result']}")

        print(f"\n✓ Total de turnos: {len(report)}")
        print("\n✓ Demo 4 concluída!")

    except Exception as e:
        print(f"\n✗ Erro na demo: {e}")
    finally:
        driver.quit()


def main():
    """Executa todas as demos."""
    print("\n" + "=" * 70)
    print("🛡️ SELUM OF PERSISTENCE - DEMONSTRAÇÃO")
    print("=" * 70)

    print("\nEste script demonstra as capacidades do Paladino Selum.")
    print("Cada demo mostra uma manobra diferente em ação.\n")

    try:
        # Verificar se ChromeDriver está disponível
        from selenium.webdriver.chrome.service import Service  # noqa: F401
        from webdriver_manager.chrome import ChromeDriverManager  # noqa: F401

        print("✓ ChromeDriver detectado\n")

        # Executar demos
        demos = [
            ("Strike (Clique Resiliente)", demo_basic_strike),
            ("Scout (Reconhecimento)", demo_scout),
            ("Cleansing Aura (Limpeza)", demo_cleansing_aura),
            ("Relatório de Batalha", demo_battle_report),
        ]

        for demo_name, demo_func in demos:
            try:
                demo_func()
            except Exception as e:
                print(f"\n✗ Erro na demo '{demo_name}': {e}")
                continue

        print("\n" + "=" * 70)
        print("✓ TODAS AS DEMOS CONCLUÍDAS!")
        print("=" * 70 + "\n")

    except ImportError:
        print("\n✗ ChromeDriver não encontrado.")
        print("Instale com: pip install webdriver-manager")
        print("\nOu configure manualmente o ChromeDriver.")


if __name__ == "__main__":
    main()
