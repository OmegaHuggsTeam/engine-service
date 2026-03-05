"""
Extrator de API Keys via Selenium.

Automatiza login em plataformas web, navega até a seção de API Keys
e extrai a chave para salvar em data/raw/api_key.txt ou atualizar o .env.

Suporta:
- Trocar email Google Groups e usar como email para criação de github e usar login github
para logar no groq e coletar a chave de forma gratuita e automatizada.
- Login com usuário/senha (formulário)
- Modo manual: aguarda OAuth (ex: Groq com Google/GitHub)
- Modo headless (navegador invisível)

Credenciais e URLs vêm do .env. Nunca fixe senhas no código.
"""

import json
import os
import random
import sys
import re
import string
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from selenium.common.exceptions import (
    NoSuchElementException,
    TimeoutException,
    WebDriverException,
)

from src.extractors.validators import validate_api_key, ValidationError
from src.utils.logger import get_logger, setup_logger
from src.utils.retry import retry

# Carrega .env antes de usar variáveis
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Telemetria de Agente (checkpoints + Paladino) no undetected-chromedriver
if os.getenv("EXTRACTOR_UC_TELEMETRY", "").lower() in ("true", "1", "yes"):
    try:
        from src.utils.uc_telemetry import install_telemetry
        install_telemetry(timeout_seconds=int(os.getenv("EXTRACTOR_UC_TELEMETRY_TIMEOUT", "10")))
    except Exception:
        pass

# Força encoding UTF-8 na saída
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Setup logger
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FILE = os.getenv("LOG_FILE")
log_path = PROJECT_ROOT / LOG_FILE if LOG_FILE else None
setup_logger("api_key_extractor", level=LOG_LEVEL, log_file=log_path)
logger = get_logger(__name__)

# Diretórios do projeto
RAW_DIR = PROJECT_ROOT / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)
IDENTITY_KEYS_FILE = RAW_DIR / "identity_keys.json"

# Sequencia de cliques ao abrir (header Google). 1o = Gmail, 2o = usuario fornecera
# 1o: <a class="gb_Z" aria-label="Gmail " href="https://mail.google.com/...">
_FIRST_ELEMENTS_ON_OPEN: list[tuple[str, str]] = [
    ("css", "a.gb_Z[aria-label*='Gmail'], a[href*='mail.google.com'][aria-label*='Gmail'], a[data-pid='23'][aria-label*='Gmail']"),
]

# Contrato de bypass: URLs e titulos que indicam travas do Chrome.
# Estender via .env: EXTRACTOR_BYPASS_URLS=url1,url2  EXTRACTOR_BYPASS_TITLES=t1,t2
def _get_bypass_urls():
    base = (
        "chrome://restart", "chrome://crash", "chrome://hang",
        "chrome://kill", "chrome://shutdown", "edge://restart",
    )
    extra = os.getenv("EXTRACTOR_BYPASS_URLS", "").strip()
    return base + tuple(x.strip().lower() for x in extra.split(",") if x.strip())


def _get_bypass_titles():
    base = (
        "restore", "restaurar", "restaurar sess", "restore pages",
        "chrome didn't", "chrome nao", "didn't shut down", "nao encerrou",
        "restore previous", "restaurar sessao",
    )
    extra = os.getenv("EXTRACTOR_BYPASS_TITLES", "").strip()
    return base + tuple(x.strip().lower() for x in extra.split(",") if x.strip())


class ExtractionError(Exception):
    """Erro durante extração de API key."""
    pass


SESSION_CACHE_PATH = Path(__file__).parent / "cache" / "session_google.json"
CHECKPOINT_PATH = Path(__file__).parent / "cache" / "checkpoint.json"
CHECKPOINT_MAX_AGE_HOURS = 24


# ============================================================================
# ANTI-HONEYPOT TECHNIQUES - Visão Híbrida
# ============================================================================

def _find_element_by_text_js(driver, text: str, tag: str = "a", case_sensitive: bool = False) -> dict | None:
    """
    Encontra elemento por texto usando document.evaluate (XPath via JS).
    Ignora Shadow DOM, overlays invisíveis e outras armadilhas.
    
    Args:
        driver: WebDriver do Selenium
        text: Texto a procurar
        tag: Tag HTML (default: 'a' para links)
        case_sensitive: Se True, busca case-sensitive
    
    Returns:
        Dict com {element, x, y, width, height} ou None
    """
    script = """
    function findElementByText(text, tag, caseSensitive) {
        // XPath que ignora case se necessário
        let xpath;
        if (caseSensitive) {
            xpath = `//${tag}[contains(text(), '${text}')]`;
        } else {
            xpath = `//${tag}[contains(translate(text(), 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz'), '${text.toLowerCase()}')]`;
        }
        
        // Usar document.evaluate para buscar
        let result = document.evaluate(
            xpath,
            document,
            null,
            XPathResult.FIRST_ORDERED_NODE_TYPE,
            null
        );
        
        let element = result.singleNodeValue;
        if (!element) return null;
        
        // Obter coordenadas reais (mesmo se invisível para Selenium)
        let rect = element.getBoundingClientRect();
        
        return {
            found: true,
            x: rect.left + rect.width / 2,
            y: rect.top + rect.height / 2,
            width: rect.width,
            height: rect.height,
            text: element.textContent,
            href: element.href || null,
            isVisible: rect.width > 0 && rect.height > 0,
            isInViewport: rect.top >= 0 && rect.left >= 0 && 
                         rect.bottom <= window.innerHeight && 
                         rect.right <= window.innerWidth
        };
    }
    
    return findElementByText(arguments[0], arguments[1], arguments[2]);
    """
    
    try:
        result = driver.execute_script(script, text, tag, case_sensitive)
        if result and result.get("found"):
            logger.info(f"Elemento encontrado via JS: {result.get('text', '')[:50]}")
            return result
        return None
    except Exception as e:
        logger.warning(f"Erro ao buscar elemento via JS: {e}")
        return None
def _find_delivery_email_field_coordinates(driver) -> dict | None:
    """
    Localiza o campo de email de entrega e retorna suas coordenadas na tela.

    Usa injeção de JavaScript para:
    1. Encontrar label contendo "E-mail de entrega" ou "Delivery email"
    2. Obter o campo de input associado via atributo 'for', querySelector ou sibling
    3. Rolar o campo para o centro da visualização (scrollIntoView)
    4. Calcular coordenadas da tela a partir do bounding rectangle (centro do elemento)

    A busca tenta múltiplas estratégias para localizar o input:
    - Via atributo 'for' do label (targetLabel.htmlFor)
    - Via querySelector dentro do label
    - Via elementos siblings adjacentes ao label

    Args:
        driver: Instância do Selenium WebDriver

    Returns:
        dict: {"x": int, "y": int} com coordenadas do centro do campo se encontrado,
              None se o campo não for localizado

    Note:
        - As coordenadas retornadas são relativas ao viewport, não à tela absoluta
        - Erros durante a execução do JavaScript são capturados e registrados no log
        - A função não lança exceções, retornando None em caso de falha
    """
    script = """
    function findDeliveryEmailField() {
        // Procurar por labels com texto "E-mail de entrega" ou "Delivery email"
        const labels = Array.from(document.querySelectorAll('label'));
        const targetLabel = labels.find(label => {
            const text = label.textContent.trim();
            return text.includes('E-mail de entrega') || text.includes('Delivery email');
        });

        if (!targetLabel) {
            return null;
        }

        // Obter o campo de input associado
        let inputField = null;

        // Tentar via atributo 'for'
        if (targetLabel.htmlFor) {
            inputField = document.getElementById(targetLabel.htmlFor);
        }

        // Tentar via querySelector (campo dentro ou próximo ao label)
        if (!inputField) {
            inputField = targetLabel.querySelector('input');
        }

        // Tentar campo próximo ao label
        if (!inputField) {
            let sibling = targetLabel.nextElementSibling;
            while (sibling && !inputField) {
                if (sibling.tagName === 'INPUT') {
                    inputField = sibling;
                } else {
                    inputField = sibling.querySelector('input');
                }
                sibling = sibling.nextElementSibling;
            }
        }

        if (!inputField) {
            return null;
        }

        // Rolar o elemento para o centro da visualização
        inputField.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });

        // Aguardar um momento para a rolagem completar
        // (em contexto síncrono, retornamos imediatamente, mas o navegador processará)

        // Obter coordenadas do elemento
        const rect = inputField.getBoundingClientRect();

        return {
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            width: rect.width,
            height: rect.height
        };
    }

    return findDeliveryEmailField();
    """

    try:
        result = driver.execute_script(script)
        if result and 'x' in result and 'y' in result:
            logger.info(f"Campo de email de entrega encontrado em ({result['x']}, {result['y']})")
            return {"x": result['x'], "y": result['y']}

        logger.error("Campo de email de entrega não encontrado. Procurado por labels: ['E-mail de entrega', 'Delivery email']")
        return None

    except Exception as e:
        logger.error(f"Erro ao localizar campo de email de entrega: {e}", exc_info=True)
        return None



def _update_field_with_hardware_input(x: int, y: int, new_value: str) -> bool:
    """
    Atualiza um campo usando operações de teclado e mouse em nível de hardware.

    Executa a seguinte sequência de operações físicas via pyautogui:
    1. Move o mouse para (x, y) com duração suave de 0.3s
    2. Clica no campo
    3. Ctrl+A (selecionar todo o texto)
    4. Backspace (limpar o campo)
    5. Digita o novo valor caractere por caractere (interval=0.05s)

    A função implementa retry logic: se a primeira tentativa falhar, a operação
    será repetida uma vez antes de retornar False (máximo de 2 tentativas).

    Args:
        x: Coordenada X da tela (pixels do lado esquerdo)
        y: Coordenada Y da tela (pixels do topo)
        new_value: Texto a digitar no campo (deve conter apenas caracteres ASCII)

    Returns:
        bool: True se as operações foram bem-sucedidas, False caso contrário

    Note:
        - Requer pyautogui instalado: pip install pyautogui
        - Se pyautogui não estiver disponível, retorna False e registra warning
        - Delays entre operações garantem que o navegador processe cada ação
        - Coordenadas devem ser absolutas na tela, não relativas ao viewport
        - Todos os erros são capturados e registrados com exc_info=True
    """
    try:
        import pyautogui
    except ImportError:
        logger.warning("pyautogui não instalado. Instale com: pip install pyautogui")
        return False

    max_attempts = 2

    for attempt in range(1, max_attempts + 1):
        try:
            if attempt > 1:
                logger.info(f"Tentativa {attempt}/{max_attempts} de atualizar campo em ({x}, {y})")
            else:
                logger.info(f"Atualizando campo em ({x}, {y}) com valor: {new_value}")

            # 1. Mover mouse para a posição com duração suave
            pyautogui.moveTo(x, y, duration=0.3)
            time.sleep(0.2)

            # 2. Clicar no campo
            pyautogui.click()
            time.sleep(0.2)

            # 3. Selecionar todo o texto (Ctrl+A)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)

            # 4. Limpar o campo (Backspace)
            pyautogui.press('backspace')
            time.sleep(0.2)

            # 5. Digitar o novo valor caractere por caractere
            pyautogui.typewrite(new_value, interval=0.05)
            time.sleep(0.2)

            logger.info("Campo atualizado com sucesso via hardware")
            return True

        except Exception as e:
            logger.error(
                f"Erro ao atualizar campo com hardware (tentativa {attempt}/{max_attempts}): {e}",
                exc_info=True
            )

            if attempt < max_attempts:
                logger.info(f"Repetindo operação de atualização do campo...")
                time.sleep(0.5)  # Aguardar antes de tentar novamente
            else:
                logger.error(
                    f"Falha ao atualizar campo após {max_attempts} tentativas em coordenadas ({x}, {y})"
                )
                return False

    return False

