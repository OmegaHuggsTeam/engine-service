"""
Bot do Telegram - Agentes RAG (Marketing, Social, Analytics).

Usa Groq (llama-3.3-70b-versatile) para responder.
Comandos: /start, /agente, /groq_refresh, /status, /processar, /resumo, /ajuda
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Modelo Groq (OpenAI em SKIP - usar Groq)
TELEGRAM_GROQ_MODEL = os.getenv("TELEGRAM_GROQ_MODEL", "llama-3.3-70b-versatile")

# Agentes disponiveis
AGENTES = {
    "marketing": ("Marketing", "src.agents.marketing_agent"),
    "social": ("Social Media", "src.agents.social_media_agent"),
    "analytics": ("Analytics", "src.agents.analytics_agent"),
}

# Estado por chat_id: qual agente esta ativo
_current_agent: dict[int, str] = {}


def _get_agent_module(name: str):
    """Retorna modulo do agente pelo nome."""
    import importlib

    key = name.lower().strip()
    if key not in AGENTES:
        return None
    _, module_path = AGENTES[key]
    return importlib.import_module(module_path)


def _get_current_agent(chat_id: int) -> str:
    """Retorna agente ativo para o chat. Default: marketing."""
    return _current_agent.get(chat_id, "marketing")


def _set_agent(chat_id: int, name: str) -> bool:
    """Define agente ativo. Retorna True se valido."""
    key = name.lower().strip()
    if key not in AGENTES:
        return False
    _current_agent[chat_id] = key
    return True


def _is_authorized(chat_id: int) -> bool:
    """Verifica se o chat esta autorizado (AUTHORIZED_CHAT_ID)."""
    allowed = os.getenv("AUTHORIZED_CHAT_ID", "").strip()
    if not allowed:
        return True  # Sem restricao = todos autorizados
    try:
        return chat_id == int(allowed)
    except ValueError:
        return False


def _listar_agentes() -> str:
    """Texto para /start com lista de agentes."""
    lines = [
        "**Agentes disponiveis:**",
        "",
    ]
    for key, (label, _) in AGENTES.items():
        lines.append(f"- **{label}**: `/agente {key}`")
    lines.extend([
        "",
        "Envie uma mensagem para consultar o agente atual.",
        "Use `/agente <nome>` para trocar.",
    ])
    return "\n".join(lines)


def _responder_com_agente(chat_id: int, pergunta: str) -> str:
    """Chama o agente ativo e retorna a resposta."""
    agent_key = _get_current_agent(chat_id)
    module = _get_agent_module(agent_key)
    if not module:
        return "Agente nao encontrado. Use /agente marketing|social|analytics"

    # Chunks sao compartilhados entre todos os agentes
    from src.agents.marketing_agent import load_chunks

    chunks = load_chunks()
    if not chunks:
        return "Nenhum chunk carregado. Execute o processor antes de usar o bot."

    try:
        return module.ask_agent(chunks, pergunta, model=TELEGRAM_GROQ_MODEL)
    except Exception as e:
        return f"Erro ao processar: {str(e)[:200]}"


async def cmd_start(update, context):
    """Comando /start - lista agentes."""
    chat_id = update.effective_chat.id
    if not _is_authorized(chat_id):
        await update.message.reply_text("Acesso nao autorizado.")
        return

    agent_key = _get_current_agent(chat_id)
    label = AGENTES.get(agent_key, ("?", ""))[0]
    msg = f"Olá! Agente atual: **{label}**\n\n" + _listar_agentes()
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_agente(update, context):
    """Comando /agente <nome> - troca de agente."""
    chat_id = update.effective_chat.id
    if not _is_authorized(chat_id):
        await update.message.reply_text("Acesso nao autorizado.")
        return

    if not context.args:
        await update.message.reply_text(
            "Uso: /agente marketing | social | analytics"
        )
        return

    nome = " ".join(context.args).strip()
    if _set_agent(chat_id, nome):
        label = AGENTES[nome.lower()][0]
        await update.message.reply_text(f"Agente alterado para: **{label}**", parse_mode="Markdown")
    else:
        await update.message.reply_text(
            f"Agente invalido: '{nome}'. Use: marketing, social ou analytics."
        )


def _get_ajuda_text() -> str:
    """Lista todos os comandos disponiveis."""
    return """*Comandos disponiveis:*

/groq_refresh - Ativa o Selenium para logar na Groq, gerar nova API Key e atualizar o .env

/status - Executa o health_check e envia o relatorio resumido

/agente [nome] - Troca a personalidade do bot (marketing, social, analytics)

/processar - Lista arquivos novos em data/raw e pergunta se quer iniciar o pipeline

/resumo - Pede ao agente de Marketing um resumo do ultimo curso processado

/ajuda - Lista todos os comandos
/start - Lista agentes e agente atual"""


async def cmd_groq_refresh(update, context):
    """Comando /groq_refresh - rotacao de API Key Groq via Selenium."""
    chat_id = update.effective_chat.id
    if not _is_authorized(chat_id):
        await update.message.reply_text("Acesso nao autorizado.")
        return

    await update.message.reply_text(
        "🔄 Iniciando rotação de API Key... Isso pode levar alguns segundos."
    )

    def _run_rotation():
        from src.extractors.web_extractor import run_groq_rotation, ExtractionError
        from src.extractors.validators import ValidationError

        try:
            return run_groq_rotation(headless=True, wait_seconds=60, validate=True)
        except (ExtractionError, ValidationError):
            raise
        except Exception as e:
            raise RuntimeError(str(e)) from e

    try:
        key = await asyncio.to_thread(_run_rotation)
        await update.message.reply_text(
            "✅ Nova API Key da Groq configurada e validada!"
        )
    except Exception as e:
        err_msg = str(e)[:400]
        await update.message.reply_text(f"Erro na rotacao:\n{err_msg}")


async def cmd_ajuda(update, context):
    """Comando /ajuda - lista todos os comandos."""
    chat_id = update.effective_chat.id
    if not _is_authorized(chat_id):
        await update.message.reply_text("Acesso nao autorizado.")
        return

    await update.message.reply_text(_get_ajuda_text(), parse_mode="Markdown")


async def handle_message(update, context):
    """Responde mensagens de texto usando o agente ativo."""
    chat_id = update.effective_chat.id
    if not _is_authorized(chat_id):
        await update.message.reply_text("Acesso nao autorizado.")
        return

    text = (update.message.text or "").strip()
    if not text:
        return

    # Ignora comandos (tratados separadamente)
    if text.startswith("/"):
        return

    await update.message.chat.send_action("typing")
    resposta = _responder_com_agente(chat_id, text)
    await update.message.reply_text(resposta)


def run_bot():
    """Inicia o bot do Telegram."""
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise ValueError(
            "Configure TELEGRAM_BOT_TOKEN no .env. "
            "Obtenha em @BotFather no Telegram."
        )

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("agente", cmd_agente))
    app.add_handler(CommandHandler("groq_refresh", cmd_groq_refresh))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado. Modelo Groq:", TELEGRAM_GROQ_MODEL)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    run_bot()
