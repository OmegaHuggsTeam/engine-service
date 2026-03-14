"""
Abstraction Vow Validator - Valida código e detecta violações do Voto de Abstração.

Este módulo usa AST parsing para detectar código Selenium bruto (driver.find_element,
driver.execute_script, etc.) e garantir que apenas abstrações do SelumOfPersistence
sejam usadas.
"""

import ast
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class Violation:
    """Violação detectada no código."""

    line_number: int
    code_snippet: str
    forbidden_pattern: str
    suggested_fix: str


@dataclass
class ValidationResult:
    """Resultado de validação do Voto de Abstração."""

    is_valid: bool
    violations: List[Violation]
    suggestions: List[str]


class AbstractionVowValidator:
    """Validador que detecta código Selenium bruto usando AST parsing."""

    # Padrões proibidos
    FORBIDDEN_PATTERNS = [
        "driver.find_element",
        "driver.find_elements",
        "driver.execute_script",
        "WebDriverWait(",
        "ActionChains(",
    ]

    # Abstrações permitidas
    ALLOWED_ABSTRACTIONS = [
        "strike",
        "scout",
        "vigilance",
        "steady_gaze",
        "cleansing_aura",
        "invoke_wisdom",
        "divine_inspiration",
        "execute_skill",
        "combo_login",
        "combo_navigate_to_settings",
    ]

    def __init__(self):
        """Inicializa o validador."""
        pass

    def validate(self, code: str) -> ValidationResult:
        """
        Valida código usando AST parsing.

        Args:
            code: Código Python a validar

        Returns:
            ValidationResult com status e detalhes
        """
        violations = []
        suggestions = []

        # Tentar parsear código
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            # Código com erro de sintaxe é rejeitado (fail-safe)
            return ValidationResult(
                is_valid=False,
                violations=[
                    Violation(
                        line_number=e.lineno if e.lineno else 0,
                        code_snippet=e.text if e.text else "",
                        forbidden_pattern="SyntaxError",
                        suggested_fix="Corrigir erro de sintaxe antes de validar",
                    )
                ],
                suggestions=["Código contém erro de sintaxe e foi rejeitado por segurança"],
            )

        # Visitar nós da árvore AST
        visitor = VowViolationVisitor()
        visitor.visit(tree)

        # Processar violações encontradas
        for violation_info in visitor.violations:
            line_num, pattern, context = violation_info

            # Criar violação
            violation = Violation(
                line_number=line_num,
                code_snippet=self._extract_line(code, line_num),
                forbidden_pattern=pattern,
                suggested_fix=self._suggest_fix(pattern),
            )
            violations.append(violation)

            # Adicionar sugestão
            suggestion = self._suggest_fix(pattern)
            if suggestion not in suggestions:
                suggestions.append(suggestion)

        # Código é válido se não houver violações
        is_valid = len(violations) == 0

        return ValidationResult(is_valid=is_valid, violations=violations, suggestions=suggestions)

    def _extract_line(self, code: str, line_number: int) -> str:
        """
        Extrai linha específica do código.

        Args:
            code: Código completo
            line_number: Número da linha (1-indexed)

        Returns:
            Linha de código
        """
        lines = code.split("\n")
        if 0 < line_number <= len(lines):
            return lines[line_number - 1].strip()
        return ""

    def _suggest_fix(self, pattern: str) -> str:
        """
        Sugere abstração correta baseada no padrão violado.

        Args:
            pattern: Padrão proibido detectado

        Returns:
            Sugestão de correção
        """
        suggestions_map = {
            "driver.find_element": "Use selum.scout([{'css': 'selector'}]) para localizar elementos",
            "driver.find_elements": "Use selum.scout([{'css': 'selector'}]) para localizar elementos",
            "driver.execute_script": "Use selum.strike(selector, strategy='force') para JavaScript click",
            "WebDriverWait(": "Use selum.vigilance(selector, timeout=N) para aguardar elementos",
            "ActionChains(": "Use selum.strike(selector, strategy='force') para ações complexas",
        }

        return suggestions_map.get(pattern, "Use abstrações do SelumOfPersistence")

    def suggest_abstraction(self, violation: str, rag_system) -> Optional[str]:
        """
        Sugere abstração correta baseada em violação detectada.

        Consulta RAG para encontrar abstração mais relevante.

        Args:
            violation: Código que violou o voto
            rag_system: Sistema RAG para consulta

        Returns:
            Nome da abstração sugerida ou None
        """
        # Mapeamento direto de violações para abstrações
        direct_mapping = {
            "find_element": ["scout", "strike"],
            "find_elements": ["scout"],
            "execute_script": ["strike"],
            "WebDriverWait": ["vigilance", "steady_gaze"],
            "ActionChains": ["strike"],
        }

        # Encontrar abstração sugerida baseada no padrão
        suggested_abstractions = []
        for pattern, abstractions in direct_mapping.items():
            if pattern in violation:
                suggested_abstractions.extend(abstractions)

        # Se não encontrou mapeamento direto, usar RAG
        if not suggested_abstractions:
            # Extrair contexto da violação e criar query específica
            if "find_element" in violation:
                query = "scout localizar elemento seletor"
            elif "execute_script" in violation and "click" in violation:
                query = "strike clicar javascript force"
            elif "WebDriverWait" in violation:
                query = "vigilance aguardar elemento timeout"
            elif "ActionChains" in violation:
                query = "strike ações mouse hover"
            else:
                query = "abstração manobra selum"

            # Consultar RAG
            results = rag_system.query(query, top_k=5)

            # Procurar por abstrações válidas nos resultados
            valid_abstractions = [
                "strike",
                "scout",
                "vigilance",
                "steady_gaze",
                "cleansing_aura",
                "invoke_wisdom",
                "divine_inspiration",
                "execute_skill",
                "combo_login",
                "combo_navigate_to_settings",
            ]

            for result in results:
                # Extrair nome da abstração do título da seção (ex: "## strike" -> "strike")
                section_title = result.section.replace("#", "").strip().lower()

                # Verificar se é uma abstração válida
                for abstraction in valid_abstractions:
                    if abstraction in section_title:
                        suggested_abstractions.append(abstraction)
                        break

        # Retornar primeira sugestão
        return suggested_abstractions[0] if suggested_abstractions else None