def _find_save_button_coordinates(driver) -> dict | None:
    """
    Localiza o botão "Salvar alterações" e retorna suas coordenadas na tela.

    Usa injeção de JavaScript para:
    1. Encontrar botão/input contendo "Salvar alterações" ou "Save changes"
    2. Rolar o botão para o centro da visualização (scrollIntoView)
    3. Calcular coordenadas da tela a partir do bounding rectangle (centro do elemento)

    A busca procura nos seguintes tipos de elementos:
    - <button> tags
    - <input type="button">
    - <input type="submit">

    Args:
        driver: Instância do Selenium WebDriver

    Returns:
        dict: {"x": int, "y": int} com coordenadas do centro do botão se encontrado,
              None se o botão não for localizado

    Note:
        - As coordenadas retornadas são relativas ao viewport, não à tela absoluta
        - A busca verifica tanto textContent quanto value do elemento
        - Erros durante a execução do JavaScript são capturados e registrados no log
        - A função não lança exceções, retornando None em caso de falha
    """
    script = """
    function findSaveButton() {
        // Procurar por botões com texto "Salvar alterações" ou "Save changes"
        const buttons = Array.from(document.querySelectorAll('button, input[type="button"], input[type="submit"]'));
        const targetButton = buttons.find(button => {
            const text = button.textContent.trim() || button.value || '';
            return text.includes('Salvar alterações') || text.includes('Save changes');
        });

        if (!targetButton) {
            return null;
        }

        // Rolar o elemento para o centro da visualização
        targetButton.scrollIntoView({ behavior: 'smooth', block: 'center', inline: 'center' });

        // Obter coordenadas do elemento
        const rect = targetButton.getBoundingClientRect();

        return {
            x: Math.round(rect.left + rect.width / 2),
            y: Math.round(rect.top + rect.height / 2),
            width: rect.width,
            height: rect.height
        };
    }

    return findSaveButton();
    """

    try:
        result = driver.execute_script(script)
        if result and 'x' in result and 'y' in result:
            logger.info(f"Botão de salvar encontrado em ({result['x']}, {result['y']})")
            return {"x": result['x'], "y": result['y']}

        logger.error("Botão de salvar não encontrado. Procurado por textos: ['Salvar alterações', 'Save changes']")
        return None

    except Exception as e:
        logger.error(f"Erro ao localizar botão de salvar: {e}", exc_info=True)
        return None



def _click_with_physical_mouse(driver, x: int, y: int) -> bool:
    """
    Simula clique físico usando pyautogui (força isTrusted=true).
    
    Args:
        driver: WebDriver do Selenium
        x: Coordenada X na tela
        y: Coordenada Y na tela
    
    Returns:
        True se sucesso, False se falhar
    """
    try:
        import pyautogui
        
        # Obter posição da janela do navegador
        window_pos = driver.execute_script("""
            return {
                x: window.screenX,
                y: window.screenY
            };
        """)
        
        # Calcular posição absoluta na tela
        screen_x = window_pos['x'] + x
        screen_y = window_pos['y'] + y
        
        logger.info(f"Movendo mouse físico para ({screen_x}, {screen_y})")
        
        # Mover mouse suavemente (mais humano)
        pyautogui.moveTo(screen_x, screen_y, duration=0.3)
        time.sleep(0.1)
        
        # Clicar
        pyautogui.click()
        logger.info("Clique físico executado")
        
        return True
        
    except ImportError:
        logger.warning("pyautogui não instalado. Instale com: pip install pyautogui")
        return False
    except Exception as e:
        logger.warning(f"Erro ao clicar com mouse físico: {e}")
        return False


def update_delivery_email_hardware(driver, new_email: str, timeout: int = 10) -> bool:
    """
    Atualiza o campo de email de entrega no Google Groups usando automação de hardware.

    Esta função orquestra todo o processo de atualização do email de entrega,
    utilizando operações de hardware (pyautogui) para gerar eventos isTrusted=true
    que não são detectados como automação pelo navegador.

    Fluxo de execução:
    1. Localiza o campo de email de entrega usando JavaScript
    2. Atualiza o campo usando operações de hardware (mouse e teclado físicos)
    3. Verifica se o valor foi atualizado corretamente via JavaScript
    4. Localiza o botão "Salvar alterações"
    5. Clica no botão usando mouse físico
    6. Aguarda 2 segundos para a página processar a operação

    Args:
        driver: Instância do Selenium WebDriver com sessão ativa no Google Groups
        new_email: O novo endereço de email a ser definido (formato: user@domain.com)
        timeout: Tempo máximo de espera para operações em segundos (padrão: 10)
                 Nota: Atualmente não utilizado, reservado para implementação futura

    Returns:
        bool: True se o email foi atualizado com sucesso, False caso contrário

    Raises:
        Nenhuma exceção é lançada - todos os erros são capturados e registrados

    Note:
        - Requer pyautogui instalado: pip install pyautogui
        - A página deve estar carregada na seção de configurações do Google Groups
        - Todos os passos são registrados no log com nível INFO
        - Falhas em qualquer etapa resultam em retorno False e log de erro
        - A verificação do campo garante que o valor foi realmente atualizado

    Example:
        >>> from selenium import webdriver
        >>> driver = webdriver.Chrome()
        >>> driver.get("https://groups.google.com/g/mygroup/settings")
        >>> # Aguardar login manual se necessário
        >>> success = update_delivery_email_hardware(driver, "new@example.com")
        >>> if success:
        ...     print("Email atualizado com sucesso!")
        ... else:
        ...     print("Falha ao atualizar email. Verifique os logs.")
        >>> driver.quit()
    """
    try:
        logger.info(f"Iniciando atualização de email de entrega para: {new_email}")

        # 1. Localizar o campo de email de entrega
        logger.info("Passo 1: Localizando campo de email de entrega...")
        field_coords = _find_delivery_email_field_coordinates(driver)

        if not field_coords:
            logger.error("Falha ao localizar campo de email de entrega")
            return False

        logger.info(f"Campo encontrado em coordenadas: {field_coords}")

        # 2. Atualizar o campo usando hardware
        logger.info("Passo 2: Atualizando campo com entrada de hardware...")
        update_success = _update_field_with_hardware_input(
            field_coords['x'],
            field_coords['y'],
            new_email
        )

        if not update_success:
            logger.error("Falha ao atualizar campo com hardware")
            return False

        # Aguardar um momento para o campo processar a entrada
        time.sleep(0.5)

        # 3. Verificar se o valor do campo corresponde ao novo email
        logger.info("Passo 3: Verificando valor do campo...")
        verification_script = """
        function verifyFieldValue() {
            const labels = Array.from(document.querySelectorAll('label'));
            const targetLabel = labels.find(label => {
                const text = label.textContent.trim();
                return text.includes('E-mail de entrega') || text.includes('Delivery email');
            });

            if (!targetLabel) return null;

            let inputField = null;
            if (targetLabel.htmlFor) {
                inputField = document.getElementById(targetLabel.htmlFor);
            }
            if (!inputField) {
                inputField = targetLabel.querySelector('input');
            }
            if (!inputField) {
                let sibling = targetLabel.nextElementSibling;
                while (sibling && !inputField) {
                    if (sibling.tagName === 'INPUT') {
                        inputField = sibling;
                    } else {
                        inputField = sibling.querySelector('input');
                    }
                    sibling = sibling.nextElementSibling;
                }
            }

            return inputField ? inputField.value : null;
        }

        return verifyFieldValue();
        """

        try:
            actual_value = driver.execute_script(verification_script)

            if actual_value != new_email:
                logger.warning(
                    f"Verificação do campo falhou. Esperado: {new_email}, Obtido: {actual_value}"
                )
                return False

            logger.info(f"Campo verificado com sucesso: {actual_value}")

        except Exception as e:
            logger.error(f"Erro ao verificar valor do campo: {e}", exc_info=True)
            return False

        # 4. Localizar o botão de salvar
        logger.info("Passo 4: Localizando botão de salvar...")
        save_button_coords = _find_save_button_coordinates(driver)

        if not save_button_coords:
            logger.error("Falha ao localizar botão de salvar")
            return False

        logger.info(f"Botão de salvar encontrado em coordenadas: {save_button_coords}")

        # 5. Clicar no botão de salvar usando mouse físico
        logger.info("Passo 5: Clicando no botão de salvar com mouse físico...")
        click_success = _click_with_physical_mouse(
            driver,
            save_button_coords['x'],
            save_button_coords['y']
        )

        if not click_success:
            logger.error("Falha ao clicar no botão de salvar")
            return False

        # 6. Aguardar a página processar a operação de salvamento
        logger.info("Passo 6: Aguardando processamento da operação de salvamento...")
        time.sleep(2)  # Aguardar 2 segundos para a página processar

        logger.info("Atualização de email de entrega concluída com sucesso!")
        return True

    except Exception as e:
        logger.error(
            f"Erro durante atualização de email de entrega: {e}",
            exc_info=True
        )
        return False



def _force_dom_refresh(driver) -> None:
    """
    Força refresh do DOM após 2FA para evitar "estado de choque".
    Usa scroll suave em vez de refresh completo (mais rápido).
    
    Args:
        driver: WebDriver do Selenium
    """
    try:
        logger.info("Forçando refresh do DOM...")
        
        # Scroll suave para baixo e volta (força re-render)
        driver.execute_script("""
            window.scrollTo({
                top: 300,
                behavior: 'smooth'
            });
        """)
        time.sleep(0.5)
        
        driver.execute_script("""
            window.scrollTo({
                top: 0,
                behavior: 'smooth'
            });
        """)
        time.sleep(0.5)
        
        logger.info("DOM refreshed")
        
    except Exception as e:
        logger.warning(f"Erro ao refresh DOM: {e}")


def _detect_honeypot_overlay(driver) -> bool:
    """
    Detecta se há overlay invisível cobrindo a página (honeypot).
    
    Args:
        driver: WebDriver do Selenium
    
    Returns:
        True se overlay detectado, False caso contrário
    """
    script = """
    // Procurar por elementos com z-index alto e opacity baixa
    let elements = document.querySelectorAll('*');
    for (let el of elements) {
        let style = window.getComputedStyle(el);
        let zIndex = parseInt(style.zIndex);
        let opacity = parseFloat(style.opacity);
        let display = style.display;
        let visibility = style.visibility;
        
        // Overlay suspeito: z-index alto + (opacity baixa OU visibility hidden)
        if (zIndex > 1000 && (opacity < 0.1 || visibility === 'hidden')) {
            let rect = el.getBoundingClientRect();
            // Se cobre boa parte da tela
            if (rect.width > window.innerWidth * 0.5 && rect.height > window.innerHeight * 0.5) {
                return {
                    detected: true,
                    element: el.tagName,
                    zIndex: zIndex,
                    opacity: opacity,
                    visibility: visibility
                };
            }
        }
    }
    return {detected: false};
    """
    
    try:
        result = driver.execute_script(script)
        if result.get("detected"):
            logger.warning(f"⚠ HONEYPOT OVERLAY DETECTADO: {result}")
            return True
        return False
    except Exception as e:
        logger.warning(f"Erro ao detectar overlay: {e}")
        return False


