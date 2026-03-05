"""
Telegram Command Handler - Long poll para comandos do bot.

Usa TELEGRAM_BOT_TOKEN para long polling. Implementa /explain_workflow [url]
passando URL para SpecialistAgent (GitHub repo ou .json). Envia "Digitando..."
enquanto processa.
"""

import json
import logging
import os
import re
import tempfile
import threading
import time
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_API = "https://api.telegram.org/bot{token}/"
LONG_POLL_TIMEOUT = 30
PENDING_DEPLOY_EXPIRY_SEC = 300  # 5 min
GATEWAY_URL = os.environ.get("GATEWAY_URL", "http://localhost:8766")

# Hugo = dono do lab (dashboard completo). Amigos = apenas busca e ajuda.
def _get_hugo_user_id() -> int:
    val = os.environ.get("AUTHORIZED_CHAT_ID", "") or ""
    try:
        return int(val) if val else 0
    except ValueError:
        return 0


HUGO_USER_ID = _get_hugo_user_id()

# Estado de aprovação para /deploy_internal_n8n
_pending_deployments: dict[int, dict] = {}
_pending_lock = threading.Lock()

# Persistência: amigos que já deram /start (para log de "amigo novo")
_STARTED_USERS_FILE = Path(__file__).resolve().parent.parent.parent.parent / "data" / "telegram_started_users.json"


def _api_url(method: str) -> str:
    return TELEGRAM_API.format(token=TELEGRAM_BOT_TOKEN) + method


def _is_hugo(chat_id: int) -> bool:
    """True se for o Hugo (dono do lab)."""
    return HUGO_USER_ID and chat_id == HUGO_USER_ID


def _get_started_users() -> set[int]:
    """Lê IDs de usuários que já deram /start."""
    try:
        if _STARTED_USERS_FILE.exists():
            data = json.loads(_STARTED_USERS_FILE.read_text(encoding="utf-8"))
            return set(data.get("user_ids", []))
    except Exception:
        pass
    return set()


def _add_started_user(user_id: int) -> bool:
    """Adiciona user_id à lista. Retorna True se era novo."""
    users = _get_started_users()
    if user_id in users:
        return False
    users.add(user_id)
    try:
        _STARTED_USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
        _STARTED_USERS_FILE.write_text(json.dumps({"user_ids": list(users)}, indent=2), encoding="utf-8")
    except Exception:
        pass
    return True


def _notify_hugo_new_friend(user_id: int, first_name: str = "", username: str = "") -> None:
    """Envia DM ao Hugo quando um amigo novo dá /start."""
    if not HUGO_USER_ID or not TELEGRAM_BOT_TOKEN:
        return
    name = first_name or "Sem nome"
    handle = f"@{username}" if username else "(sem @)"
    text = f"🆕 Amigo novo deu /start no Lab-Hub!\n\n👤 {name} {handle}\n🆔 ID: {user_id}"
    _send_message(HUGO_USER_ID, text)
    logger.info("Lab-Hub: amigo novo /start - %s %s (ID: %s)", name, handle, user_id)


def _is_github_repo_url(url: str) -> bool:
    """URL de repositório GitHub (não blob/raw/tree)."""
    url = url.strip().lower()
    if "github.com" not in url or "raw." in url:
        return False
    parsed = urlparse(url)
    if "github.com" not in parsed.netloc.lower():
        return False
    parts = parsed.path.strip("/").split("/")
    if len(parts) < 2 or not parts[0] or not parts[1]:
        return False
    if "blob" in parts or "tree" in parts:
        return False
    return True


def _is_json_url(url: str) -> bool:
    """URL de arquivo .json (raw ou direto)."""
    url = url.strip().lower()
    return url.endswith(".json") or ".json?" in url


