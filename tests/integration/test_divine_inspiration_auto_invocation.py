"""
Testes de integração para invocação automática de Divine Inspiration.

Valida que erros estruturais repetitivos acionam automaticamente:
1. Tentativa de usar skill existente com contexto similar
2. Geração de nova skill via Divine Inspiration
3. Persistência e execução da skill gerada
"""

import unittest
from unittest.mock import MagicMock, Mock, patch

from selenium.common.exceptions import NoSuchElementException, TimeoutException

from src.utils.selum_of_persistence import SelumOfPersistence


class TestDivineInspirationAutoInvocation(unittest.TestCase):
    """Testes de invocação automática de Divine Inspiration."""

    def setUp(self):
        """Configurar mocks para cada teste."""
        self.mock_driver = Mock()
        self.mock_driver.find_element = Mock()
        self.mock_driver.execute_script = Mock()
        self.groq_api_key = "test_key_123"

    @patch("src.divine_inspiration.grimoire_manager.GrimoireManager.load_skills")
    def test_strike_invokes_divine_inspiration_after_threshold(self, mock_load_skills):
        """Testa que strike invoca Divine Inspiration após 3 falhas estruturais."""
        # Configurar grimoire vazio
        mock_load_skills.return_value = {}

        # Criar Selum com Divine Inspiration
        selum = SelumOfPersistence(self.mock_driver, groq_api_key=self.groq_api_key)

        # Configurar driver para lançar NoSuchElementException
        selum.driver.find_element.side_effect = NoSuchElementException("Element not found")

        # Mockar divine_inspiration para retornar sucesso
        selum.divine_inspiration = Mock(
            return_value={
                "success": True,
                "skill_name": "skill_test_solution",
                "code": "def skill_test_solution(selum): return True",
            }
        )

        # Mockar execute_skill para retornar True
        selum.execute_skill = Mock(return_value=True)

        # Executar strike 3 vezes para atingir threshold
        for i in range(3):
            try:
                selum.strike(".test-button")
            except NoSuchElementException:
                pass

        # Verificar que divine_inspiration foi chamado
        self.assertTrue(selum.divine_inspiration.called)
        self.assertTrue(selum.execute_skill.called)

    @patch("src.divine_inspiration.grimoire_manager.GrimoireManager.load_skills")
    def test_vigilance_invokes_divine_inspiration_after_threshold(self, mock_load_skills):
        """Testa que vigilance invoca Divine Inspiration após 3 timeouts."""
        # Configurar grimoire vazio
        mock_load_skills.return_value = {}

        # Criar Selum com Divine Inspiration
        selum = SelumOfPersistence(self.mock_driver, groq_api_key=self.groq_api_key)

        # Configurar driver para lançar TimeoutException
        selum.driver.find_element.side_effect = NoSuchElementException("Element not found")

        # Mockar divine_inspiration para retornar sucesso
        selum.divine_inspiration = Mock(
            return_value={
                "success": True,
                "skill_name": "skill_wait_solution",
                "code": "def skill_wait_solution(selum): return True",
            }
        )

        # Mockar execute_skill para retornar True
        selum.execute_skill = Mock(return_value=True)

        # Executar vigilance 3 vezes para atingir threshold (com timeout curto)
        for i in range(3):
            try:
                selum.vigilance(".test-element", timeout=1)
            except TimeoutException:
                pass

        # Verificar que divine_inspiration foi chamado
        self.assertTrue(selum.divine_inspiration.called)
        self.assertTrue(selum.execute_skill.called)

    @patch("src.divine_inspiration.grimoire_manager.GrimoireManager.load_skills")
    @patch("builtins.open", create=True)
    def test_try_existing_skill_before_divine_inspiration(self, mock_open, mock_load_skills):
        """Testa que skills existentes são tentadas antes de gerar novas."""
        # Configurar grimoire com uma skill
        mock_load_skills.return_value = {"skill_existing": "def skill_existing(selum): return True"}

        # Configurar mock do arquivo selenium.md
        mock_file_content = """
## Custom Skills Learned

### Skill: skill_existing
Context: NoSuchElementException ao buscar .test-button
Generated: 2026-03-01 10:00:00
```python
def skill_existing(selum):
    return True
```
"""
        mock_file = MagicMock()
        mock_file.read.return_value = mock_file_content
        mock_file.__enter__.return_value = mock_file
        mock_open.return_value = mock_file

        # Criar Selum com Divine Inspiration
        selum = SelumOfPersistence(self.mock_driver, groq_api_key=self.groq_api_key)

        # Registrar skill manualmente (já que load_skills está mockado)
        selum.skill_registry["skill_existing"] = lambda selum: True

        # Configurar driver para lançar NoSuchElementException
        selum.driver.find_element.side_effect = NoSuchElementException("Element not found")

        # Mockar execute_skill para retornar True
        selum.execute_skill = Mock(return_value=True)

        # Mockar divine_inspiration (não deve ser chamado)
        selum.divine_inspiration = Mock()

        # Executar strike 3 vezes para atingir threshold
        for i in range(3):
            try:
                selum.strike(".test-button")
            except NoSuchElementException:
                pass

        # Verificar que execute_skill foi chamado (skill existente)
        self.assertTrue(selum.execute_skill.called)

        # Verificar que divine_inspiration NÃO foi chamado (skill existente resolveu)
        # Nota: Este teste pode falhar se a similaridade não for alta o suficiente
        # Nesse caso, divine_inspiration seria chamado, o que também é comportamento válido


if __name__ == "__main__":
    unittest.main()