def _click_element_anti_honeypot(driver, element_text: str, wait_obj, tag: str = "a") -> bool:
    """
    Técnica de Visão Híbrida para clicar em elementos evitando honeypots.
    
    Estratégia em 3 camadas:
    1. Tentar Selenium normal (wait_click)
    2. Se falhar, usar JS (document.evaluate) para encontrar
    3. Se encontrar, usar mouse físico (pyautogui) para clicar
    
    Args:
        driver: WebDriver do Selenium
        element_text: Texto do elemento a clicar
        wait_obj: WebDriverWait object
        tag: Tag HTML (default: 'a')
    
    Returns:
        True se sucesso, False se falhar
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException
    
    logger.info(f"Tentando clicar em: '{element_text}' (anti-honeypot)")
    
    # Detectar overlay antes de tentar
    if _detect_honeypot_overlay(driver):
        logger.warning("Overlay detectado! Pulando para método JS direto...")
    else:
        # Camada 1: Selenium normal
        try:
            logger.info("Camada 1: Tentando Selenium normal...")
            el = wait_obj.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, element_text)))
            el.click()
            logger.info("✓ Clique Selenium bem-sucedido")
            return True
        except TimeoutException:
            logger.warning("✗ Selenium timeout - elemento não clicável")
        except Exception as e:
            logger.warning(f"✗ Selenium falhou: {e}")
    
    # Camada 2: Busca via JS
    logger.info("Camada 2: Buscando via document.evaluate (JS)...")
    element_info = _find_element_by_text_js(driver, element_text, tag=tag, case_sensitive=False)
    
    if not element_info:
        logger.error(f"✗ Elemento '{element_text}' não encontrado nem via JS")
        return False
    
    logger.info(f"✓ Elemento encontrado: {element_info}")
    
    # Verificar se está visível
    if not element_info.get("isVisible"):
        logger.warning("⚠ Elemento existe mas não está visível (possível honeypot)")
    
    # Camada 3: Clique físico
    logger.info("Camada 3: Tentando clique físico (pyautogui)...")
    
    # Scroll para elemento se não estiver no viewport
    if not element_info.get("isInViewport"):
        logger.info("Scrollando para elemento...")
        driver.execute_script(f"window.scrollTo(0, {element_info['y'] - 200});")
        time.sleep(0.5)
    
    # Tentar clique físico
    if _click_with_physical_mouse(driver, int(element_info['x']), int(element_info['y'])):
        logger.info("✓ Clique físico bem-sucedido")
        return True
    
    # Fallback: JS click direto
    logger.info("Fallback: Tentando JS click direto...")
    try:
        if element_info.get("href"):
            driver.execute_script(f"window.location.href = '{element_info['href']}';")
            logger.info("✓ Navegação via JS bem-sucedida")
            return True
    except Exception as e:
        logger.error(f"✗ JS click falhou: {e}")
    
    return False



def mark_step_as_complete(step_name: str) -> bool:
    """
    Registra que um passo foi concluído com sucesso.
    Salva em checkpoint.json: {"step_name": "success", "timestamp": "..."}.
    """
    try:
        CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        if CHECKPOINT_PATH.exists():
            try:
                data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
            except Exception:
                pass
        data[step_name] = "success"
        data["timestamp"] = datetime.now().isoformat()
        data[f"{step_name}_at"] = datetime.now().isoformat()
        CHECKPOINT_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"mark_step_as_complete: {step_name}")
        return True
    except Exception as e:
        logger.debug(f"mark_step_as_complete falhou: {e}")
        return False


def is_step_recently_complete(step_name: str) -> bool:
    """
    Verifica se o passo foi concluído e o checkpoint tem menos de 24h.
    Se True, o Agente pode pular a etapa.
    """
    if not CHECKPOINT_PATH.exists():
        return False
    try:
        data = json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        if data.get(step_name) != "success":
            return False
        ts = data.get("timestamp") or data.get(f"{step_name}_at", "")
        if not ts:
            return False
        try:
            saved = datetime.fromisoformat(ts.replace("Z", "").split("+")[0])
        except ValueError:
            return False
        age_hours = (datetime.now() - saved).total_seconds() / 3600
        return age_hours < CHECKPOINT_MAX_AGE_HOURS
    except Exception:
        return False


def save_happy_path_state(driver) -> bool:
    """
    Salva cookies, localStorage e sessionStorage para reciclagem de sessão.
    Chamado após sucesso do execute_identity_swap.
    Mantém estado de "Dispositivo Confiável".
    """
    if driver is None:
        return False
    try:
        SESSION_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        cookies = driver.get_cookies()
        local_storage = driver.execute_script(
            "return Object.assign({}, window.localStorage);"
        ) or {}
        session_storage = driver.execute_script(
            "return Object.assign({}, window.sessionStorage);"
        ) or {}
        data = {
            "cookies": cookies,
            "localStorage": dict(local_storage),
            "sessionStorage": dict(session_storage),
            "url": driver.current_url or "",
            "saved_at": datetime.now().isoformat(),
        }
        SESSION_CACHE_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        logger.info(f"save_happy_path_state: sessao salva em {SESSION_CACHE_PATH}")
        return True
    except Exception as e:
        logger.debug(f"save_happy_path_state falhou: {e}")
        return False


def load_session_from_cache(driver) -> bool:
    """
    Injeta cookies, localStorage e sessionStorage do session_google.json.
    Usado nas Estratégias 0 e 2 para pular login/2FA (Happy Path).
    Retorna True se injetou e a URL nao redirecionou para /login.
    """
    if not SESSION_CACHE_PATH.exists():
        return False
    try:
        data = json.loads(SESSION_CACHE_PATH.read_text(encoding="utf-8"))
        cookies = data.get("cookies", [])
        local_storage = data.get("localStorage", {})
        session_storage = data.get("sessionStorage", {})
        if not cookies:
            return False

        driver.get("https://www.google.com")
        time.sleep(1)
        for c in cookies:
            try:
                driver.add_cookie(c)
            except Exception:
                pass

        driver.get("https://groups.google.com/all-groups")
        time.sleep(3)

        for key, val in (local_storage or {}).items():
            try:
                driver.execute_script(f"window.localStorage.setItem(arguments[0], arguments[1]);", key, val)
            except Exception:
                pass
        for key, val in (session_storage or {}).items():
            try:
                driver.execute_script(f"window.sessionStorage.setItem(arguments[0], arguments[1]);", key, val)
            except Exception:
                pass

        driver.refresh()
        time.sleep(2)
        url = (driver.current_url or "").lower()
        if "/login" in url or "accounts.google" in url or "signin" in url:
            return False
        logger.info("load_session_from_cache: Happy Path detectado. Pulando desafio de 2FA.")
        return True
    except Exception as e:
        logger.debug(f"load_session_from_cache falhou: {e}")
        return False


def inject_cookies_from_env(driver) -> bool:
    """
    Injeta cookies de sessão do .env via driver.add_cookie().
    Lê EXTRACTOR_GOOGLE_COOKIES ou EXTRACTOR_SESSION_COOKIES (JSON array de dicts).
    Formato: [{"name":"SID","value":"xxx","domain":".google.com"}, ...]
    Deve ser chamado ANTES de navegar para Groups. Navega para google.com para estabelecer dominio.
    Retorna True se injetou pelo menos um cookie.
    """
    raw = (
        os.getenv("EXTRACTOR_GOOGLE_COOKIES", "").strip()
        or os.getenv("EXTRACTOR_SESSION_COOKIES", "").strip()
    )
    if not raw:
        return False
    try:
        cookies = json.loads(raw)
        if not isinstance(cookies, list) or not cookies:
            return False
    except json.JSONDecodeError:
        return False

    try:
        driver.get("https://www.google.com")
        time.sleep(1)
        injected = 0
        for c in cookies:
            if not isinstance(c, dict) or "name" not in c or "value" not in c:
                continue
            cookie = dict(c)
            if "domain" not in cookie:
                cookie["domain"] = ".google.com"
            try:
                driver.add_cookie(cookie)
                injected += 1
            except Exception:
                pass
        if injected:
            logger.info(f"inject_cookies_from_env: {injected} cookies injetados")
        return injected > 0
    except Exception as e:
        logger.debug(f"inject_cookies_from_env falhou: {e}")
        return False


LOCK_FILES = ["SingletonLock", "SingletonCookie", "SingletonSocket", "lockfile", "Parent.lock"]


def _kill_process_holding_file(filepath: Path) -> bool:
    """Tenta matar o processo que segura o arquivo via psutil."""
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "open_files"]):
            try:
                for f in proc.open_files() or []:
                    if Path(f.path).resolve() == filepath.resolve():
                        proc.kill()
                        logger.info(f"Processo {proc.pid} morto (segurava {filepath.name})")
                        return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
    except ImportError:
        pass
    return False


def _remove_profile_locks(user_data_dir: str | None) -> None:
    """
    Remove arquivos de lock do perfil (SingletonLock, Parent.lock, etc).
    Usa os.remove em try/except. Se falhar, tenta matar processo via psutil.
    """
    if not user_data_dir or not Path(user_data_dir).exists():
        return
    dirs_to_clean = [Path(user_data_dir)]
    default_dir = Path(user_data_dir) / "Default"
    if default_dir.exists():
        dirs_to_clean.append(default_dir)
    for base in dirs_to_clean:
        for name in LOCK_FILES:
            p = base / name
            try:
                if p.exists():
                    os.remove(str(p))
                    logger.info(f"Removido lock: {base.name}/{name}")
            except OSError as e:
                if _kill_process_holding_file(p):
                    time.sleep(1)
                    try:
                        if p.exists():
                            os.remove(str(p))
                            logger.info(f"Removido lock apos kill: {base.name}/{name}")
                    except OSError:
                        pass
                else:
                    logger.warning(f"Nao foi possivel remover {name}: {e}")


def _deep_clean_for_profile(user_data_dir: str | None) -> None:
    """
    Limpeza Hard: taskkill Chrome/chromedriver, remove locks fisicamente, espera 5s.
    Garante acesso exclusivo ao perfil real antes de instanciar o driver.
    """
    if not user_data_dir or not Path(user_data_dir).exists():
        return
    import subprocess
    for _ in range(2):
        try:
            for proc in ["chrome.exe", "chromedriver.exe"]:
                subprocess.run(
                    ["taskkill", "/F", "/IM", proc, "/T"],
                    capture_output=True, text=True, timeout=15,
                )
        except Exception:
            pass
        time.sleep(2)
    _remove_profile_locks(user_data_dir)
    logger.info("Aguardando 5s apos limpeza antes de abrir Chrome...")
    time.sleep(5)


def _verify_profile_ready(profile_path: str | None) -> None:
    """
    Verifica se o diretorio do perfil existe. Tenta remover locks.
    Levanta ExtractionError com mensagem clara se invalido.
    """
    if not profile_path or not profile_path.strip():
        return
    p = Path(profile_path.strip())
    if not p.exists():
        raise ExtractionError(
            f"Diretorio do perfil nao existe: {profile_path}\n"
            "Verifique EXTRACTOR_CHROME_USER_DATA no .env ou crie o diretorio."
        )
    _remove_profile_locks(profile_path)
    still_locked = [n for n in ["SingletonLock", "Parent.lock", "SingletonSocket"] if (p / n).exists()]
    if still_locked:
        raise ExtractionError(
            f"Perfil bloqueado. Nao foi possivel remover: {', '.join(still_locked)}\n"
            "Feche o Chrome completamente ou use EXTRACTOR_KILL_CHROME_BEFORE=true no .env."
        )


def _create_driver_with_options(options, headless: bool):
    """Cria driver com as options dadas. Usado por _get_driver."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    driver.set_page_load_timeout(60)
    if driver.window_handles:
        driver.switch_to.window(driver.window_handles[0])
    driver.maximize_window()
    _bypass_chrome_protections(driver)
    _focus_main_window(driver)
    return driver


def _create_undetected_driver(use_profile_path: str | None, headless: bool, extra_args: list[str] | None = None):
    """
    Cria driver com undetected-chromedriver (evita deteccao "navegador nao seguro").
    Headless nao e oficialmente suportado; em headless usa driver normal.
    """
    try:
        import undetected_chromedriver as uc
    except ImportError:
        raise ExtractionError(
            "undetected-chromedriver nao instalado. Execute: pip install undetected-chromedriver"
        ) from None

    # Blindagem de Sigilo: User-Agent de Chrome real
    _REAL_CHROME_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.6778.200 Safari/537.36"
    )
    opts = uc.ChromeOptions()
    opts.page_load_strategy = "eager"  # DOM pronto, nao espera recursos (evita travar em paginas lentas)
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--disable-browser-side-navigation")
    opts.add_argument("--disable-restore-session-state")
    opts.add_argument("--window-size=1920,1080")
    opts.add_argument("--disable-blink-features=AutomationControlled")
    if headless:
        opts.add_argument("--headless=new")
        opts.add_argument(f"--user-agent={_REAL_CHROME_UA}")
    if use_profile_path:
        Path(use_profile_path).mkdir(parents=True, exist_ok=True)
        opts.add_argument(f"--user-data-dir={use_profile_path}")
        opts.add_argument(f"--profile-directory={os.getenv('EXTRACTOR_CHROME_PROFILE', 'Default').strip() or 'Default'}")
        opts.add_argument("--no-first-run")
        opts.add_argument("--no-default-browser-check")
    for arg in (extra_args or []):
        if arg and arg.startswith("--"):
            opts.add_argument(arg)

    driver = uc.Chrome(options=opts)
    driver.set_page_load_timeout(60)
    if driver.window_handles:
        driver.switch_to.window(driver.window_handles[0])
    driver.maximize_window()
    _bypass_chrome_protections(driver)
    _focus_main_window(driver)
    return driver


