"""
Testes unitários para Abstraction Vow Validator.
"""

import unittest
from src.rag.abstraction_vow_validator import AbstractionVowValidator
from src.rag.rag_query_system import RAGQuerySystem


class TestAbstractionVowValidator(unittest.TestCase):
    """Testes para AbstractionVowValidator."""
    
    def setUp(self):
        """Configurar validator para testes."""
        self.validator = AbstractionVowValidator()
    
    def test_valid_code_with_abstractions(self):
        """Testa que código usando apenas abstrações é aprovado."""
        code = """
def skill_test(selum):
    selum.strike(".button")
    element = selum.scout([{"css": ".item"}])
    selum.vigilance(".loading", timeout=10)
    return True
"""
        result = self.validator.validate(code)
        
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.violations), 0)
    
    def test_detect_driver_find_element(self):
        """Testa detecção de driver.find_element."""
        code = """
def bad_skill(selum):
    element = driver.find_element(By.CSS_SELECTOR, ".button")
    return True
"""
        result = self.validator.validate(code)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.violations), 0)
        self.assertEqual(result.violations[0].forbidden_pattern, "driver.find_element")
    
    def test_detect_driver_execute_script(self):
        """Testa detecção de driver.execute_script."""
        code = """
def bad_skill(selum):
    driver.execute_script("arguments[0].click();", element)
    return True
"""
        result = self.validator.validate(code)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.violations), 0)
        self.assertEqual(result.violations[0].forbidden_pattern, "driver.execute_script")
    
    def test_detect_webdriverwait(self):
        """Testa detecção de WebDriverWait direto."""
        code = """
from selenium.webdriver.support.ui import WebDriverWait

def bad_skill(selum):
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "test")))
    return True
"""
        result = self.validator.validate(code)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.violations), 0)
        self.assertEqual(result.violations[0].forbidden_pattern, "WebDriverWait(")
    
    def test_detect_actionchains(self):
        """Testa detecção de ActionChains direto."""
        code = """
from selenium.webdriver.common.action_chains import ActionChains

def bad_skill(selum):
    ActionChains(driver).move_to_element(element).click().perform()
    return True
"""
        result = self.validator.validate(code)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.violations), 0)
        self.assertEqual(result.violations[0].forbidden_pattern, "ActionChains(")
    
    def test_allow_self_driver_in_selum_class(self):
        """Testa que self.driver é permitido dentro de SelumOfPersistence."""
        code = """
class SelumOfPersistence:
    def strike(self, selector):
        element = self.driver.find_element(By.CSS_SELECTOR, selector)
        element.click()
        return True
"""
        result = self.validator.validate(code)
        
        # Deve ser válido pois está dentro da classe SelumOfPersistence
        self.assertTrue(result.is_valid)
        self.assertEqual(len(result.violations), 0)
    
    def test_reject_driver_outside_selum_class(self):
        """Testa que driver é rejeitado fora de SelumOfPersistence."""
        code = """
class OtherClass:
    def method(self):
        element = self.driver.find_element(By.CSS_SELECTOR, ".button")
        return True
"""
        result = self.validator.validate(code)
        
        # Deve ser inválido pois não está em SelumOfPersistence
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.violations), 0)
    
    def test_syntax_error_rejected(self):
        """Testa que código com erro de sintaxe é rejeitado (fail-safe)."""
        code = """
def bad_syntax(selum)
    selum.strike(".button"  # Faltando parêntese
    return True
"""
        result = self.validator.validate(code)
        
        self.assertFalse(result.is_valid)
        self.assertGreater(len(result.violations), 0)
        self.assertEqual(result.violations[0].forbidden_pattern, "SyntaxError")
    
    def test_suggest_fix_for_find_element(self):
        """Testa sugestão de correção para find_element."""
        code = """
def bad_skill(selum):
    element = driver.find_element(By.CSS_SELECTOR, ".button")
    return True
"""
        result = self.validator.validate(code)
        
        self.assertGreater(len(result.suggestions), 0)
        self.assertIn("scout", result.suggestions[0].lower())
    
    def test_suggest_fix_for_webdriverwait(self):
        """Testa sugestão de correção para WebDriverWait."""
        code = """
def bad_skill(selum):
    element = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "test")))
    return True
"""
        result = self.validator.validate(code)
        
        self.assertGreater(len(result.suggestions), 0)
        self.assertIn("vigilance", result.suggestions[0].lower())
    
    def test_suggest_fix_for_actionchains(self):
        """Testa sugestão de correção para ActionChains."""
        code = """
def bad_skill(selum):
    ActionChains(driver).move_to_element(element).click().perform()
    return True
"""
        result = self.validator.validate(code)
        
        self.assertGreater(len(result.suggestions), 0)
        self.assertIn("strike", result.suggestions[0].lower())
    
    def test_multiple_violations(self):
        """Testa detecção de múltiplas violações."""
        code = """
def bad_skill(selum):
    element = driver.find_element(By.CSS_SELECTOR, ".button")
    driver.execute_script("arguments[0].click();", element)
    WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "test")))
    return True
"""
        result = self.validator.validate(code)
        
        self.assertFalse(result.is_valid)
        # Deve detectar 3 violações
        self.assertEqual(len(result.violations), 3)
    
    def test_extract_line_number(self):
        """Testa que número de linha é extraído corretamente."""
        code = """
def bad_skill(selum):
    element = driver.find_element(By.CSS_SELECTOR, ".button")
    return True
"""
        result = self.validator.validate(code)
        
        self.assertGreater(len(result.violations), 0)
        # Violação deve estar na linha 3
        self.assertEqual(result.violations[0].line_number, 3)


class TestAbstractionVowValidatorWithRAG(unittest.TestCase):
    """Testes de integração com RAG."""
    
    def setUp(self):
        """Configurar validator e RAG."""
        self.validator = AbstractionVowValidator()
        self.rag = RAGQuerySystem(grimoire_path="docs/paladin_grimoire/")
    
    def test_suggest_abstraction_for_find_element(self):
        """Testa sugestão de abstração via RAG para find_element."""
        violation = "driver.find_element(By.CSS_SELECTOR, '.button')"
        
        suggestion = self.validator.suggest_abstraction(violation, self.rag)
        
        # Deve sugerir scout ou strike
        self.assertIsNotNone(suggestion)
        self.assertTrue(
            'scout' in suggestion.lower() or 'strike' in suggestion.lower()
        )
    
    def test_suggest_abstraction_for_webdriverwait(self):
        """Testa sugestão de abstração via RAG para WebDriverWait."""
        violation = "WebDriverWait(driver, 10).until(...)"
        
        suggestion = self.validator.suggest_abstraction(violation, self.rag)
        
        # Deve sugerir vigilance
        self.assertIsNotNone(suggestion)


if __name__ == '__main__':
    unittest.main()
