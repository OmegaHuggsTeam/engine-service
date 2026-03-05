"""
GroqReporter - Relator de Execução via Groq API (Modo Free).
Analisa logs de automação Selenium e gera resumo técnico para o usuário.
"""

import json
import re
from pathlib import Path
from typing import Any

from src.utils.llm_client import chat_completion, _load_groq_keys, DEFAULT_MODELS

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

_GRIMOIRE_CACHE: str | None = None


def _load_grimoire() -> str:
    """Carrega o Grimório de Combate (PROMPT_GUERREIRO.md) para injeção no system prompt."""
    global _GRIMOIRE_CACHE
    if _GRIMOIRE_CACHE is not None:
        return _GRIMOIRE_CACHE
    path = PROJECT_ROOT / "PROMPT_GUERREIRO.md"
    if path.exists():
        try:
            _GRIMOIRE_CACHE = path.read_text(encoding="utf-8")
            return _GRIMOIRE_CACHE
        except Exception:
            pass
    _GRIMOIRE_CACHE = ""
    return ""


def _should_use_grimoire(error: str) -> bool:
    """Detecta erros que se beneficiam do Grimório (conexão, session, timeout, KeyboardInterrupt)."""
    err_lower = (error or "").lower()
    triggers = [
        "cannot connect to chrome",
        "session not created",
        "invalid session",
        "keyboardinterrupt",
        "devtools",
        "singletonlock",
        "timeout",
        "90s",
        "join()",
    ]
    return any(t in err_lower for t in triggers)


def _sanitize_utf8(text: str) -> str:
    """Força encoding UTF-8 seguro para envio e impressão."""
    return text.encode("utf-8", errors="replace").decode("utf-8")


SYSTEM_PROMPT = """Você é um Engenheiro de Confiabilidade. Analise os logs de automação Selenium abaixo e crie um resumo técnico conciso de 5 linhas para o usuário. Foque em:
1. Por que falhou?
2. O processo estava travado?
3. Qual o próximo passo exato?"""


def generate_groq_report(logs: list[str], context_json: dict[str, Any] | None = None) -> str | None:
    """
    Gera relatório de inteligência via Groq a partir dos logs e contexto.

    Args:
        logs: Últimos 50 eventos do log (ou menos).
        context_json: Status do erro, URL, tentativa, etc.

    Returns:
        Resumo técnico de 5 linhas ou None se falhar (ex: sem API key).
    """
    if not _load_groq_keys():
        return None

    logs_text = "\n".join(logs[-50:]) if logs else "(nenhum log capturado)"
    context_str = json.dumps(context_json or {}, indent=2, ensure_ascii=False)
    logs_text = _sanitize_utf8(logs_text)
    context_str = _sanitize_utf8(context_str)

    system_content = _sanitize_utf8(SYSTEM_PROMPT)
    if _should_use_grimoire(logs_text + " " + context_str):
        grimoire = _load_grimoire()
        if grimoire:
            system_content = f"{_sanitize_utf8(grimoire)}\n\n---\n\n{system_content}"

    user_content = f"""## Logs (últimos eventos)
```
{logs_text}
```

## Contexto do erro
```json
{context_str}
```
"""
    user_content = _sanitize_utf8(user_content)

    try:
        model = DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile")
        response = chat_completion(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": user_content},
            ],
            model=model,
        )
        if response:
            return _sanitize_utf8(response.strip())
        return None
    except Exception:
        return None


CONFIG_RECOMMENDATION_PROMPT = """Você é um Engenheiro de Confiabilidade. Analise o ciclo de tentativas abaixo.

Fases da estratégia Self-Healing:
- Fase 1: Perfil Real (EXTRACTOR_CHROME_USER_DATA)
- Fase 2: Recuperação (deep_clean + retry)
- Fase 3: Fallback Dinâmico (EXTRACTOR_UNDETECTED=false, Selenium padrão)
- Fase 4: Perfil Temporário (.temp_profile)
- Fase 5: Navegação de Último Recurso (_robust_navigate com JavaScript/Ctrl+L)

Responda em 3 blocos:
1. Qual fase funcionou (ou qual foi a última tentada)?
2. Por que as fases anteriores falharam (resumo técnico)?
3. Recomendação de configuração permanente para o .env (liste as variáveis e valores sugeridos)."""