def _bypass_chrome_protections(driver) -> None:
    """
    Contorna travas/protecoes do Chrome:
    - Fecha abas de protecao (restore, crash, etc.)
    - Remove foco de link selecionado (navega para about:blank)
    - Garante que a aba principal esta pronta para uso
    """
    try:
        handles = list(driver.window_handles)
        if not handles:
            return
        # URLs de protecao que indicam aba indesejada
        tabs_to_close = []
        for h in handles:
            try:
                driver.switch_to.window(h)
                url = (driver.current_url or "").lower()
                title = (driver.title or "").lower()
                if any(p in url for p in _get_bypass_urls()):
                    tabs_to_close.append(h)
                elif any(t in title for t in _get_bypass_titles()):
                    tabs_to_close.append(h)
            except Exception:
                continue
        # Fechar abas de protecao (manter pelo menos 1)
        for h in tabs_to_close:
            if len(driver.window_handles) > 1:
                try:
                    driver.switch_to.window(h)
                    driver.close()
                except Exception:
                    pass
        # Focar na primeira aba e limpar estado (remove link selecionado / foco indesejado)
        if driver.window_handles:
            driver.switch_to.window(driver.window_handles[0])
            try:
                driver.execute_script("""
                    if (document.activeElement && document.activeElement.blur) document.activeElement.blur();
                    window.getSelection && window.getSelection().removeAllRanges();
                    window.location.href = 'about:blank';
                """)
            except Exception:
                driver.execute_script("window.location.href = 'about:blank';")
            time.sleep(0.5)
    except Exception as e:
        logger.warning(f"Bypass protecoes: {e}")


def _focus_main_window(driver) -> None:
    """Mitiga aba fantasma: window.focus + 2s delay apos get_driver."""
    try:
        driver.execute_script("window.focus();")
        time.sleep(2)
    except Exception as e:
        logger.debug(f"Focus main window: {e}")


def _robust_navigate(driver, url: str, timeout: int = 20, debug: bool = True) -> bool:
    """
    Navega com: (1) driver.get, (2) window.location.replace, (3) Ctrl+L+send_keys.
    Retorna True se navegou com sucesso.
    """
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains

    def _print(msg: str):
        if debug:
            print(f"  >> {msg}", flush=True)
        logger.info(msg)

    driver.set_page_load_timeout(timeout)
    for attempt, (name, do_nav) in enumerate([
        ("driver.get", lambda: driver.get(url)),
        ("location.replace", lambda: driver.execute_script(f"window.location.replace('{url}');")),
    ], 1):
        try:
            _print(f"Tentativa {attempt}: {name}...")
            do_nav()
            time.sleep(2)
            if driver.current_url and "about:blank" not in (driver.current_url or ""):
                _print(f"OK: {name} funcionou")
                return True
        except Exception as e:
            _print(f"Falhou: {name} - {e}")
            logger.warning(f"Nav {name} falhou: {e}")
    try:
        _print("Tentativa 3: Ctrl+L + teclado (digitar URL)...")
        ac = ActionChains(driver)
        ac.key_down(Keys.CONTROL).send_keys("l").key_up(Keys.CONTROL).perform()
        time.sleep(0.5)
        ac.send_keys(url).send_keys(Keys.ENTER).perform()
        time.sleep(3)
        ok = bool(driver.current_url and driver.current_url != "about:blank")
        if ok:
            _print("OK: navegacao por teclado funcionou")
        else:
            _print("Falhou: navegacao por teclado nao alterou URL")
        return ok
    except Exception as e:
        _print(f"Falhou: teclado - {e}")
        logger.warning(f"Nav por teclado falhou: {e}")
        return False


