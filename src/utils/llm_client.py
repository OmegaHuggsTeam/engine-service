"""
Cliente LLM - Groq como padrão (custo zero, alta velocidade).
Suporta OpenAI e Gemini como alternativas.
Load Balancer com múltiplas chaves Groq (GROQ_KEY_1..10).

Quando litellm esta instalado e config/litellm_models.yaml existe,
delega roteamento para LiteLLMRouter (latency-based, fallbacks, cost tracking).
Caso contrario, mantem o roteamento manual original.
"""

import asyncio
import hashlib
import itertools
import logging
import os
import threading
import time
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger(__name__)

# Groq como provider padrão
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "groq").lower()
LLM_MODEL = os.getenv("LLM_MODEL", "").strip()

# Modelos padrão
DEFAULT_MODELS = {
    "groq": "llama-3.3-70b-versatile",
    "openai": "gpt-4o-mini",
    "gemini": "gemini-1.5-flash",
}

# Load Balancer
_KEY_MANAGER = None
_KEY_MANAGER_LOCK = threading.Lock()
RATE_LIMIT_SLEEP = 0.5
COOLDOWN_429_SEC = 60


def _load_groq_keys() -> list[str]:
    """Carrega GROQ_KEY_1..10 ou fallback para GROQ_API_KEY."""
    keys = []
    for i in range(1, 11):
        k = os.getenv(f"GROQ_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    if not keys:
        fallback = os.getenv("GROQ_API_KEY", "").strip()
        if fallback:
            keys = [fallback]
    return keys


def get_key_manager() -> "KeyManager":
    """Retorna o KeyManager singleton (thread-safe)."""
    global _KEY_MANAGER
    with _KEY_MANAGER_LOCK:
        if _KEY_MANAGER is None:
            _KEY_MANAGER = KeyManager(_load_groq_keys())
        return _KEY_MANAGER


class KeyManager:
    """
    Load Balancer de chaves Groq com itertools.cycle.
    Em 429: desativa chave por 60s e passa para a próxima.
    """

    def __init__(self, keys: list[str]):
        self._keys = [(k, 0.0) for k in keys]  # (key, cooldown_until)
        self._cycle = itertools.cycle(range(len(self._keys))) if self._keys else None
        self._lock = threading.Lock()

    def get_next_key(self) -> tuple[str | None, int]:
        """Retorna (key, key_index). key_index em 1..10 para telemetria."""
        if not self._keys:
            return None, 0
        with self._lock:
            time.sleep(RATE_LIMIT_SLEEP)
            now = time.monotonic()
            for _ in range(len(self._keys)):
                idx = next(self._cycle)
                key, cooldown = self._keys[idx]
                if cooldown <= now:
                    return key, idx + 1
            wait = min(c for _, c in self._keys) - now + 0.1
        if wait > 0:
            time.sleep(min(wait, COOLDOWN_429_SEC))
        return self._keys[0][0], 1

    def mark_429(self, key: str):
        """Desativa chave por 60s após Rate Limit."""
        with self._lock:
            for i, (k, _) in enumerate(self._keys):
                if k == key:
                    self._keys[i] = (k, time.monotonic() + COOLDOWN_429_SEC)
                    break

    # ---- Secret Vault Extension ----

    def register_key(self, key: str, checksum: str, provider: str = "groq") -> bool:
        """
        Valida SHA-256 checksum e, se valido, adiciona key a pool.
        Returns True se registrada com sucesso.
        """
        if not self.validate_checksum(key, checksum):
            return False
        with self._lock:
            # Evita duplicatas
            for k, _ in self._keys:
                if k == key:
                    return True
            self._keys.append((key, 0.0))
            # Recria cycle com novo tamanho
            self._cycle = itertools.cycle(range(len(self._keys)))
            if not hasattr(self, "_providers"):
                self._providers = set()
            self._providers.add(provider)
        return True

    @staticmethod
    def validate_checksum(key: str, expected_checksum: str) -> bool:
        """Valida SHA-256(key) == expected_checksum."""
        computed = hashlib.sha256(key.encode()).hexdigest()
        return computed == expected_checksum

    def get_vault_status(self) -> dict:
        """Retorna status do vault: keys ativas, em cooldown, providers."""
        with self._lock:
            now = time.monotonic()
            active = sum(1 for _, cd in self._keys if cd <= now)
            in_cooldown = sum(1 for _, cd in self._keys if cd > now)
            providers = getattr(self, "_providers", set())
            return {
                "total_keys": len(self._keys),
                "active_keys": active,
                "in_cooldown": in_cooldown,
                "providers": sorted(providers) if providers else ["groq"],
            }


def _get_groq_key_pool():
    """Alias para compatibilidade (retorna KeyManager)."""
    return get_key_manager()


def _get_config() -> dict[str, Any]:
    """Retorna config do LLM baseado em LLM_PROVIDER e .env."""
    provider = LLM_PROVIDER
    api_key = (
        os.getenv("GROQ_API_KEY")
        or os.getenv("OPENAI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
        or os.getenv("LLM_API_KEY")
    )
    model = LLM_MODEL or DEFAULT_MODELS.get(provider, DEFAULT_MODELS["groq"])
    return {"provider": provider, "api_key": api_key, "model": model}


def _get_litellm_router():
    """
    Retorna LiteLLMRouter singleton se disponivel, ou None.
    Graceful: nunca levanta exception, apenas retorna None.
    """
    try:
        from src.utils.litellm_router import LiteLLMRouter

        router = LiteLLMRouter.from_env()
        if router.is_available:
            return router
    except Exception as e:
        logger.debug("LiteLLM Router not available: %s", e)
    return None


def _run_async(coro):
    """Executa coroutine em contexto sync (compatibilidade com callers sync)."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # Estamos dentro de um event loop — cria thread para rodar
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


def chat_completion(
    messages: list[dict[str, str]],
    model: str | None = None,
    api_key: str | None = None,
    on_key_used=None,
    max_tokens: int | None = None,
) -> str:
    """
    Invoca o LLM configurado. Padrão: Groq (llama-3.3-70b-versatile).

    Quando LiteLLM esta disponivel, delega para LiteLLMRouter com
    roteamento por latencia e fallbacks automaticos.
    Caso contrario, usa o roteamento manual original.

    Args:
        messages: [{"role": "system"|"user"|"assistant", "content": "..."}]
        model: Override do modelo (opcional)
        api_key: Override da API key (ignora LiteLLM se fornecida)
        on_key_used: Callback para telemetria de chave Groq
        max_tokens: Limite de tokens na resposta
    """
    # ── LiteLLM delegation ──
    # Somente delega se nao tem api_key override (respeita uso explicito)
    if api_key is None:
        router = _get_litellm_router()
        if router is not None:
            try:
                from src.utils.litellm_router import LiteLLMRouter

                tier = LiteLLMRouter.resolve_tier(model)
                result = _run_async(
                    router.completion_with_messages(
                        messages=messages,
                        model_tier=tier,
                        max_tokens=max_tokens or 2048,
                    )
                )
                return result["content"]
            except Exception as e:
                logger.warning("LiteLLM call failed, falling back to manual routing: %s", e)
                # Fall through to manual routing

    # ── Manual routing (fallback / backward compat) ──
    cfg = _get_config()
    model = model or cfg["model"]
    api_key = api_key or cfg["api_key"]

    if cfg["provider"] == "groq":
        if not _load_groq_keys():
            raise ValueError(
                "Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env " "(obtenha em console.groq.com)"
            )
    elif cfg["provider"] == "openai" and not (api_key or os.getenv("OPENAI_API_KEY")):
        raise ValueError("Configure OPENAI_API_KEY no .env para usar OpenAI.")
    elif cfg["provider"] == "gemini" and not (api_key or os.getenv("GOOGLE_API_KEY")):
        raise ValueError("Configure GOOGLE_API_KEY no .env para usar Gemini.")
    elif not api_key:
        raise ValueError(
            "Configure a chave de API no .env (GROQ_API_KEY, OPENAI_API_KEY ou GOOGLE_API_KEY)."
        )

    if cfg["provider"] == "groq":
        return _chat_groq(messages, model, on_key_used=on_key_used, max_tokens=max_tokens)

    if cfg["provider"] == "gemini":
        try:
            return _chat_gemini(messages, model, api_key)
        except ImportError:
            raise ImportError("Gemini requer: pip install langchain-google-genai") from None

    return _chat_openai(messages, model, api_key)


def _chat_groq(
    messages: list[dict], model: str, on_key_used=None, max_tokens: int | None = None
) -> str:
    """Usa cliente Groq. KeyManager com rotação e retry em 429 (cooldown 60s)."""
    from groq import Groq

    mgr = get_key_manager()
    key, key_idx = mgr.get_next_key()
    if not key:
        raise ValueError("Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env")

    for attempt in range(len(mgr._keys) + 1):
        try:
            if on_key_used:
                on_key_used(key_idx)
            client = Groq(api_key=key)
            kwargs = {"model": model, "messages": messages}
            if max_tokens is not None:
                kwargs["max_tokens"] = max_tokens
            _call_start = time.perf_counter()
            response = client.chat.completions.create(**kwargs)
            _call_latency_ms = (time.perf_counter() - _call_start) * 1000
            # Record token usage + latency for cost profiling
            try:
                from src.utils.cost_context import get_cost_profile

                profile = get_cost_profile()
                if profile and hasattr(response, "usage") and response.usage:
                    _in = getattr(response.usage, "prompt_tokens", 0)
                    _out = getattr(response.usage, "completion_tokens", 0)
                    if hasattr(profile, "record_llm_call_with_latency"):
                        profile.record_llm_call_with_latency(model, _in, _out, _call_latency_ms)
                    elif hasattr(profile, "record_llm_call"):
                        profile.record_llm_call(model, _in, _out)
            except ImportError:
                pass
            return response.choices[0].message.content.strip()
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                mgr.mark_429(key)
                key, key_idx = mgr.get_next_key()
                if not key:
                    raise RuntimeError("Todas as chaves Groq em rate limit. Aguarde 60s.") from e
                continue
            raise


def transcribe_audio_groq(
    audio_path: str | Path,
    model: str = "whisper-large-v3",
    language: str = "pt",
    on_key_used=None,
) -> str:
    """
    Transcreve áudio via Groq API (whisper-large-v3).
    Usa KeyManager para rotação de chaves.
    """
    from groq import Groq

    mgr = get_key_manager()
    key, key_idx = mgr.get_next_key()
    if not key:
        raise ValueError("Configure GROQ_API_KEY ou GROQ_KEY_1..10 no .env")

    path = Path(audio_path)
    if not path.exists():
        raise FileNotFoundError(f"Áudio não encontrado: {path}")

    for attempt in range(len(mgr._keys) + 1):
        try:
            if on_key_used:
                on_key_used(key_idx)
            client = Groq(api_key=key)
            with open(path, "rb") as f:
                transcription = client.audio.transcriptions.create(
                    file=(path.name, f.read()),
                    model=model,
                    language=language,
                    response_format="text",
                )
            return (
                transcription.text.strip() if hasattr(transcription, "text") else str(transcription)
            )
        except Exception as e:
            err_str = str(e).lower()
            if "429" in err_str or "rate limit" in err_str:
                mgr.mark_429(key)
                key, key_idx = mgr.get_next_key()
                if not key:
                    raise RuntimeError("Todas as chaves Groq em rate limit. Aguarde 60s.") from e
                continue
            raise


def _chat_openai(messages: list[dict], model: str, api_key: str) -> str:
    """Usa cliente OpenAI."""
    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.chat.completions.create(model=model, messages=messages)
    return response.choices[0].message.content.strip()


def _chat_gemini(messages: list[dict], model: str, api_key: str) -> str:
    """Usa LangChain para Gemini."""
    from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
    from langchain_google_genai import ChatGoogleGenerativeAI

    lc_messages = []
    for m in messages:
        role, content = m.get("role", "user"), m.get("content", "")
        if role == "system":
            lc_messages.append(SystemMessage(content=content))
        elif role == "assistant":
            lc_messages.append(AIMessage(content=content))
        else:
            lc_messages.append(HumanMessage(content=content))

    llm = ChatGoogleGenerativeAI(model=model, google_api_key=api_key)
    response = llm.invoke(lc_messages)
    return response.content if hasattr(response, "content") else str(response)