def generate_config_recommendation(
    logs: list[str],
    phases_attempted: list[str],
    success_phase: str | None,
    final_error: str | None,
) -> str | None:
    """
    Gera recomendação de configuração .env baseada nas fases executadas.
    """
    if not _load_groq_keys():
        return None

    logs_text = "\n".join(logs[-80:]) if logs else "(nenhum log)"
    context = {
        "phases_attempted": phases_attempted,
        "success_phase": success_phase,
        "final_error": final_error,
    }
    context_str = json.dumps(context, indent=2, ensure_ascii=False)

    user_content = f"""## Logs
```
{_sanitize_utf8(logs_text)}
```

## Fases executadas
```json
{_sanitize_utf8(context_str)}
```
"""

    try:
        model = DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile")
        response = chat_completion(
            messages=[
                {"role": "system", "content": _sanitize_utf8(CONFIG_RECOMMENDATION_PROMPT)},
                {"role": "user", "content": user_content},
            ],
            model=model,
        )
        if response:
            return _sanitize_utf8(response.strip())
        return None
    except Exception:
        return None


CHROME_FLAG_PROMPT = """Você é um especialista em Selenium e ChromeDriver. O usuário teve o seguinte erro ao tentar abrir o Chrome:

```
{error}
```

Responda APENAS com UMA flag de ChromeOptions que pode ajudar na próxima tentativa. Formato: --nome-da-flag ou --flag=valor
Exemplos válidos: --disable-dev-shm-usage, --no-sandbox, --disable-gpu, --single-process
Se não souber, responda: --disable-dev-shm-usage
NÃO inclua explicações, apenas a flag."""


def ask_groq_for_chrome_flag(error: str) -> str | None:
    """
    Pergunta à Groq qual flag de ChromeOptions adicionar para a próxima tentativa.
    Retorna a flag sugerida ou None.
    """
    if not _load_groq_keys():
        return None
    try:
        model = DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile")
        content = CHROME_FLAG_PROMPT.format(error=_sanitize_utf8(error[:2000]))
        response = chat_completion(
            messages=[{"role": "user", "content": content}],
            model=model,
        )
        if response:
            for line in response.strip().split("\n"):
                line = line.strip()
                if line.startswith("--"):
                    return line.split()[0] if line.split() else line
            return _sanitize_utf8(response.strip())[:200]
        return None
    except Exception:
        return None


DYNAMIC_REPAIR_PROMPT = """Você é um executor de Python. Dada uma falha no Selenium, escreva uma função dynamic_repair(driver) que use comandos de baixo nível (JS injection, action chains ou atalhos) para contornar o erro. Não explique, apenas dê o código.

Erro:
```
{error}
```

Regras:
- A função deve se chamar exatamente: def dynamic_repair(driver):
- Use apenas: driver, selenium (By, Keys, ActionChains, WebDriverWait), time
- Não use imports adicionais
- Retorne None ou nada
- Código Python válido, sem markdown ou explicações"""