def _click_first_elements_on_open(driver, wait_time: float = 3) -> None:
    """
    Clica na sequencia _FIRST_ELEMENTS_ON_OPEN (ex: Gmail no header Google).
    Chamar apos carregar a primeira pagina com header Google.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait = WebDriverWait(driver, wait_time)
    by_map = {"css": By.CSS_SELECTOR, "xpath": By.XPATH, "link": By.PARTIAL_LINK_TEXT}
    for kind, sel in _FIRST_ELEMENTS_ON_OPEN:
        try:
            by = by_map.get(kind.lower(), By.CSS_SELECTOR)
            el = wait.until(EC.element_to_be_clickable((by, sel)))
            el.click()
            logger.info(f"Clique primeiro elemento: {sel[:50]}...")
            time.sleep(random.uniform(1, 2))
        except TimeoutException:
            logger.debug(f"Primeiro elemento nao encontrado: {sel[:50]}")
            break


def _random_click_on_page(driver) -> None:
    """
    Clica em um ponto aleatorio da pagina (simula comportamento humano, evita padroes roboticos).
    Chamar apos cada navegacao para nova pagina.
    """
    try:
        from selenium.webdriver.common.by import By
        from selenium.webdriver.common.action_chains import ActionChains

        body = driver.find_element(By.TAG_NAME, "body")
        w = max(100, body.size.get("width", 800))
        h = max(100, body.size.get("height", 600))
        if w < 200 or h < 200:
            try:
                w, h = driver.execute_script("return [window.innerWidth, window.innerHeight];")
            except Exception:
                pass
        x = random.randint(50, max(51, int(w) - 50))
        y = random.randint(50, max(51, int(h) - 50))
        ActionChains(driver).move_to_element_with_offset(body, x, y).click().perform()
        time.sleep(random.uniform(0.2, 0.6))
    except Exception as e:
        logger.debug(f"Random click: {e}")


def _trigger_chrome_ai_panel(driver) -> bool:
    """
    Tenta abrir o painel lateral de IA do Chrome via atalhos de teclado.
    Tática A: Ctrl+Shift+L (ou atalho configurado). Tática B: deep links.
    Retorna True se executou sem erro (não garante que o painel abriu).
    Nota: O Selenium não enxerga elementos fora do DOM da página (barra lateral).
    Para capturar texto da IA: use pyautogui + OCR ou Accessibility Tree (CDP).
    """
    try:
        from selenium.webdriver.common.keys import Keys
        from selenium.webdriver.common.action_chains import ActionChains

        # Tática A: Atalhos de teclado (Chrome 3.14+ pode usar Ctrl+Shift+L ou similar)
        ac = ActionChains(driver)
        ac.key_down(Keys.CONTROL).key_down(Keys.SHIFT).send_keys("l").key_up(Keys.SHIFT).key_up(Keys.CONTROL).perform()
        time.sleep(1)
        logger.info("Atalho Ctrl+Shift+L enviado para painel IA")
        return True
    except Exception as e:
        logger.debug(f"Atalho IA falhou: {e}")
        try:
            # Tática B: Deep link (Chrome pode ter chrome://settings/ai)
            driver.get("chrome://settings/ai")
            time.sleep(2)
            return True
        except Exception:
            pass
        return False


def _get_accessibility_tree_for_ai_text(driver) -> str | None:
    """
    Tenta obter árvore de acessibilidade via CDP (Chrome DevTools Protocol).
    O painel de IA do Chrome pode estar em um shadow DOM ou iframe separado;
    a Accessibility Tree pode expor o texto gerado pela IA.
    Retorna JSON da árvore ou None.
    """
    try:
        result = driver.execute_cdp_cmd("Accessibility.getFullAXTree", {})
        return str(result)[:5000] if result else None
    except Exception as e:
        logger.debug(f"Accessibility tree falhou: {e}")
        return None


def _screenshot_desktop_for_ai_panel() -> str | None:
    """
    Tira screenshot da tela inteira (Desktop) via pyautogui.
    Útil para verificar se o painel de IA do Chrome apareceu.
    Retorna path do arquivo salvo ou None.
    """
    try:
        import pyautogui
        from pathlib import Path
        path = PROJECT_ROOT / "logs" / f"desktop_ai_panel_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        path.parent.mkdir(parents=True, exist_ok=True)
        pyautogui.screenshot(str(path))
        logger.info(f"Screenshot desktop salvo: {path}")
        return str(path)
    except ImportError:
        logger.debug("pyautogui não instalado. pip install pyautogui para screenshot desktop")
        return None
    except Exception as e:
        logger.debug(f"Screenshot desktop falhou: {e}")
        return None


def _get_driver(
    headless: bool = True,
    use_undetected_override: bool | None = None,
    profile_override: str | None = None,
    skip_deep_clean: bool = False,
    skip_fallback: bool = False,
    extra_chrome_args: list[str] | None = None,
):
    """
    Cria o WebDriver do Chrome. Tenta perfil real (EXTRACTOR_CHROME_USER_DATA);
    se falhar (Chrome em uso, DevToolsActivePort), usa perfil de fallback.

    Overrides (para Self-Healing):
        use_undetected_override: Força undetected True/False
        profile_override: Força perfil (ex: .temp_profile)
        skip_deep_clean: Pula limpeza de locks
        skip_fallback: Nao tenta fallback interno ao falhar
    """
    logger.info(f"Inicializando WebDriver (headless={headless})...")

    from selenium import webdriver
    from selenium.webdriver.chrome.options import Options
    from selenium.common.exceptions import SessionNotCreatedException

    # Blindagem de Sigilo: User-Agent de Chrome real (evita deteccao headless)
    _REAL_CHROME_UA = (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/131.0.6778.200 Safari/537.36"
    )

    def _build_options(use_profile_path: str | None, extra_args: list[str] | None = None) -> Options:
        opts = Options()
        opts.page_load_strategy = "eager"  # DOM pronto, evita travar em paginas lentas
        if headless:
            opts.add_argument("--headless=new")
            opts.add_argument("--disable-blink-features=AutomationControlled")
            opts.add_argument(f"--user-agent={_REAL_CHROME_UA}")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-gpu")
        opts.add_argument("--disable-software-rasterizer")
        opts.add_argument("--disable-extensions")
        opts.add_argument("--remote-debugging-port=0")
        opts.add_argument("--disable-browser-side-navigation")
        opts.add_argument("--window-size=1920,1080")
        opts.add_argument("--disable-restore-session-state")
        opts.add_argument("--disable-crash-reporter")
        opts.add_argument("--disable-in-process-stack-traces")
        opts.add_argument("--log-level=3")
        # Bypass protecoes: remove banner "Chrome is being controlled", evita deteccao
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_argument("--disable-infobars")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--disable-popup-blocking")
        opts.add_argument("--disable-save-password-bubble")
        opts.add_argument("--disable-single-click-autofill")
        opts.add_argument("--disable-sync")
        opts.add_argument("--disable-translate")
        opts.add_argument("--disable-features=TranslateUI")
        if not headless and use_profile_path:
            Path(use_profile_path).mkdir(parents=True, exist_ok=True)
            opts.add_argument(f"--user-data-dir={use_profile_path}")
            opts.add_argument(f"--profile-directory={os.getenv('EXTRACTOR_CHROME_PROFILE', 'Default').strip() or 'Default'}")
            opts.add_argument("--no-first-run")
            opts.add_argument("--no-default-browser-check")
        for arg in (extra_args or []):
            if arg and arg.startswith("--"):
                opts.add_argument(arg)
        return opts

    chrome_selenium_profile = os.path.join(
        os.environ.get("LOCALAPPDATA", ""),
        "ChromeSelenium",
        "UserData",
    )
    temp_profile_dir = str(PROJECT_ROOT / ".temp_profile")
    user_profile = profile_override or os.getenv("EXTRACTOR_CHROME_USER_DATA", "").strip()
    use_undetected = (
        use_undetected_override
        if use_undetected_override is not None
        else (os.getenv("EXTRACTOR_UNDETECTED", "true").strip().lower() == "true")
    )
    use_fallback = not skip_fallback and (
        os.getenv("EXTRACTOR_CHROME_FALLBACK", "false").strip().lower() == "true"
    )
    is_temp_profile = profile_override == temp_profile_dir or user_profile == temp_profile_dir

    # Deep clean: apenas para perfil real, nao para temp_profile
    if user_profile and not skip_deep_clean and not is_temp_profile:
        _deep_clean_for_profile(user_profile)
        _verify_profile_ready(user_profile)
    elif is_temp_profile:
        Path(temp_profile_dir).mkdir(parents=True, exist_ok=True)

    # Perfil a usar
    profile_to_try = user_profile or chrome_selenium_profile
    if user_profile:
        logger.info(f"Tentando perfil real: {user_profile}")
    else:
        logger.info(f"Usando perfil ChromeSelenium: {chrome_selenium_profile}")
    if use_undetected:
        logger.info("Modo undetected ativado (evita 'navegador nao seguro')")

    extra_args = extra_chrome_args or []
    try:
        if use_undetected:
            try:
                driver = _create_undetected_driver(
                    profile_to_try if not headless else None,
                    headless,
                    extra_args=extra_args,
                )
            except (SessionNotCreatedException, WebDriverException, OSError, ConnectionError) as uc_err:
                logger.warning(f"Undetected falhou: {uc_err}. Tentando Selenium padrao...")
                options = _build_options(profile_to_try if not headless else None, extra_args)
                driver = _create_driver_with_options(options, headless)
        else:
            options = _build_options(profile_to_try if not headless else None, extra_args)
            driver = _create_driver_with_options(options, headless)
        logger.info("WebDriver inicializado com sucesso")
        return driver
    except (SessionNotCreatedException, WebDriverException, OSError, ConnectionError) as e:
        err_lower = str(e).lower()
        if user_profile and use_fallback and (
            "chrome instance exited" in err_lower
            or "devtoolsactiveport" in err_lower
            or "session not created" in err_lower
        ):
            fallback_profile = temp_profile_dir
            Path(fallback_profile).mkdir(parents=True, exist_ok=True)
            logger.warning(f"Perfil real falhou ({e}). Iniciando perfil de fallback...")
            print("  >> Perfil real travado, iniciando Perfil de Fallback...", flush=True)
            if use_undetected:
                driver = _create_undetected_driver(fallback_profile if not headless else None, headless, extra_args=extra_args)
            else:
                options = _build_options(fallback_profile if not headless else None, extra_args)
                driver = _create_driver_with_options(options, headless)
            logger.info("WebDriver inicializado com perfil de fallback (.temp_profile)")
            return driver
        if user_profile:
            raise ExtractionError(
                "Perfil real falhou. FECHE O CHROME COMPLETAMENTE (todas as janelas) e execute novamente. "
                "O perfil nao pode estar em uso. Use EXTRACTOR_CHROME_FALLBACK=true no .env para permitir fallback."
            ) from e
        raise ExtractionError(f"Falha ao inicializar navegador: {e}") from e


def _extract_key_from_page(driver, platform: str = "groq") -> str | None:
    """
    Procura no HTML da página atual por um texto que pareça uma API key.
    Usa validação de formato do módulo validators.
    """
    logger.info(f"Extraindo chave da página para plataforma '{platform}'...")

    from src.extractors.validators import API_KEY_PATTERNS

    pattern = API_KEY_PATTERNS.get(platform, API_KEY_PATTERNS["generic"])
    page_source = driver.page_source

    match = pattern.search(page_source)
    if match:
        key = match.group(0)
        logger.info(f"Chave encontrada: {key[:10]}...")
        return key

    logger.warning("Nenhuma chave encontrada no HTML da página")
    return None


def _save_api_key(
    key: str,
    platform: str,
    update_env: bool = True,
    save_to_supabase: bool = False,
) -> Path:
    """
    Salva a API key em data/raw/api_key.txt e, opcionalmente, atualiza o .env e Supabase.

    Args:
        key: API key extraída
        platform: Plataforma (groq, openai, etc.)
        update_env: Se True, atualiza .env
        save_to_supabase: Se True, salva no Supabase

    Returns:
        Path do arquivo salvo
    """
    logger.info(f"Salvando API key para plataforma '{platform}'...")

    # Salvar em arquivo
    out_file = RAW_DIR / "api_key.txt"
    with open(out_file, "w", encoding="utf-8") as f:
        f.write(key)
    logger.info(f"Chave salva em: {out_file}")

    # Atualizar .env
    if update_env:
        env_path = PROJECT_ROOT / ".env"
        env_key = "GROQ_API_KEY" if platform == "groq" else "OPENAI_API_KEY"

        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Atualiza ou adiciona a chave
            if f"{env_key}=" in content:
                content = re.sub(
                    rf"({env_key}=)[^\n]*",
                    rf"\g<1>{key}",
                    content,
                )
            else:
                content = content.rstrip() + f"\n{env_key}={key}\n"
            with open(env_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f".env atualizado com {env_key}")

    # Salvar no Supabase
    if save_to_supabase:
        try:
            from src.extractors.supabase_client import SupabaseAPIKeyManager

            manager = SupabaseAPIKeyManager()
            manager.create_key(
                platform=platform,
                key_value=key,
                validate=True,
                metadata={"origin": "web_extractor"},
            )
            logger.info("Chave salva no Supabase com sucesso")
        except Exception as e:
            logger.error(f"Erro ao salvar no Supabase: {e}")
            # Não falha se Supabase não estiver configurado

    return out_file


def _save_identity_key_association(
    api_key: str,
    display_name: str,
    old_display_name: str | None,
    platform: str = "groq",
) -> Path:
    """
    Salva associacao API key <-> nome de exibicao em identity_keys.json.
    Cada chave fica vinculada ao nome NOVO (usado naquela rodada).
    """
    entry = {
        "display_name": display_name,
        "old_display_name": old_display_name or "",
        "api_key": api_key,
        "platform": platform,
        "created_at": datetime.now().isoformat(),
    }
    entries = []
    if IDENTITY_KEYS_FILE.exists():
        try:
            with open(IDENTITY_KEYS_FILE, "r", encoding="utf-8") as f:
                entries = json.loads(f.read())
            if not isinstance(entries, list):
                entries = [entries]
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(entry)
    with open(IDENTITY_KEYS_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(entries, indent=2, ensure_ascii=False))
    logger.info(f"Associacao salva: {display_name} -> {api_key[:12]}...")
    return IDENTITY_KEYS_FILE


def _generate_display_name() -> str:
    """Gera nome unico por rodada (prefixo + timestamp)."""
    prefix = os.getenv("EXTRACTOR_DISPLAY_NAME_PREFIX", "Groq").strip() or "Groq"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{prefix}_{ts}"


def _generate_group_email_prefix() -> str:
    """Gera prefixo unico para Email do grupo. Nome natural + sufixo aleatorio a cada rodada."""
    base = os.getenv("EXTRACTOR_GROUP_EMAIL_PREFIX", "groq-test-implementation").strip().lower()
    base = base or "groq-test-implementation"
    # Sufixo aleatorio (4 chars) para nao parecer padrao/timestamp ao GitHub
    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{base}-{suffix}"


def _save_group_email_for_github(old_email: str, new_email: str) -> Path:
    """Salva email antigo/novo do grupo para uso na criacao da conta GitHub. Imprime no CLI."""
    entry = {
        "group_email_old": old_email,
        "group_email_new": new_email,
        "group_email_full": f"{new_email}@googlegroups.com",
        "created_at": datetime.now().isoformat(),
    }
    entries = []
    if IDENTITY_KEYS_FILE.exists():
        try:
            with open(IDENTITY_KEYS_FILE, "r", encoding="utf-8") as f:
                entries = json.loads(f.read())
            if not isinstance(entries, list):
                entries = [entries]
        except (json.JSONDecodeError, OSError):
            entries = []
    entries.append(entry)
    with open(IDENTITY_KEYS_FILE, "w", encoding="utf-8") as f:
        f.write(json.dumps(entries, indent=2, ensure_ascii=False))
    print("\n" + "=" * 50, flush=True)
    print("  DADOS PARA CRIAR CONTA NO GITHUB:", flush=True)
    print(f"  Nome antigo (email grupo): {old_email}@googlegroups.com", flush=True)
    print(f"  Nome novo  (email grupo): {new_email}@googlegroups.com", flush=True)
    print("  Use o email NOVO para registrar no GitHub.", flush=True)
    print("=" * 50 + "\n", flush=True)
    return IDENTITY_KEYS_FILE


def extract_api_key(
    url: str | None = None,
    user: str | None = None,
    password: str | None = None,
    headless: bool = True,
    manual_login: bool = False,
    wait_seconds: int = 60,
    platform: str = "groq",
    validate: bool = True,
    save_to_supabase: bool = False,
) -> str:
    """
    Fluxo principal: acessa URL, faz login (ou aguarda manual), extrai API key.

    Args:
        url: URL da plataforma (ex: https://console.groq.com)
        user: Usuário/email para login (lido do .env se não informado)
        password: Senha para login (lida do .env se não informada)
        headless: Se True, roda o navegador invisível
        manual_login: Se True, aguarda o usuário fazer login manualmente (OAuth)
        wait_seconds: Tempo de espera para login manual (segundos)
        platform: 'groq' ou 'openai' (afeta padrão de extração e .env)
        validate: Se True, valida chave antes de salvar
        save_to_supabase: Se True, salva no Supabase

    Returns:
        A API key extraída.

    Raises:
        ExtractionError: Se extração falhar
        ValidationError: Se validação falhar
    """
    logger.info(f"Iniciando extração de API key para plataforma '{platform}'...")

    url = url or os.getenv("EXTRACTOR_URL", "https://console.groq.com")
    user = user or os.getenv("EXTRACTOR_USER", "").strip()
    password = password or os.getenv("EXTRACTOR_PASS", "").strip()
    if os.getenv("EXTRACTOR_HEADLESS", "true").strip().lower() == "false":
        headless = False

    if not url:
        raise ExtractionError("Configure EXTRACTOR_URL no .env ou passe url=.")

    driver = None
    try:
        driver = _get_driver(headless=headless)

        # Etapa 1: Acessar a URL da plataforma
        logger.info(f"Acessando {url}...")
        driver.get(url)
        time.sleep(2)

        if manual_login:
            # Etapa 2a: Modo OAuth – abrir login e aguardar usuário completar
            if "groq" in url.lower():
                logger.info("Navegando para página de login...")
                driver.get("https://console.groq.com/login")
                time.sleep(2)

            logger.info(f"Aguardando {wait_seconds}s para login manual...")
            time.sleep(wait_seconds)

            # Navegar para a página de API Keys
            keys_url = os.getenv("EXTRACTOR_KEYS_URL", "https://console.groq.com/keys")
            logger.info(f"Navegando para {keys_url}...")
            driver.get(keys_url)
            time.sleep(3)
        else:
            # Etapa 2b: Login automático com usuário/senha
            if not user or not password:
                raise ExtractionError(
                    "Para login automático, configure EXTRACTOR_USER e EXTRACTOR_PASS no .env."
                )

            logger.info("Fazendo login automático...")

            # Seletores genéricos – ajuste conforme a plataforma
            user_sel = os.getenv(
                "EXTRACTOR_USER_SELECTOR",
                "input[name='email'], input[type='email'], #email",
            )
            pass_sel = os.getenv(
                "EXTRACTOR_PASS_SELECTOR",
                "input[name='password'], input[type='password'], #password",
            )
            btn_sel = os.getenv(
                "EXTRACTOR_BTN_SELECTOR",
                "button[type='submit'], input[type='submit']",
            )

            from selenium.webdriver.common.by import By
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.webdriver.support.ui import WebDriverWait

            wait = WebDriverWait(driver, 10)

            try:
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, user_sel)))
                driver.find_element(By.CSS_SELECTOR, user_sel).send_keys(user)
                driver.find_element(By.CSS_SELECTOR, pass_sel).send_keys(password)
                driver.find_element(By.CSS_SELECTOR, btn_sel).click()
                logger.info("Credenciais enviadas, aguardando...")
                time.sleep(5)
            except NoSuchElementException as e:
                raise ExtractionError(
                    f"Elemento não encontrado. Verifique os seletores CSS: {e}"
                ) from e

            # Navegar para API Keys
            keys_url = os.getenv("EXTRACTOR_KEYS_URL", "https://console.groq.com/keys")
            logger.info(f"Navegando para {keys_url}...")
            driver.get(keys_url)
            time.sleep(3)

        # Etapa 3: Extrair a API key do HTML da página
        key = _extract_key_from_page(driver, platform)
        if not key:
            raise ExtractionError(
                "Nenhuma API key encontrada na página. "
                "Verifique se está logado e na página de API Keys."
            )

        # Etapa 4: Validar chave (opcional)
        if validate:
            logger.info("Validando API key...")
            try:
                validate_api_key(key, platform)
                logger.info("Validação bem-sucedida!")
            except ValidationError as e:
                logger.error(f"Validação falhou: {e}")
                raise

        # Etapa 5: Salvar em arquivo e opcionalmente no .env/Supabase
        out_path = _save_api_key(
            key, platform, update_env=True, save_to_supabase=save_to_supabase
        )
        logger.info(f"API key extraída e salva em: {out_path}")

        return key

    except (ExtractionError, ValidationError):
        # Re-raise erros conhecidos
        raise
    except Exception as e:
        logger.error(f"Erro inesperado durante extração: {e}")
        raise ExtractionError(f"Erro inesperado: {e}") from e
    finally:
        if driver:
            logger.info("Fechando navegador...")
            driver.quit()


def execute_identity_swap(
    driver,
    save_to_env: bool = False,
    validate: bool = False,
    debug: bool = True,
) -> str | None:
    """
    Navegacao em cadeia: Google Groups -> Gmail -> Groq.

    Passo 1: Abre Google Groups, localiza grupo, troca nome de exibicao (Identidade).
    Passo 2: Abre Gmail, aguarda email de confirmacao do GitHub e clica no link.
    Passo 3: Abre Groq Console e realiza login via GitHub.

    Args:
        driver: WebDriver do Selenium
        save_to_env: Se True, atualiza .env com a chave extraida
        validate: Se True, valida chave via API antes de retornar
        debug: Se True, imprime progresso no terminal

    Returns:
        API key extraida ou None se falhar
    """
    def _log(msg: str):
        if debug:
            print(f"  [identity_swap] {msg}", flush=True)
        logger.info(msg)

    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait_short = WebDriverWait(driver, 15)
    wait_email = WebDriverWait(driver, int(os.getenv("EXTRACTOR_GMAIL_WAIT_SECONDS", "90")))

    expected_email = os.getenv("EXTRACTOR_GOOGLE_EMAIL", "").strip()
    gh_user = os.getenv("EXTRACTOR_USER", "").strip()
    gh_pass = os.getenv("EXTRACTOR_PASS", "").strip()
    gmail_search = os.getenv("EXTRACTOR_GMAIL_SEARCH", "from:github OR from:noreply").strip()
    group_name = os.getenv("EXTRACTOR_GOOGLE_GROUP_NAME", "").strip()
    group_url = os.getenv("EXTRACTOR_GOOGLE_GROUP_URL", "").strip()
    # Email do grupo: novo a cada rodada para criar conta GitHub
    new_group_email = _generate_group_email_prefix()
    old_group_email: str | None = None

    # Garantir que estamos na aba principal
    if driver.window_handles:
        driver.switch_to.window(driver.window_handles[0])
        _log("Focado na aba principal")

    all_groups_url = "https://groups.google.com/all-groups"

    # Checkpoint: se google_login completo nas últimas 24h, pular login
    if is_step_recently_complete("google_login"):
        print("  >> Checkpoint válido (<24h). Pulando etapa de login e indo direto para Groups.", flush=True)
        logger.info("Checkpoint google_login válido. Pulando login.")
        try:
            driver.get(all_groups_url)
            time.sleep(3)
        except Exception:
            driver.execute_script(f"window.location.href = '{all_groups_url}';")
        time.sleep(2)
    elif load_session_from_cache(driver):
        print("  >> Happy Path detectado. Pulando desafio de 2FA e indo direto para a missão.", flush=True)
        logger.info("Happy Path detectado. Pulando desafio de 2FA.")
        mark_step_as_complete("google_login")
    else:
        # Injeção de cookies do .env (fallback)
        inject_cookies_from_env(driver)

    # --- Fluxo Cliques Burros: 6 passos com WebDriverWait element_to_be_clickable ---
    wait_click = WebDriverWait(driver, 20)
    google_user = os.getenv("EXTRACTOR_GOOGLE_USER", "").strip() or os.getenv("EXTRACTOR_USER", "").strip()
    google_pass = os.getenv("EXTRACTOR_GOOGLE_PASS", "").strip() or os.getenv("EXTRACTOR_PASS", "").strip()

    # Passo 1: Entrada - Navegar para all-groups (ou garantir que estamos la)
    _log("Passo 1: Navegando para all-groups...")
    print("  [1/6] Navegando para https://groups.google.com/all-groups", flush=True)
    if "groups.google.com" not in (driver.current_url or ""):
        try:
            driver.get(all_groups_url)
        except Exception:
            driver.execute_script(f"window.location.href = '{all_groups_url}';")
    wait_click.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(4)

    # DETECÇÃO PRECOCE: solve_oauth_flow ANTES de qualquer click()
    from src.utils.evolutionary_orchestrator import solve_oauth_flow, _is_oauth_login_screen
    if _is_oauth_login_screen(driver) and solve_oauth_flow(driver):
        print("  >> OAuth quebrado pelo Agente (JS puro). Prosseguindo...", flush=True)
        mark_step_as_complete("google_login")
        time.sleep(4)
        _random_click_on_page(driver)
    else:
        _random_click_on_page(driver)
        current_url = driver.current_url
        page_lower = driver.page_source.lower()

        # Login classico apenas se Agente nao resolveu (fallback)
        if "access-error" in page_lower or "accounts.google.com" in current_url or "entrar" in page_lower or "sign in" in page_lower or "iniciar sess" in page_lower or "identifique-se" in page_lower or "fazer login" in page_lower:
            print("  >> Pagina de login detectada (Agente nao resolveu). Tentando login classico...", flush=True)
            if google_user and google_pass:
                try:
                    # Ir direto ao login (access-error nao tem botao Fazer Login)
                    driver.get("https://accounts.google.com/")
                    time.sleep(3)
                    _random_click_on_page(driver)
                    # Trocar conta se AccountChooser aparecer (timeout curto para nao travar)
                    wait_quick = WebDriverWait(driver, 3)
                    for link_text in ["Use another account", "Usar outra conta", "Add account", "Adicionar conta"]:
                        try:
                            btn = wait_quick.until(EC.element_to_be_clickable((By.PARTIAL_LINK_TEXT, link_text)))
                            btn.click()
                            time.sleep(2)
                            break
                        except TimeoutException:
                            continue
                    email_inp = wait_click.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email'], input[name='identifier']")))
                    email_inp.clear()
                    email_inp.send_keys(google_user)
                    time.sleep(1)
                    next_btn = wait_click.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']/.. | //span[text()='Avançar']/.. | //button[contains(., 'Next')] | //div[@role='button'][contains(., 'Avançar')]")))
                    try:
                        next_btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(3)
                    pass_inp = wait_click.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password'], input[name='password']")))
                    pass_inp.clear()
                    pass_inp.send_keys(google_pass)
                    time.sleep(1)
                    next_btn = wait_click.until(EC.element_to_be_clickable((By.XPATH, "//span[text()='Next']/.. | //span[text()='Avançar']/.. | //button[contains(., 'Next')]")))
                    try:
                        next_btn.click()
                    except Exception:
                        driver.execute_script("arguments[0].click();", next_btn)
                    time.sleep(5)
                    try:
                        driver.get(all_groups_url)
                    except Exception:
                        driver.execute_script(f"window.location.href = '{all_groups_url}';")
                    time.sleep(4)
                    _random_click_on_page(driver)
                    print("  >> Login realizado. Cookies salvos no perfil para proximas rodadas.", flush=True)
                    mark_step_as_complete("google_login")
                except (TimeoutException, NoSuchElementException) as e:
                    print(f"  >> [AVISO] Login automatico falhou: {e}. Faca login manualmente.", flush=True)
                    time.sleep(15)
            else:
                print("  >> Configure EXTRACTOR_GOOGLE_USER e EXTRACTOR_GOOGLE_PASS no .env. Aguardando 30s para login manual...", flush=True)
                time.sleep(30)

    if expected_email and expected_email.lower() in driver.page_source.lower():
        print(f"  >> Estou logado na conta: {expected_email}", flush=True)

    # Passo 2: Selecao - Clicar no elemento "Inteligencias Do Pai" (ANTI-HONEYPOT)
    group_entered = False
    if group_name:
        print(f"  [2/6] Clicando no grupo: {group_name} (modo anti-honeypot)", flush=True)
        
        # NOVO: Forçar refresh do DOM após 2FA
        _force_dom_refresh(driver)
        
        # NOVO: Usar técnica de Visão Híbrida
        if _click_element_anti_honeypot(driver, group_name, wait_click, tag="a"):
            print(f"  >> ✓ Grupo acessado com sucesso: {group_name}", flush=True)
            time.sleep(4)
            group_entered = True
        else:
            # Fallback: tentar com primeira palavra do nome
            if " " in group_name:
                first_word = group_name.split()[0]
                print(f"  >> Tentando com primeira palavra: {first_word}", flush=True)
                if _click_element_anti_honeypot(driver, first_word, wait_click, tag="a"):
                    print(f"  >> ✓ Grupo acessado (palavra parcial): {first_word}", flush=True)
                    time.sleep(4)
                    group_entered = True
        
        # Se ainda não entrou, tentar métodos legados
        if not group_entered:
            print("  >> Tentando métodos legados...", flush=True)
            try:
                # XPath com ActionChains
                for el in driver.find_elements(By.XPATH, "//a[contains(@href, 'groups.google.com/g/')]"):
                    if group_name.split()[0].lower() in (el.text or "").lower():
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(driver).move_to_element(el).click().perform()
                        print(f"  >> ✓ Grupo acessado (XPath): {group_name}", flush=True)
                        time.sleep(4)
                        group_entered = True
                        break
            except Exception as e:
                logger.warning(f"XPath fallback falhou: {e}")
            
            # Estratégia de Busca Difusa
            if not group_entered:
                parts = [group_name.split()[0], group_name.split()[-1] if " " in group_name else group_name[:8]]
                for part in parts:
                    if not part or len(part) < 2:
                        continue
                    try:
                        el = driver.find_element(By.XPATH, f"//a[contains(text(), '{part}')]")
                        from selenium.webdriver.common.action_chains import ActionChains
                        ActionChains(driver).move_to_element(el).click().perform()
                        print(f"  >> ✓ Grupo acessado (Busca Difusa): {part}", flush=True)
                        time.sleep(4)
                        group_entered = True
                        break
                    except NoSuchElementException:
                        continue
                
                # CSS lista
                if not group_entered:
                    for el in driver.find_elements(By.CSS_SELECTOR, "[role='listitem'] a, .group-list a, a[href*='groups.google.com/g/']"):
                        if any(p.lower() in (el.text or "").lower() for p in parts if p):
                            el.click()
                            print(f"  >> ✓ Grupo acessado (CSS lista)", flush=True)
                            time.sleep(4)
                            group_entered = True
                            break
        
        # Fallback final: URL direta
        if not group_entered and group_url:
            print(f"  >> Fallback final: navegando para URL direta", flush=True)
            try:
                driver.get(group_url)
                time.sleep(4)
                if "groups.google.com/g/" in (driver.current_url or ""):
                    group_entered = True
                    print(f"  >> ✓ Grupo acessado por URL: {group_url}", flush=True)
            except Exception as e:
                logger.warning(f"URL fallback falhou: {e}")
        
        # Se ainda não entrou, reportar erro detalhado
        if not group_entered:
            # Capturar informações de diagnóstico
            page_source_sample = driver.page_source[:500] if driver.page_source else "N/A"
            current_url = driver.current_url or "N/A"
            
            msg = (
                f"Guerreiro, o caminho mudou? Não achei o grupo '{group_name}'.\n"
                f"  URL atual: {current_url}\n"
                f"  Possíveis causas:\n"
                f"    1. Honeypot overlay invisível\n"
                f"    2. Shadow DOM encapsulado\n"
                f"    3. ID/Class shuffling após 2FA\n"
                f"    4. Elemento ghost (HTML existe mas isDisplayed=false)\n"
                f"  Diagnóstico: Verifique screenshot em logs/"
            )
            print(f"\n  >> [BLOQUEIO ANTI-HONEYPOT] {msg}", flush=True)
            
            # Salvar screenshot para diagnóstico
            try:
                screenshot_path = PROJECT_ROOT / "logs" / f"honeypot_debug_{int(time.time())}.png"
                screenshot_path.parent.mkdir(exist_ok=True)
                driver.save_screenshot(str(screenshot_path))
                print(f"  >> Screenshot salvo: {screenshot_path}", flush=True)
            except Exception:
                pass
            
            raise ExtractionError(f"Grupo '{group_name}' não encontrado (possível honeypot). {msg}")

    # Passo 3: Configuracao - Clicar em engrenagem ou "Configurações do grupo"
    # Buscar DENTRO de [role='main'] para evitar clicar no header do Google (icone conta no topo)
    if group_entered:
        print("  [3/6] Clicando em Configurações do grupo (engrenagem ou link)", flush=True)
        clicked = False
        for by, sel in [
            (By.PARTIAL_LINK_TEXT, "Definições do grupo"),
            (By.PARTIAL_LINK_TEXT, "Configurações do grupo"),
            (By.PARTIAL_LINK_TEXT, "Group settings"),
            (By.XPATH, "//*[@role='main']//a[contains(., 'Definições do grupo') or contains(., 'Configurações do grupo') or contains(., 'Group settings')]"),
            (By.XPATH, "//*[@role='main']//*[contains(@aria-label, 'Configurações') or contains(@aria-label, 'Group settings')]"),
            (By.XPATH, "//*[@role='main']//a[contains(., 'Definições') or contains(., 'Configurações') or contains(., 'Settings')]"),
            (By.XPATH, "//*[@role='main']//*[contains(@aria-label, 'Configura') or contains(@aria-label, 'Settings')]"),
            (By.PARTIAL_LINK_TEXT, "Definições"),
            (By.PARTIAL_LINK_TEXT, "Settings"),
            (By.CSS_SELECTOR, "[aria-label*='Configura'], [aria-label*='Settings'], [title*='Configura']"),
            (By.XPATH, "//a[contains(., 'Definições') or contains(., 'Configura') or contains(., 'Settings')]"),
        ]:
            try:
                el = wait_click.until(EC.element_to_be_clickable((by, sel)))
                el.click()
                print("  >> Cliquei em Configurações do grupo", flush=True)
                time.sleep(3)
                clicked = True
                break
            except TimeoutException:
                continue
        if not clicked:
            print("  >> [AVISO] Configurações nao encontradas", flush=True)

        # Passo 4: Identidade - Clicar em "Identidade" ou "Membros" ou "Geral"
        print("  [4/6] Clicando em Identidade ou Geral", flush=True)
        for by, sel in [
            (By.PARTIAL_LINK_TEXT, "Identidade"),
            (By.PARTIAL_LINK_TEXT, "Identity"),
            (By.PARTIAL_LINK_TEXT, "Membros"),
            (By.PARTIAL_LINK_TEXT, "Members"),
            (By.PARTIAL_LINK_TEXT, "Geral"),
            (By.PARTIAL_LINK_TEXT, "General"),
        ]:
            try:
                el = wait_click.until(EC.element_to_be_clickable((by, sel)))
                el.click()
                print(f"  >> Cliquei em {sel}", flush=True)
                time.sleep(3)
                break
            except TimeoutException:
                continue

        # Passo 5: Troca de Email - Localizar campo, limpar, digitar novo
        print("  [5/6] Localizando campo Email do grupo, limpando e digitando novo", flush=True)
        for by, sel in [
            (By.XPATH, "//input[contains(@aria-label, 'Email') or contains(@placeholder, 'Email')]"),
            (By.XPATH, "//*[contains(text(), 'Email do grupo')]/following::input[1]"),
            (By.CSS_SELECTOR, "input[type='text']"),
        ]:
            try:
                inputs = driver.find_elements(by, sel) if by == By.CSS_SELECTOR else [driver.find_element(by, sel)]
                for inp in inputs:
                    val = (inp.get_attribute("value") or "").strip()
                    if inp.is_displayed() and val and "@" not in val and " " not in val and len(val) < 50:
                        old_group_email = val
                        inp.clear()
                        inp.send_keys(new_group_email)
                        print(f"  >> Mudando: {old_group_email} -> {new_group_email}", flush=True)
                        time.sleep(2)
                        break
                else:
                    continue
                break
            except NoSuchElementException:
                continue

        # Passo 6: Salvar - Clicar em "Salvar alterações"
        print("  [6/6] Clicando em Salvar alterações", flush=True)
        for xpath in [
            "//button[contains(., 'Guardar') or contains(., 'Salvar') or contains(., 'Save')]",
            "//*[contains(., 'Guardar alterações')]",
            "//*[contains(., 'Salvar alterações')]",
        ]:
            try:
                btn = wait_click.until(EC.element_to_be_clickable((By.XPATH, xpath)))
                btn.click()
                print("  >> Guardou alterações. Dados prontos para GitHub.", flush=True)
                time.sleep(3)
                if old_group_email:
                    _save_group_email_for_github(old_group_email, new_group_email)
                break
            except TimeoutException:
                continue

    # Garantir aba principal antes de Gmail
    if driver.window_handles:
        driver.switch_to.window(driver.window_handles[0])
        _log("Focado na aba principal (pre-Gmail)")

    # --- Passo 2: Gmail - capturar link de confirmacao do GitHub ---
    print("Navegando para Gmail...", flush=True)
    print(f"  >> Busca: {gmail_search}", flush=True)
    _log("Passo 2: Abrindo Gmail para capturar link de confirmacao...")
    gmail_url = f"https://mail.google.com/mail/u/0/#search/{gmail_search.replace(' ', '+')}"
    # 1o elemento: clica Gmail no header (mais humano); depois vai para busca
    _click_first_elements_on_open(driver, wait_time=5)
    driver.get(gmail_url)
    wait_email.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(5)
    _random_click_on_page(driver)

    # Aguarda lista de emails carregar e clica no primeiro (mais recente)
    print("Procurando emails na lista...")
    try:
        for sel in ["tr.zA", "div[role='main'] tr", "tr"]:
            try:
                rows = wait_email.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, sel)))
                for row in rows[:8]:
                    if row.is_displayed() and row.get_attribute("role") != "presentation":
                        row.click()
                        _log("Clicou no email mais recente")
                        time.sleep(4)
                        break
                else:
                    continue
                break
            except TimeoutException:
                continue

        # Dentro do email: procura e clica no link de confirmacao
        print("Procurando link de confirmacao no email...")
        links = driver.find_elements(By.CSS_SELECTOR, "a[href^='http']")
        for link in links:
            href = link.get_attribute("href") or ""
            text = (link.text or "").lower()
            if any(x in href.lower() for x in ["github", "confirm", "verif", "authorize", "groq"]):
                if any(x in text for x in ["confirm", "verif", "valid", "authorize", "clicar"]):
                    link.click()
                    _log("Clicou no link de confirmacao")
                    time.sleep(4)
                    break
        else:
            # Fallback: clica no primeiro link externo
            for link in links[:5]:
                if "google" not in (link.get_attribute("href") or "").lower():
                    link.click()
                    _log("Clicou em link alternativo")
                    time.sleep(4)
                    break
    except Exception as e:
        _log(f"Gmail: {e} - aguardando 30s para intervencao manual...")
        time.sleep(int(os.getenv("EXTRACTOR_GMAIL_MANUAL_WAIT", "30")))

    # Garantir aba principal antes de Groq
    if driver.window_handles:
        driver.switch_to.window(driver.window_handles[0])
        _log("Focado na aba principal (pre-Groq)")

    # --- Passo 3: Groq Console - login via GitHub ---
    print("Navegando para Groq Console...", flush=True)
    print(f"  >> Usando GitHub: {gh_user or '(nao configurado)'}", flush=True)
    _log("Passo 3: Abrindo Groq Console e realizando login via GitHub...")
    driver.get("https://console.groq.com/login")
    wait_short.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)
    _random_click_on_page(driver)

    # GitHub nao logado? Faz login
    try:
        driver.get("https://github.com/login")
        time.sleep(2)
        _random_click_on_page(driver)
        login_field = driver.find_element(By.ID, "login_field")
        if login_field.is_displayed() and gh_user and gh_pass:
            _log("GitHub nao logado. Realizando login...")
            driver.find_element(By.ID, "login_field").send_keys(gh_user)
            driver.find_element(By.ID, "password").send_keys(gh_pass)
            driver.find_element(By.NAME, "commit").click()
            time.sleep(4)
    except NoSuchElementException:
        _log("GitHub ja logado.")

    # Volta ao Groq e clica em Login with GitHub
    driver.get("https://console.groq.com/login")
    time.sleep(3)
    _random_click_on_page(driver)

    print("Procurando botao Login with GitHub...")
    clicked = False
    for by, sel in [
        (By.CSS_SELECTOR, "a[href*='github']"),
        (By.XPATH, "//a[contains(@href, 'github')]"),
        (By.PARTIAL_LINK_TEXT, "GitHub"),
    ]:
        try:
            el = driver.find_element(by, sel)
            if el.is_displayed() and el.is_enabled():
                el.click()
                print("Clicou em Login with GitHub")
                _log("Clicou em Login with GitHub")
                clicked = True
                break
        except NoSuchElementException:
            continue
    if not clicked:
        raise ExtractionError("Botao 'Login with GitHub' nao encontrado.")

    time.sleep(5)

    # Autorizar se necessario
    try:
        auth_btn = driver.find_element(By.XPATH, "//*[contains(., 'Authorize') or contains(., 'Autorizar')]")
        if auth_btn.is_displayed():
            auth_btn.click()
            time.sleep(3)
    except NoSuchElementException:
        pass

    # Extrair API Key
    keys_url = os.getenv("EXTRACTOR_KEYS_URL", "https://console.groq.com/keys")
    driver.get(keys_url)
    time.sleep(4)
    _random_click_on_page(driver)

    key = _extract_key_from_page(driver, "groq")
    if not key:
        return None

    if validate:
        validate_api_key(key, "groq")

    if save_to_env:
        _save_api_key(key, "groq", update_env=True, save_to_supabase=False)

    # Associar API key ao email do grupo (usado para criar conta GitHub)
    _save_identity_key_association(
        api_key=key,
        display_name=new_group_email or "",
        old_display_name=old_group_email,
        platform="groq",
    )
    _log(f"Chave associada a: {new_group_email or 'N/A'}")

    return key


def _run_rotating_identity_groq(driver, validate: bool = True) -> str:
    """
    Fluxo de Identidade Rotativa: Google Groups -> Gmail -> GitHub -> Groq.

    1. Google Groups: Troca o email de encaminhamento
    2. Gmail: Localiza email de confirmacao e clica no link
    3. GitHub: Login com novo email e autoriza Groq
    4. Groq Console: Extrai API Key e salva no .env

    Usa WebDriverWait em cada transicao (tempo de email varia).
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait_short = WebDriverWait(driver, 15)
    wait_email = WebDriverWait(driver, int(os.getenv("EXTRACTOR_GMAIL_WAIT_SECONDS", "120")))

    new_email = os.getenv("EXTRACTOR_NEW_EMAIL", "").strip()
    gh_user = os.getenv("EXTRACTOR_USER", "").strip()
    gh_pass = os.getenv("EXTRACTOR_PASS", "").strip()
    group_url = os.getenv("EXTRACTOR_GOOGLE_GROUP_URL", "").strip()

    if not new_email:
        raise ExtractionError(
            "Configure EXTRACTOR_NEW_EMAIL no .env (email para encaminhamento no Google Groups)."
        )

    # --- Etapa 1: Google Groups - troca email de encaminhamento ---
    logger.info("Etapa 1: Acessando Google Groups para troca de email...")
    base_url = group_url or "https://groups.google.com/"
    driver.get(base_url)
    wait_short.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)

    # Navega para configuracoes do grupo (se URL especifica) ou menu de opcoes
    try:
        # Tenta encontrar link de configuracoes / delivery
        settings_selectors = [
            (By.LINK_TEXT, "Configurações"),
            (By.LINK_TEXT, "Settings"),
            (By.PARTIAL_LINK_TEXT, "Configura"),
            (By.CSS_SELECTOR, "a[href*='edit'], a[href*='settings']"),
        ]
        for by, sel in settings_selectors:
            try:
                el = driver.find_element(by, sel)
                if el.is_displayed():
                    el.click()
                    time.sleep(2)
                    break
            except NoSuchElementException:
                continue

        # Campo para adicionar/alterar email de encaminhamento
        email_input_selectors = [
            (By.CSS_SELECTOR, "input[type='email']"),
            (By.CSS_SELECTOR, "input[name*='email']"),
            (By.XPATH, "//input[contains(@placeholder, 'email') or contains(@aria-label, 'email')]"),
        ]
        for by, sel in email_input_selectors:
            try:
                inp = wait_short.until(EC.presence_of_element_located((by, sel)))
                if inp.is_displayed():
                    inp.clear()
                    inp.send_keys(new_email)
                    logger.info(f"Email de encaminhamento alterado para: {new_email}")
                    time.sleep(2)
                    # Salvar
                    for btn in driver.find_elements(By.XPATH, "//button[contains(., 'Salvar') or contains(., 'Save')]"):
                        if btn.is_displayed():
                            btn.click()
                            break
                    break
            except (TimeoutException, NoSuchElementException):
                continue
    except Exception as e:
        logger.warning(f"Google Groups: ajuste manual pode ser necessario: {e}")

    time.sleep(2)

    # --- Etapa 2: Gmail - localizar email de confirmacao e clicar no link ---
    logger.info("Etapa 2: Abrindo Gmail para localizar email de confirmacao...")
    gmail_search = os.getenv(
        "EXTRACTOR_GMAIL_SEARCH",
        "confirma OR verification OR confirmar OR validar",
    )
    gmail_url = f"https://mail.google.com/mail/u/0/#search/{gmail_search.replace(' ', '+')}"
    driver.get(gmail_url)
    wait_email.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(5)

    # Aguarda e clica no primeiro email da lista (mais recente)
    try:
        email_row_selectors = [
            (By.CSS_SELECTOR, "tr.zA"),
            (By.XPATH, "//div[@role='tabpanel']//tr[contains(@class, 'zA')]"),
            (By.CSS_SELECTOR, "[role='main'] tr"),
        ]
        for by, sel in email_row_selectors:
            try:
                rows = wait_email.until(EC.presence_of_all_elements_located((by, sel)))
                for row in rows[:5]:
                    if row.is_displayed():
                        row.click()
                        time.sleep(3)
                        break
                else:
                    continue
                break
            except TimeoutException:
                continue

        # Dentro do email: clica no link de confirmacao
        link_selectors = [
            (By.XPATH, "//a[contains(@href, 'http') and (contains(., 'confirm') or contains(., 'verif') or contains(., 'valid') or contains(@href, 'github') or contains(@href, 'groq'))]"),
            (By.CSS_SELECTOR, "a[href^='http']"),
        ]
        for by, sel in link_selectors:
            try:
                links = driver.find_elements(by, sel)
                for link in links:
                    href = link.get_attribute("href") or ""
                    if any(x in href.lower() for x in ["confirm", "verif", "valid", "github", "groq", "authorize"]):
                        link.click()
                        logger.info("Clicou no link de confirmacao")
                        break
                else:
                    continue
                break
            except NoSuchElementException:
                continue
    except Exception as e:
        logger.warning(f"Gmail: aguardando intervencao manual. Erro: {e}")
        time.sleep(int(os.getenv("EXTRACTOR_GMAIL_MANUAL_WAIT", "30")))

    # --- Etapa 3: GitHub OAuth - login com novo email ---
    logger.info("Etapa 3: Navegando para GitHub OAuth...")
    driver.get("https://github.com/login")
    wait_short.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)

    try:
        login_field = wait_short.until(EC.presence_of_element_located((By.ID, "login_field")))
        if login_field.is_displayed() and gh_user and gh_pass:
            logger.info("Realizando login no GitHub...")
            driver.find_element(By.ID, "login_field").send_keys(gh_user or new_email)
            driver.find_element(By.ID, "password").send_keys(gh_pass)
            driver.find_element(By.NAME, "commit").click()
            time.sleep(5)
    except (TimeoutException, NoSuchElementException):
        logger.info("GitHub pode ja estar logado.")

    # --- Etapa 4: Groq Console - Login with GitHub e extrair chave ---
    logger.info("Etapa 4: Acessando Groq e clicando em Login with GitHub...")
    driver.get("https://console.groq.com/login")
    wait_short.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(3)

    gh_selectors = [
        (By.CSS_SELECTOR, "a[href*='github']"),
        (By.XPATH, "//a[contains(@href, 'github')]"),
        (By.PARTIAL_LINK_TEXT, "GitHub"),
    ]
    clicked = False
    for by, selector in gh_selectors:
        try:
            el = driver.find_element(by, selector)
            if el.is_displayed() and el.is_enabled():
                el.click()
                clicked = True
                logger.info("Clicou em Login with GitHub")
                break
        except NoSuchElementException:
            continue

    if not clicked:
        raise ExtractionError("Botao 'Login with GitHub' nao encontrado.")

    time.sleep(5)

    # Autorizacao OAuth - clicar em Authorize se aparecer
    try:
        auth_btn = driver.find_element(By.XPATH, "//*[contains(., 'Authorize') or contains(., 'Autorizar')]")
        if auth_btn.is_displayed():
            auth_btn.click()
            time.sleep(3)
    except NoSuchElementException:
        pass

    # --- Extracao: Pagina de API Keys ---
    keys_url = os.getenv("EXTRACTOR_KEYS_URL", "https://console.groq.com/keys")
    logger.info(f"Navegando para {keys_url}...")
    driver.get(keys_url)
    wait_short.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(4)

    # Gerar nova chave se botao existir
    try:
        create_btn = driver.find_element(By.XPATH, "//*[contains(., 'Create') or contains(., 'Criar') or contains(., 'Generate') or contains(., 'Add')]")
        if create_btn.is_displayed():
            create_btn.click()
            time.sleep(2)
    except NoSuchElementException:
        pass

    key = _extract_key_from_page(driver, "groq")
    if not key:
        raise ExtractionError("Nenhuma API key encontrada na pagina.")

    if validate:
        logger.info("Validando API key...")
        validate_api_key(key, "groq")

    return key


