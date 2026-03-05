"""
Teste de integracao de voz - Simula comando chegando do IFTTT.
Uso: python tests/test_voice.py "Modo leitura"
     python tests/test_voice.py "Prepare o quarto para leitura e feche o VS Code"
"""

import json
import os
import subprocess
import sys
from pathlib import Path

# Adiciona automation_hub ao path
HUB_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HUB_ROOT))

try:
    from dotenv import load_dotenv
    for p in [HUB_ROOT.parent / ".env", HUB_ROOT / "config" / "credentials.env"]:
        if p.exists():
            load_dotenv(p)
            break
except ImportError:
    pass


def simular_ifttt(comando: str, webhook_url: str = "http://localhost:8765/webhook") -> dict:
    """
    Simula o IFTTT enviando um POST para o webhook.
    value1 = comando de voz da Alexa.
    """
    import urllib.request
    key = os.environ.get("IFTTT_WEBHOOK_KEY") or os.environ.get("IFTTT_KEY") or "haB9jt-wmjlsy-k77AandNNbDvE0Y2PeWp3zIxZmEX6"
    url = f"{webhook_url}?key={key}"
    body = json.dumps({"event": "voice_command", "value1": comando}).encode("utf-8")
    try:
        req = urllib.request.Request(url, data=body, method="POST", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"ok": resp.status == 200}
    except urllib.error.URLError as e:
        return {"ok": False, "erro": str(e.reason)}
    except Exception as e:
        return {"ok": False, "erro": str(e)}


def enfileirar_direto(comando: str):
    """Enfileira comando direto em commands.json (sem webhook)."""
    commands_file = HUB_ROOT / "commands.json"
    if commands_file.exists():
        with open(commands_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        data = {"queue": [], "processed": []}
    data["queue"].append({"action": "GROQ_RAW", "raw_text": comando, "event": "test"})
    with open(commands_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"Enfileirado: {comando}")


def main():
    comando = sys.argv[1] if len(sys.argv) > 1 else "Modo leitura"
    print(f"Teste de voz: '{comando}'")
    print("-" * 40)

    # Tenta webhook primeiro (se estiver rodando)
    result = simular_ifttt(comando)
    if result.get("ok"):
        print("Webhook: OK - comando enviado")
        print("Aguarde o groq_operator processar a fila.")
    else:
        print("Webhook indisponivel - enfileirando direto")
        enfileirar_direto(comando)
        print("Execute: python agents/groq_operator.py once")

    print("-" * 40)


if __name__ == "__main__":
    main()
