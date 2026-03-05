"""
Ponte de Voz - FastAPI server que recebe webhooks da Alexa/IFTTT.
Rede segura: Tailscale. Porta 8765. value1 = comando de voz.
"""

import json
import os
import subprocess
import sys
from pathlib import Path

from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse

HUB_ROOT = Path(__file__).resolve().parent.parent
COMMANDS_FILE = HUB_ROOT / "commands.json"

# Carrega .env
try:
    from dotenv import load_dotenv
    for p in [HUB_ROOT.parent / ".env", HUB_ROOT / "config" / "credentials.env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass

IFTTT_KEY = os.environ.get("IFTTT_WEBHOOK_KEY") or os.environ.get("IFTTT_KEY") or "haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6"


def get_tailscale_ip() -> str | None:
    """Obtem IP do Tailscale (100.x.y.z) para configurar no IFTTT."""
    try:
        r = subprocess.run(["tailscale", "ip", "-4"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except Exception:
        pass
    return None

EVENT_MAP = {
    "modo_leitura": {"action": "GROQ_RAW", "raw_text": "Modo Leitura"},
    "ativar_modo_leitura": {"action": "GROQ_RAW", "raw_text": "Modo Leitura"},
    "ligar_quarto_hugo": {"action": "GROQ_RAW", "raw_text": "Acender luz"},
    "desligar_quarto_hugo": {"action": "GROQ_RAW", "raw_text": "Apagar luz"},
    "luz_branca": {"action": "LUZ", "mode": "branco"},
    "hoza_modo_sexo": {"action": "MODO_SEXO"},
}

app = FastAPI(title="Kiro Cortex - Webhook Bridge", version="1.0")

# Register Neural Link routes (optional - graceful if not available)
try:
    from src.neural_link.api.webhook_integration import register_neural_link_routes
    register_neural_link_routes(app)
except (ImportError, Exception):
    pass  # Neural Link not installed - webhook continues normally


def _enqueue(cmd: dict):
    COMMANDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if COMMANDS_FILE.exists():
        with open(COMMANDS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"queue": [], "processed": []}
    data["queue"].append(cmd)
    with open(COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


@app.get("/")
def health():
    """Health check."""
    return {"status": "ok", "service": "kiro-cortex-webhook"}


@app.post("/webhook")
async def webhook(
    request: Request,
    x_webhook_key: str | None = Header(None, alias="X-Webhook-Key"),
):
    """
    Recebe webhooks do IFTTT.
    Autenticacao: header X-Webhook-Key ou query ?key=IFTTT_KEY
    Body: JSON com event, value1, value2, value3 (texto do comando)
    """
    # Validar chave (header ou query)
    key = x_webhook_key or request.query_params.get("key")
    if not key or key != IFTTT_KEY:
        raise HTTPException(status_code=401, detail="Webhook key invalida ou ausente")

    body = await request.body()
    data = {}
    if body:
        try:
            data = json.loads(body.decode("utf-8", errors="ignore"))
        except json.JSONDecodeError:
            pass

    event = (data.get("event") or data.get("trigger") or "").strip().lower()
    # value1 = comando de voz da Alexa (prioridade)
    raw_text = (data.get("value1") or data.get("value2") or data.get("value3") or "").strip()

    if not event:
        event = request.query_params.get("event", "modo_leitura").lower().replace(" ", "_")

    # Comando complexo: raw_text vai direto pro Groq (ex: "Prepare o quarto e feche o VS Code")
    cmd = EVENT_MAP.get(event, {"action": "GROQ_RAW", "raw_text": raw_text or "Modo Leitura"})
    cmd = {**cmd, "raw_text": raw_text or cmd.get("raw_text", ""), "event": event}

    _enqueue(cmd)
    return JSONResponse({"ok": True, "event": event, "queued": True})


# Compatibilidade: endpoint legado por path
@app.post("/{event:path}")
async def webhook_by_path(
    event: str,
    request: Request,
    x_webhook_key: str | None = Header(None, alias="X-Webhook-Key"),
):
    """POST /modo_leitura, /ligar_quarto_hugo, etc."""
    key = x_webhook_key or request.query_params.get("key")
    if not key or key != IFTTT_KEY:
        raise HTTPException(status_code=401, detail="Webhook key invalida ou ausente")

    ev = event.strip("/").lower().replace(" ", "_")
    cmd = EVENT_MAP.get(ev, {"action": "GROQ_RAW", "raw_text": ev.replace("_", " ")})
    cmd = {**cmd, "raw_text": cmd.get("raw_text", ""), "event": ev}
    _enqueue(cmd)
    return JSONResponse({"ok": True, "event": ev, "queued": True})


def run_server(port: int = 8765):
    import uvicorn
    host = "0.0.0.0"  # Escuta em todas as interfaces (incl. Tailscale)
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8765
    ts_ip = get_tailscale_ip()
    print("=" * 50)
    print("Kiro Cortex - Hub Hibrido (Groq + Tailscale + IFTTT)")
    print("=" * 50)
    print(f"Webhook: http://0.0.0.0:{port}")
    if ts_ip:
        print(f"IP Tailscale (IFTTT): http://{ts_ip}:{port}/webhook")
        print(f"URL completa: http://{ts_ip}:{port}/webhook?key=SUA_IFTTT_WEBHOOK_KEY")
    else:
        print("Tailscale: execute 'tailscale ip -4' para obter o IP")
    print("Regra: NUNCA exponha portas no roteador. Use apenas Tailscale.")
    print("=" * 50, flush=True)
    run_server(port)
