"""
Teste simplificado de rotação - Google Groups.

Versão minimalista para diagnóstico de problemas.
Usa apenas Selenium básico + SelumOfPersistence.

Uso: python scripts/test_rotation_simple.py
"""

import os
import sys
import time
from pathlib import Path

# Configuração de encoding para Windows
if sys.platform == "win32":
    import codecs

    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.buffer, errors="replace")
    sys.stderr = codecs.getwriter("utf-8")(sys.stderr.buffer, errors="replace")

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_ROOT / ".env")


def log(msg: str):
    """Log simples com timestamp."""
    from datetime import datetime

    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] {msg}", flush=True)


def cleanup_chrome():
    """Limpa processos Chrome (Windows)."""
    import subprocess

    log("Limpando processos Chrome...")

    for proc in ["chrome.exe", "chromedriver.exe"]:
        try:
            subprocess.run(["taskkill", "/F", "/IM", proc], capture_output=True, timeout=5)
        except Exception:
            pass

    time.sleep(2)


def main():
    """Executa teste simples."""
    log("=" * 60)
    log("TESTE SIMPLES - Google Groups")
    log("=" * 60)

    # Limpeza inicial
    cleanup_chrome()

    driver = None

    try:
        # Importar Selenium
        log("\n[1/5] Importando Selenium...")
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options

        log("✓ Selenium importado")

        # Configurar opções Chrome
        log("\n[2/5] Configurando Chrome...")
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # Perfil (se configurado)
        profile_path = os.getenv("EXTRACTOR_CHROME_USER_DATA", "").strip()
        if profile_path and Path(profile_path).exists():
            log(f"✓ Usando perfil: {profile_path}")
            options.add_argument(f"--user-data-dir={profile_path}")
        else:
            log("⚠ Sem perfil configurado, usando perfil temporário")

        log("✓ Opções configuradas")

        # Inicializar driver
        log("\n[3/5] Inicializando ChromeDriver...")
        driver = webdriver.Chrome(options=options)
        log("✓ Driver inicializado")

        # Aguardar estabilização
        time.sleep(2)

        # Navegar para Google
        log("\n[4/5] Navegando para Google...")
        driver.get("https://www.google.com")
        time.sleep(3)

        current_url = driver.current_url
        log(f"✓ URL atual: {current_url}")

        if "google" not in current_url.lower():
            log("⚠ URL não contém 'google'")
        else:
            log("✓ Google carregado com sucesso")

        # Navegar para Google Groups
        log("\n[5/5] Navegando para Google Groups...")
        driver.get("https://groups.google.com/all-groups")
        time.sleep(5)

        current_url = driver.current_url
        page_title = driver.title

        log(f"✓ URL final: {current_url}")
        log(f"✓ Título: {page_title}")

        # Verificar se chegou
        if "groups.google.com" in current_url:
            log("✓ Google Groups carregado!")
        else:
            log(f"⚠ URL inesperada: {current_url}")

        # Screenshot
        screenshot_path = PROJECT_ROOT / "logs" / "test_simple.png"
        screenshot_path.parent.mkdir(exist_ok=True)
        driver.save_screenshot(str(screenshot_path))
        log(f"✓ Screenshot: {screenshot_path}")

        # Resultado
        log("\n" + "=" * 60)
        log("TESTE CONCLUÍDO COM SUCESSO")
        log("=" * 60)

        return True

    except Exception as e:
        log(f"\n✗ ERRO: {e}")
        import traceback

        log(f"\nTraceback:\n{traceback.format_exc()}")

        if driver:
            try:
                screenshot_path = PROJECT_ROOT / "logs" / "test_error.png"
                screenshot_path.parent.mkdir(exist_ok=True)
                driver.save_screenshot(str(screenshot_path))
                log(f"Screenshot de erro: {screenshot_path}")
            except Exception:
                pass

        return False

    finally:
        # Limpeza
        log("\nLimpeza...")
        if driver:
            try:
                driver.quit()
                log("✓ Driver encerrado")
            except Exception as e:
                log(f"⚠ Erro ao encerrar: {e}")

        time.sleep(2)
        cleanup_chrome()


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        log("\n⚠ Interrompido pelo usuário")
        sys.exit(130)
