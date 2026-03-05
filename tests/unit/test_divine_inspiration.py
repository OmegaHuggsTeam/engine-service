"""
Testes unitários para o sistema Divine Inspiration.

Este módulo testa os componentes base do sistema de auto-evolução.
"""

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from src.divine_inspiration.error_detection import ErrorContext, ErrorDetector
from src.divine_inspiration.alchemists_filter import AlchemistsFilter
from src.divine_inspiration.code_validator import CodeValidator
from src.divine_inspiration.hot_patcher import HotPatcher
from src.divine_inspiration.skill_executor import SkillExecutor


class TestErrorDetection:
    """Testes para ErrorDetector e ErrorContext."""
    
    def test_error_context_creation(self):
        """Testa criação de ErrorContext."""
        ctx = ErrorContext(
            error_type="NoSuchElementException",
            selector=".button",
            by_type="CSS_SELECTOR",
            html_context="<html></html>",
            attempt_count=1,
            timestamp=1234567890.0,
            maneuver_history=["strike"]
        )
        
        assert ctx.error_type == "NoSuchElementException"
        assert ctx.selector == ".button"
        assert ctx.attempt_count == 1
        assert "strike" in ctx.maneuver_history
    
    def test_error_context_to_description(self):
        """Testa conversão de ErrorContext para descrição."""
        ctx = ErrorContext(
            error_type="TimeoutException",
            selector="#submit",
            by_type="CSS_SELECTOR",
            html_context="",
            attempt_count=3,
            timestamp=1234567890.0
        )
        
        description = ctx.to_description()
        assert "TimeoutException" in description
        assert "#submit" in description
        assert "3 attempts" in description
    
    def test_is_structural_error(self):
        """Testa classificação de erros estruturais."""
        detector = ErrorDetector()
        
        # Erros estruturais
        assert detector.is_structural_error(NoSuchElementException())
        assert detector.is_structural_error(TimeoutException())
        
        # Erro não estrutural
        assert not detector.is_structural_error(ValueError())
    
    def test_track_error(self):
        """Testa rastreamento de erros."""
        detector = ErrorDetector()
        
        # Primeira tentativa
        ctx1 = detector.track_error(
            NoSuchElementException(),
            ".button",
            "CSS_SELECTOR",
            "strike"
        )
        assert ctx1.attempt_count == 1
        
        # Segunda tentativa
        ctx2 = detector.track_error(
            NoSuchElementException(),
            ".button",
            "CSS_SELECTOR",
            "strike"
        )
        assert ctx2.attempt_count == 2
        assert ctx1 is ctx2  # Mesmo contexto
    
    def test_should_invoke_divine_inspiration(self):
        """Testa threshold para invocar Divine Inspiration."""
        detector = ErrorDetector()
        
        ctx = ErrorContext(
            error_type="NoSuchElementException",
            selector=".button",
            by_type="CSS_SELECTOR",
            html_context="",
            attempt_count=2,
            timestamp=1234567890.0
        )
        
        assert not detector.should_invoke_divine_inspiration(ctx)
        
        ctx.attempt_count = 3
        assert detector.should_invoke_divine_inspiration(ctx)


class TestAlchemistsFilter:
    """Testes para AlchemistsFilter."""
    
    def test_validate_syntax_valid_code(self):
        """Testa validação de código válido."""
        code = """
def skill_test(selum: SelumOfPersistence) -> bool:
    return True
"""
        is_valid, error = AlchemistsFilter.validate_syntax(code)
        assert is_valid
        assert error is None
    
    def test_validate_syntax_invalid_code(self):
        """Testa validação de código inválido."""
        code = """
def skill_test(selum: SelumOfPersistence) -> bool:
    return True
    invalid syntax here
"""
        is_valid, error = AlchemistsFilter.validate_syntax(code)
        assert not is_valid
        assert "SyntaxError" in error
    
    def test_build_recovery_prompt(self):
        """Testa construção de prompt de recuperação."""
        ctx = ErrorContext(
            error_type="NoSuchElementException",
            selector=".button",
            by_type="CSS_SELECTOR",
            html_context="<html></html>",
            attempt_count=3,
            timestamp=1234567890.0
        )
        
        prompt = AlchemistsFilter.build_recovery_prompt(
            ctx,
            "def skill_test(): pass",
            "SyntaxError: invalid syntax",
            "syntax",
            1
        )
        
        assert "NoSuchElementException" in prompt
        assert ".button" in prompt
        assert "SyntaxError" in prompt
        assert "Recovery Attempt 1/2" in prompt


