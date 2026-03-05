"""
EvolutionaryOrchestrator - Navegação Resiliente com Self-Healing.

Agente de Live Coding (CLI): ReAct loop, safe_globals persistentes,
verificador de progresso real, session log.
"""

import functools
import hashlib
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

PROJECT_ROOT = Path(__file__).parent.parent.parent


class OrchestratorTimeoutError(Exception):
    """Timeout customizado para operações do orquestrador."""
    pass


def with_timeout(seconds: int):
    """Decorador que envolve funções com timeout. Levanta OrchestratorTimeoutError se exceder."""
    def decorator(func: Callable):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            result = [None]
            exc_holder = [None]

            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    exc_holder[0] = e

            # Windows: threading + join com timeout (signal.alarm não existe)
            import threading
            t = threading.Thread(target=target, daemon=True)
            t.start()
            t.join(timeout=seconds)
            if t.is_alive():
                raise OrchestratorTimeoutError(
                    f"{func.__name__} excedeu o timeout de {seconds}s"
                )
            if exc_holder[0]:
                raise exc_holder[0]
            return result[0]
        return wrapper
    return decorator


class SelfHealingManager:
    """
    Gerencia estratégias de recuperação progressivas.
    strategy_index: 0 = Perfil Real + Undetected, 1 = Real + Deep Clean + Selenium,
    2 = Fallback (.temp_profile) + Selenium, 3 = Headless emergência.
    """

    MAX_STRATEGIES = 4

    def __init__(self, profile_path: str | None = None):
        self.strategy_index = 0
        self.profile_path = profile_path or os.getenv("EXTRACTOR_CHROME_USER_DATA", "").strip()
        self.temp_profile = str(PROJECT_ROOT / ".temp_profile")
        self.extra_chrome_args: list[str] = []
        self._strategies = [
            ("Estratégia 0: Perfil Real + Undetected", self._config_0),
            ("Estratégia 1: Perfil Real + Deep Clean + Selenium", self._config_1),
            ("Estratégia 2: Perfil Fallback (.temp_profile) + Selenium", self._config_2),
            ("Estratégia 3: Modo Headless Emergência", self._config_3),
        ]

    def _config_0(self) -> dict[str, Any]:
        return {
            "use_undetected": True,
            "profile_override": None,
            "skip_deep_clean": False,
            "skip_fallback": True,
            "headless": True,
        }

    def _config_1(self) -> dict[str, Any]:
        return {
            "use_undetected": False,
            "profile_override": None,
            "skip_deep_clean": False,
            "skip_fallback": True,
            "headless": True,
        }

    def _config_2(self) -> dict[str, Any]:
        return {
            "use_undetected": False,
            "profile_override": self.temp_profile,
            "skip_deep_clean": True,
            "skip_fallback": True,
            "headless": True,
        }

    def _config_3(self) -> dict[str, Any]:
        return {
            "use_undetected": False,
            "profile_override": self.temp_profile,
            "skip_deep_clean": True,
            "skip_fallback": True,
            "headless": True,
        }

    def get_current_strategy_name(self) -> str:
        if 0 <= self.strategy_index < len(self._strategies):
            return self._strategies[self.strategy_index][0]
        return "Estratégia desconhecida"

    def get_current_config(self) -> dict[str, Any]:
        if 0 <= self.strategy_index < len(self._strategies):
            return self._strategies[self.strategy_index][1]()
        return self._config_3()

    def get_next_strategy(self) -> bool:
        """Incrementa strategy_index. Retorna True se há próxima estratégia."""
        self.strategy_index += 1
        return self.strategy_index < self.MAX_STRATEGIES

    def add_chrome_flag(self, flag: str) -> None:
        """Adiciona flag dinâmica sugerida pela Groq. Ignora flags que sobrescrevem perfil."""
        if not flag or not flag.strip() or flag.startswith("#"):
            return
        flag = flag.strip()
        # Não sobrescrever perfil (user-data-dir, profile-directory)
        if "--user-data-dir" in flag or "--profile-directory" in flag:
            return
        if flag not in self.extra_chrome_args:
            self.extra_chrome_args.append(flag)

    def clear_extra_flags(self) -> None:
        self.extra_chrome_args.clear()

    def apply_specialist_strategy(
        self,
        specialist_spec: str,
        driver: Any,
        error: str,
        user: str = "",
        password: str = "",
    ) -> bool:
        """
        Aplica a estratégia do Especialista (AgentFactory) para reparo.
        Se lib_name for selenium e erro envolver login/auth, usa timeout 300s.
        NÃO lê .env - user/pass vêm via argumentos seguros.
        """
        err_lower = (error or "").lower()
        is_login_auth = any(
            t in err_lower
            for t in ["login", "auth", "oauth", "2fa", "timeout", "elementnotinteractable"]
        )
        timeout = 300 if is_login_auth else 30

        if is_login_auth:
            print(
                "\n  >> [AgentFactory] Erro de login/auth detectado. Timeout aumentado para 300s (2FA).",
                flush=True,
            )

        return attempt_dynamic_fix(
            driver,
            error,
            specialist_spec=specialist_spec,
            timeout=timeout,
        )