def _ingest_url(url: str) -> tuple[bool, str]:
    """
    Ingere URL (GitHub repo ou .json) no ChromaDB.
    Returns (success, message).
    """
    url = url.strip()
    try:
        if _is_github_repo_url(url):
            from src.extractors.github_ingestor import ingest_repository
            stats = ingest_repository(url, save_to_chromadb=True)
            return True, f"Repositório ingerido: {stats['workflows_processed']} workflows, {stats['chunks_saved']} chunks."

        if _is_json_url(url):
            from src.extractors.n8n_extractor import extract_operation_modules, is_n8n_workflow
            from src.utils.vector_db import add_chunks

            with httpx.Client(timeout=30, follow_redirects=True) as client:
                r = client.get(url)
                r.raise_for_status()
                content = r.text

            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                f.write(content)
                tmp_path = f.name

            try:
                if not is_n8n_workflow(tmp_path):
                    return False, "Arquivo não é um workflow n8n válido."

                modules = extract_operation_modules(tmp_path)
                for mod in modules:
                    mod["category"] = "external_template"
                    mod["source_url"] = url
                    mod["source_file"] = f"json/{Path(url).name}"

                add_chunks(modules)
                return True, f"Arquivo ingerido: {len(modules)} módulos."
            finally:
                Path(tmp_path).unlink(missing_ok=True)

        return False, "URL deve ser repositório GitHub ou arquivo .json."
    except Exception as e:
        logger.exception("Erro ao ingerir %s: %s", url, e)
        msg = str(e)
        if _is_cluster_connection_error(e):
            msg += _cluster_error_suggestion()
        return False, msg


def _explain_workflow(url: str) -> str:
    """
    Ingere URL e pede ao SpecialistAgent para explicar os workflows.
    """
    ok, msg = _ingest_url(url)
    if not ok:
        return f"❌ Erro ao ingerir: {msg}"

    try:
        from src.neural_link.agents.specialist_agent import SpecialistAgent
        agent = SpecialistAgent()
        agent.load_knowledge("external_template")
        task = (
            f"Explique os workflows e a estrutura deste recurso: {url}\n\n"
            "Descreva os nodes, conexões e fluxo de dados. "
            "Cite a fonte (source_url) quando disponível."

        )
        return agent.execute(task, chunk_type="external_template")
    except Exception as e:
        logger.exception("SpecialistAgent falhou: %s", e)
        msg = str(e)
        if _is_cluster_connection_error(e):
            msg += _cluster_error_suggestion()
        return f"❌ Erro ao explicar: {msg}"


def _send_message(chat_id: int, text: str, reply_markup: Optional[dict] = None, parse_mode: Optional[str] = None) -> bool:
    """Envia mensagem de texto."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        payload: dict = {"chat_id": chat_id, "text": text[:4096]}
        if reply_markup:
            payload["reply_markup"] = reply_markup
        if parse_mode:
            payload["parse_mode"] = parse_mode
        with httpx.Client(timeout=15) as client:
            r = client.post(_api_url("sendMessage"), json=payload)
            return r.status_code == 200
    except Exception as e:
        logger.warning("sendMessage falhou: %s", e)
        return False


def _send_chat_action(chat_id: int, action: str = "typing") -> bool:
    """Envia ação de chat (ex: typing = 'Digitando...')."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        with httpx.Client(timeout=5) as client:
            r = client.post(
                _api_url("sendChatAction"),
                json={"chat_id": chat_id, "action": action},
            )
            return r.status_code == 200
    except Exception as e:
        logger.debug("sendChatAction falhou: %s", e)
        return False


def _answer_callback_query(callback_query_id: str, text: Optional[str] = None) -> bool:
    """Responde callback de inline keyboard para remover loading."""
    if not TELEGRAM_BOT_TOKEN:
        return False
    try:
        payload: dict = {"callback_query_id": callback_query_id}
        if text:
            payload["text"] = text[:200]
        with httpx.Client(timeout=5) as client:
            r = client.post(_api_url("answerCallbackQuery"), json=payload)
            return r.status_code == 200
    except Exception as e:
        logger.debug("answerCallbackQuery falhou: %s", e)
        return False