class TestCodeValidator:
    """Testes para CodeValidator."""
    
    def test_validate_safe_code(self):
        """Testa validação de código seguro."""
        code = """
def skill_test(selum: SelumOfPersistence) -> bool:
    try:
        selum.strike(".button")
        return True
    except:
        return False
"""
        is_valid, error = CodeValidator.validate(code, "skill_test")
        assert is_valid
        assert error == ""
    
    def test_validate_dangerous_import(self):
        """Testa rejeição de imports perigosos."""
        code = """
import os
def skill_test(selum: SelumOfPersistence) -> bool:
    return True
"""
        is_valid, error = CodeValidator.validate(code, "skill_test")
        assert not is_valid
        assert "Dangerous import" in error
        assert "os" in error
    
    def test_validate_invalid_signature(self):
        """Testa rejeição de assinatura inválida."""
        code = """
def skill_test(driver) -> bool:
    return True
"""
        is_valid, error = CodeValidator.validate(code, "skill_test")
        assert not is_valid
        assert "Invalid function signature" in error
    
    def test_validate_missing_return(self):
        """Testa rejeição de função sem return."""
        code = """
def skill_test(selum: SelumOfPersistence) -> bool:
    selum.strike(".button")
"""
        is_valid, error = CodeValidator.validate(code, "skill_test")
        assert not is_valid
        assert "must return True or False" in error


class TestHotPatcher:
    """Testes para HotPatcher."""
    
    def test_patch_skill_valid(self):
        """Testa compilação de skill válida."""
        code = """
def skill_test(selum) -> bool:
    return True
"""
        registry = {}
        result = HotPatcher.patch_skill("skill_test", code, registry)
        
        assert result
        assert "skill_test" in registry
        assert callable(registry["skill_test"])
    
    def test_patch_skill_invalid(self):
        """Testa compilação de skill inválida."""
        code = """
def skill_test(selum) -> bool:
    invalid syntax
"""
        registry = {}
        result = HotPatcher.patch_skill("skill_test", code, registry)
        
        assert not result
        assert "skill_test" not in registry


class TestSkillExecutor:
    """Testes para SkillExecutor."""
    
    def test_execute_success(self):
        """Testa execução bem-sucedida."""
        def skill_test(selum) -> bool:
            return True
        
        registry = {"skill_test": skill_test}
        success, error = SkillExecutor.execute("skill_test", registry, None, False)
        
        assert success
        assert error is None
    
    def test_execute_failure(self):
        """Testa execução com falha."""
        def skill_test(selum) -> bool:
            raise ValueError("Test error")
        
        registry = {"skill_test": skill_test}
        success, error = SkillExecutor.execute("skill_test", registry, None, False)
        
        assert not success
        assert "ValueError" in error
    
    def test_execute_not_found(self):
        """Testa execução de skill inexistente."""
        registry = {}
        success, error = SkillExecutor.execute("skill_test", registry, None, False)
        
        assert not success
        assert "not found" in error
    
    def test_execute_invalid_return_type(self):
        """Testa execução com tipo de retorno inválido."""
        def skill_test(selum):
            return "not a bool"
        
        registry = {"skill_test": skill_test}
        success, error = SkillExecutor.execute("skill_test", registry, None, True)
        
        assert not success
        assert "instead of bool" in error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
