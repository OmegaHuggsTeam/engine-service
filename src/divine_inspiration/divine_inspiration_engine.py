"""
Divine Inspiration Engine - Motor de auto-evolução com Recovery Maneuver.

Este módulo implementa o motor que gera skills customizadas usando Groq AI,
com suporte a recuperação iterativa quando código falha.
"""

import re
from typing import Any, Dict, Optional

from groq import Groq

from .alchemists_filter import AlchemistsFilter
from .error_detection import ErrorContext


class DivineInspirationEngine:
    """Motor de auto-evolução que gera skills customizadas com recuperação iterativa."""

    MAX_RECOVERY_ATTEMPTS = 2

    def __init__(self, groq_api_key: str):
        """
        Inicializa o motor Divine Inspiration.

        Args:
            groq_api_key: Chave da API Groq
        """
        self.groq_client = Groq(api_key=groq_api_key)
        self.model = "llama-3.3-70b-versatile"

    def generate_skill(
        self, context: ErrorContext, previous_attempt: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Gera uma skill customizada para resolver o problema.

        Args:
            context: Contexto do erro estrutural
            previous_attempt: Dict com 'code', 'error', 'error_type', 'attempt_number' da tentativa anterior

        Returns:
            {
                'skill_name': str,
                'skill_code': str,
                'success': bool,
                'error_message': str (opcional),
                'attempt_number': int
            }
        """
        # Determinar se é tentativa de recuperação
        if previous_attempt:
            prompt = AlchemistsFilter.build_recovery_prompt(
                context,
                previous_attempt["code"],
                previous_attempt["error"],
                previous_attempt["error_type"],
                previous_attempt.get("attempt_number", 1),
            )
        else:
            prompt = self._build_prompt(context)

        try:
            response = self.groq_client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert Python developer specializing in Selenium automation. Generate compact, safe Python functions that use only Selum commands.",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=1000,
            )

            raw_code = response.choices[0].message.content
            skill_code = self._extract_code(raw_code)
            skill_name = self._extract_function_name(skill_code)

            return {
                "skill_name": skill_name,
                "skill_code": skill_code,
                "success": True,
                "attempt_number": (
                    previous_attempt.get("attempt_number", 0) + 1 if previous_attempt else 1
                ),
            }

        except Exception as e:
            return {
                "skill_name": None,
                "skill_code": None,
                "success": False,
                "error_message": str(e),
                "attempt_number": (
                    previous_attempt.get("attempt_number", 0) + 1 if previous_attempt else 1
                ),
            }

    def _build_prompt(self, context: ErrorContext) -> str:
        """Constrói o prompt para Groq."""
        return f"""
I'm encountering a repetitive Selenium error and need a custom solution.

**Error Details:**
- Type: {context.error_type}
- Selector: {context.selector} (using {context.by_type})
- Attempts: {context.attempt_count}
- Recent maneuvers: {', '.join(context.maneuver_history[-5:])}

**HTML Context:**
```html
{context.html_context[:5000]}
```

**Available Selum Commands:**
- selum.strike(selector, by=By.CSS_SELECTOR, strategy='smart') - Click with fallback
- selum.scout(possibilities_list) - Find first matching element from multiple options
- selum.steady_gaze(selector, by=By.CSS_SELECTOR) - Scroll to element
- selum.vigilance(selector, timeout=20, by=By.CSS_SELECTOR) - Wait for element
- selum.cleansing_aura() - Remove overlays and modals

**Task:**
Generate a compact Python function that resolves this specific challenge using ONLY the Selum commands above.

**Requirements:**
1. Function signature: `def skill_<descriptive_name>(selum: SelumOfPersistence) -> bool:`
2. Use ONLY Selum commands (no direct Selenium calls)
3. Return True if successful, False otherwise
4. Include try-except for error handling
5. Keep it compact (< 30 lines)
6. Add a docstring explaining what it does

**Example Format:**
```python
def skill_skip_cookie_banner(selum: SelumOfPersistence) -> bool:
    \"\"\"Skips common cookie consent banners.\"\"\"
    try:
        cookie_options = [
            {{"text": "Accept"}},
            {{"text": "Aceitar"}},
            {{"css": ".cookie-accept"}}
        ]
        element = selum.scout(cookie_options)
        if element:
            selum.strike(element)
            return True
        return False
    except Exception:
        return False
```

Generate the function now:
"""

    def _extract_code(self, raw_response: str) -> str:
        """Extrai código Python da resposta do Groq."""
        # Remove markdown code blocks
        if "```python" in raw_response:
            code = raw_response.split("```python")[1].split("```")[0]
        elif "```" in raw_response:
            code = raw_response.split("```")[1].split("```")[0]
        else:
            code = raw_response

        return code.strip()

    def _extract_function_name(self, code: str) -> str:
        """Extrai o nome da função do código."""
        match = re.search(r"def (skill_\w+)\(", code)
        if match:
            return match.group(1)
        raise ValueError("Could not extract function name from code")