def attempt_dynamic_fix(
    driver,
    error_traceback: str,
    specialist_spec: str | None = None,
    timeout: int = 30,
) -> bool:
    """
    Tenta auto-cura via injeção dinâmica de código gerado pela Groq.
    Se specialist_spec (AgentFactory) for fornecido, usa como contexto.
    timeout: 300s para login/auth quando 2FA pode aparecer.
    """
    if driver is None:
        return False

    from src.utils.groq_reporter import generate_dynamic_repair_code

    code = generate_dynamic_repair_code(error_traceback, specialist_spec=specialist_spec)
    if not code:
        return False

    try:
        ok, _ = _run_dynamic_repair(driver, code, timeout=timeout)
        return ok
    except Exception:
        return False


def _is_oauth_login_screen(driver) -> bool:
    """Detecta se estamos em tela de login Google/OAuth."""
    try:
        url = (driver.current_url or "").lower()
        title = (driver.title or "").lower()
        page = (driver.page_source or "").lower()
        triggers = [
            "accounts.google.com",
            "accounts.google.",
            "login",
            "sign in",
            "signin",
            "entrar",
            "iniciar sess",
            "identifique-se",
            "fazer login",
            "oauth",
            "authorize",
        ]
        if any(t in url for t in ["accounts.google", "login", "oauth", "signin"]):
            return True
        if any(t in title for t in ["sign in", "login", "entrar", "google"]):
            return True
        if "type=\"email\"" in page or "type=\"password\"" in page or "identifier" in page:
            if "google" in url or "accounts" in url or "login" in url:
                return True
        return False
    except Exception:
        return False


def solve_oauth_flow(driver) -> bool:
    """
    Agente de Quebra de OAuth (O Cérebro).
    Quando detecta tela de login Google/OAuth:
    - Captura document.documentElement.outerHTML
    - Envia para Groq para gerar dynamic_repair que injeta credenciais via JS
    - Executa o código (evita detecção de mouse)
    Retorna True se conseguiu executar e não houve erro.
    """
    if driver is None:
        return False
    if not _is_oauth_login_screen(driver):
        return False

    from src.utils.groq_reporter import generate_oauth_break_code

    user = os.getenv("EXTRACTOR_GOOGLE_USER") or os.getenv("EXTRACTOR_GOOGLE_EMAIL") or os.getenv("EXTRACTOR_USER", "")
    password = os.getenv("EXTRACTOR_GOOGLE_PASS") or os.getenv("EXTRACTOR_PASS", "")
    if not user or not password:
        return False

    try:
        html = driver.execute_script("return document.documentElement.outerHTML;") or driver.page_source or ""
        if not html:
            return False

        # Bypass 2FA: Alerta máximo se detectar desafio manual
        html_lower = html.lower()
        _2fa_triggers = [
            "confirm your identity",
            "digite o código",
            "2fa",
            "two-factor",
            "two factor",
            "verification code",
            "código de verificação",
            "approve this sign-in",
            "aprovar este login",
        ]
        if any(t in html_lower for t in _2fa_triggers):
            import logging
            _log2 = logging.getLogger("api_key_extractor")
            _log2.warning(
                "ALERTA MÁXIMO: Atenção Hugo: O Google exigiu 2FA manual. "
                "Aguardando 60s para você aprovar no celular ou injetar o código via CLI."
            )
            print(
                "\n  >> GUERREIRO, PRECISO DE VOCÊ! O Dragão exige um Código de Verificação. Insira-o agora ou aprove no celular.",
                flush=True,
            )
            # Extração de brutos em tempo real: gera target_site_2fa_structure.md
            try:
                from src.utils.cartographer import generate_bruto_for_site, add_gap
                generate_bruto_for_site("2fa", html, "2FA detectado - desafio manual", None, "google_oauth")
                add_gap("Um seletor de bypass para o Iframe de Login (2FA)")
            except Exception:
                pass
            time.sleep(60)

        code = generate_oauth_break_code(html, user, password)
        if not code:
            return False

        safe_globals = _get_safe_globals(driver)
        safe_globals["user"] = user
        safe_globals["password"] = password
        exec(code, safe_globals)
        dynamic_repair = safe_globals.get("dynamic_repair")
        if not callable(dynamic_repair):
            return False

        exc_holder = [None]

        def run():
            try:
                dynamic_repair(driver)
            except Exception as e:
                exc_holder[0] = e

        import threading
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=30)
        if t.is_alive():
            return False
        if exc_holder[0]:
            return False
        time.sleep(2)
        return True
    except Exception:
        return False


