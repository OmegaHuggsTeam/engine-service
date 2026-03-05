"""
Gemini-Cortex - Orquestrador com motor de decisao Gemini 3 Flash.
Recebe comando do Webhook, carrega RAG (/knowledge), decide acao via Gemini.
Retorna JSON estruturado e executa: ifttt_client.ps1 ou AHK.
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

# Carrega .env antes de qualquer uso
try:
    from dotenv import load_dotenv
    for p in [HUB_ROOT.parent / ".env", HUB_ROOT / ".env", HUB_ROOT / "config" / "credentials.env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

COMMANDS_FILE = HUB_ROOT / "commands.json"
BRAIN_LOG = HUB_ROOT / "logs" / "brain.log"
OPERATOR_LOG = HUB_ROOT / "logs" / "operator.log"
HARDWARE_DIR = HUB_ROOT / "hardware"
KNOWLEDGE_DIR = HUB_ROOT / "knowledge"
CONFIG_DIR = HUB_ROOT / "config"

import google.generativeai as genai


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
    """Log do raciocinio do Gemini em brain.log."""
    BRAIN_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(BRAIN_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[brain] {msg}")


def operator_log(msg: str):
    """Log geral do operador."""
    OPERATOR_LOG.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(OPERATOR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def run_ps1(script: str, *args) -> bool:
    """Executa script PowerShell."""
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
    """Executa script AHK."""
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


def ask_gemini(comando: str, contexto_rag: str) -> dict:
    """
    Envia comando + RAG ao Gemini. Retorna JSON estruturado.
    action: "ifttt" | "ahk" | "both" | "none"
    ifttt_arg: on|off|leitura|branco|vermelho_piscante
    ahk_script: focus_layout.ahk|alert.ahk|...
    reasoning: o que o Gemini pensou
    """
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        brain_log("ERRO: GEMINI_API_KEY nao definida no .env")
        return {"action": "none", "reasoning": "API key ausente", "warn": True}

    genai.configure(api_key=api_key)
    model_name = os.environ.get("GEMINI_MODEL", "gemini-1.5-flash")
    model = genai.GenerativeModel(model_name)

    system = """Voce e o nucleo de decisao de um sistema de automacao domestica.
Comandos de voz (Alexa) chegam via webhook. Voce decide qual script executar.

ACOES DISPONIVEIS:
- ifttt: controle de luzes (on, off, leitura, branco, vermelho_piscante)
- ahk: scripts de interface (focus_layout.ahk, alert.ahk)

REGRAS:
1. Seja CONCISO e ECONOMICO. Resposta apenas em JSON valido.
2. Se NAO souber o que fazer, retorne action="none" e reasoning com aviso. NAO invente comandos.
3. Retorne SEMPRE um JSON valido neste formato exato:
{"action": "ifttt"|"ahk"|"both"|"none", "ifttt_arg": "leitura", "ahk_script": "focus_layout.ahk", "reasoning": "explicacao curta"}

Exemplos:
- "Modo leitura" -> action=both, ifttt_arg=leitura, ahk_script=focus_layout.ahk
- "Acender luz" -> action=ifttt, ifttt_arg=on
- "Apagar" -> action=ifttt, ifttt_arg=off
- Comando desconhecido -> action=none, reasoning="Comando X nao reconhecido"
"""

    prompt = f"""{system}

CONTEXTO (manuais e preferencias):
{contexto_rag or "(nenhum arquivo em /knowledge)"}

O usuario disse: "{comando}"

Responda APENAS com o JSON, sem markdown ou texto extra."""

    try:
        text = ""
        for attempt in range(3):
            try:
                response = model.generate_content(prompt)
                text = response.text.strip()
                break
            except Exception as e:
                if "429" in str(e) and attempt < 2:
                    brain_log(f"429 rate limit, retry em 2s (attempt {attempt+1}/3)")
                    time.sleep(2)
                    continue
                raise
        if not text:
            return {"action": "none", "reasoning": "Resposta vazia do Gemini", "warn": True}
        # Remove possivel bloco markdown
        if text.startswith("```"):
            text = re.sub(r"^```\w*\n?", "", text)
            text = re.sub(r"\n?```$", "", text)
        data = json.loads(text)
        brain_log(f"Gemini respondeu: {json.dumps(data, ensure_ascii=False)}")
        return data
    except json.JSONDecodeError as e:
        brain_log(f"ERRO: Gemini nao retornou JSON valido: {text[:200] if text else 'vazio'}")
        return {"action": "none", "reasoning": f"Parse error: {e}", "warn": True}
    except Exception as e:
        brain_log(f"ERRO Gemini: {e}")
        return {"action": "none", "reasoning": str(e), "warn": True}


def execute_decision(decision: dict) -> bool:
    """Executa a decisao do Gemini (ifttt e/ou ahk)."""
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
    """
    Maquina de estados: comando -> RAG -> Gemini -> JSON -> execucao.
    """
    brain_log(f"Comando recebido: {comando}")
    contexto = load_rag_context()
    brain_log(f"RAG: {len(contexto)} chars de contexto")
    decision = ask_gemini(comando, contexto)
    brain_log(f"Decisao: {decision.get('action')} | reasoning: {decision.get('reasoning', '')[:80]}")
    execute_decision(decision)
    return decision


def process_queue():
    """Processa fila de commands.json."""
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
    """Loop principal."""
    brain_log("Gemini-Cortex iniciado. Monitorando commands.json...")
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
        # Teste direto: python gemini_operator.py test "Modo leitura"
        comando = sys.argv[2] if len(sys.argv) > 2 else "Modo leitura"
        process_command(comando)
    else:
        watch_loop()
