"""
Selum of Persistence - O Paladino do Selenium

Este módulo implementa uma camada de abstração sobre Selenium que transforma
operações técnicas em "manobras de combate" narrativas e resilientes.

Autor: Hugo (Planejamento) + Kiro (Implementação)
Paladino: Moltor, também conhecido como "Selum of Persistence"
"""

import os
import time
import traceback
from typing import Any, Dict, List, Optional, Union

from selenium import webdriver
from selenium.common.exceptions import (
    ElementClickInterceptedException,
    NoSuchElementException,
    TimeoutException,
)
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support.ui import WebDriverWait

from .combat_logger import CombatLogger


class SelumOfPersistence:
    """
    O Paladino Selum - Guardião das Interações Web.

    Esta classe encapsula operações Selenium em métodos resilientes com
    narrativa de RPG. Cada ação é um "turno de combate" e cada falha
    é uma oportunidade de aprendizado através do AgentFactory.

    Attributes:
        driver: WebDriver do Selenium
        turn_counter: Contador de turnos de combate
        battle_log: Histórico de todas as ações realizadas
        logger: Instância do CombatLogger para logs narrativos

    Example:
        >>> from selenium import webdriver
        >>> driver = webdriver.Chrome()
        >>> selum = SelumOfPersistence(driver)
        >>> selum.strike(".settings-button")
        [Turno 1 - Selum of Persistence]: Empunhando 'strike' contra '.settings-button'...
        [Resultado]: ✓ Golpe certeiro! O caminho está livre.
    """

    def __init__(self, driver: webdriver.Remote, groq_api_key: Optional[str] = None):
        """
        Inicializa o Paladino Selum com um WebDriver.

        Args:
            driver: Instância do WebDriver do Selenium
            groq_api_key: Chave da API Groq para Divine Inspiration (opcional)
        """
        self.driver = driver
        self.turn_counter = 0
        self.battle_log: List[Dict[str, Any]] = []
        self.logger = CombatLogger

        # Divine Inspiration - Sistema de auto-evolução
        self.skill_registry: Dict[str, Any] = {}
        self.error_detector = None
        self.divine_engine = None

        # Inicializar Divine Inspiration se API key fornecida
        if groq_api_key:
            try:
                from src.divine_inspiration import DivineInspirationEngine, ErrorDetector

                self.error_detector = ErrorDetector(driver)
                self.divine_engine = DivineInspirationEngine(groq_api_key)
                self._load_custom_skills()
            except Exception as e:
                self.logger.warning(f"Divine Inspiration não pôde ser inicializado: {e}")
        else:
            # Tentar carregar da variável de ambiente
            import os

            groq_key_env = os.getenv("GROQ_API_KEY")
            if groq_key_env:
                try:
                    from src.divine_inspiration import DivineInspirationEngine, ErrorDetector

                    self.error_detector = ErrorDetector(driver)
                    self.divine_engine = DivineInspirationEngine(groq_key_env)
                    self._load_custom_skills()
                except Exception as e:
                    self.logger.warning(f"Divine Inspiration não pôde ser inicializado: {e}")

    def _increment_turn(self) -> int:
        """
        Incrementa o contador de turnos e retorna o turno atual.

        Returns:
            int: Número do turno atual
        """
        self.turn_counter += 1
        return self.turn_counter

    def _log_action(self, action: str, target: str, result: str, success: bool) -> None:
        """
        Registra uma ação no histórico de batalha.

        Args:
            action: Nome da ação executada
            target: Alvo da ação
            result: Resultado da ação
            success: Se a ação foi bem-sucedida
        """
        self.battle_log.append(
            {
                "turn": self.turn_counter,
                "action": action,
                "target": target,
                "result": result,
                "success": success,
                "timestamp": time.time(),
            }
        )

    def get_battle_report(self) -> List[Dict[str, Any]]:
        """
        Retorna o relatório completo de batalha.

        Returns:
            List[Dict]: Lista com todas as ações realizadas
        """
        return self.battle_log.copy()

    def strike(
        self, selector: Union[str, WebElement], by: str = By.CSS_SELECTOR, strategy: str = "smart"
    ) -> bool:
        """
        Executa um clique resiliente com fallback automático.

        Esta é a manobra principal do Paladino. Tenta um clique normal e,
        se falhar por interceptação, usa "Injeção de Força" (JavaScript click).

        Args:
            selector: Seletor CSS, XPath, ou WebElement já localizado
            by: Tipo de seletor (By.CSS_SELECTOR, By.XPATH, etc.)
            strategy: Estratégia de clique:
                - 'smart': Tenta clique normal → JS click se falhar (padrão)
                - 'force': Usa JS click direto
                - 'gentle': Apenas clique normal (sem fallback)

        Returns:
            bool: True se o clique foi bem-sucedido

        Raises:
            Exception: Se todas as estratégias falharem

        Example:
            >>> selum.strike(".settings-button", strategy='smart')
            [Turno 1 - Selum of Persistence]: Empunhando 'strike' contra '.settings-button'...
            [Resultado]: ✓ Golpe certeiro! O caminho está livre.
        """
        turn = self._increment_turn()
        target_str = selector if isinstance(selector, str) else "WebElement"

        self.logger.turn_action(turn, "Empunhando 'strike'", target_str)

        try:
            # Localizar elemento se for string
            if isinstance(selector, str):
                element = self.driver.find_element(by, selector)
            else:
                element = selector

            # Estratégia: force - JS click direto
            if strategy == "force":
                self.driver.execute_script("arguments[0].click();", element)
                self.logger.result(True, "Injeção de Força aplicada! O caminho está livre.")
                self._log_action("strike", target_str, "Force click successful", True)
                return True

            # Estratégia: gentle ou smart - tentar clique normal primeiro
            try:
                element.click()
                self.logger.result(True, "O caminho está livre.")
                self._log_action("strike", target_str, "Normal click successful", True)
                return True
            except ElementClickInterceptedException:
                if strategy == "gentle":
                    # Gentle não tem fallback
                    self.logger.result(
                        False, "Elemento interceptado. Estratégia 'gentle' não permite fallback."
                    )
                    self._log_action("strike", target_str, "Click intercepted, no fallback", False)
                    raise

                # Smart: usar fallback JS click
                self.logger.warning("Bloqueado! Usando Injeção de Força...")
                self.driver.execute_script("arguments[0].click();", element)
                self.logger.result(True, "Injeção de Força bem-sucedida! O caminho está livre.")
                self._log_action("strike", target_str, "JS click fallback successful", True)
                return True

        except Exception as e:
            self.logger.error(f"Todas as estratégias falharam: {str(e)}")
            self._log_action("strike", target_str, f"Failed: {str(e)}", False)

            # Detectar se é erro estrutural e rastrear
            if self.error_detector and self.error_detector.is_structural_error(e):
                error_context = self.error_detector.track_error(
                    exception=e, selector=target_str, by_type=by, maneuver_name="strike"
                )

                # Se atingiu threshold, tentar skill existente ou gerar nova
                if self.error_detector.should_invoke_divine_inspiration(error_context):
                    self.logger.wisdom(
                        "Erro estrutural detectado repetidamente. Buscando solução..."
                    )

                    # Tentar skill existente primeiro
                    if self._try_existing_skill(error_context):
                        self.logger.result(True, "Skill existente resolveu o problema!")
                        return True

                    # Se não resolveu, invocar Divine Inspiration
                    context_desc = error_context.to_description()
                    result = self.divine_inspiration(context_desc)

                    if result["success"]:
                        # Tentar executar a nova skill
                        skill_name = result["skill_name"]
                        if self.execute_skill(skill_name):
                            self.logger.result(
                                True, f"Nova skill '{skill_name}' resolveu o problema!"
                            )
                            return True

            # Invocar sabedoria dos Anciões
            tb_str = traceback.format_exc()
            self.invoke_wisdom(e, tb_str)
            raise

    def scout(self, possibilities_list: List[Dict[str, str]]) -> Optional[WebElement]:
        """
        Reconhece o terreno e retorna o primeiro caminho seguro encontrado.

        Esta manobra permite buscar múltiplos seletores/textos para o mesmo
        objetivo, útil para lidar com diferentes idiomas ou estruturas de página.

        Args:
            possibilities_list: Lista de possíveis seletores/textos.
                Formato aceito:
                [
                    {"text": "Definições", "type": "link"},
                    {"text": "Settings", "type": "button"},
                    {"css": ".settings-btn"},
                    {"xpath": "//button[@id='settings']"},
                    {"id": "settings-button"}
                ]

        Returns:
            WebElement: Primeiro elemento encontrado
            None: Se nenhum caminho for encontrado

        Example:
            >>> element = selum.scout([
            ...     {"text": "Definições"},
            ...     {"text": "Settings"},
            ...     {"css": ".settings-btn"}
            ... ])
            [Turno 2 - Selum of Persistence]: Farejando trilhas em busca de 3 caminhos...
            [Resultado]: ✓ Caminho seguro encontrado: Settings
        """
        turn = self._increment_turn()
        num_paths = len(possibilities_list)

        self.logger.turn_action(turn, "Farejando trilhas", f"{num_paths} caminhos possíveis")

        for possibility in possibilities_list:
            try:
                element = None
                path_desc = ""

                # Tentar por texto
                if "text" in possibility:
                    text = possibility["text"]
                    path_desc = f"text='{text}'"

                    # Determinar tipo de elemento
                    if possibility.get("type") == "link":
                        element = self.driver.find_element(By.LINK_TEXT, text)
                    elif possibility.get("type") == "partial":
                        element = self.driver.find_element(By.PARTIAL_LINK_TEXT, text)
                    else:
                        # Tentar XPath genérico para qualquer elemento com o texto
                        element = self.driver.find_element(
                            By.XPATH, f"//*[contains(text(), '{text}')]"
                        )

                # Tentar por CSS
                elif "css" in possibility:
                    css = possibility["css"]
                    path_desc = f"css='{css}'"
                    element = self.driver.find_element(By.CSS_SELECTOR, css)

                # Tentar por XPath
                elif "xpath" in possibility:
                    xpath = possibility["xpath"]
                    path_desc = f"xpath='{xpath}'"
                    element = self.driver.find_element(By.XPATH, xpath)

                # Tentar por ID
                elif "id" in possibility:
                    elem_id = possibility["id"]
                    path_desc = f"id='{elem_id}'"
                    element = self.driver.find_element(By.ID, elem_id)

                # Tentar por Name
                elif "name" in possibility:
                    name = possibility["name"]
                    path_desc = f"name='{name}'"
                    element = self.driver.find_element(By.NAME, name)

                # Se encontrou, retornar
                if element:
                    self.logger.result(True, f"Caminho seguro encontrado: {path_desc}")
                    self._log_action("scout", f"{num_paths} paths", f"Found: {path_desc}", True)
                    return element

            except (NoSuchElementException, Exception):
                # Continuar tentando próximo caminho
                continue

        # Nenhum caminho encontrado
        self.logger.result(False, "Nenhum caminho seguro detectado.")
        self._log_action("scout", f"{num_paths} paths", "No path found", False)
        return None

    def vigilance(self, selector: str, timeout: int = 20, by: str = By.CSS_SELECTOR) -> WebElement:
        """
        Aguarda um elemento aparecer com logs de progresso.

        Esta manobra implementa uma espera inteligente que reporta o progresso
        a cada 5 segundos, mantendo o usuário informado sobre o estado da vigília.

        Args:
            selector: Seletor do elemento a aguardar
            timeout: Tempo máximo de espera em segundos (padrão: 20)
            by: Tipo de seletor (By.CSS_SELECTOR, By.XPATH, etc.)

        Returns:
            WebElement: Elemento encontrado

        Raises:
            TimeoutException: Se o elemento não aparecer no tempo limite

        Example:
            >>> element = selum.vigilance(".api-key-field", timeout=30)
            [Turno 3 - Selum of Persistence]: Em vigília constante aguardando '.api-key-field'...
            [Progresso]: Ainda em vigília... (5s de 30s)
            [Progresso]: Ainda em vigília... (10s de 30s)
            [Resultado]: ✓ Brecha na armadura do DOM detectada!
        """
        turn = self._increment_turn()

        self.logger.turn_action(turn, "Em vigília constante aguardando", selector)

        start_time = time.time()
        last_log_time = start_time

        try:
            # Criar WebDriverWait
            wait = WebDriverWait(self.driver, timeout, poll_frequency=0.5)

            # Função customizada para checar elemento e logar progresso
            def check_and_log(driver):
                nonlocal last_log_time
                current_time = time.time()
                elapsed = int(current_time - start_time)

                # Logar progresso a cada 5 segundos
                if current_time - last_log_time >= 5:
                    self.logger.progress(f"Ainda em vigília... ({elapsed}s de {timeout}s)")
                    last_log_time = current_time

                # Tentar encontrar elemento
                try:
                    element = driver.find_element(by, selector)
                    return element if element else False
                except NoSuchElementException:
                    return False

            # Aguardar elemento
            element = wait.until(check_and_log)

            self.logger.result(True, "Brecha na armadura do DOM detectada!")
            self._log_action("vigilance", selector, "Element found", True)
            return element

        except TimeoutException as e:
            elapsed = int(time.time() - start_time)
            self.logger.result(False, f"Alvo não apareceu. Tempo esgotado ({elapsed}s).")
            self._log_action("vigilance", selector, f"Timeout after {elapsed}s", False)

            # Detectar se é erro estrutural e rastrear
            if self.error_detector and self.error_detector.is_structural_error(e):
                error_context = self.error_detector.track_error(
                    exception=e, selector=selector, by_type=by, maneuver_name="vigilance"
                )

                # Se atingiu threshold, tentar skill existente ou gerar nova
                if self.error_detector.should_invoke_divine_inspiration(error_context):
                    self.logger.wisdom(
                        "Erro estrutural detectado repetidamente. Buscando solução..."
                    )

                    # Tentar skill existente primeiro
                    if self._try_existing_skill(error_context):
                        self.logger.result(True, "Skill existente resolveu o problema!")
                        # Tentar encontrar o elemento novamente
                        try:
                            element = self.driver.find_element(by, selector)
                            return element
                        except Exception:
                            pass

                    # Se não resolveu, invocar Divine Inspiration
                    context_desc = error_context.to_description()
                    result = self.divine_inspiration(context_desc)

                    if result["success"]:
                        # Tentar executar a nova skill
                        skill_name = result["skill_name"]
                        if self.execute_skill(skill_name):
                            self.logger.result(
                                True, f"Nova skill '{skill_name}' resolveu o problema!"
                            )
                            # Tentar encontrar o elemento novamente
                            try:
                                element = self.driver.find_element(by, selector)
                                return element
                            except Exception:
                                pass

            # Invocar sabedoria
            tb_str = traceback.format_exc()
            self.invoke_wisdom(e, tb_str)
            raise

    def cleansing_aura(self) -> int:
        """
        Remove overlays, modais e pop-ups que bloqueiam o caminho.

        Esta manobra tenta identificar e remover obstáculos comuns que
        impedem a interação com elementos da página.

        Returns:
            int: Número de obstáculos removidos

        Example:
            >>> removed = selum.cleansing_aura()
            [Turno 4 - Selum of Persistence]: Invocando Aura de Limpeza...
            [Resultado]: ✓ 2 névoas dissipadas!
        """
        turn = self._increment_turn()

        self.logger.turn_action(turn, "Invocando Aura de Limpeza", "obstáculos do DOM")

        # Lista de seletores comuns de overlays e modais
        obstacle_selectors = [
            ".modal-backdrop",
            ".overlay",
            ".modal",
            "[class*='popup']",
            "[class*='cookie']",
            "[class*='banner']",
            "[aria-modal='true']",
            "[role='dialog']",
            "button[aria-label*='Close']",
            "button[aria-label*='Fechar']",
            "button[class*='close']",
            ".close",
            "[data-dismiss='modal']",
        ]

        removed_count = 0

        for selector in obstacle_selectors:
            try:
                # Tentar encontrar elementos com este seletor
                elements = self.driver.find_elements(By.CSS_SELECTOR, selector)

                for element in elements:
                    try:
                        # Tentar clicar (para botões de fechar)
                        if "button" in element.tag_name.lower() or "close" in selector.lower():
                            element.click()
                            removed_count += 1
                        # Ou remover via JavaScript
                        else:
                            self.driver.execute_script("arguments[0].remove();", element)
                            removed_count += 1
                    except Exception:
                        # Se falhar, tentar remover via JS
                        try:
                            self.driver.execute_script("arguments[0].remove();", element)
                            removed_count += 1
                        except Exception:
                            continue

            except Exception:
                continue

        if removed_count > 0:
            self.logger.result(True, f"{removed_count} névoas dissipadas!")
            self._log_action("cleansing_aura", "DOM obstacles", f"{removed_count} removed", True)
        else:
            self.logger.result(True, "Nenhuma névoa detectada. O caminho está limpo.")
            self._log_action("cleansing_aura", "DOM obstacles", "None found", True)

        return removed_count

    def steady_gaze(
        self, selector: Union[str, WebElement], by: str = By.CSS_SELECTOR
    ) -> WebElement:
        """
        Move o foco (scroll) até o elemento para garantir visibilidade.

        Esta manobra garante que o elemento esteja visível no viewport
        antes de qualquer interação, prevenindo erros de elemento não interagível.

        Args:
            selector: Seletor CSS, XPath, ou WebElement já localizado
            by: Tipo de seletor (By.CSS_SELECTOR, By.XPATH, etc.)

        Returns:
            WebElement: Elemento focado

        Example:
            >>> element = selum.steady_gaze(".hidden-button")
            [Turno 5 - Selum of Persistence]: Fixando o olhar em '.hidden-button'...
            [Resultado]: ✓ Alvo em foco!
        """
        turn = self._increment_turn()
        target_str = selector if isinstance(selector, str) else "WebElement"

        self.logger.turn_action(turn, "Fixando o olhar em", target_str)

        try:
            # Localizar elemento se for string
            if isinstance(selector, str):
                element = self.driver.find_element(by, selector)
            else:
                element = selector

            # Scroll suave até o elemento (centralizado)
            self.driver.execute_script(
                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});", element
            )

            # Aguardar scroll completar
            time.sleep(0.5)

            self.logger.result(True, "Alvo em foco!")
            self._log_action("steady_gaze", target_str, "Element in view", True)
            return element

        except Exception as e:
            self.logger.error(f"Falha ao focar elemento: {str(e)}")
            self._log_action("steady_gaze", target_str, f"Failed: {str(e)}", False)

            # Detectar se é erro estrutural e rastrear
            if self.error_detector and self.error_detector.is_structural_error(e):
                error_context = self.error_detector.track_error(
                    exception=e, selector=target_str, by_type=by, maneuver_name="steady_gaze"
                )

                # Se atingiu threshold, tentar skill existente ou gerar nova
                if self.error_detector.should_invoke_divine_inspiration(error_context):
                    self.logger.wisdom(
                        "Erro estrutural detectado repetidamente. Buscando solução..."
                    )

                    # Tentar skill existente primeiro
                    if self._try_existing_skill(error_context):
                        self.logger.result(True, "Skill existente resolveu o problema!")
                        # Tentar encontrar o elemento novamente
                        try:
                            if isinstance(selector, str):
                                element = self.driver.find_element(by, selector)
                            else:
                                element = selector
                            return element
                        except Exception:
                            pass

                    # Se não resolveu, invocar Divine Inspiration
                    context_desc = error_context.to_description()
                    result = self.divine_inspiration(context_desc)

                    if result["success"]:
                        # Tentar executar a nova skill
                        skill_name = result["skill_name"]
                        if self.execute_skill(skill_name):
                            self.logger.result(
                                True, f"Nova skill '{skill_name}' resolveu o problema!"
                            )
                            # Tentar encontrar o elemento novamente
                            try:
                                if isinstance(selector, str):
                                    element = self.driver.find_element(by, selector)
                                else:
                                    element = selector
                                return element
                            except Exception:
                                pass

            # Invocar sabedoria
            tb_str = traceback.format_exc()
            self.invoke_wisdom(e, tb_str)
            raise

    def invoke_wisdom(self, exception: Exception, traceback_str: str) -> Dict[str, Any]:
        """
        Invoca a sabedoria dos Anciões (AgentFactory) quando uma manobra falha.

        Esta manobra especial conecta o Paladino ao sistema de aprendizado,
        permitindo que falhas sejam analisadas e novas estratégias sejam
        adicionadas ao grimório (selenium.md).

        Args:
            exception: Exceção que ocorreu durante a manobra
            traceback_str: Traceback completo da exceção

        Returns:
            dict: Resposta do AgentFactory contendo:
                - specialist_name: Nome do especialista (selenium)
                - specialist_exists: Se o especialista já existia
                - combat_maneuvers_applied: Manobras aplicadas
                - evolution_triggered: Se houve evolução
                - suggested_solution: Solução sugerida
                - error: Mensagem de erro (se houver)

        Example:
            >>> try:
            ...     selum.strike(".non-existent")
            ... except Exception as e:
            ...     response = selum.invoke_wisdom(e, traceback.format_exc())
            [Turno 6 - Selum of Persistence]: Invocando a sabedoria dos Anciões...
            [Sabedoria Ancestral]: Use scout() para múltiplos seletores
        """
        turn = self._increment_turn()

        self.logger.turn_action(turn, "Invocando a sabedoria dos Anciões", type(exception).__name__)

        try:
            # Importar AgentFactory
            from src.agents.agent_factory import AgentFactory

            # Chamar AgentFactory
            response = AgentFactory.handle_exception(exception, traceback_str)

            # Logar solução sugerida se houver
            if response.get("suggested_solution"):
                self.logger.wisdom(response["suggested_solution"])
            elif response.get("error"):
                self.logger.warning(f"Anciões não puderam ajudar: {response['error']}")
            else:
                self.logger.wisdom("Grimório atualizado com nova sabedoria.")

            self._log_action("invoke_wisdom", type(exception).__name__, "Wisdom invoked", True)
            return response

        except Exception as e:
            self.logger.error(f"Falha ao invocar sabedoria: {str(e)}")
            self._log_action("invoke_wisdom", type(exception).__name__, f"Failed: {str(e)}", False)

            # Retornar resposta vazia em caso de falha
            return {
                "specialist_name": None,
                "specialist_exists": False,
                "combat_maneuvers_applied": [],
                "evolution_triggered": False,
                "suggested_solution": None,
                "error": str(e),
            }

    def combo_login(
        self,
        username: str,
        password: str,
        username_selector: str = "#username",
        password_selector: str = "#password",
        submit_selector: str = "button[type='submit']",
    ) -> bool:
        """
        Combo de manobras para realizar login.

        Esta é uma sequência pré-definida de ações para facilitar logins.

        Args:
            username: Nome de usuário
            password: Senha
            username_selector: Seletor do campo de usuário
            password_selector: Seletor do campo de senha
            submit_selector: Seletor do botão de submit

        Returns:
            bool: True se o login foi bem-sucedido

        Example:
            >>> selum.combo_login("user@example.com", "senha123")
            [Turno 7 - Selum of Persistence]: Executando Combo: Login Sequence...
            [Resultado]: ✓ Combo executado com sucesso!
        """
        pass  # Implementação futura (Fase 6)

    def combo_navigate_to_settings(
        self, settings_possibilities: Optional[List[Dict[str, str]]] = None
    ) -> bool:
        """
        Combo de manobras para navegar até configurações.

        Args:
            settings_possibilities: Lista de possíveis seletores para configurações
                Se None, usa lista padrão com múltiplos idiomas

        Returns:
            bool: True se a navegação foi bem-sucedida

        Example:
            >>> selum.combo_navigate_to_settings()
            [Turno 8 - Selum of Persistence]: Executando Combo: Navigate to Settings...
            [Resultado]: ✓ Combo executado com sucesso!
        """
        pass  # Implementação futura (Fase 6)

    def _calculate_context_similarity(self, ctx1: str, ctx2: str) -> float:
        """
        Calcula similaridade entre dois contextos de erro.

        Args:
            ctx1: Primeiro contexto (descrição de erro)
            ctx2: Segundo contexto (descrição de erro)

        Returns:
            float: Valor entre 0.0 (totalmente diferente) e 1.0 (idêntico)
        """
        from difflib import SequenceMatcher

        return SequenceMatcher(None, ctx1.lower(), ctx2.lower()).ratio()

    def _try_existing_skill(self, error_context) -> bool:
        """
        Tenta resolver o problema com uma skill existente.

        Args:
            error_context: ErrorContext com informações do erro atual

        Returns:
            bool: True se alguma skill resolveu o problema
        """
        if not self.skill_registry:
            return False

        # Carregar contextos originais das skills do grimório
        try:
            import re

            grimoire_path = "src/agents/specs/selenium.md"

            if not os.path.exists(grimoire_path):
                return False

            with open(grimoire_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extrair contextos das skills
            skill_contexts = {}
            pattern = r"### Skill: (skill_\w+)\n.*?Context: (.*?)\n"
            matches = re.finditer(pattern, content, re.DOTALL)

            for match in matches:
                skill_name = match.group(1)
                context = match.group(2).strip()
                skill_contexts[skill_name] = context

            # Tentar skills com contexto similar
            current_context = error_context.to_description()

            for skill_name, original_context in skill_contexts.items():
                if skill_name not in self.skill_registry:
                    continue

                # Calcular similaridade
                similarity = self._calculate_context_similarity(current_context, original_context)

                if similarity > 0.7:
                    self.logger.wisdom(
                        f"Skill '{skill_name}' tem contexto similar (similaridade: {similarity:.2f}). Tentando..."
                    )

                    # Executar skill
                    try:
                        success = self.execute_skill(skill_name)
                        if success:
                            self.logger.result(True, f"Skill '{skill_name}' resolveu o problema!")
                            return True
                    except Exception as e:
                        self.logger.warning(f"Skill '{skill_name}' falhou: {str(e)}")
                        continue

            return False

        except Exception as e:
            self.logger.warning(f"Erro ao tentar skills existentes: {str(e)}")
            return False

    def _load_custom_skills(self) -> None:
        """
        Carrega skills customizadas do grimório na inicialização.

        Este método é chamado automaticamente no __init__ se Divine Inspiration
        estiver habilitado. Carrega todas as skills salvas no selenium.md.
        """
        if not self.divine_engine:
            return

        try:
            from src.divine_inspiration import (
                AlchemistsFilter,
                CodeValidator,
                GrimoireManager,
                HotPatcher,
            )

            # Carregar skills do grimório
            skills = GrimoireManager.load_skills()

            loaded_count = 0
            for skill_name, skill_code in skills.items():
                try:
                    # Validar sintaxe
                    is_valid_syntax, syntax_error = AlchemistsFilter.validate_syntax(skill_code)
                    if not is_valid_syntax:
                        self.logger.warning(
                            f"Skill {skill_name} tem erro de sintaxe: {syntax_error}"
                        )
                        continue

                    # Validar segurança
                    is_valid_security, security_error = CodeValidator.validate(
                        skill_code, skill_name
                    )
                    if not is_valid_security:
                        self.logger.warning(
                            f"Skill {skill_name} falhou validação de segurança: {security_error}"
                        )
                        continue

                    # Compilar e registrar
                    if HotPatcher.patch_skill(skill_name, skill_code, self.skill_registry):
                        loaded_count += 1
                    else:
                        self.logger.warning(f"Falha ao compilar skill {skill_name}")

                except Exception as e:
                    self.logger.warning(f"Erro ao carregar skill {skill_name}: {e}")
                    continue

            if loaded_count > 0:
                self.logger.wisdom(f"Carregadas {loaded_count} skills customizadas do grimório")

        except Exception as e:
            self.logger.warning(f"Erro ao carregar skills customizadas: {e}")

    def _calculate_context_similarity(self, ctx1: str, ctx2: str) -> float:
        """
        Calcula similaridade entre dois contextos de erro.

        Args:
            ctx1: Primeiro contexto (descrição de erro)
            ctx2: Segundo contexto (descrição de erro)

        Returns:
            float: Valor entre 0.0 (totalmente diferente) e 1.0 (idêntico)
        """
        from difflib import SequenceMatcher

        return SequenceMatcher(None, ctx1.lower(), ctx2.lower()).ratio()

    def _try_existing_skill(self, error_context) -> bool:
        """
        Tenta resolver o problema com uma skill existente.

        Args:
            error_context: ErrorContext com informações do erro atual

        Returns:
            bool: True se alguma skill resolveu o problema
        """
        if not self.skill_registry:
            return False

        # Carregar contextos originais das skills do grimório
        try:
            import re

            grimoire_path = "src/agents/specs/selenium.md"

            if not os.path.exists(grimoire_path):
                return False

            with open(grimoire_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Extrair contextos das skills
            skill_contexts = {}
            pattern = r"### Skill: (skill_\w+)\n.*?Context: (.*?)\n"
            matches = re.finditer(pattern, content, re.DOTALL)

            for match in matches:
                skill_name = match.group(1)
                context = match.group(2).strip()
                skill_contexts[skill_name] = context

            # Tentar skills com contexto similar
            current_context = error_context.to_description()

            for skill_name, original_context in skill_contexts.items():
                if skill_name not in self.skill_registry:
                    continue

                # Calcular similaridade
                similarity = self._calculate_context_similarity(current_context, original_context)

                if similarity > 0.7:
                    self.logger.wisdom(
                        f"Skill '{skill_name}' tem contexto similar (similaridade: {similarity:.2f}). Tentando..."
                    )

                    # Executar skill
                    try:
                        success = self.execute_skill(skill_name)
                        if success:
                            self.logger.result(True, f"Skill '{skill_name}' resolveu o problema!")
                            return True
                    except Exception as e:
                        self.logger.warning(f"Skill '{skill_name}' falhou: {str(e)}")
                        continue

            return False

        except Exception as e:
            self.logger.warning(f"Erro ao tentar skills existentes: {str(e)}")
            return False

    def divine_inspiration(self, context_description: str) -> Dict[str, Any]:
        """
        Invoca a Inspiração Divina para gerar uma nova skill customizada.

        Este método implementa o Recovery Loop completo:
        1. Gera código com Groq
        2. Valida sintaxe com compile()
        3. Se falha, tenta Recovery Maneuver (máx 2 tentativas)
        4. Valida segurança
        5. Executa em sandbox
        6. Se bem-sucedida, persiste no grimório

        Args:
            context_description: Descrição do problema encontrado

        Returns:
            dict: Resultado contendo:
                - success: bool
                - skill_name: str (se sucesso)
                - skill_code: str (se sucesso)
                - error_message: str (se falha)

        Example:
            >>> result = selum.divine_inspiration("NoSuchElementException on .button after 3 attempts")
            [Turno: Selum] Invocando Inspiração Divina para resolver: NoSuchElementException...
            [Turno: Selum] Nova skill aprendida: skill_handle_button_click
        """
        if not self.divine_engine or not self.error_detector:
            return {"success": False, "error_message": "Divine Inspiration not initialized"}

        turn = self._increment_turn()

        try:
            from src.divine_inspiration import (
                AlchemistsFilter,
                CodeValidator,
                ErrorContext,
                GrimoireManager,
                HotPatcher,
                SkillExecutor,
            )

            # Criar ErrorContext a partir da descrição
            # (simplificado - em produção seria mais robusto)
            parts = context_description.split(" on ")
            error_type = parts[0] if len(parts) > 0 else "UnknownError"
            selector = parts[1].split(" after")[0] if len(parts) > 1 else "unknown"

            context = ErrorContext(
                error_type=error_type,
                selector=selector,
                by_type="CSS_SELECTOR",
                html_context=self.error_detector._extract_html_context(selector),
                attempt_count=3,
                timestamp=time.time(),
                maneuver_history=[],
            )

            self.logger.turn_action(
                turn, "Invocando Inspiração Divina para resolver", context_description
            )

            # Recovery Loop (máx 2 tentativas)
            previous_attempt = None
            max_attempts = AlchemistsFilter.MAX_RECOVERY_ATTEMPTS

            for attempt in range(1, max_attempts + 1):
                # Gerar skill
                if attempt > 1:
                    self.logger.warning(
                        f"[Turno: Selum] Invocando Manobra de Recuperação (tentativa {attempt}/{max_attempts})..."
                    )

                result = self.divine_engine.generate_skill(context, previous_attempt)

                if not result["success"]:
                    return {
                        "success": False,
                        "error_message": result.get("error_message", "Failed to generate skill"),
                    }

                skill_name = result["skill_name"]
                skill_code = result["skill_code"]

                # Validar sintaxe com AlchemistsFilter
                is_valid_syntax, syntax_error = AlchemistsFilter.validate_syntax(skill_code)
                if not is_valid_syntax:
                    self.logger.warning(
                        "[Turno: Selum] A inspiração divina veio corrompida! Recuando para meditação..."
                    )
                    previous_attempt = {
                        "code": skill_code,
                        "error": syntax_error,
                        "error_type": "syntax",
                        "attempt_number": attempt,
                    }
                    continue

                # Validar segurança
                is_valid_security, security_error = CodeValidator.validate(skill_code, skill_name)
                if not is_valid_security:
                    # Erro de segurança não tem recovery
                    return {
                        "success": False,
                        "error_message": f"Security validation failed: {security_error}",
                    }

                # Compilar
                if not HotPatcher.patch_skill(skill_name, skill_code, self.skill_registry):
                    previous_attempt = {
                        "code": skill_code,
                        "error": "Failed to compile skill",
                        "error_type": "execution",
                        "attempt_number": attempt,
                    }
                    continue

                # Executar em sandbox (primeira execução)
                success, exec_error = SkillExecutor.execute(
                    skill_name, self.skill_registry, self, is_first_execution=True
                )

                if not success:
                    self.logger.warning(
                        f"[Turno: Selum] A skill falhou em combate! Erro: {exec_error}"
                    )
                    previous_attempt = {
                        "code": skill_code,
                        "error": exec_error,
                        "error_type": "execution",
                        "attempt_number": attempt,
                    }
                    continue

                # Sucesso! Persistir no grimório
                self.logger.wisdom("[Turno: Selum] Skill consagrada! A manobra foi bem-sucedida!")

                if attempt > 1:
                    self.logger.wisdom(
                        "[Turno: Selum] A meditação trouxe clareza! Nova skill gerada com sucesso."
                    )

                self.logger.wisdom(f"Nova skill aprendida: {skill_name}")

                GrimoireManager.save_skill(
                    skill_name, skill_code, context_description, context.html_context
                )

                self.logger.wisdom(f"Skill persistida no grimório: {skill_name}")

                return {"success": True, "skill_name": skill_name, "skill_code": skill_code}

            # Todas as tentativas falharam
            self.logger.warning(
                "[Turno: Selum] Todas as tentativas de inspiração divina falharam. Retornando ao combate tradicional."
            )
            return {"success": False, "error_message": "All recovery attempts failed"}

        except Exception as e:
            self.logger.error(f"Erro durante Divine Inspiration: {e}")
            return {"success": False, "error_message": str(e)}

    def execute_skill(self, skill_name: str) -> bool:
        """
        Executa uma skill customizada do registry.

        Args:
            skill_name: Nome da skill a executar

        Returns:
            bool: True se bem-sucedida, False caso contrário

        Example:
            >>> selum.execute_skill("skill_handle_cookie_banner")
            [Turno: Selum] Executando skill customizada: skill_handle_cookie_banner
            True
        """
        if not self.skill_registry or skill_name not in self.skill_registry:
            self.logger.warning(f"Skill {skill_name} não encontrada no registry")
            return False

        try:
            from src.divine_inspiration import SkillExecutor

            turn = self._increment_turn()
            self.logger.turn_action(turn, "Executando skill customizada", skill_name)

            success, error = SkillExecutor.execute(
                skill_name, self.skill_registry, self, is_first_execution=False
            )

            if success:
                self.logger.result(True, f"Skill {skill_name} executada com sucesso!")
            else:
                self.logger.result(False, f"Skill {skill_name} falhou: {error}")

            return success

        except Exception as e:
            self.logger.error(f"Erro ao executar skill {skill_name}: {e}")
            return False