def _get_safe_globals(driver):
    """Retorna safe_globals ampliados para exec de código dinâmico."""
    import time as _time
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.common.action_chains import ActionChains
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC

    return {
        "__builtins__": __builtins__,
        "driver": driver,
        "time": _time,
        "By": By,
        "Keys": Keys,
        "ActionChains": ActionChains,
        "WebDriverWait": WebDriverWait,
        "EC": EC,
    }


def _capture_state(driver) -> str:
    """Captura estado atual: URL, titulo, snippet HTML."""
    try:
        url = driver.current_url or "(vazio)"
        title = driver.title or "(vazio)"
        html = (driver.page_source or "")[:2000]
        return f"URL: {url}\nTitulo: {title}\nHTML (snippet):\n{html}"
    except Exception:
        return "(erro ao capturar estado)"


def _compute_state_hash(driver) -> str:
    """Hash do estado para verificar progresso real (anti-loop refresh)."""
    try:
        url = driver.current_url or ""
        title = driver.title or ""
        html = (driver.page_source or "")[:1500]
        raw = f"{url}|{title}|{html}"
        return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]
    except Exception:
        return ""


def _check_real_progress(hashes: list[str], min_changes: int = 2) -> bool:
    """
    Verifica se houve progresso real entre os últimos passos.
    Se os últimos min_changes hashes forem iguais, está em loop (ex: refresh infinito).
    Retorna False se detectar loop, True se há progresso.
    """
    if len(hashes) < min_changes:
        return True
    last = hashes[-min_changes:]
    return len(set(last)) > 1


def _run_dynamic_repair(driver, code: str, timeout: int = 30) -> tuple[bool, str | None]:
    """Executa código dynamic_repair(driver). Retorna (sucesso, erro)."""
    try:
        safe_globals = _get_safe_globals(driver)
        exec(code, safe_globals)
        dynamic_repair = safe_globals.get("dynamic_repair")
        if not callable(dynamic_repair):
            return False, "dynamic_repair não encontrada"

        exc_holder = [None]

        def run():
            try:
                dynamic_repair(driver)
            except Exception as e:
                exc_holder[0] = e

        import threading
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            return False, "Timeout"
        if exc_holder[0]:
            return False, str(exc_holder[0])
        return True, None
    except Exception as e:
        return False, str(e)


def _run_with_persistent_globals(
    driver,
    code: str,
    safe_globals: dict,
    timeout: int = 30,
) -> tuple[bool, str | None]:
    """
    Executa código usando o MESMO safe_globals (variáveis persistem entre passos).
    Atualiza driver em safe_globals antes de executar.
    """
    safe_globals["driver"] = driver
    try:
        exec(code, safe_globals)
        dynamic_repair = safe_globals.get("dynamic_repair")
        if not callable(dynamic_repair):
            return False, "dynamic_repair não encontrada"

        exc_holder = [None]

        def run():
            try:
                dynamic_repair(driver)
            except Exception as e:
                exc_holder[0] = e

        import threading
        t = threading.Thread(target=run, daemon=True)
        t.start()
        t.join(timeout=timeout)
        if t.is_alive():
            return False, "Timeout"
        if exc_holder[0]:
            return False, str(exc_holder[0])
        return True, None
    except Exception as e:
        return False, str(e)


def _save_session_log(
    path: Path,
    objetivo: str,
    sucesso: bool,
    decisoes: list[dict],
    report: str | None,
) -> None:
    """Salva autonomous_session_log.md com cada decisão."""
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Autonomous Session Log",
        f"**Data:** {datetime.now().isoformat()}",
        f"**Objetivo:** {objetivo}",
        f"**Sucesso:** {sucesso}",
        "",
        "## Decisões",
        "",
    ]
    for i, d in enumerate(decisoes, 1):
        lines.append(f"### Passo {i}")
        lines.append(f"- **PENSAMENTO:** {d.get('thought', '-')}")
        lines.append(f"- **Código:** ```python\n{d.get('code', '')[:500]}...\n```")
        lines.append(f"- **Erro (se houver):** {d.get('error', '-')}")
        lines.append(f"- **Hash estado:** {d.get('state_hash', '-')}")
        lines.append("")
    if report:
        lines.append("## Relatório de Missão")
        lines.append("")
        lines.append(report)
    try:
        path.write_text("\n".join(lines), encoding="utf-8")
    except Exception:
        pass