def _run_identity_jump_groq(driver, validate: bool = True) -> str:
    """
    Sequencia de Saltos de Identidade: Google Groups -> GitHub -> Groq.
    Usa EXTRACTOR_CHROME_USER_DATA para manter cookies entre saltos.
    """
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.support.ui import WebDriverWait

    wait = WebDriverWait(driver, 15)
    expected_email = os.getenv("EXTRACTOR_GOOGLE_EMAIL", "").strip()
    gh_user = os.getenv("EXTRACTOR_USER", "").strip()
    gh_pass = os.getenv("EXTRACTOR_PASS", "").strip()

    # --- Aba 1: Google Groups - garantir que o email da sessao e o correto ---
    logger.info("Aba 1: Acessando Google Groups...")
    driver.get("https://groups.google.com/")
    time.sleep(3)

    if expected_email:
        page = driver.page_source.lower()
        if expected_email.lower() not in page:
            logger.warning(
                f"Email esperado '{expected_email}' nao encontrado na pagina. "
                "Verifique EXTRACTOR_GOOGLE_EMAIL ou faça login no Chrome com a conta correta."
            )
        else:
            logger.info(f"Email da sessao confirmado: {expected_email}")

    # --- Aba 2: GitHub - login se necessario ---
    logger.info("Aba 2: Acessando GitHub...")
    driver.get("https://github.com/login")
    time.sleep(3)

    # Se o form de login estiver visivel, faz login
    try:
        login_field = wait.until(EC.presence_of_element_located((By.ID, "login_field")))
        if login_field.is_displayed():
            if gh_user and gh_pass:
                logger.info("GitHub nao logado. Realizando login...")
                driver.find_element(By.ID, "login_field").send_keys(gh_user)
                driver.find_element(By.ID, "password").send_keys(gh_pass)
                driver.find_element(By.NAME, "commit").click()
                time.sleep(4)
            else:
                raise ExtractionError(
                    "GitHub nao logado. Configure EXTRACTOR_USER e EXTRACTOR_PASS no .env."
                )
        else:
            logger.info("GitHub ja logado (sessao do perfil).")
    except (TimeoutException, NoSuchElementException):
        # Sem form de login = ja logado (redirect para feed)
        logger.info("GitHub ja logado (sessao do perfil).")

    # --- Aba 3: Groq - Login with GitHub ---
    logger.info("Aba 3: Acessando Groq e clicando em Login with GitHub...")
    driver.get("https://console.groq.com/login")
    time.sleep(3)

    # Clica em "Login with GitHub"
    gh_selectors = [
        (By.CSS_SELECTOR, "a[href*='github']"),
        (By.XPATH, "//a[contains(@href, 'github')]"),
        (By.PARTIAL_LINK_TEXT, "GitHub"),
    ]
    clicked = False
    for by, selector in gh_selectors:
        try:
            el = driver.find_element(by, selector)
            if el.is_displayed() and el.is_enabled():
                el.click()
                clicked = True
                logger.info("Clicou em Login with GitHub")
                break
        except NoSuchElementException:
            continue

    if not clicked:
        raise ExtractionError(
            "Botao 'Login with GitHub' nao encontrado. "
            "Verifique se a pagina do Groq carregou corretamente."
        )

    time.sleep(5)

    # --- Extracao: Pagina de API Keys ---
    keys_url = os.getenv("EXTRACTOR_KEYS_URL", "https://console.groq.com/keys")
    logger.info(f"Navegando para {keys_url}...")
    driver.get(keys_url)
    time.sleep(4)

    key = _extract_key_from_page(driver, "groq")
    if not key:
        raise ExtractionError(
            "Nenhuma API key encontrada. Verifique se o login com GitHub foi concluido."
        )

    if validate:
        logger.info("Validando API key...")
        validate_api_key(key, "groq")

    return key


