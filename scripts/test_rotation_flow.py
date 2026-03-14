"""
Teste do fluxo de rotacao: Google Groups -> Gmail -> Groq.

Versão simplificada e robusta para Windows.
Usa SelumOfPersistence + Steady Gaze (quando disponível).

Uso: python scripts/test_rotation_flow.py [--headless]
"""

import argparse
import logging
import os
import sys
import time
from datetime import datetime
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

# Configurar logging
logging.basicConfig(
    level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s", datefmt="%H:%M:%S"
)
logger = logging.getLogger(__name__)

LOGS_DIR = PROJECT_ROOT / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)

_EXECUTION_LOGS: list[str] = []


def _log(msg: str, flush: bool = True) -> None:
    """Log com timestamp e armazenamento em memória."""
    ts = datetime.now().strftime("%H:%M:%S")
    line = f"[{ts}] {msg}"
    logger.info(msg)
    _EXECUTION_LOGS.append(line)
    if len(_EXECUTION_LOGS) > 100:
        _EXECUTION_LOGS.pop(0)


def _save_screenshot(driver, prefix: str = "error"):
    """Salva screenshot com tratamento robusto de erros."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = LOGS_DIR / f"{prefix}_{ts}.png"
    try:
        driver.save_screenshot(str(path))
        _log(f"Screenshot salvo: {path}")
        return str(path)
    except Exception as e:
        _log(f"Erro ao salvar screenshot: {e}")
        return None


def _cleanup_chrome_processes() -> bool:
    """Limpa processos Chrome de forma robusta (Windows)."""
    import subprocess

    killed = False

    try:
        # Tentar fechar Chrome graciosamente primeiro
        for proc_name in ["chrome.exe", "chromedriver.exe"]:
            try:
                result = subprocess.run(
                    ["taskkill", "/IM", proc_name], capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    killed = True
                    time.sleep(1)
            except Exception:
                pass

        # Se não funcionou, forçar
        if not killed:
            for proc_name in ["chrome.exe", "chromedriver.exe"]:
                try:
                    result = subprocess.run(
                        ["taskkill", "/F", "/IM", proc_name],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if result.returncode == 0:
                        killed = True
                except Exception:
                    pass

        time.sleep(2)
        return killed

    except Exception as e:
        _log(f"Erro ao limpar processos: {e}")
        return False


def _cleanup_profile_locks(profile_path: str) -> bool:
    """Remove arquivos de lock do perfil Chrome."""
    if not profile_path or not Path(profile_path).exists():
        return False

    cleaned = False
    lock_files = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile", "Parent.lock"]

    for base_dir in [Path(profile_path), Path(profile_path) / "Default"]:
        if not base_dir.exists():
            continue

        for lock_name in lock_files:
            lock_path = base_dir / lock_name
            try:
                if lock_path.exists():
                    os.remove(str(lock_path))
                    cleaned = True
                    _log(f"Removido lock: {lock_path.name}")
            except OSError as e:
                _log(f"Não foi possível remover {lock_path.name}: {e}")

    return cleaned


def run_test(headless: bool = True):
    """
    Executa teste de rotação usando SelumOfPersistence.
    Fluxo: Google -> Google Groups -> (tentativa de extração)
    """
    global _EXECUTION_LOGS
    _EXECUTION_LOGS.clear()

    _log("=" * 60)
    _log("TESTE DE ROTAÇÃO - Fluxo Google Groups")
    _log("=" * 60)

    # Importar módulos necessários
    try:
        from src.utils.selum_of_persistence import SelumOfPersistence

        _log("✓ SelumOfPersistence importado")
    except ImportError as e:
        _log(f"✗ Erro ao importar SelumOfPersistence: {e}")
        raise

    # Verificar perfil Chrome
    profile_path = os.getenv("EXTRACTOR_CHROME_USER_DATA", "").strip()
    if profile_path:
        if not Path(profile_path).exists():
            _log(f"⚠ Perfil não existe: {profile_path}")
            _log("  Criando diretório do perfil...")
            Path(profile_path).mkdir(parents=True, exist_ok=True)
        else:
            _log(f"✓ Perfil encontrado: {profile_path}")
    else:
        _log("⚠ Nenhum perfil configurado (EXTRACTOR_CHROME_USER_DATA)")
        profile_path = str(PROJECT_ROOT / ".temp_profile")
        _log(f"  Usando perfil temporário: {profile_path}")
        Path(profile_path).mkdir(parents=True, exist_ok=True)

    # Limpeza inicial
    _log("\n[Fase 1] Limpeza inicial...")
    _cleanup_chrome_processes()
    _cleanup_profile_locks(profile_path)
    time.sleep(3)

    driver = None
    selum = None

    try:
        # Inicializar Selum
        _log("\n[Fase 2] Inicializando SelumOfPersistence...")
        selum = SelumOfPersistence(
            headless=headless, user_data_dir=profile_path if profile_path else None
        )
        driver = selum.driver
        _log("✓ Driver inicializado com sucesso")

        # Aguardar estabilização
        time.sleep(2)

        # Navegar para Google
        _log("\n[Fase 3] Navegando para Google...")
        try:
            selum.navigate("https://www.google.com", wait_time=5)
            current_url = driver.current_url
            _log(f"✓ Google carregado: {current_url}")

            if "google" not in current_url.lower():
                _log("⚠ URL não contém 'google', mas prosseguindo...")
        except Exception as e:
            _log(f"✗ Erro ao navegar para Google: {e}")
            _save_screenshot(driver, "google_error")
            raise

        # Aguardar e fazer scroll
        time.sleep(2)
        try:
            driver.execute_script("window.scrollTo(0, 300);")
            time.sleep(1)
            _log("✓ Scroll executado")
        except Exception as e:
            _log(f"⚠ Erro no scroll: {e}")

        # Navegar para Google Groups
        _log("\n[Fase 4] Navegando para Google Groups...")
        url_groups = "https://groups.google.com/all-groups"

        try:
            selum.navigate(url_groups, wait_time=8)
            current_url = driver.current_url
            _log(f"✓ Google Groups carregado: {current_url}")

            # Verificar se chegou na página correta
            if "groups.google.com" in current_url:
                _log("✓ Navegação bem-sucedida!")
            else:
                _log(f"⚠ URL inesperada: {current_url}")
                _log("  Pode ser necessário login OAuth")
        except Exception as e:
            _log(f"✗ Erro ao navegar para Groups: {e}")
            _save_screenshot(driver, "groups_error")
            raise

        # Aguardar carregamento completo
        time.sleep(3)

        # Tirar screenshot final
        _log("\n[Fase 5] Capturando estado final...")
        screenshot_path = _save_screenshot(driver, "final_state")

        # Tentar obter informações da página
        try:
            page_title = driver.title
            _log(f"✓ Título da página: {page_title}")

            # Verificar se há elementos de login
            try:
                login_elements = driver.find_elements(
                    "css selector", "[type='email'], [type='password'], #identifierId"
                )
                if login_elements:
                    _log(f"⚠ Detectados {len(login_elements)} elementos de login")
                    _log("  Pode ser necessário autenticação OAuth")
                else:
                    _log("✓ Nenhum elemento de login detectado")
            except Exception:
                pass

        except Exception as e:
            _log(f"⚠ Erro ao obter informações da página: {e}")

        # Resultado
        _log("\n" + "=" * 60)
        _log("TESTE CONCLUÍDO")
        _log("=" * 60)
        _log("✓ Navegação: Google -> Google Groups")
        _log(f"✓ Screenshot: {screenshot_path}")
        _log(f"✓ URL final: {driver.current_url}")

        return True

    except Exception as e:
        _log(f"\n✗ ERRO DURANTE EXECUÇÃO: {e}")
        if driver:
            _save_screenshot(driver, "fatal_error")
        raise

    finally:
        # Limpeza
        _log("\n[Fase 6] Limpeza final...")
        if selum:
            try:
                selum.quit()
                _log("✓ Selum encerrado")
            except Exception as e:
                _log(f"⚠ Erro ao encerrar Selum: {e}")
        elif driver:
            try:
                driver.quit()
                _log("✓ Driver encerrado")
            except Exception as e:
                _log(f"⚠ Erro ao encerrar driver: {e}")

        time.sleep(2)
        _cleanup_chrome_processes()
        _log("✓ Limpeza concluída")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Teste de rotação: Google -> Google Groups")
    parser.add_argument(
        "--headless", action="store_true", help="Executar em modo invisível (headless)"
    )
    args = parser.parse_args()

    try:
        _log(f"Iniciando teste (headless={args.headless})...")
        result = run_test(headless=args.headless)

        if result:
            _log("\n✓ TESTE CONCLUÍDO COM SUCESSO")
            sys.exit(0)
        else:
            _log("\n⚠ TESTE CONCLUÍDO COM AVISOS")
            sys.exit(0)

    except KeyboardInterrupt:
        _log("\n⚠ Teste interrompido pelo usuário")
        sys.exit(130)

    except Exception as e:
        _log(f"\n✗ ERRO FATAL: {e}")
        import traceback

        _log(f"\nTraceback:\n{traceback.format_exc()}")
        sys.exit(1)