def autonomous_repair_loop(
    driver,
    objetivo: str,
    erro_atual: str,
    max_steps: int = 10,
    on_step: Callable | None = None,
    logs_recentes: str = "",
    save_log_path: Path | None = None,
) -> tuple[bool, str | None]:
    """
    Agente de Live Coding (CLI): Loop ReAct com safe_globals persistentes.
    - Formato PENSAMENTO + CÓDIGO
    - Variáveis persistem entre passos
    - Retry imediato com traceback em falha
    - Verificador de progresso real (anti-loop refresh)
    - Salva autonomous_session_log.md
    """
    if driver is None:
        return False, "Driver ausente"

    from src.utils.groq_reporter import (
        generate_react_response,
        generate_next_autonomous_command,
        evaluate_did_it_work,
        generate_mission_report,
    )

    safe_globals = _get_safe_globals(driver)
    historico_comandos: list[str] = []
    decisoes: list[dict] = []
    state_hashes: list[str] = []
    ultimo_erro = erro_atual
    step = 0
    max_retries_per_step = 2

    while step < max_steps:
        step += 1
        time.sleep(2)

        try:
            estado_atual = _capture_state(driver)
            state_hash = _compute_state_hash(driver)
            state_hashes.append(state_hash)
        except Exception:
            estado_atual = "(erro ao capturar)"
            state_hash = ""

        if not _check_real_progress(state_hashes, min_changes=2):
            ultimo_erro = "Loop detectado: estado identico em passos consecutivos (ex: refresh infinito)"
            decisoes.append({
                "thought": "BLOQUEIO: Sem progresso real",
                "code": "",
                "error": ultimo_erro,
                "state_hash": state_hash,
            })
            break

        thought, code = generate_react_response(
            objetivo=objetivo,
            estado_atual=estado_atual,
            logs=logs_recentes,
            historico=historico_comandos,
            erro=ultimo_erro,
        )
        if not code:
            code = generate_next_autonomous_command(
                objetivo, estado_atual, historico_comandos, ultimo_erro
            )
        if not code:
            break

        historico_comandos.append(f"[{step}] {thought or '-'} | {code[:150]}...")

        if on_step:
            on_step(step, thought, code)

        retries = 0
        while retries <= max_retries_per_step:
            ok, err = _run_with_persistent_globals(driver, code, safe_globals)
            if ok:
                decisoes.append({
                    "thought": thought or "-",
                    "code": code,
                    "error": None,
                    "state_hash": state_hash,
                })
                break
            ultimo_erro = err or "Erro desconhecido"
            decisoes.append({
                "thought": thought or "-",
                "code": code,
                "error": ultimo_erro,
                "state_hash": state_hash,
            })
            retries += 1
            if retries <= max_retries_per_step:
                thought, code = generate_react_response(
                    objetivo, estado_atual, logs_recentes,
                    historico_comandos, ultimo_erro,
                )
                if not code:
                    code = generate_next_autonomous_command(
                        objetivo, estado_atual, historico_comandos, ultimo_erro
                    )
                if not code:
                    break
                historico_comandos.append(f"[retry {retries}] {ultimo_erro[:100]}")
            else:
                break
        else:
            continue

        if not ok:
            time.sleep(2)
            continue

        time.sleep(2)

        try:
            estado_pos = _capture_state(driver)
        except Exception:
            estado_pos = "(erro ao capturar)"

        if evaluate_did_it_work(objetivo, estado_pos, code):
            report = generate_mission_report(
                objetivo, step, True, historico_comandos
            )
            log_path = save_log_path or (PROJECT_ROOT / "logs" / "autonomous_session_log.md")
            _save_session_log(log_path, objetivo, True, decisoes, report)
            return True, report

        time.sleep(2)

    report = generate_mission_report(
        objetivo, step, False, historico_comandos
    )
    log_path = save_log_path or (PROJECT_ROOT / "logs" / "autonomous_session_log.md")
    _save_session_log(log_path, objetivo, False, decisoes, report)
    return False, report