def generate_dynamic_repair_code(error: str, specialist_spec: str | None = None) -> str | None:
    """
    Gera código Python para dynamic_repair(driver) via Groq.
    Retorna a string de código ou None.
    Injeta o Grimório de Combate quando o erro for de conexão/session/timeout.
    Se specialist_spec (AgentFactory) for fornecido, injeta como System Prompt.
    """
    if not _load_groq_keys():
        return None
    try:
        model = DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile")
        content = DYNAMIC_REPAIR_PROMPT.format(error=_sanitize_utf8(error[:2000]))
        system_content = "Você responde APENAS com código Python. Sem markdown, sem ```python. Apenas o código da função dynamic_repair(driver)."
        if specialist_spec:
            system_content = f"{_sanitize_utf8(specialist_spec[:4000])}\n\n---\n\n{system_content}"
        elif _should_use_grimoire(error):
            grimoire = _load_grimoire()
            if grimoire:
                system_content = f"{_sanitize_utf8(grimoire)}\n\n---\n\n{system_content}"
        response = chat_completion(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": content},
            ],
            model=model,
        )
        if response:
            code = response.strip()
            # Regex robusto: extrai bloco entre ```python e ``` (Groq pode ignorar prompt e enviar markdown)
            match = re.search(r"```(?:python)?\s*\n(.*?)```", code, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
            elif "```" in code:
                start = code.find("```")
                start = code.find("\n", start) + 1 if start >= 0 else 0
                end = code.rfind("```")
                code = code[start:end].strip() if end > start else code
            return _sanitize_utf8(code) if code and "def dynamic_repair" in code else None
        return None
    except Exception:
        return None


OAUTH_BREAK_PROMPT = """Estamos presos no OAuth (tela de login Google ou similar).

HTML da página (document.documentElement.outerHTML):
```
{html}
```

Credenciais do .env (NÃO inclua no código, use como variáveis):
- user/email: {user}
- password: (fornecida)

Gere uma função dynamic_repair(driver) que:
1. Injete as credenciais nos campos de input (identifique por id, name, type="email", type="password")
2. Clique nos botões via JavaScript puro (element.click()) para evitar detecção de mouse/Selenium
3. Use driver.execute_script() para preencher e clicar - NÃO use send_keys ou ActionChains
4. Trate possíveis scripts de desafio (reCAPTCHA, 2FA) - se houver, sugira pausa para manual

Regras:
- Código Python com def dynamic_repair(driver):
- Use driver.execute_script("document.querySelector(...).value = '...'") para preencher
- Use driver.execute_script("document.querySelector(...).click()") para clicar
- Variáveis user e password estarão disponíveis no escopo
- Responda APENAS com o código, sem markdown ou explicações"""


def generate_oauth_break_code(html: str, user: str, password: str) -> str | None:
    """
    Gera código dynamic_repair(driver) para quebrar OAuth via injeção JS.
    O Agente analisa os campos de input e gera código que injeta credenciais via JS puro.
    """
    if not _load_groq_keys():
        return None
    try:
        model = DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile")
        content = OAUTH_BREAK_PROMPT.format(
            html=_sanitize_utf8(html[:12000]),
            user=_sanitize_utf8(user or "(vazio)"),
        )
        system_content = """Você gera APENAS código Python. A função dynamic_repair(driver) recebe user e password
como variáveis no escopo (não como parâmetros). Use driver.execute_script para injetar valores e clicar.
Formato: def dynamic_repair(driver): ... (código)"""
        response = chat_completion(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": content},
            ],
            model=model,
        )
        if response:
            code = response.strip()
            match = re.search(r"```(?:python)?\s*\n(.*?)```", code, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
            elif "```" in code:
                start = code.find("```")
                start = code.find("\n", start) + 1 if start >= 0 else 0
                end = code.rfind("```")
                code = code[start:end].strip() if end > start else code
            if "def dynamic_repair" in code:
                return _sanitize_utf8(code)
        return None
    except Exception:
        return None


# --- Autonomous Repair Loop (ReAct / Live Coding Agent) ---

REACT_PROMPT = """Objetivo: {objetivo}

Estado Atual (URL, titulo, HTML snippet):
{estado_atual}

Logs recentes:
{logs}

O que você fez antes (histórico):
{historico}

Último erro (se houver):
{erro}

Responda no formato EXATO:

PENSAMENTO: "Sua análise do estado e próximo passo."
CÓDIGO:
```python
def dynamic_repair(driver):
    # Use driver, By, Keys, ActionChains, WebDriverWait, EC, time
    # Variáveis criadas em passos anteriores estão em safe_globals
    pass
```

Regras: Use apenas driver, By, Keys, ActionChains, WebDriverWait, EC, time. Variáveis persistem entre passos."""

NEXT_COMMAND_PROMPT = """Objetivo: {objetivo}

Estado Atual (URL, titulo, HTML snippet):
{estado_atual}

O que você fez antes (histórico de comandos):
{historico}

Último erro:
{erro}

Gere o PRÓXIMO comando Python como função dynamic_repair(driver) para nos aproximar do objetivo.
Use apenas: driver, By, Keys, ActionChains, WebDriverWait, EC, time.
Responda APENAS com o código da função, sem explicações."""

EVALUATE_WORKED_PROMPT = """Objetivo: {objetivo}

Estado da página APÓS o comando (URL, titulo, snippet HTML):
{estado_pos}

O comando executado foi: {comando_executado}

Pergunta: Isso funcionou? O objetivo foi alcançado ou estamos mais perto?
Responda APENAS: Sim ou Não"""

MISSION_REPORT_PROMPT = """Você executou um loop de reparo autônomo.

Objetivo: {objetivo}
Tentativas: {tentativas}
Sucesso: {sucesso}

Histórico do que foi tentado:
{historico}

Gere um Relatório de Missão em 4 linhas:
1. O que tentou (X, Y, Z)
2. Qual foi o bloqueio (W)
3. Próxima sugestão de configuração do driver (flags ChromeOptions: A, B, C)
4. Recomendação final"""


def generate_react_response(
    objetivo: str,
    estado_atual: str,
    logs: str,
    historico: list[str],
    erro: str,
) -> tuple[str | None, str | None]:
    """
    Gera resposta ReAct: PENSAMENTO + CÓDIGO.
    Retorna (pensamento, codigo) ou (None, None).
    """
    if not _load_groq_keys():
        return None, None
    try:
        hist_str = "\n".join(historico[-10:]) if historico else "(nenhum)"
        content = REACT_PROMPT.format(
            objetivo=objetivo,
            estado_atual=_sanitize_utf8(estado_atual[:3500]),
            logs=_sanitize_utf8((logs or "")[:1000]),
            historico=hist_str,
            erro=_sanitize_utf8(erro[:1500]),
        )
        system_content = "Responda no formato PENSAMENTO: e CÓDIGO: com bloco python."
        if _should_use_grimoire(erro or ""):
            grimoire = _load_grimoire()
            if grimoire:
                system_content = f"{_sanitize_utf8(grimoire)}\n\n---\n\n{system_content}"
        response = chat_completion(
            messages=[
                {"role": "system", "content": system_content},
                {"role": "user", "content": content},
            ],
            model=DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile"),
        )
        if not response:
            return None, None

        thought = None
        code = None

        # Parse PENSAMENTO:
        m_thought = re.search(r"PENSAMENTO:\s*[\"']?(.*?)(?=CÓDIGO:|$)", response, re.DOTALL | re.IGNORECASE)
        if m_thought:
            thought = m_thought.group(1).strip().strip('"').strip("'")[:500]

        # Parse CÓDIGO:
        m_code = re.search(r"```(?:python)?\s*\n(.*?)```", response, re.DOTALL | re.IGNORECASE)
        if m_code:
            code = m_code.group(1).strip()
        if code and "def dynamic_repair" in code:
            return thought, _sanitize_utf8(code)
        return thought, None
    except Exception:
        return None, None


def generate_next_autonomous_command(
    objetivo: str,
    estado_atual: str,
    historico: list[str],
    erro: str,
) -> str | None:
    """Gera o próximo comando dynamic_repair(driver) para o loop autônomo."""
    if not _load_groq_keys():
        return None
    try:
        hist_str = "\n".join(historico[-10:]) if historico else "(nenhum)"
        content = NEXT_COMMAND_PROMPT.format(
            objetivo=objetivo,
            estado_atual=_sanitize_utf8(estado_atual[:3000]),
            historico=hist_str,
            erro=_sanitize_utf8(erro[:1500]),
        )
        response = chat_completion(
            messages=[
                {"role": "system", "content": "Responda APENAS com código Python da função dynamic_repair(driver). Sem markdown."},
                {"role": "user", "content": content},
            ],
            model=DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile"),
        )
        if response:
            code = response.strip()
            match = re.search(r"```(?:python)?\s*\n(.*?)```", code, re.DOTALL | re.IGNORECASE)
            if match:
                code = match.group(1).strip()
            return _sanitize_utf8(code) if code and "def dynamic_repair" in code else None
        return None
    except Exception:
        return None


def evaluate_did_it_work(
    objetivo: str,
    estado_pos: str,
    comando_executado: str,
) -> bool:
    """Pergunta à Groq se o comando funcionou. Retorna True se Sim."""
    if not _load_groq_keys():
        return False
    try:
        content = EVALUATE_WORKED_PROMPT.format(
            objetivo=objetivo,
            estado_pos=_sanitize_utf8(estado_pos[:2500]),
            comando_executado=comando_executado[:500],
        )
        response = chat_completion(
            messages=[{"role": "user", "content": content}],
            model=DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile"),
        )
        if response:
            r = response.strip().lower()
            if "não" in r[:50] or "no" in r[:50]:
                return False
            return "sim" in r or "yes" in r
        return False
    except Exception:
        return False


def generate_mission_report(
    objetivo: str,
    tentativas: int,
    sucesso: bool,
    historico: list[str],
) -> str | None:
    """Gera relatório de missão após o loop."""
    if not _load_groq_keys():
        return None
    try:
        hist_str = "\n".join(historico) if historico else "(nenhum)"
        content = MISSION_REPORT_PROMPT.format(
            objetivo=objetivo,
            tentativas=tentativas,
            sucesso="Sim" if sucesso else "Não",
            historico=hist_str,
        )
        response = chat_completion(
            messages=[{"role": "user", "content": content}],
            model=DEFAULT_MODELS.get("groq", "llama-3.3-70b-versatile"),
        )
        return _sanitize_utf8(response.strip()) if response else None
    except Exception:
        return None