def run_groq_rotation(
    headless: bool = True,
    wait_seconds: int = 60,
    validate: bool = True,
    use_identity_jump: bool | None = None,
    use_rotating_identity: bool | None = None,
) -> str:
    """
    Rotacao de API Key Groq.

    Modos:
    - use_rotating_identity: Google Groups (troca email) -> Gmail (confirmacao) -> GitHub -> Groq
    - use_identity_jump: Google Groups (verifica) -> GitHub (login) -> Groq

    Args:
        headless: Se True, navegador invisivel
        wait_seconds: Ignorado nos fluxos automatizados
        validate: Se True, valida chave antes de salvar
        use_identity_jump: Fluxo simples (Google->GitHub->Groq)
        use_rotating_identity: Fluxo completo com troca de email e Gmail

    Returns:
        Nova API key extraida e salva no .env
    """
    if use_rotating_identity is None:
        use_rotating_identity = os.getenv("EXTRACTOR_USE_ROTATING_IDENTITY", "false").strip().lower() == "true"
    if use_identity_jump is None:
        use_identity_jump = os.getenv("EXTRACTOR_USE_IDENTITY_JUMP", "true").strip().lower() == "true"

    if use_rotating_identity:
        driver = None
        try:
            driver = _get_driver(headless=headless)
            key = _run_rotating_identity_groq(driver, validate=validate)
            out_path = _save_api_key(key, "groq", update_env=True, save_to_supabase=False)
            logger.info(f"API key extraida e salva em: {out_path}")
            return key
        finally:
            if driver:
                driver.quit()
    elif use_identity_jump:
        driver = None
        try:
            driver = _get_driver(headless=headless)
            key = _run_identity_jump_groq(driver, validate=validate)
            out_path = _save_api_key(key, "groq", update_env=True, save_to_supabase=False)
            logger.info(f"API key extraida e salva em: {out_path}")
            return key
        finally:
            if driver:
                driver.quit()
    else:
        return extract_api_key(
            url=os.getenv("EXTRACTOR_URL", "https://console.groq.com"),
            headless=headless,
            manual_login=True,
            wait_seconds=wait_seconds,
            platform="groq",
            validate=validate,
            save_to_supabase=False,
        )


