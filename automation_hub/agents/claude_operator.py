"""
Orquestrador - Monitora commands.json e executa comandos.
Fase 3: Decide AHK (mouse/janelas) vs Bash/PS1 (luzes) e usa RAG para config.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))
from agents.rag_engine import search_knowledge, get_error_context
COMMANDS_FILE = HUB_ROOT / "commands.json"
LOG_FILE = HUB_ROOT / "logs" / "operator.log"
HARDWARE_DIR = HUB_ROOT / "hardware"
CONFIG_DIR = HUB_ROOT / "config"


def load_credentials():
    """Carrega credenciais do config."""
    env_file = CONFIG_DIR / "credentials.env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ[key.strip()] = val.strip()


def log(msg: str):
    """Escreve no log."""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def run_ps1(script: str, *args):
    """Executa script PowerShell."""
    script_path = HARDWARE_DIR / script
    if not script_path.exists():
        log(f"ERRO: Script nao encontrado: {script_path}")
        return False
    cmd = ["powershell", "-ExecutionPolicy", "Bypass", "-File", str(script_path)] + list(args)
    log(f"Executando: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HARDWARE_DIR))
        if result.stdout:
            log(result.stdout.strip())
        if result.stderr:
            log(f"stderr: {result.stderr.strip()}")
        return result.returncode == 0
    except Exception as e:
        log(f"ERRO: {e}")
        return False


def run_ahk(script: str):
    """Executa script AHK (AutoHotkey)."""
    script_path = HARDWARE_DIR / script
    if not script_path.exists():
        log(f"ERRO: Script AHK nao encontrado: {script_path}")
        return False
    # Tenta Autohotkey.exe ou Ahk2Exe compilado
    ahk_exe = "AutoHotkey.exe"
    cmd = [ahk_exe, str(script_path)]
    log(f"Executando AHK: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(HARDWARE_DIR))
        return result.returncode == 0
    except FileNotFoundError:
        # Fallback: se AutoHotkey nao estiver no PATH, tenta caminho comum
        for path in [
            r"C:\Program Files\AutoHotkey\v2\AutoHotkey64.exe",
            r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
        ]:
            if os.path.exists(path):
                result = subprocess.run([path, str(script_path)], capture_output=True, text=True, cwd=str(HARDWARE_DIR))
                return result.returncode == 0
        log("ERRO: AutoHotkey nao encontrado. Instale em https://www.autohotkey.com/")
        return False


def execute_error_alert(reason: str = ""):
    """
    Contexto de erro: luz vermelho piscante + alert.ahk.
    RAG em preferencias_gerais.txt define o comportamento.
    """
    cfg = get_error_context()
    log(f"ERRO: {reason}. Executando alerta: luz={cfg['luz_erro']}, ahk={cfg['alert_ahk']}")
    run_ps1("ifttt_client.ps1", cfg["luz_erro"])
    run_ahk(cfg["alert_ahk"])


def run_app(path: str) -> bool:
    """Abre app (luz = IFTTT/curl, interface = AHK)."""
    try:
        subprocess.Popen([path], shell=True, cwd=str(HUB_ROOT))
        return True
    except Exception as e:
        log(f"ERRO ao abrir app {path}: {e}")
        return False


def execute_modo_leitura(cmd: dict | None = None):
    """
    Fluxo completo do Modo Leitura.
    RAG: busca em /knowledge qual luz e apps abrir.
    Decisao: Luz -> PS1 (IFTTT), Layout/Apps -> AHK ou subprocess.
    """
    raw_text = (cmd or {}).get("raw_text", "Modo Leitura")
    cfg = search_knowledge(raw_text)
    log(f"MODO_LEITURA: RAG config={cfg}")

    # Luz: sempre PS1/IFTTT (lampada fisica)
    # RAG pode retornar "modo_leitura" -> mapear para "leitura"
    luz_raw = cfg.get("luz", "leitura")
    luz_mode = "leitura" if "leitura" in luz_raw.lower() else luz_raw
    ok1 = run_ps1("ifttt_client.ps1", luz_mode)

    # Apps: subprocess (abrir PDF, etc)
    apps = cfg.get("apps", [])
    for app in apps:
        if Path(app).exists():
            run_app(app)
        else:
            log(f"App nao encontrado: {app}")

    # Layout: AHK (mouse/janelas)
    layout = cfg.get("layout", "focus_layout.ahk")
    ok2 = run_ahk(layout)

    # Silenciar notificacoes
    ok3 = run_ps1("silence_notifications.ps1") if cfg.get("silenciar_notificacoes", True) else True

    if not ok1:
        execute_error_alert("IFTTT/luz falhou no Modo Leitura")
    log(f"MODO_LEITURA: Luzes={ok1}, Layout={ok2}, Silencio={ok3}")
    return ok1 or ok2 or ok3


def execute_command(cmd: dict):
    """
    Executa comando da fila.
    Decisao: LUZ -> PS1 (IFTTT). AHK -> mouse/janelas. MODO_* -> RAG + ambos.
    Em caso de falha: luz vermelho piscante + alert.ahk (preferencias_gerais.txt).
    """
    try:
        action = cmd.get("action", "").upper()
        if action == "MODO_LEITURA":
            return execute_modo_leitura(cmd)
        if action == "LUZ":
            mode = cmd.get("mode", "on")
            ok = run_ps1("ifttt_client.ps1", mode)
            if not ok:
                execute_error_alert("IFTTT/luz falhou")
            return ok
        if action == "AHK":
            script = cmd.get("script", "focus_layout.ahk")
            return run_ahk(script)
        log(f"Comando desconhecido: {action}")
        return False
    except Exception as e:
        log(f"ERRO ao executar comando: {e}")
        execute_error_alert(str(e))
        return False


def process_queue():
    """Processa a fila de comandos."""
    if not COMMANDS_FILE.exists():
        return
    try:
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        log(f"ERRO ao ler commands.json: {e}")
        return
    queue = data.get("queue", [])
    if not queue:
        return
    processed = []
    for cmd in queue:
        execute_command(cmd)
        processed.append(cmd)
    data["queue"] = []
    data["processed"] = data.get("processed", []) + processed
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    log(f"Processados {len(processed)} comandos.")


def watch_loop(interval: float = 1.0):
    """Loop principal - monitora commands.json."""
    load_credentials()
    log("Orquestrador iniciado. Monitorando commands.json...")
    while True:
        try:
            process_queue()
        except KeyboardInterrupt:
            log("Encerrado pelo usuario.")
            break
        except Exception as e:
            log(f"ERRO: {e}")
        time.sleep(interval)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "once":
        load_credentials()
        process_queue()
    else:
        watch_loop()
