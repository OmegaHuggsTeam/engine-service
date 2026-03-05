"""
Boot Inicial do Sovereign AI Command Center.

Orquestra: docker compose up -> Gateway -> System Check.
Uso: python tools/boot_sovereign.py [--compose-only | --gateway-only | --check-only]
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run_cmd(cmd: list[str], cwd: Path | None = None) -> int:
    """Executa comando e retorna exit code."""
    print(f"  $ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=cwd or PROJECT_ROOT)
    return r.returncode


def wait_for_health(services: list[str], timeout: int = 120) -> bool:
    """Aguarda serviços ficarem healthy."""
    for _ in range(timeout // 5):
        r = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            time.sleep(5)
            continue
        # Parse simples - verifica se containers estão running
        if "healthy" in r.stdout.lower() or "running" in r.stdout.lower():
            return True
        time.sleep(5)
    return False


def main():
    parser = argparse.ArgumentParser(description="Boot do Sovereign AI Command Center")
    parser.add_argument("--compose-only", action="store_true", help="Apenas docker compose up")
    parser.add_argument("--gateway-only", action="store_true", help="Apenas iniciar Gateway (porta 8766)")
    parser.add_argument("--check-only", action="store_true", help="Apenas system_check")
    parser.add_argument("--skip-ws", action="store_true", help="Pular verificação WebSocket no check")
    args = parser.parse_args()

    if not args.check_only and not args.gateway_only:
        print("🐳 Subindo cluster (docker compose up -d)...")
        if run_cmd(["docker", "compose", "up", "-d"]) != 0:
            print("❌ docker compose falhou")
            return 1
        print("⏳ Aguardando serviços (30s)...")
        time.sleep(30)

        print("📋 Status dos containers:")
        run_cmd(["docker", "compose", "ps"])

    if args.compose_only:
        print("✅ Compose-only: cluster subiu. Use --gateway-only para iniciar o Gateway.")
        return 0

    if not args.check_only:
        print("\n🚀 Iniciando Gateway na porta 8766...")
        print("   (O Gateway está no docker-compose como serviço 'gateway'.)")
        print("   Se rodando localmente: python -m src.neural_link.api.sovereign_gateway")
        # Se gateway está no compose, já está rodando
        # Se não, usuário pode rodar manualmente
        time.sleep(2)

    if not args.gateway_only:
        print("\n🔍 Verificação de saúde (system_check)...")
        cmd = [sys.executable, str(PROJECT_ROOT / "tools" / "system_check.py"), "--gateway-url", "http://localhost:8766"]
        if args.skip_ws:
            cmd.append("--skip-ws")
        exit_code = subprocess.call(cmd, cwd=PROJECT_ROOT)
        if exit_code != 0:
            return 1

    print("\n✅ Boot completo. Sovereign AI Command Center operacional.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