class VowViolationVisitor(ast.NodeVisitor):
    """Visitor que detecta violações do Voto de Abstração na AST."""

    def __init__(self):
        """Inicializa o visitor."""
        self.violations = []  # Lista de (line_number, pattern, context)
        self.in_selum_class = False
        self.current_class = None

    def visit_ClassDef(self, node):
        """Visita definição de classe."""
        # Marcar se estamos dentro de SelumOfPersistence
        old_class = self.current_class
        old_in_selum = self.in_selum_class

        self.current_class = node.name
        # Apenas marcar como True se for SelumOfPersistence, caso contrário False
        self.in_selum_class = node.name == "SelumOfPersistence"

        # Visitar filhos
        self.generic_visit(node)

        # Restaurar estado
        self.current_class = old_class
        self.in_selum_class = old_in_selum

    def visit_Attribute(self, node):
        """Visita acesso a atributo (ex: driver.find_element)."""
        # Construir nome completo do atributo
        attr_name = self._get_full_attribute_name(node)

        # Verificar se é violação
        if self._is_violation(attr_name):
            self.violations.append((node.lineno, self._extract_pattern(attr_name), attr_name))

        # Continuar visitando
        self.generic_visit(node)

    def visit_Call(self, node):
        """Visita chamada de função."""
        # Verificar se é chamada de WebDriverWait ou ActionChains
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in ["WebDriverWait", "ActionChains"]:
                self.violations.append((node.lineno, f"{func_name}(", func_name))

        # Continuar visitando
        self.generic_visit(node)

    def _get_full_attribute_name(self, node):
        """
        Constrói nome completo de um atributo (ex: driver.find_element).

        Args:
            node: Nó AST do tipo Attribute

        Returns:
            Nome completo do atributo
        """
        parts = []
        current = node

        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value

        if isinstance(current, ast.Name):
            parts.append(current.id)

        return ".".join(reversed(parts))

    def _is_violation(self, attr_name: str) -> bool:
        """
        Verifica se atributo é uma violação.

        Args:
            attr_name: Nome completo do atributo

        Returns:
            True se é violação, False caso contrário
        """
        # Padrões proibidos
        forbidden_patterns = [
            "driver.find_element",
            "driver.find_elements",
            "driver.execute_script",
            "driver.get",
            "driver.refresh",
        ]

        # Verificar se contém algum padrão proibido
        for pattern in forbidden_patterns:
            if pattern in attr_name:
                # Se estamos dentro de SelumOfPersistence e é self.driver, permitir
                # (pois é implementação interna da classe)
                if self.in_selum_class and attr_name.startswith("self.driver"):
                    return False
                # Caso contrário, é violação
                return True

        return False

    def _extract_pattern(self, attr_name: str) -> str:
        """
        Extrai padrão proibido do nome do atributo.

        Args:
            attr_name: Nome completo do atributo

        Returns:
            Padrão proibido
        """
        if "find_element" in attr_name:
            return "driver.find_element"
        elif "execute_script" in attr_name:
            return "driver.execute_script"
        elif "get" in attr_name:
            return "driver.get"
        elif "refresh" in attr_name:
            return "driver.refresh"

        return attr_name
