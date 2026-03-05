"""
Groq Turbo - Orquestrador com Llama 3 70B (velocidade da luz).
Usa groq + RAG. Mesma estrutura do gemini_operator.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

try:
    from dotenv import load_dotenv
    for p in [HUB_ROOT.parent / ".env", HUB_ROOT / ".env", HUB_ROOT / "config" / "credentials.env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

from groq import Groq

COMMANDS_FILE = HUB_ROOT / "commands.json"
BRAIN_LOG = HUB_ROOT / "logs" / "brain.log"
OPERATOR_LOG = HUB_ROOT / "logs" / "operator.log"
HARDWARE_DIR = HUB_ROOT / "hardware"
KNOWLEDGE_DIR = HUB_ROOT / "knowledge"


def load_rag_context() -> str:
    """Carrega TODOS os arquivos de /knowledge como contexto."""
    if not KNOWLEDGE_DIR.exists():
        return ""
    parts = []
    for path in sorted(KNOWLEDGE_DIR.glob("**/*.txt")):
        try:
            content = path.read_text(encoding="utf-8", errors="ignore")
            parts.append(f"--- {path.name} ---\n{content}")
        except Exception:
            continue
    return "\n\n".join(parts) if parts else ""


def brain_log(msg: str):
    BRAIN_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(BRAIN_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[brain] {msg}")


def operator_log(msg: str):
    OPERATOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(OPERATOR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def run_ps1(script: str, *args) -> bool:
    script_path = HARDWARE_DIR / script
    if not script_path.exists():
        operator_log(f"ERRO: Script nao encontrado: {script_path}")
        return False
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)] + list(args)
    operator_log(f"Executando: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HARDWARE_DIR))
        return result.returncode == 0
    except Exception as e:
        operator_log(f"ERRO: {e}")
        return False


def run_ahk(script: str) -> bool:
    script_path = HARDWARE_DIR / script
    if not script_path.exists():
        operator_log(f"ERRO: AHK nao encontrado: {script_path}")
        return False
    for exe in ["AutoHotkey.exe", "AutoHotkey64.exe"]:
        try:
            result = subprocess.run([exe, str(script_path)], capture_output=True, text=True, cwd=str(HARDWARE_DIR))
            return result.returncode == 0
        except FileNotFoundError:
            continue
    for path in [r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe", r"C:\Program Files\AutoHotkey\AutoHotkey.exe"]:
        if os.path.exists(path):
            result = subprocess.run([path, str(script_path)], capture_output=True, text=True, cwd=str(HARDWARE_DIR))
            return result.returncode == 0
    operator_log("ERRO: AutoHotkey nao encontrado")
    return False


# Definicao das funcoes para o Groq (tool use / function calling)
GROQ_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "ifttt_luz",
            "description": "Controla as luzes do quarto via IFTTT. Argumentos: on, off, leitura, branco, vermelho_piscante",
            "parameters": {
                "type": "object",
                "properties": {
                    "argumento": {
                        "type": "string",
                        "enum": ["on", "off", "leitura", "branco", "vermelho_piscante"],
                        "description": "Modo da luz",
                    }
                },
                "required": ["argumento"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ahk_script",
            "description": "Executa script AHK (janelas, alertas). Ex: focus_layout.ahk, alert.ahk, close_vscode.ahk",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {
                        "type": "string",
                        "description": "Nome do script .ahk em hardware/",
                    }
                },
                "required": ["script"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "fechar_app",
            "description": "Fecha um aplicativo pelo nome. Ex: Code (VS Code), notepad, chrome",
            "parameters": {
                "type": "object",
                "properties": {
                    "nome": {
                        "type": "string",
                        "description": "Nome do processo: Code, notepad, chrome, etc",
                    }
                },
                "required": ["nome"],
            },
        },
    },
]


def executar_tool(name: str, args: dict) -> str:
    """Executa a funcao chamada pelo Groq e retorna resultado."""
    if name == "ifttt_luz":
        arg = args.get("argumento", "on")
        ok = run_ps1("ifttt_client.ps1", arg)
        if not ok:
            run_ps1("ifttt_client.ps1", "vermelho_piscante")
            run_ahk("alert.ahk")
        return json.dumps({"ok": ok, "luz": arg})
    if name == "ahk_script":
        script = args.get("script", "focus_layout.ahk")
        ok = run_ahk(script)
        return json.dumps({"ok": ok, "script": script})
    if name == "fechar_app":
        nome = args.get("nome", "")
        ok = _fechar_app(nome)
        return json.dumps({"ok": ok, "app": nome})
    return json.dumps({"ok": False, "erro": f"Funcao desconhecida: {name}"})


def _fechar_app(nome: str) -> bool:
    """Fecha app pelo nome do processo (ex: Code=VS Code, notepad, chrome)."""
    if not nome:
        return False
    exe = f"{nome}.exe" if not nome.lower().endswith(".exe") else nome
    try:
        r = subprocess.run(["taskkill", "/IM", exe, "/F"], capture_output=True, timeout=5)
        return r.returncode == 0
    except Exception as e:
        operator_log(f"Erro ao fechar {nome}: {e}")
        return False


def pensar_na_velocidade_da_luz(comando_usuario: str, contexto_rag: str) -> dict:
    """
    Cerebro do Bunker do Hugo. Groq + Function Calling.
    O modelo INVOCA as funcoes ifttt_luz e ahk_script diretamente.
    """
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        brain_log("ERRO: GROQ_API_KEY nao definida no .env")
        return {"action": "none", "reasoning": "API key ausente", "warn": True}

    client = Groq(api_key=api_key)
    model = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

    system = f"""Voce e o cerebro do Bunker do Hugo. Use este contexto RAG: {contexto_rag or "(nenhum)"}

