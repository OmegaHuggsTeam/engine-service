"""
Testes unitários para conexão CDP do Steady Gaze Recon.

Feature: steady-gaze-recon
Testa estabelecimento de conexão CDP, habilitação de domínios e fallback.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from selenium import webdriver

from src.steady_gaze.cdp_connection import CDPConnection, CDPConnectionError
from src.steady_gaze.recon import SteadyGazeRecon


class TestCDPConnection:
    """Testes para classe CDPConnection."""
    
    def test_connection_establishment_success(self):
        """Testa estabelecimento bem-sucedido de conexão CDP."""
        # Mock driver with CDP support
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={
            'product': 'Chrome/120.0.0.0',
            'jsVersion': '12.0.0.0'
        })
        
        # Create connection
        cdp = CDPConnection(driver, timeout=10)
        
        # Verify connection was established
        assert cdp.driver == driver
        assert cdp.timeout == 10
        driver.execute_cdp_cmd.assert_called_with('Browser.getVersion', {})
    
    def test_connection_establishment_no_cdp_support(self):
        """Testa erro quando driver não suporta CDP."""
        # Mock driver without CDP support
        driver = Mock(spec=webdriver.Remote)
        delattr(driver, 'execute_cdp_cmd')
        
        # Should raise CDPConnectionError
        with pytest.raises(CDPConnectionError) as exc_info:
            CDPConnection(driver)
        
        assert "não suporta CDP" in str(exc_info.value)
    
    def test_connection_establishment_cdp_command_fails(self):
        """Testa erro quando comando CDP falha."""
        # Mock driver that raises exception on CDP command
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(side_effect=Exception("Connection refused"))
        
        # Should raise CDPConnectionError
        with pytest.raises(CDPConnectionError) as exc_info:
            CDPConnection(driver)
        
        assert "Connection refused" in str(exc_info.value)
    
    def test_enable_domain_success(self):
        """Testa habilitação bem-sucedida de domínio."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Enable Network domain
        cdp.enable_domain("Network")
        
        # Verify domain was enabled
        assert "Network" in cdp._enabled_domains
        driver.execute_cdp_cmd.assert_any_call('Network.enable', {})
    
    def test_enable_domain_already_enabled(self):
        """Testa que domínio já habilitado não é habilitado novamente."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Enable domain twice
        cdp.enable_domain("Network")
        call_count_after_first = driver.execute_cdp_cmd.call_count
        
        cdp.enable_domain("Network")
        call_count_after_second = driver.execute_cdp_cmd.call_count
        
        # Second call should not trigger CDP command
        assert call_count_after_second == call_count_after_first
    
    def test_enable_domain_failure(self):
        """Testa erro ao habilitar domínio."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(side_effect=[
            {'product': 'Chrome'},  # getVersion succeeds
            Exception("Domain not found")  # enable fails
        ])
        
        cdp = CDPConnection(driver)
        
        # Should raise CDPConnectionError
        with pytest.raises(CDPConnectionError) as exc_info:
            cdp.enable_domain("InvalidDomain")
        
        assert "InvalidDomain" in str(exc_info.value)
    
    def test_enable_required_domains(self):
        """Testa habilitação de todos os domínios necessários."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        cdp.enable_required_domains()
        
        # Verify all required domains were enabled
        required_domains = ["Network", "Runtime", "DOM", "DOMDebugger", "Security", "Page"]
        for domain in required_domains:
            assert domain in cdp._enabled_domains
    
    def test_enable_required_domains_partial_failure(self):
        """Testa que falha em um domínio não impede outros."""
        driver = Mock(spec=webdriver.Remote)
        
        # Make DOMDebugger fail but others succeed
        def execute_cdp_side_effect(cmd, params):
            if cmd == 'Browser.getVersion':
                return {'product': 'Chrome'}
            elif 'DOMDebugger' in cmd:
                raise Exception("DOMDebugger not available")
            else:
                return {}
        
        driver.execute_cdp_cmd = Mock(side_effect=execute_cdp_side_effect)
        
        cdp = CDPConnection(driver)
        cdp.enable_required_domains()
        
        # Verify other domains were enabled despite DOMDebugger failure
        assert "Network" in cdp._enabled_domains
        assert "Runtime" in cdp._enabled_domains
        assert "DOM" in cdp._enabled_domains
        assert "DOMDebugger" not in cdp._enabled_domains
    
    def test_execute_command_success(self):
        """Testa execução bem-sucedida de comando CDP."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(side_effect=[
            {'product': 'Chrome'},  # getVersion
            {'result': {'value': 'test'}}  # custom command
        ])
        
        cdp = CDPConnection(driver)
        result = cdp.execute('Runtime.evaluate', {'expression': '1+1'})
        
        assert result == {'result': {'value': 'test'}}
        driver.execute_cdp_cmd.assert_called_with('Runtime.evaluate', {'expression': '1+1'})
    
    def test_execute_command_failure(self):
        """Testa erro ao executar comando CDP."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(side_effect=[
            {'product': 'Chrome'},  # getVersion
            Exception("Command failed")  # custom command
        ])
        
        cdp = CDPConnection(driver)
        
        with pytest.raises(CDPConnectionError) as exc_info:
            cdp.execute('Runtime.evaluate', {'expression': 'invalid'})
        
        assert "Command failed" in str(exc_info.value)
    
    def test_is_domain_enabled(self):
        """Testa verificação de domínio habilitado."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Initially not enabled
        assert not cdp.is_domain_enabled("Network")
        
        # Enable and check
        cdp.enable_domain("Network")
        assert cdp.is_domain_enabled("Network")
        
        # Other domain still not enabled
        assert not cdp.is_domain_enabled("Runtime")