def main():
    """Ponto de entrada via linha de comando."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Extrai API Key de plataforma web via Selenium"
    )
    parser.add_argument("--url", help="URL da plataforma")
    parser.add_argument(
        "--manual", action="store_true", help="Aguardar login manual (OAuth)"
    )
    parser.add_argument("--no-headless", action="store_true", help="Mostrar o navegador")
    parser.add_argument("--wait", type=int, default=60, help="Segundos para login manual")
    parser.add_argument(
        "--platform", choices=["groq", "openai"], default="groq", help="Plataforma"
    )
    parser.add_argument(
        "--no-validate", action="store_true", help="Não validar chave após extração"
    )
    parser.add_argument(
        "--supabase", action="store_true", help="Salvar no Supabase"
    )
    parser.add_argument(
        "--no-identity-jump", action="store_true",
        help="Usar fluxo manual em vez de Saltos de Identidade",
    )
    parser.add_argument(
        "--rotating-identity", action="store_true",
        help="Usar fluxo Identidade Rotativa (Google Groups->Gmail->GitHub->Groq)",
    )
    args = parser.parse_args()

    try:
        if args.no_identity_jump:
            key = extract_api_key(
                url=args.url or "https://console.groq.com",
                headless=not args.no_headless,
                manual_login=True,
                wait_seconds=args.wait,
                platform=args.platform,
                validate=not args.no_validate,
                save_to_supabase=args.supabase,
            )
        else:
            key = run_groq_rotation(
                headless=not args.no_headless,
                wait_seconds=args.wait,
                validate=not args.no_validate,
                use_identity_jump=not args.rotating_identity,
                use_rotating_identity=args.rotating_identity,
            )
        print(f"✅ Sucesso! Chave extraída: {key[:10]}...")
    except (ExtractionError, ValidationError) as e:
        print(f"❌ Erro: {e}")
        exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        logger.exception("Erro inesperado")
        exit(1)


if __name__ == "__main__":
    main()