Voce tem acesso a funcoes (pode chamar VARIAS simultaneamente para comandos complexos):
- ifttt_luz: luzes (on, off, leitura, branco, vermelho_piscante)
- ahk_script: focus_layout.ahk, alert.ahk, close_vscode.ahk
- fechar_app: fecha app pelo nome (Code=VS Code, notepad, chrome)

Ex: "Prepare o quarto para leitura e feche o VS Code" -> ifttt_luz(leitura) + ahk_script(focus_layout.ahk) + fechar_app(Code).
Seja conciso. NAO invente comandos."""

    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": comando_usuario},
    ]

    try:
        completion = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=GROQ_TOOLS,
            tool_choice="auto",
        )
        msg = completion.choices[0].message
        tool_calls = getattr(msg, "tool_calls", None) or []

        if not tool_calls:
            content = getattr(msg, "content", "") or ""
            brain_log(f"Groq nao chamou funcoes: {content[:100] if content else '(sem resposta)'}")
            return {"action": "none", "reasoning": content or "Comando nao reconhecido", "warn": True}

        result = {"action": "executed", "calls": []}
        for tc in tool_calls:
            fn = getattr(tc, "function", tc)
            name = getattr(fn, "name", "?")
            raw_args = getattr(fn, "arguments", "{}") or "{}"
            try:
                args = json.loads(raw_args) if isinstance(raw_args, str) else (raw_args or {})
            except json.JSONDecodeError:
                args = {}
            brain_log(f"Groq chamou: {name}({args})")
            result["calls"].append({"name": name, "args": args})
            output = executar_tool(name, args)
            brain_log(f"Resultado {name}: {output}")

        return result
    except Exception as e:
        brain_log(f"ERRO Groq: {e}")
        return {"action": "none", "reasoning": str(e), "warn": True}


def execute_decision(decision: dict) -> bool:
    """Fallback para decisao em JSON (compatibilidade). Com function calling, a execucao ja acontece em executar_tool."""
    if decision.get("action") == "executed":
        return True
    action = (decision.get("action") or "none").lower()
    ok = True
    if action in ("ifttt", "both"):
        arg = decision.get("ifttt_arg", "on")
        if not run_ps1("ifttt_client.ps1", arg):
            ok = False
            run_ps1("ifttt_client.ps1", "vermelho_piscante")
            run_ahk("alert.ahk")
    if action in ("ahk", "both"):
        script = decision.get("ahk_script", "focus_layout.ahk")
        if not run_ahk(script):
            ok = False
    if action == "none" and decision.get("warn"):
        brain_log(f"AVISO (nao executado): {decision.get('reasoning', '')}")
    return ok


def process_command(comando: str) -> dict:
    brain_log(f"Comando recebido: {comando}")
    contexto = load_rag_context()
    brain_log(f"RAG: {len(contexto)} chars de contexto")
    decision = pensar_na_velocidade_da_luz(comando, contexto)
    if decision.get("action") != "executed":
        brain_log(f"Decisao: {decision.get('action')} | reasoning: {str(decision.get('reasoning', ''))[:80]}")
        execute_decision(decision)
    return decision


def process_queue():
    if not COMMANDS_FILE.exists():
        return
    try:
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        operator_log(f"ERRO commands.json: {e}")
        return
    queue = data.get("queue", [])
    if not queue:
        return
    processed = []
    for cmd in queue:
        raw = cmd.get("raw_text") or cmd.get("event", "").replace("_", " ")
        if not raw:
            raw = str(cmd.get("action", ""))
        process_command(raw)
        processed.append(cmd)
    data["queue"] = []
    data["processed"] = data.get("processed", []) + processed
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    operator_log(f"Processados {len(processed)} comandos.")


def watch_loop(interval: float = 1.0):
    brain_log("Groq Turbo iniciado. Monitorando commands.json...")
    while True:
        try:
            process_queue()
        except KeyboardInterrupt:
            brain_log("Encerrado pelo usuario.")
            break
        except Exception as e:
            brain_log(f"ERRO: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        process_queue()
    elif len(sys.argv) > 1 and sys.argv[1] == "test":
        comando = sys.argv[2] if len(sys.argv) > 2 else "Modo leitura"
        process_command(comando)
    else:
        watch_loop()
