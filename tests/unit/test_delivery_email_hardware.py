"""
Testes unitários para a funcionalidade de atualização de email de entrega com hardware.

Valida a função update_delivery_email_hardware() e suas integrações com as funções auxiliares.
"""

import os
import sys
from unittest.mock import MagicMock, Mock, patch

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

import pytest


class TestUpdateDeliveryEmailHardware:
    """Testes para a função principal update_delivery_email_hardware()."""

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    @patch("src.extractors.web_extractor._update_field_with_hardware_input")
    @patch("src.extractors.web_extractor._find_save_button_coordinates")
    @patch("src.extractors.web_extractor._click_with_physical_mouse")
    @patch("src.extractors.web_extractor.time.sleep")
    def test_successful_email_update(
        self, mock_sleep, mock_click, mock_find_save, mock_update_field, mock_find_field
    ):
        """Testa atualização bem-sucedida de email."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        # Setup mocks
        mock_driver = Mock()
        mock_find_field.return_value = {"x": 100, "y": 200}
        mock_update_field.return_value = True
        mock_driver.execute_script.return_value = "new@example.com"
        mock_find_save.return_value = {"x": 300, "y": 400}
        mock_click.return_value = True

        # Execute
        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        # Verify
        assert result is True
        mock_find_field.assert_called_once_with(mock_driver)
        mock_update_field.assert_called_once_with(100, 200, "new@example.com")
        mock_find_save.assert_called_once_with(mock_driver)
        mock_click.assert_called_once_with(mock_driver, 300, 400)

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    def test_field_not_found(self, mock_find_field):
        """Testa falha quando campo de email não é encontrado."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        mock_driver = Mock()
        mock_find_field.return_value = None

        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        assert result is False

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    @patch("src.extractors.web_extractor._update_field_with_hardware_input")
    def test_hardware_update_fails(self, mock_update_field, mock_find_field):
        """Testa falha quando atualização de hardware falha."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        mock_driver = Mock()
        mock_find_field.return_value = {"x": 100, "y": 200}
        mock_update_field.return_value = False

        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        assert result is False

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    @patch("src.extractors.web_extractor._update_field_with_hardware_input")
    @patch("src.extractors.web_extractor.time.sleep")
    def test_verification_fails(self, mock_sleep, mock_update_field, mock_find_field):
        """Testa falha quando verificação do campo não corresponde."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        mock_driver = Mock()
        mock_find_field.return_value = {"x": 100, "y": 200}
        mock_update_field.return_value = True
        mock_driver.execute_script.return_value = "wrong@example.com"

        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        assert result is False

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    @patch("src.extractors.web_extractor._update_field_with_hardware_input")
    @patch("src.extractors.web_extractor._find_save_button_coordinates")
    @patch("src.extractors.web_extractor.time.sleep")
    def test_save_button_not_found(
        self, mock_sleep, mock_find_save, mock_update_field, mock_find_field
    ):
        """Testa falha quando botão de salvar não é encontrado."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        mock_driver = Mock()
        mock_find_field.return_value = {"x": 100, "y": 200}
        mock_update_field.return_value = True
        mock_driver.execute_script.return_value = "new@example.com"
        mock_find_save.return_value = None

        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        assert result is False

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    @patch("src.extractors.web_extractor._update_field_with_hardware_input")
    @patch("src.extractors.web_extractor._find_save_button_coordinates")
    @patch("src.extractors.web_extractor._click_with_physical_mouse")
    @patch("src.extractors.web_extractor.time.sleep")
    def test_click_save_button_fails(
        self, mock_sleep, mock_click, mock_find_save, mock_update_field, mock_find_field
    ):
        """Testa falha quando clique no botão de salvar falha."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        mock_driver = Mock()
        mock_find_field.return_value = {"x": 100, "y": 200}
        mock_update_field.return_value = True
        mock_driver.execute_script.return_value = "new@example.com"
        mock_find_save.return_value = {"x": 300, "y": 400}
        mock_click.return_value = False

        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        assert result is False

    @patch("src.extractors.web_extractor._find_delivery_email_field_coordinates")
    def test_exception_handling(self, mock_find_field):
        """Testa tratamento de exceções."""
        from src.extractors.web_extractor import update_delivery_email_hardware

        mock_driver = Mock()
        mock_find_field.side_effect = Exception("Erro inesperado")

        result = update_delivery_email_hardware(mock_driver, "new@example.com")

        assert result is False


class TestFieldUpdateRetryLogic:
    """Testes para a lógica de retry na função _update_field_with_hardware_input()."""

    @patch("src.extractors.web_extractor.time.sleep")
    def test_retry_on_first_failure_then_success(self, mock_sleep):
        """Testa que a função tenta novamente após falha inicial e tem sucesso na segunda tentativa."""
        from src.extractors.web_extractor import _update_field_with_hardware_input

        # Mock pyautogui dentro do contexto de importação
        with patch.dict("sys.modules", {"pyautogui": MagicMock()}):
            import sys

            mock_pyautogui = sys.modules["pyautogui"]

            # Simular falha na primeira tentativa, sucesso na segunda
            mock_pyautogui.moveTo.side_effect = [Exception("Falha temporária"), None]

            result = _update_field_with_hardware_input(100, 200, "test@example.com")

            # Deve ter sucesso na segunda tentativa
            assert result is True
            # Deve ter tentado duas vezes
            assert mock_pyautogui.moveTo.call_count == 2

    @patch("src.extractors.web_extractor.time.sleep")
    def test_retry_fails_after_two_attempts(self, mock_sleep):
        """Testa que a função falha após duas tentativas sem sucesso."""
        from src.extractors.web_extractor import _update_field_with_hardware_input

        # Mock pyautogui dentro do contexto de importação
        with patch.dict("sys.modules", {"pyautogui": MagicMock()}):
            import sys

            mock_pyautogui = sys.modules["pyautogui"]

            # Simular falha em ambas as tentativas
            mock_pyautogui.moveTo.side_effect = Exception("Falha persistente")

            result = _update_field_with_hardware_input(100, 200, "test@example.com")

            # Deve falhar após duas tentativas
            assert result is False
            # Deve ter tentado exatamente duas vezes
            assert mock_pyautogui.moveTo.call_count == 2

    @patch("src.extractors.web_extractor.time.sleep")
    def test_success_on_first_attempt_no_retry(self, mock_sleep):
        """Testa que não há retry quando a primeira tentativa é bem-sucedida."""
        from src.extractors.web_extractor import _update_field_with_hardware_input

        # Mock pyautogui dentro do contexto de importação
        with patch.dict("sys.modules", {"pyautogui": MagicMock()}):
            import sys

            mock_pyautogui = sys.modules["pyautogui"]

            # Configurar mocks para sucesso
            mock_pyautogui.moveTo.return_value = None
            mock_pyautogui.click.return_value = None
            mock_pyautogui.hotkey.return_value = None
            mock_pyautogui.press.return_value = None
            mock_pyautogui.typewrite.return_value = None

            result = _update_field_with_hardware_input(100, 200, "test@example.com")

            # Deve ter sucesso
            assert result is True
            # Deve ter tentado apenas uma vez
            assert mock_pyautogui.moveTo.call_count == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