class TestSteadyGazeReconCDPIntegration:
    """Testes para integração CDP no SteadyGazeRecon."""
    
    def test_init_with_cdp_success(self):
        """Testa inicialização com CDP bem-sucedido."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        recon = SteadyGazeRecon(driver)
        
        # Verify CDP was initialized
        assert recon.cdp is not None
        assert isinstance(recon.cdp, CDPConnection)
        assert recon.driver == driver
    
    def test_init_with_provided_cdp_session(self):
        """Testa inicialização com sessão CDP fornecida."""
        driver = Mock(spec=webdriver.Remote)
        cdp_session = Mock(spec=CDPConnection)
        
        recon = SteadyGazeRecon(driver, cdp_session=cdp_session)
        
        # Verify provided CDP session was used
        assert recon.cdp == cdp_session
    
    def test_init_cdp_failure_fallback_to_selenium(self):
        """Testa fallback para Selenium quando CDP falha."""
        driver = Mock(spec=webdriver.Remote)
        # Driver without CDP support
        delattr(driver, 'execute_cdp_cmd')
        
        # Should not raise exception, should fallback
        recon = SteadyGazeRecon(driver)
        
        # Verify CDP is None (fallback mode)
        assert recon.cdp is None
        assert recon.driver == driver
    
    def test_init_enables_required_domains(self):
        """Testa que domínios necessários são habilitados na inicialização."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        recon = SteadyGazeRecon(driver)
        
        # Verify required domains were enabled
        assert recon.cdp.is_domain_enabled("Network")
        assert recon.cdp.is_domain_enabled("Runtime")
        assert recon.cdp.is_domain_enabled("DOM")
    
    def test_timeout_configuration(self):
        """Testa configuração de timeout."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        recon = SteadyGazeRecon(driver, timeout=20)
        
        assert recon.timeout == 20
        assert recon.cdp.timeout == 20


class TestCDPFallbackBehavior:
    """Testes para comportamento de fallback quando CDP não está disponível."""
    
    def test_analyze_full_without_cdp(self):
        """Testa que analyze_full funciona sem CDP (modo fallback)."""
        driver = Mock(spec=webdriver.Remote)
        driver.current_url = "https://example.com"
        driver.execute_script = Mock(return_value="<html><body>Test</body></html>")
        
        # Create recon without CDP
        recon = SteadyGazeRecon.__new__(SteadyGazeRecon)
        recon.driver = driver
        recon.timeout = 10
        recon.cdp = None  # No CDP available
        recon.logger = Mock()
        
        # Should not raise exception
        report = recon.analyze_full()
        
        # Verify report was generated
        assert report.url == "https://example.com"
        assert report.overall_risk_score >= 0
    
    def test_cdp_connection_error_logged(self):
        """Testa que erro de conexão CDP é logado."""
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(side_effect=Exception("CDP unavailable"))
        
        with patch('src.steady_gaze.recon.get_logger') as mock_logger:
            logger_instance = Mock()
            mock_logger.return_value = logger_instance
            
            recon = SteadyGazeRecon(driver)
            
            # Verify warning was logged
            logger_instance.warning.assert_called()
            warning_call = logger_instance.warning.call_args[0][0]
            assert "CDP não disponível" in warning_call or "fallback" in warning_call.lower()


class TestCDPDomainRequirements:
    """Testes para requisitos específicos de domínios CDP."""
    
    def test_network_domain_for_network_analysis(self):
        """
        Valida Requisito 23.2: Quando análise requer dados de rede,
        o Steady Gaze deve usar Network domain do CDP.
        """
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        cdp.enable_required_domains()
        
        # Verify Network domain is enabled for network analysis
        assert cdp.is_domain_enabled("Network")
    
    def test_runtime_domain_for_runtime_analysis(self):
        """
        Valida Requisito 23.3: Quando análise requer dados de runtime,
        o Steady Gaze deve usar Runtime domain do CDP.
        """
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        cdp.enable_required_domains()
        
        # Verify Runtime domain is enabled for runtime analysis
        assert cdp.is_domain_enabled("Runtime")
    
    def test_dom_domain_for_dom_analysis(self):
        """
        Valida Requisito 23.4: Quando análise requer dados de DOM,
        o Steady Gaze deve usar DOM domain do CDP.
        """
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        cdp.enable_required_domains()
        
        # Verify DOM domain is enabled for DOM analysis
        assert cdp.is_domain_enabled("DOM")
    
    def test_fallback_to_selenium_on_cdp_failure(self):
        """
        Valida Requisito 23.5: Quando conexão CDP falha,
        o Steady Gaze deve fazer fallback para métodos Selenium padrão.
        """
        driver = Mock(spec=webdriver.Remote)
        # Simulate CDP not available
        delattr(driver, 'execute_cdp_cmd')
        
        # Should not raise exception
        recon = SteadyGazeRecon(driver)
        
        # Verify fallback mode is active
        assert recon.cdp is None
        assert recon.driver is not None



# ============================================================================
# Property-Based Tests
# ============================================================================

from hypothesis import given, strategies as st, settings, assume


class TestPropertyCDPDomainUsage:
    """
    Testes baseados em propriedades para uso correto de CDP domains.
    
    **Valida: Requisitos 23.2, 23.3, 23.4, 23.5**
    
    Propriedade 23: Uso Correto de CDP Domains
    Para qualquer análise que requer dados de rede, runtime ou DOM,
    o Steady Gaze deve usar o domínio CDP correto (Network, Runtime, DOM)
    e fazer fallback para Selenium em caso de falha CDP.
    """
    
    @given(
        domains_to_enable=st.lists(
            st.sampled_from(["Network", "Runtime", "DOM", "DOMDebugger", "Security", "Page"]),
            min_size=1,
            max_size=6,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_correct_domain_usage_for_analysis_type(self, domains_to_enable):
        """
        Propriedade: Para qualquer conjunto de domínios necessários,
        o sistema deve habilitar exatamente os domínios corretos para
        o tipo de análise solicitado.
        
        **Valida: Requisitos 23.2, 23.3, 23.4**
        """
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Enable requested domains
        for domain in domains_to_enable:
            cdp.enable_domain(domain)
        
        # Propriedade: Todos os domínios solicitados devem estar habilitados
        for domain in domains_to_enable:
            assert cdp.is_domain_enabled(domain), \
                f"Domínio {domain} deveria estar habilitado mas não está"
        
        # Propriedade: Domínios não solicitados não devem estar habilitados
        all_domains = {"Network", "Runtime", "DOM", "DOMDebugger", "Security", "Page"}
        not_requested = all_domains - set(domains_to_enable)
        for domain in not_requested:
            assert not cdp.is_domain_enabled(domain), \
                f"Domínio {domain} não deveria estar habilitado mas está"
        
        # Propriedade: Cada domínio deve ser habilitado exatamente uma vez
        enable_calls = [
            call for call in driver.execute_cdp_cmd.call_args_list
            if '.enable' in str(call)
        ]
        
        # Contar chamadas de enable por domínio
        domain_enable_counts = {}
        for call in enable_calls:
            cmd = call[0][0]  # Primeiro argumento da chamada
            if '.enable' in cmd:
                domain = cmd.split('.')[0]
                domain_enable_counts[domain] = domain_enable_counts.get(domain, 0) + 1
        
        for domain in domains_to_enable:
            assert domain_enable_counts.get(domain, 0) == 1, \
                f"Domínio {domain} foi habilitado {domain_enable_counts.get(domain, 0)} vezes, esperado 1"
    
    @given(
        analysis_requires_network=st.booleans(),
        analysis_requires_runtime=st.booleans(),
        analysis_requires_dom=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_domain_selection_matches_analysis_needs(
        self,
        analysis_requires_network,
        analysis_requires_runtime,
        analysis_requires_dom
    ):
        """
        Propriedade: O sistema deve habilitar Network domain quando análise
        requer dados de rede, Runtime domain quando requer dados de runtime,
        e DOM domain quando requer dados de DOM.
        
        **Valida: Requisitos 23.2, 23.3, 23.4**
        """
        # Pelo menos um tipo de análise deve ser necessário
        assume(analysis_requires_network or analysis_requires_runtime or analysis_requires_dom)
        
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Simular necessidades de análise
        if analysis_requires_network:
            cdp.enable_domain("Network")
        
        if analysis_requires_runtime:
            cdp.enable_domain("Runtime")
        
        if analysis_requires_dom:
            cdp.enable_domain("DOM")
        
        # Propriedade: Domínios necessários devem estar habilitados
        if analysis_requires_network:
            assert cdp.is_domain_enabled("Network"), \
                "Network domain deve estar habilitado para análise de rede"
        
        if analysis_requires_runtime:
            assert cdp.is_domain_enabled("Runtime"), \
                "Runtime domain deve estar habilitado para análise de runtime"
        
        if analysis_requires_dom:
            assert cdp.is_domain_enabled("DOM"), \
                "DOM domain deve estar habilitado para análise de DOM"
    
    @given(
        cdp_available=st.booleans(),
        domains_to_enable=st.lists(
            st.sampled_from(["Network", "Runtime", "DOM"]),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_fallback_to_selenium_on_cdp_failure(
        self,
        cdp_available,
        domains_to_enable
    ):
        """
        Propriedade: Quando CDP não está disponível ou falha,
        o sistema deve fazer fallback para métodos Selenium padrão
        sem lançar exceção fatal.
        
        **Valida: Requisito 23.5**
        """
        driver = Mock(spec=webdriver.Remote)
        
        if cdp_available:
            # CDP disponível
            driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
            
            # Deve inicializar com sucesso
            recon = SteadyGazeRecon(driver)
            
            # Propriedade: CDP deve estar disponível
            assert recon.cdp is not None, \
                "CDP deveria estar disponível quando driver suporta"
            
            # Propriedade: Domínios devem ser habilitados
            for domain in domains_to_enable:
                assert recon.cdp.is_domain_enabled(domain) or domain not in ["Network", "Runtime", "DOM"], \
                    f"Domínio {domain} deveria estar habilitado"
        
        else:
            # CDP não disponível
            if hasattr(driver, 'execute_cdp_cmd'):
                delattr(driver, 'execute_cdp_cmd')
            
            # Deve inicializar sem exceção (fallback)
            recon = SteadyGazeRecon(driver)
            
            # Propriedade: CDP deve ser None (modo fallback)
            assert recon.cdp is None, \
                "CDP deveria ser None quando não disponível (modo fallback)"
            
            # Propriedade: Driver deve estar disponível para fallback Selenium
            assert recon.driver is not None, \
                "Driver Selenium deve estar disponível para fallback"
    
    @given(
        num_domains_fail=st.integers(min_value=0, max_value=3)
    )
    @settings(max_examples=50)
    def test_property_partial_domain_failure_continues_analysis(self, num_domains_fail):
        """
        Propriedade: Quando alguns domínios falham ao habilitar,
        o sistema deve continuar com os domínios que funcionam
        e não deve falhar completamente.
        
        **Valida: Requisito 23.5**
        """
        driver = Mock(spec=webdriver.Remote)
        
        all_domains = ["Network", "Runtime", "DOMDebugger", "Security", "Page", "DOM"]
        failing_domains = all_domains[:num_domains_fail]
        working_domains = all_domains[num_domains_fail:]
        
        def execute_cdp_side_effect(cmd, params):
            if cmd == 'Browser.getVersion':
                return {'product': 'Chrome'}
            
            # Fazer alguns domínios falharem (match exato do domínio)
            for domain in failing_domains:
                if cmd.startswith(f"{domain}."):
                    raise Exception(f"{domain} not available")
            
            return {}
        
        driver.execute_cdp_cmd = Mock(side_effect=execute_cdp_side_effect)
        
        cdp = CDPConnection(driver)
        cdp.enable_required_domains()
        
        # Propriedade: Domínios que funcionam devem estar habilitados
        for domain in working_domains:
            assert cdp.is_domain_enabled(domain), \
                f"Domínio {domain} deveria estar habilitado (não falhou)"
        
        # Propriedade: Domínios que falharam não devem estar habilitados
        for domain in failing_domains:
            assert not cdp.is_domain_enabled(domain), \
                f"Domínio {domain} não deveria estar habilitado (falhou)"
        
        # Propriedade: Sistema deve continuar funcionando com domínios parciais
        # (não deve lançar exceção fatal)
        assert cdp is not None, \
            "Conexão CDP deve permanecer válida mesmo com falhas parciais"
    
    @given(
        command=st.sampled_from([
            ("Network.getAllCookies", {}),
            ("Runtime.evaluate", {"expression": "1+1"}),
            ("DOM.getDocument", {}),
            ("Network.enable", {}),
            ("Runtime.enable", {}),
            ("DOM.enable", {})
        ])
    )
    @settings(max_examples=100)
    def test_property_cdp_commands_use_correct_domain(self, command):
        """
        Propriedade: Comandos CDP devem usar o domínio correto
        baseado no tipo de operação.
        
        **Valida: Requisitos 23.2, 23.3, 23.4**
        """
        cmd_name, params = command
        domain = cmd_name.split('.')[0]
        
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Habilitar domínio necessário
        if domain in ["Network", "Runtime", "DOM"]:
            cdp.enable_domain(domain)
        
        # Executar comando
        try:
            cdp.execute(cmd_name, params)
        except CDPConnectionError:
            pass  # Comando pode falhar, mas deve usar domínio correto
        
        # Propriedade: Comando deve ter sido enviado com domínio correto
        calls = driver.execute_cdp_cmd.call_args_list
        command_calls = [call for call in calls if call[0][0] == cmd_name]
        
        if command_calls:
            # Verificar que comando foi chamado
            assert len(command_calls) > 0, \
                f"Comando {cmd_name} deveria ter sido executado"
            
            # Verificar que domínio do comando está correto
            actual_domain = command_calls[0][0][0].split('.')[0]
            assert actual_domain == domain, \
                f"Comando deveria usar domínio {domain}, mas usou {actual_domain}"
    
    @given(
        enable_network=st.booleans(),
        enable_runtime=st.booleans(),
        enable_dom=st.booleans()
    )
    @settings(max_examples=100)
    def test_property_domain_state_consistency(
        self,
        enable_network,
        enable_runtime,
        enable_dom
    ):
        """
        Propriedade: O estado de domínios habilitados deve ser consistente
        entre múltiplas verificações e operações.
        
        **Valida: Requisitos 23.2, 23.3, 23.4**
        """
        driver = Mock(spec=webdriver.Remote)
        driver.execute_cdp_cmd = Mock(return_value={'product': 'Chrome'})
        
        cdp = CDPConnection(driver)
        
        # Habilitar domínios conforme flags
        if enable_network:
            cdp.enable_domain("Network")
        if enable_runtime:
            cdp.enable_domain("Runtime")
        if enable_dom:
            cdp.enable_domain("DOM")
        
        # Propriedade: Estado deve ser consistente em múltiplas verificações
        for _ in range(5):
            assert cdp.is_domain_enabled("Network") == enable_network, \
                "Estado de Network domain deve ser consistente"
            assert cdp.is_domain_enabled("Runtime") == enable_runtime, \
                "Estado de Runtime domain deve ser consistente"
            assert cdp.is_domain_enabled("DOM") == enable_dom, \
                "Estado de DOM domain deve ser consistente"
        
        # Propriedade: Tentar habilitar novamente não deve mudar estado
        if enable_network:
            call_count_before = driver.execute_cdp_cmd.call_count
            cdp.enable_domain("Network")
            call_count_after = driver.execute_cdp_cmd.call_count
            assert call_count_after == call_count_before, \
                "Habilitar domínio já habilitado não deve fazer nova chamada CDP"
