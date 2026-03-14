"""
Code Validator - Valida código gerado para segurança.

Este módulo implementa validação de segurança para código gerado dinamicamente,
verificando imports perigosos e assinatura correta da função.
"""

import re
from typing import Set, Tuple


class CodeValidator:
    """Valida código gerado para segurança."""

    DANGEROUS_IMPORTS: Set[str] = {
        "os",
        "sys",
        "subprocess",
        "eval",
        "exec",
        "__import__",
        "compile",
        "open",
        "file",
        "input",
        "raw_input",
        "execfile",
        "reload",
    }

    ALLOWED_IMPORTS: Set[str] = {"time", "typing", "selenium", "dataclasses", "datetime"}

    @staticmethod
    def validate(code: str, expected_function_name: str) -> Tuple[bool, str]:
        """
        Valida código gerado para segurança.

        NOTA: Validação de sintaxe é feita pelo AlchemistsFilter.

        Args:
            code: Código Python a validar
            expected_function_name: Nome esperado da função

        Returns:
            (is_valid, error_message)
        """
        # 1. Verificar imports perigosos
        for dangerous in CodeValidator.DANGEROUS_IMPORTS:
            # Verificar import direto
            if re.search(rf"\bimport\s+{dangerous}\b", code):
                return False, f"Dangerous import detected: {dangerous}"
            # Verificar from ... import
            if re.search(rf"\bfrom\s+{dangerous}\b", code):
                return False, f"Dangerous import detected: {dangerous}"
            # Verificar uso direto de funções perigosas
            if dangerous in ["eval", "exec", "compile", "__import__"]:
                if re.search(rf"\b{dangerous}\s*\(", code):
                    return False, f"Dangerous function call detected: {dangerous}()"

        # 2. Verificar assinatura da função
        pattern = rf"def\s+{re.escape(expected_function_name)}\s*\(\s*selum\s*:\s*SelumOfPersistence\s*\)\s*->\s*bool\s*:"
        if not re.search(pattern, code):
            return (
                False,
                f"Invalid function signature. Expected: def {expected_function_name}(selum: SelumOfPersistence) -> bool:",
            )

        # 3. Verificar que retorna bool
        if "return True" not in code and "return False" not in code:
            return False, "Function must return True or False"

        return True, ""

    @staticmethod
    def extract_imports(code: str) -> Set[str]:
        """
        Extrai todos os imports do código.

        Args:
            code: Código Python

        Returns:
            Set de módulos importados
        """
        imports = set()

        # Padrão: import module
        for match in re.finditer(r"\bimport\s+(\w+)", code):
            imports.add(match.group(1))

        # Padrão: from module import ...
        for match in re.finditer(r"\bfrom\s+(\w+)\s+import", code):
            imports.add(match.group(1))

        return imports

    @staticmethod
    def is_safe_import(module_name: str) -> bool:
        """
        Verifica se um import é seguro.

        Args:
            module_name: Nome do módulo

        Returns:
            True se seguro, False caso contrário
        """
        return (
            module_name in CodeValidator.ALLOWED_IMPORTS
            or module_name not in CodeValidator.DANGEROUS_IMPORTS
        )