def _deploy_workflow_via_gateway(workflow_path: str) -> tuple[bool, str]:
    """
    Envia workflow para o Gateway flows/deploy, que injeta no n8n e ativa.
    workflow_path: path relativo em data/workflows/ (ex: Activecampaign/0057_xxx.json)
    """
    base = Path(__file__).resolve().parent.parent.parent.parent / "data" / "workflows"
    fp = base / workflow_path
    if not fp.exists():
        return False, f"Arquivo não encontrado: {workflow_path}"

    try:
        workflow = json.loads(fp.read_text(encoding="utf-8"))
    except Exception as e:
        return False, f"Erro ao ler JSON: {e}"

    if "nodes" not in workflow:
        return False, "Workflow inválido: falta 'nodes'"

    url = f"{GATEWAY_URL.rstrip('/')}/api/v1/flows/deploy"
    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json={"workflow": workflow})
        data = r.json() if r.headers.get("content-type", "").startswith("application/json") else {}
        if r.status_code in (200, 201) and data.get("success"):
            return True, data.get("message", "Workflow importado e ativado no n8n")
        return False, data.get("message", r.text[:200]) or f"Erro {r.status_code}"
    except Exception as e:
        logger.exception("Deploy via gateway falhou: %s", e)
        msg = str(e)
        if _is_cluster_connection_error(e):
            msg += _cluster_error_suggestion()
        return False, msg


def _get_n8n_url() -> str:
    """URL da API n8n. Fallback K8s: http://n8n:5678/api/v1/workflows (DNS interno)."""
    url = os.environ.get("N8N_API_URL")
    if url:
        return url
    if os.environ.get("KUBERNETES_SERVICE_HOST"):
        return "http://n8n:5678/api/v1/workflows"
    return "http://localhost:5678/api/v1/workflows"


def _is_cluster_connection_error(exc: BaseException) -> bool:
    """Detecta erros de conexão com o cluster (DNS, timeout, recusado)."""
    if isinstance(exc, (ConnectionError, OSError)):
        return True
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, httpx.TimeoutException):
        return True
    err = str(exc).lower()
    return any(
        x in err
        for x in ("connection refused", "connection reset", "dns", "name or service not known", "timed out", "timeout")
    )


def _cluster_error_suggestion() -> str:
    """Mensagem amigável sugerindo reinício do pod."""
    return (
        "\n\n🔄 Se o cluster estiver instável, tente reiniciar o pod:\n"
        "`kubectl delete pod -n bunker -l app=bunker-app`"
    )


