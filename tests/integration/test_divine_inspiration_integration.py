"""
Teste de integração para Divine Inspiration com SelumOfPersistence.

Este teste valida a integração completa do sistema de auto-evolução.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from src.utils.selum_of_persistence import SelumOfPersistence


class TestDivineInspirationIntegration:
    """Testes de integração para Divine Inspiration."""
    
    def test_selum_initialization_without_groq_key(self):
        """Testa inicialização do Selum sem chave Groq."""
        mock_driver = Mock()
        selum = SelumOfPersistence(mock_driver)
        
        assert selum.driver == mock_driver
        assert selum.turn_counter == 0
        assert selum.skill_registry == {}
        # Divine Inspiration não deve estar inicializado
        assert selum.divine_engine is None
        assert selum.error_detector is None
    
    def test_selum_initialization_with_groq_key(self):
        """Testa inicialização do Selum com chave Groq."""
        mock_driver = Mock()
        
        with patch('src.divine_inspiration.DivineInspirationEngine'):
            with patch('src.divine_inspiration.ErrorDetector'):
                with patch.object(SelumOfPersistence, '_load_custom_skills'):
                    selum = SelumOfPersistence(mock_driver, groq_api_key="test_key")
                    
                    assert selum.driver == mock_driver
                    assert selum.skill_registry == {}
                    # Divine Inspiration deve estar inicializado
                    assert selum.divine_engine is not None
                    assert selum.error_detector is not None
    
    def test_load_custom_skills_without_divine_inspiration(self):
        """Testa carregamento de skills sem Divine Inspiration."""
        mock_driver = Mock()
        selum = SelumOfPersistence(mock_driver)
        
        # Não deve lançar exceção
        selum._load_custom_skills()
        assert selum.skill_registry == {}
    
    def test_execute_skill_not_found(self):
        """Testa execução de skill inexistente."""
        mock_driver = Mock()
        selum = SelumOfPersistence(mock_driver)
        
        result = selum.execute_skill("skill_nonexistent")
        assert result is False
    
    def test_execute_skill_success(self):
        """Testa execução bem-sucedida de skill."""
        mock_driver = Mock()
        selum = SelumOfPersistence(mock_driver)
        
        # Adicionar skill mockada ao registry
        def mock_skill(selum_instance):
            return True
        
        selum.skill_registry["skill_test"] = mock_skill
        
        with patch('src.divine_inspiration.SkillExecutor.execute', return_value=(True, None)):
            result = selum.execute_skill("skill_test")
            assert result is True
    
    def test_divine_inspiration_without_initialization(self):
        """Testa divine_inspiration sem inicialização."""
        mock_driver = Mock()
        selum = SelumOfPersistence(mock_driver)
        
        result = selum.divine_inspiration("NoSuchElementException on .button after 3 attempts")
        
        assert result['success'] is False
        assert 'not initialized' in result['error_message']
    
    @patch('src.divine_inspiration.DivineInspirationEngine')
    @patch('src.divine_inspiration.ErrorDetector')
    @patch('src.divine_inspiration.GrimoireManager')
    def test_divine_inspiration_success_flow(
        self,
        mock_grimoire,
        mock_error_detector,
        mock_engine
    ):
        """Testa fluxo completo de divine_inspiration com sucesso."""
        mock_driver = Mock()
        
        # Mock do engine para retornar skill válida
        mock_engine_instance = MagicMock()
        mock_engine.return_value = mock_engine_instance
        mock_engine_instance.generate_skill.return_value = {
            'success': True,
            'skill_name': 'skill_test',
            'skill_code': 'def skill_test(selum: SelumOfPersistence) -> bool:\n    return True',
            'attempt_number': 1
        }
        
        # Mock do error detector
        mock_error_detector_instance = MagicMock()
        mock_error_detector.return_value = mock_error_detector_instance
        mock_error_detector_instance._extract_html_context.return_value = "<html></html>"
        
        with patch.object(SelumOfPersistence, '_load_custom_skills'):
            with patch('src.divine_inspiration.AlchemistsFilter.validate_syntax', return_value=(True, None)):
                with patch('src.divine_inspiration.CodeValidator.validate', return_value=(True, "")):
                    with patch('src.divine_inspiration.HotPatcher.patch_skill', return_value=True):
                        with patch('src.divine_inspiration.SkillExecutor.execute', return_value=(True, None)):
                            selum = SelumOfPersistence(mock_driver, groq_api_key="test_key")
                            
                            result = selum.divine_inspiration("NoSuchElementException on .button after 3 attempts")
                            
                            assert result['success'] is True
                            assert result['skill_name'] == 'skill_test'
                            assert 'skill_code' in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
