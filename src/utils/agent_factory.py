"""
AgentFactory - Instancia Especialistas Paladinos por biblioteca.

Quando um erro ocorre, get_specialist(lib_name, error_context) retorna a Spec
do especialista (markdown). Se não existir, a Groq gera e salva em specs/{lib_name}.md.
"""

from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SPECS_DIR = PROJECT_ROOT / "src" / "agents" / "specs"


PALADINO_BASE = """# Especialista Paladino - {lib_name}

## Objetivo
Contornar bloqueios de interação em fluxos de login OAuth/2FA usando injeção de JS.

## Persona
Especialista Sênior em automação web. Conhece Selenium, undetected-chromedriver e técnicas de bypass.

## Manobras de Combate
- Injeção via driver.execute_script() (evita detecção de mouse)
- Preenchimento de formulários via JS puro
- Detecção de Desafio de Identidade (2FA): quando detectar, parar e alertar o usuário
"""


def _generate_spec_via_groq(lib_name: str, error_context: str) -> Optional[str]:
    """Chama a Groq para gerar a Spec do Especialista Paladino."""
    try:
        from src.utils.llm_client import chat_completion, _load_groq_keys, DEFAULT_MODELS
    except ImportError:
        return None

    if not _load_groq_keys():
        return None

    prompt = f"""Crie a Spec (markdown) do Especialista Paladino para a biblioteca "{lib_name}".

Contexto do erro que disparou a criação:
```
{error_context[:1500]}
```

A Spec deve seguir o template:
- Objetivo: Contornar bloqueios de interação em fluxos de login OAuth/2FA usando injeção de JS
- Persona: Especialista Sênior
- Manobras de Combate: inclua "Detecção de Desafio de Identidade (2FA)" - quando 2FA for detectado, o especialista deve parar e alertar: "GUERREIRO, PRECISO DE VOCÊ! O Dragão exige um Código de Verificação. Insira-o agora ou aprove no celular."

Responda APENAS com o markdown da Spec, sem explicações."""

    try:
        response = chat_completion(
            messages=[{"role": "user", "content": prompt}],
            model=DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile"),
        )
        if response:
            return response.strip()
    except Exception:
        pass
    return None


class AgentFactory:
    """
    Factory de Especialistas. Carrega ou gera Specs por lib_name.
    NÃO lê .env - recebe USER/PASS via argumentos seguros quando necessário.
    """

    def __init__(self, specs_dir: Optional[Path] = None):
        self.specs_dir = specs_dir or SPECS_DIR
        self.specs_dir.mkdir(parents=True, exist_ok=True)

    def get_specialist(self, lib_name: str, error_context: str) -> str:
        """
        Retorna a Spec do especialista para lib_name.
        Se specs/{lib_name}.md não existir, gera via Groq e salva.
        """
        if not lib_name or lib_name == "unknown":
            return PALADINO_BASE.format(lib_name="generic")

        spec_path = self.specs_dir / f"{lib_name}.md"

        if spec_path.exists():
            try:
                return spec_path.read_text(encoding="utf-8")
            except Exception:
                pass

        # Nova lib detectada - criar Especialista Paladino
        print(f"[AgentFactory] Nova lib detectada: '{lib_name}'. Criando Especialista Paladino...", flush=True)

        spec_content = _generate_spec_via_groq(lib_name, error_context)
        if spec_content:
            try:
                spec_path.write_text(spec_content, encoding="utf-8")
            except Exception:
                pass
            return spec_content

        # Fallback: spec base
        return PALADINO_BASE.format(lib_name=lib_name)


# Singleton para uso global
_agent_factory: Optional[AgentFactory] = None


def get_agent_factory() -> AgentFactory:
    global _agent_factory
    if _agent_factory is None:
        _agent_factory = AgentFactory()
    return _agent_factory