def _restart_pod(namespace: str, pod_name: str) -> tuple[bool, str]:
    """Reinicia Pod via kubectl delete (K8s recria automaticamente)."""
    try:
        import subprocess
        result = subprocess.run(
            ["kubectl", "delete", "pod", pod_name, "-n", namespace, "--wait=false"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, f"Pod {pod_name} em {namespace} marcado para reinício."
        return False, result.stderr or result.stdout or "Erro desconhecido"
    except Exception as e:
        return False, str(e)


def _get_pod_logs(namespace: str, pod_name: str, tail: int = 100) -> str:
    """Obtém logs do Pod via KubectlLogAnalyzer."""
    try:
        from src.neural_link.k8s_monitoring.log_analyzer import KubectlLogAnalyzer
        analyzer = KubectlLogAnalyzer(tail_lines=tail)
        return analyzer.get_pod_logs(pod_name, namespace) or ""
    except Exception as e:
        logger.exception("get_pod_logs failed: %s", e)
        return f"Erro ao obter logs: {e}"


def _deploy_to_n8n(workflow: dict) -> tuple[bool, str]:
    """
    Envia workflow para a API do n8n via httpx.
    Usa N8N_API_URL (fallback K8s: n8n:5678) e N8N_API_KEY.
    """
    url = _get_n8n_url()
    api_key = os.environ.get("N8N_API_KEY", "")
    if not api_key:
        return False, "N8N_API_KEY não configurado. Defina no .env"

    headers = {"Content-Type": "application/json", "X-N8N-API-KEY": api_key}
    payload = {
        "name": workflow.get("name", "Imported Workflow"),
        "nodes": workflow.get("nodes", []),
        "connections": workflow.get("connections", {}),
        "settings": workflow.get("settings", {}),
    }

    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json=payload, headers=headers)
        if r.status_code in (200, 201):
            data = r.json()
            wf_id = data.get("id", data.get("data", {}).get("id", "?"))
            return True, f"Workflow importado no n8n (ID: {wf_id})"
        return False, f"n8n retornou {r.status_code}: {r.text[:200]}"
    except Exception as e:
        logger.exception("Deploy n8n falhou: %s", e)
        msg = str(e)
        if _is_cluster_connection_error(e):
            msg += _cluster_error_suggestion()
        return False, msg


def _create_n8n_workflow(objective: str) -> str:
    """
    Cria um workflow n8n usando o ComposerAgent.
    """
    try:
        from src.neural_link.agents.composer_agent import ComposerAgent
        
        agent = ComposerAgent()
        result = agent.compose_workflow(objective)
        
        if "error" in result:
            return f"❌ Erro: {result['error']}\n\n{result.get('suggestion', '')}"
        
        # Salvar workflow em arquivo temporário
        import json
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"workflow_{timestamp}.json"
        output_dir = Path("data/generated_workflows")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / filename
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(result["workflow"], f, indent=2, ensure_ascii=False)
        
        # Formatar resposta
        response_lines = [
            "✅ Workflow criado com sucesso!",
            "",
            f"📁 Arquivo: {output_path}",
            "",
            "📊 Detalhes:",
            f"- Nome: {result['workflow']['name']}",
            f"- Nodes: {len(result['workflow']['nodes'])}",
            f"- Templates usados: {len(result['templates_used'])}",
            "",
            "🔧 Templates utilizados:",
        ]
        
        for i, template in enumerate(result["templates_used"][:3], 1):
            source = template["source"].replace("github/zie619.github.io/", "")
            response_lines.append(
                f"{i}. {template['service']} ({template['node_type']}) - {source}"
            )
        
        if len(result["templates_used"]) > 3:
            response_lines.append(f"... e mais {len(result['templates_used']) - 3}")
        
        response_lines.extend([
            "",
            "💡 Próximos passos:",
            "1. Importe o arquivo JSON no n8n",
            "2. Configure as credenciais necessárias",
            "3. Ative o workflow",
        ])
        
        return "\n".join(response_lines)
        
    except Exception as e:
        logger.exception("ComposerAgent falhou: %s", e)
        msg = str(e)
        if _is_cluster_connection_error(e):
            msg += _cluster_error_suggestion()
        return f"❌ Erro ao criar workflow: {msg}"


WELCOME_MSG = """✨ <b>BEM-VINDO AO LAB-HUB!</b> ✨

Olá! Você acaba de ganhar acesso ao laboratório pessoal do Hugo.

Imagine este bot como um <b>Assistente de Elite</b> que tem as chaves de uma biblioteca com milhares de automações prontas para facilitar a sua vida. O Hugo construiu este "Bunker Digital" para ser um lugar de descoberta e eficiência.

🛠️ <b>O que você pode fazer por aqui?</b>

🔍 <b>Explorar Ideias:</b> Use o comando /find_workflow para buscar qualquer automação (Ex: "Airtable", "Telegram", "Planilhas"). O bot vai encontrar o melhor caminho para você.
🧠 <b>Consultar o Cérebro:</b> Acesse o conhecimento indexado do Hugo para entender como cada fluxo funciona.
⚡ <b>Ver a Mágica:</b> Nosso cluster está monitorando tudo em tempo real para garantir que sua experiência seja ultra-rápida.

💡 <b>Comandos para começar:</b>
/find_workflow [termo] - Encontre automações incríveis.
/help - Veja tudo o que este bot pode fazer por você.

<i>"A tecnologia serve para nos dar tempo para <s>o que realmente importa.</s> METER O PAU NA MÁQUINA"</i>

Sinta-se em casa. O que vamos descobrir hoje? 🔋🏛️"""


def _handle_command(chat_id: int, command: str, args: str, message: Optional[dict] = None) -> None:
    """Processa comando e envia resposta."""
    is_hugo = _is_hugo(chat_id)

    if command == "start":
        _send_message(chat_id, WELCOME_MSG, parse_mode="HTML")
        if not is_hugo and message:
            from_user = message.get("from") or {}
            user_id = from_user.get("id") or chat_id
            first_name = from_user.get("first_name", "")
            username = from_user.get("username", "")
            if _add_started_user(user_id):
                _notify_hugo_new_friend(user_id, first_name, username)
        return

    if command == "help":
        if is_hugo:
            _send_message(
                chat_id,
                "Comandos disponíveis (dashboard completo):\n"
                "/find_workflow <termo> - Busca workflows (ex: /find_workflow airtable)\n"
                "/explain_workflow <url> - Explica workflows de repo GitHub ou arquivo .json\n"
                "/create_n8n <objetivo> - Cria workflow n8n a partir de um objetivo\n"
                "/deploy_internal_n8n [path] - Envia workflow aprovado para n8n local\n"
                "/cluster_status - Status de saúde do cluster",
            )
        else:
            _send_message(
                chat_id,
                "Comandos disponíveis:\n\n"
                "/find_workflow <termo> - Busque automações (ex: /find_workflow telegram)\n"
                "/explain_workflow <url> - Entenda como um workflow funciona (URL GitHub ou .json)\n"
                "/help - Veja esta mensagem",
            )
        return

    # Comandos restritos ao Hugo
    if not is_hugo and command in ("cluster_status", "deploy_internal_n8n", "create_n8n"):
        _send_message(chat_id, "Este comando é restrito ao administrador. Use /find_workflow ou /help.")
        return

    if command == "explain_workflow":
        url = args.strip()
        if not url:
            _send_message(chat_id, "Uso: /explain_workflow <url>\n\nEx: /explain_workflow https://github.com/zie619/zie619.github.io")
            return

        _send_chat_action(chat_id, "typing")
        response = _explain_workflow(url)
        _send_message(chat_id, response)

    elif command == "create_n8n":
        objective = args.strip()
        if not objective:
            _send_message(
                chat_id,
                "Uso: /create_n8n <objetivo>\n\n"
                "Ex: /create_n8n Criar workflow que monitora webhook e envia notificação no Telegram"
            )
            return

        _send_chat_action(chat_id, "typing")
        response = _create_n8n_workflow(objective)
        _send_message(chat_id, response)

    elif command == "find_workflow":
        term = args.strip()
        if not term:
            _send_message(
                chat_id,
                "Uso: /find_workflow <termo>\n\nEx: /find_workflow airtable\nEx: /find_workflow telegram webhook",
            )
            return

        _send_chat_action(chat_id, "typing")
        try:
            project_root = Path(__file__).resolve().parent.parent.parent.parent
            if str(project_root) not in __import__("sys").path:
                __import__("sys").path.insert(0, str(project_root))
            from tools.workflow_searcher import search_workflows

            results = search_workflows(term, top_k=3)
        except Exception as e:
            logger.exception("find_workflow falhou: %s", e)
            _send_message(chat_id, f"❌ Erro na busca: {e}\n\nExecute `python tools/workflow_searcher.py index` para indexar.")
            return

        if not results:
            _send_message(chat_id, f"Nenhum workflow encontrado para: {term}")
            return

        lines = [f"🔍 Resultados para '{term}':\n"]
        keyboard_rows = []
        for i, r in enumerate(results, 1):
            name = (r.get("name") or r.get("path", ""))[:50]
            path = r.get("path", "")
            lines.append(f"{i}. {name}\n   `{path}`")
            # Callback: deploy_wf:path (path deve caber em 64 bytes)
            cb = f"deploy_wf:{path}"[:64]
            keyboard_rows.append([{"text": f"🚀 Deploy no n8n ({i})", "callback_data": cb}])

        text = "\n".join(lines)
        keyboard = {"inline_keyboard": keyboard_rows}
        _send_message(chat_id, text, reply_markup=keyboard)

    elif command == "cluster_status":
        _send_chat_action(chat_id, "typing")
        try:
            from tools.cluster_health import collect_cluster_health, format_telegram
            health = collect_cluster_health()
            response = format_telegram(health)
        except Exception as e:
            logger.exception("cluster_health falhou: %s", e)
            response = f"Erro ao verificar cluster: {e}"
        _send_message(chat_id, response)

    elif command == "deploy_internal_n8n":
        path_arg = args.strip() or "data/generated_workflows/bot_evolution.json"
        workflow_path = Path(path_arg)
        if not workflow_path.is_absolute():
            workflow_path = Path(__file__).resolve().parent.parent.parent.parent / path_arg

        if not workflow_path.exists():
            _send_message(chat_id, f"❌ Arquivo não encontrado: {workflow_path}")
            return

        try:
            workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
        except Exception as e:
            _send_message(chat_id, f"❌ Erro ao ler JSON: {e}")
            return

        if "nodes" not in workflow or "connections" not in workflow:
            _send_message(chat_id, "❌ JSON inválido: falta 'nodes' ou 'connections'")
            return

        summary = (
            f"📋 Workflow: {workflow.get('name', 'Sem nome')}\n"
            f"📦 Nodes: {len(workflow.get('nodes', []))}\n"
            f"📁 Arquivo: {workflow_path.name}\n\n"
            "Aprovar e enviar para n8n local? Responda 'sim' ou 'aprovar' para confirmar."
        )

        with _pending_lock:
            _pending_deployments[chat_id] = {
                "workflow": workflow,
                "path": str(workflow_path),
                "ts": time.time(),
            }

        keyboard = {
            "inline_keyboard": [
                [{"text": "✅ Aprovar e Deploy", "callback_data": "deploy_approve"}],
                [{"text": "❌ Cancelar", "callback_data": "deploy_cancel"}],
            ]
        }
        _send_message(chat_id, summary, reply_markup=keyboard)

    else:
        if is_hugo:
            _send_message(
                chat_id,
                "Comandos disponíveis:\n"
                "/find_workflow <termo> - Busca workflows\n"
                "/explain_workflow <url> - Explica workflows\n"
                "/create_n8n <objetivo> - Cria workflow\n"
                "/deploy_internal_n8n [path] - Deploy para n8n\n"
                "/cluster_status - Status do cluster\n"
                "/help - Ajuda",
            )
        else:
            _send_message(
                chat_id,
                "Use /find_workflow para buscar automações ou /help para ver os comandos.",
            )


def _process_pending_approval(chat_id: int, text: str) -> bool:
    """Processa aprovação pendente. Retorna True se tratou."""
    t = text.lower()
    with _pending_lock:
        pending = _pending_deployments.get(chat_id)
        if not pending:
            return False
        if time.time() - pending["ts"] > PENDING_DEPLOY_EXPIRY_SEC:
            del _pending_deployments[chat_id]
            _send_message(chat_id, "⏱ Aprovação expirada. Use /deploy_internal_n8n novamente.")
            return True
        if t in ("não", "nao", "cancelar", "cancel", "n"):
            del _pending_deployments[chat_id]
            _send_message(chat_id, "Deploy cancelado.")
            return True
        if t not in ("sim", "aprovar", "approve", "s", "y"):
            return False
        workflow = pending["workflow"]
        del _pending_deployments[chat_id]

    _send_chat_action(chat_id, "typing")
    ok, msg = _deploy_to_n8n(workflow)
    _send_message(chat_id, f"✅ {msg}" if ok else f"❌ {msg}")
    return True


def _process_callback_query(update: dict) -> None:
    """Processa callback de inline keyboard (Aprovar/Cancelar, Pod failure)."""
    cb = update.get("callback_query")
    if not cb:
        return
    cb_id = cb.get("id")
    chat_id = cb.get("message", {}).get("chat", {}).get("id")
    data = cb.get("data", "")
    if not chat_id:
        return

    _answer_callback_query(cb_id or "")

    # Pod failure callbacks: pr:namespace:pod_name, approve_fix:namespace:pod_name, pl:namespace:pod_name, pod_dismiss, dismiss_fix
    if data.startswith("pr:") or data.startswith("approve_fix:"):
        prefix, rest = data.split(":", 1)
        parts = rest.split(":", 1)
        if len(parts) >= 2:
            namespace, pod_name = parts[0], parts[1]
            _send_chat_action(chat_id, "typing")
            ok, msg = _restart_pod(namespace, pod_name)
            _send_message(chat_id, f"✅ {msg}" if ok else f"❌ {msg}")
        return
    if data.startswith("pl:"):
        parts = data.split(":", 2)
        if len(parts) >= 3:
            namespace, pod_name = parts[1], parts[2]
            _send_chat_action(chat_id, "typing")
            logs = _get_pod_logs(namespace, pod_name)
            _send_message(chat_id, logs[:4096] if logs else "Logs não disponíveis.")
        return
    if data in ("pod_dismiss", "dismiss_fix"):
        _send_message(chat_id, "Alerta dispensado.")
        return

    if data.startswith("deploy_wf:"):
        rel_path = data[len("deploy_wf:") :].strip()
        if not rel_path:
            _send_message(chat_id, "❌ Path do workflow inválido.")
            return
        _send_chat_action(chat_id, "typing")
        ok, msg = _deploy_workflow_via_gateway(rel_path)
        _send_message(chat_id, f"✅ {msg}" if ok else f"❌ {msg}")
        return

    if data == "deploy_approve":
        with _pending_lock:
            pending = _pending_deployments.get(chat_id)
            if not pending:
                _send_message(chat_id, "⏱ Aprovação expirada.")
                return
            workflow = pending["workflow"]
            del _pending_deployments[chat_id]

        _send_chat_action(chat_id, "typing")
        ok, msg = _deploy_to_n8n(workflow)
        _send_message(chat_id, f"✅ {msg}" if ok else f"❌ {msg}")
    elif data == "deploy_cancel":
        with _pending_lock:
            _pending_deployments.pop(chat_id, None)
        _send_message(chat_id, "Deploy cancelado.")


def _process_update(update: dict) -> None:
    """Processa um update do Telegram."""
    # Callback query (inline buttons)
    if update.get("callback_query"):
        _process_callback_query(update)
        return

    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return

    chat_id = msg.get("chat", {}).get("id")
    text = (msg.get("text") or "").strip()
    if not chat_id:
        return

    # Aprovação pendente (sim/aprovar)
    if text and _process_pending_approval(chat_id, text):
        return

    if not text:
        return

    if text.startswith("/"):
        parts = text.split(maxsplit=1)
        command = parts[0].lstrip("/").lower()
        args = parts[1] if len(parts) > 1 else ""
        _handle_command(chat_id, command, args, message=msg)


def _get_updates(offset: int) -> tuple[list[dict], int]:
    """Long poll: obtém updates. Retorna (updates, next_offset)."""
    if not TELEGRAM_BOT_TOKEN:
        return [], offset

    try:
        with httpx.Client(timeout=LONG_POLL_TIMEOUT + 5) as client:
            r = client.get(
                _api_url("getUpdates"),
                params={"offset": offset, "timeout": LONG_POLL_TIMEOUT},
            )
            r.raise_for_status()
            data = r.json()
    except Exception as e:
        logger.warning("getUpdates falhou: %s", e)
        return [], offset

    updates = data.get("result", [])
    next_offset = offset
    if updates:
        next_offset = max(u["update_id"] for u in updates) + 1

    return updates, next_offset


class TelegramCommandHandler:
    """
    Handler de comandos Telegram com long polling.

    Usa TELEGRAM_BOT_TOKEN. Inicia thread em background para processar
    updates. Comandos: /explain_workflow [url].
    """

    def __init__(self, bot_token: Optional[str] = None):
        self._token = (bot_token or TELEGRAM_BOT_TOKEN).strip()
        self._offset = 0
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def _poll_loop(self) -> None:
        """Loop de long polling."""
        global TELEGRAM_BOT_TOKEN
        TELEGRAM_BOT_TOKEN = self._token

        while self._running:
            updates, self._offset = _get_updates(self._offset)
            for u in updates:
                try:
                    _process_update(u)
                except Exception as e:
                    logger.exception("Erro ao processar update: %s", e)

    def start(self) -> None:
        """Inicia thread de long polling."""
        if not self._token:
            logger.warning("TELEGRAM_BOT_TOKEN não configurado, handler não iniciado")
            return

        self._running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        logger.info("TelegramCommandHandler iniciado (long poll)")

    def stop(self) -> None:
        """Para o long polling."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("TelegramCommandHandler parado")


def main():
    """CLI: python -m src.neural_link.telemetry.telegram_command_handler"""
    import signal
    import sys

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    if not TELEGRAM_BOT_TOKEN:
        print("Configure TELEGRAM_BOT_TOKEN no ambiente.")
        sys.exit(1)

    handler = TelegramCommandHandler()
    handler.start()

    def _shutdown(sig=None, frame=None):
        handler.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    print("Telegram bot rodando. Ctrl+C para parar.")
    if handler._thread:
        handler._thread.join()


if __name__ == "__main__":
    main()
