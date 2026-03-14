"""
Gerenciamento de conexão Chrome DevTools Protocol (CDP).

Estabelece e mantém conexão CDP com o navegador Chrome/Chromium
para inspeção profunda não disponível via Selenium padrão.
"""

from typing import Any, Dict, Optional

from selenium import webdriver

from src.utils.logger import get_logger


class CDPConnectionError(Exception):
    """Erro de conexão CDP."""

    pass


class CDPConnection:
    """
    Gerenciador de conexão CDP.

    Estabelece conexão com Chrome DevTools Protocol e habilita
    domínios necessários para análise profunda.
    """

    def __init__(self, driver: webdriver.Remote, timeout: int = 10):
        """
        Inicializa conexão CDP.

        Args:
            driver: Instância do WebDriver Selenium
            timeout: Timeout padrão para operações CDP em segundos
        """
        self.driver = driver
        self.timeout = timeout
        self.logger = get_logger("steady_gaze.cdp")
        self._enabled_domains = set()

        # Tentar estabelecer conexão CDP
        try:
            self._establish_connection()
        except Exception as e:
            self.logger.error(f"Falha ao estabelecer conexão CDP: {e}")
            raise CDPConnectionError(f"Não foi possível conectar ao CDP: {e}")

    def _establish_connection(self) -> None:
        """
        Estabelece conexão CDP com o navegador.

        Raises:
            CDPConnectionError: Se conexão falhar
        """
        try:
            # Verificar se driver suporta CDP
            if not hasattr(self.driver, "execute_cdp_cmd"):
                raise CDPConnectionError(
                    "Driver não suporta CDP. Use ChromeDriver ou driver compatível."
                )

            # Testar conexão com comando simples
            version = self.driver.execute_cdp_cmd("Browser.getVersion", {})
            self.logger.info(f"Conexão CDP estabelecida: {version.get('product', 'Unknown')}")

        except Exception as e:
            raise CDPConnectionError(f"Erro ao estabelecer conexão CDP: {e}")

    def enable_domain(self, domain: str) -> None:
        """
        Habilita um domínio CDP.

        Args:
            domain: Nome do domínio (ex: "Network", "Runtime", "DOM")

        Raises:
            CDPConnectionError: Se falhar ao habilitar domínio
        """
        if domain in self._enabled_domains:
            self.logger.debug(f"Domínio {domain} já habilitado")
            return

        try:
            self.driver.execute_cdp_cmd(f"{domain}.enable", {})
            self._enabled_domains.add(domain)
            self.logger.debug(f"Domínio {domain} habilitado")
        except Exception as e:
            self.logger.warning(f"Falha ao habilitar domínio {domain}: {e}")
            raise CDPConnectionError(f"Não foi possível habilitar domínio {domain}: {e}")

    def enable_required_domains(self) -> None:
        """
        Habilita todos os domínios necessários para análise Steady Gaze.

        Domínios habilitados:
        - Network: Interceptação de requisições/respostas
        - Runtime: Execução de JavaScript e acesso a objetos
        - DOM: Inspeção profunda da árvore DOM
        - DOMDebugger: Event listeners e breakpoints
        - Security: Informações de certificado TLS
        - Page: Eventos de navegação e lifecycle
        """
        required_domains = ["Network", "Runtime", "DOM", "DOMDebugger", "Security", "Page"]

        for domain in required_domains:
            try:
                self.enable_domain(domain)
            except CDPConnectionError as e:
                self.logger.warning(f"Continuando sem domínio {domain}: {e}")

    def execute(self, command: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executa comando CDP.

        Args:
            command: Comando CDP (ex: "Runtime.evaluate")
            params: Parâmetros do comando

        Returns:
            Resposta do comando CDP

        Raises:
            CDPConnectionError: Se comando falhar
        """
        try:
            result = self.driver.execute_cdp_cmd(command, params or {})
            return result
        except Exception as e:
            self.logger.error(f"Erro ao executar comando CDP {command}: {e}")
            raise CDPConnectionError(f"Falha ao executar {command}: {e}")

    def is_domain_enabled(self, domain: str) -> bool:
        """
        Verifica se domínio está habilitado.

        Args:
            domain: Nome do domínio

        Returns:
            True se domínio está habilitado
        """
        return domain in self._enabled_domains
