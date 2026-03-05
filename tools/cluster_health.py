"""
Cluster Health Check - Status dos servicos K8s para o Telegram Bot.

Verifica ChromaDB, Neo4j, Evidence, n8n e Tailscale.
Chamado pelo comando /cluster_status do bot.

Uso standalone: python tools/cluster_health.py
"""

import json
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

OK = "[OK]"
FAIL = "[FAIL]"
SKIP = "[SKIP]"

_TIMEOUT = 5  # segundos para HTTP checks


def _http_check(url: str) -> tuple[str, str]:
    """GET request com timeout. Retorna (status, detalhe)."""
    try:
        import httpx

        r = httpx.get(url, timeout=_TIMEOUT)
        if r.status_code == 200:
            return OK, f"{r.status_code} ({r.elapsed.total_seconds():.1f}s)"
        return FAIL, f"HTTP {r.status_code}"
    except ImportError:
        # Fallback sem httpx
        import urllib.request

        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
                return OK, f"{resp.status} ({resp.reason})"
        except Exception as e:
            return FAIL, str(e)[:80]
    except Exception as e:
        err = str(e)[:80]
        if any(x in err.lower() for x in (
            "connection refused", "connect error", "timed out", "timeout",
            "winerror 10061", "name or service not known", "no route to host",
        )):
            return SKIP, f"Inacessivel: {err}"
        return FAIL, err


def check_chromadb() -> tuple[str, str]:
    """ChromaDB heartbeat via HTTP."""
    host = os.getenv("CHROMA_HOST", "localhost")
    port = os.getenv("CHROMA_PORT", "8000")
    url = f"http://{host}:{port}/api/v2/heartbeat"
    return _http_check(url)


def check_neo4j() -> tuple[str, str]:
    """Neo4j browser HTTP interface."""
    uri = os.getenv("NEO4J_URI", "")
    if uri:
        parsed = urlparse(uri)
        host = parsed.hostname or "localhost"
    else:
        host = os.getenv("NEO4J_HOST", "localhost")
    url = f"http://{host}:7474"
    return _http_check(url)


def check_evidence() -> tuple[str, str]:
    """Evidence server /health endpoint."""
    host = os.getenv("EVIDENCE_SERVER_HOST", "localhost")
    port = os.getenv("EVIDENCE_SERVER_PORT", "5000")
    url = f"http://{host}:{port}/health"
    return _http_check(url)


def check_n8n() -> tuple[str, str]:
    """n8n /healthz endpoint."""
    api_url = os.getenv("N8N_API_URL", "")
    if api_url:
        parsed = urlparse(api_url)
        host = parsed.hostname or "localhost"
        port = parsed.port or 5678
    else:
        host = os.getenv("N8N_HOST", "localhost")
        port = 5678
    url = f"http://{host}:{port}/healthz"
    return _http_check(url)


def _check_tailscale_host_proxy() -> tuple[str, str] | None:
    """
    Verifica Host Proxy via Service tailscale-host (K8s sem tailscale CLI).
    O Service aponta para o IP do host Windows na rede Tailscale.
    Se o host responde em :8766, o Dashboard funciona via mesh.
    """
    if not os.getenv("KUBERNETES_SERVICE_HOST"):
        return None
    host = os.getenv("TAILSCALE_HOST_SVC", "tailscale-host")
    port = int(os.getenv("TAILSCALE_HOST_PORT", "8766"))
    url = f"http://{host}:{port}/api/v1/cluster/health"
    status, detail = _http_check(url)
    if status == OK:
        return OK, "Host Proxy (OK)"
    if status == SKIP:
        return SKIP, "Host Proxy inacessivel"
    return status, f"Host Proxy: {detail}"


def _check_tailscale_proxy() -> tuple[str, str] | None:
    """Fallback: verifica mesh via host Tailscale (TAILSCALE_HOST, sem K8s Service)."""
    ts_host = os.getenv("TAILSCALE_HOST", "")
    if not ts_host:
        return None
    try:
        import httpx
        r = httpx.get(f"http://{ts_host}:8766/api/v1/cluster/health", timeout=3)
        if r.status_code == 200:
            return OK, f"Host Proxy (via {ts_host})"
    except ImportError:
        pass
    except Exception:
        pass
    import socket
    try:
        sock = socket.create_connection((ts_host, 8766), timeout=3)
        sock.close()
        return OK, f"MESH ACTIVE (Proxy via {ts_host})"
    except Exception:
        pass
    return SKIP, f"TAILSCALE_HOST={ts_host} (inacessivel)"


def check_tailscale() -> tuple[str, str]:
    """
    Tailscale: em K8s (sem CLI no host), verifica HTTP em tailscale-host.
    Caso contrario, usa CLI tailscale status.
    """
    # K8s sem tailscale CLI: prioriza HTTP no Service tailscale-host (Host Proxy)
    if os.getenv("KUBERNETES_SERVICE_HOST"):
        proxy = _check_tailscale_host_proxy()
        if proxy and proxy[0] == OK:
            return proxy
        if proxy:
            return proxy  # SKIP ou FAIL do host proxy

    # CLI disponivel: verifica peers bunker-*
    try:
        result = subprocess.run(
            ["tailscale", "status", "--json"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            stderr = result.stderr.strip()[:80]
            if "not running" in stderr.lower() or "not connected" in stderr.lower():
                return SKIP, "Tailscale nao conectado"
            return FAIL, stderr or "Exit code != 0"

        data = json.loads(result.stdout)
        peers = data.get("Peer", {})
        bunker_peers = []
        for _key, peer in peers.items():
            hostname = peer.get("HostName", "")
            if hostname.startswith("bunker-") or hostname == "n8n-bunker":
                online = peer.get("Online", False)
                bunker_peers.append(f"{hostname}:{'ON' if online else 'OFF'}")

        if not bunker_peers:
            return SKIP, "Nenhum peer bunker-* encontrado"
        return OK, ", ".join(bunker_peers)

    except FileNotFoundError:
        # CLI ausente — tenta TAILSCALE_HOST (hostname direto)
        proxy = _check_tailscale_proxy()
        if proxy:
            return proxy
        return SKIP, "tailscale CLI nao encontrado"
    except subprocess.TimeoutExpired:
        return FAIL, "Timeout (10s)"
    except json.JSONDecodeError:
        return FAIL, "Resposta JSON invalida"
    except Exception as e:
        return FAIL, str(e)[:80]


def collect_cluster_health() -> dict:
    """Retorna dict com status de cada servico + resumo."""
    checks = [
        ("ChromaDB", check_chromadb),
        ("Neo4j", check_neo4j),
        ("Evidence", check_evidence),
        ("n8n", check_n8n),
        ("Tailscale", check_tailscale),
    ]

    services = {}
    for name, check_func in checks:
        try:
            status, detail = check_func()
        except Exception as e:
            status, detail = FAIL, str(e)[:80]
        services[name] = {"status": status, "detail": detail}

    ok_count = sum(1 for s in services.values() if s["status"] == OK)
    fail_count = sum(1 for s in services.values() if s["status"] == FAIL)
    skip_count = sum(1 for s in services.values() if s["status"] == SKIP)

    return {
        "timestamp": datetime.now().isoformat(),
        "services": services,
        "summary": {
            "total": len(services),
            "ok": ok_count,
            "fail": fail_count,
            "skip": skip_count,
        },
    }


def format_telegram(health: dict) -> str:
    """Formata para Telegram Markdown."""
    lines = [
        "*Cluster Health Check*",
        f"`{health['timestamp'][:19]}`",
        "",
        "| Servico | Status | Detalhe |",
        "|---------|--------|---------|",
    ]

    for name, info in health["services"].items():
        lines.append(f"| {name} | {info['status']} | {info['detail']} |")

    s = health["summary"]
    lines.extend([
        "",
        f"*Resumo:* {s['ok']}/{s['total']} OK",
    ])

    if s["fail"] > 0:
        lines.append(f"*FAIL:* {s['fail']} servico(s) com falha")
    if s["skip"] > 0:
        lines.append(f"*SKIP:* {s['skip']} servico(s) inacessivel(is)")

    return "\n".join(lines)


def main():
    """CLI: python tools/cluster_health.py"""
    # Carrega .env se disponivel
    project_root = Path(__file__).parent.parent
    try:
        from dotenv import load_dotenv

        load_dotenv(project_root / ".env")
    except ImportError:
        pass

    health = collect_cluster_health()
    print(format_telegram(health))

    return 0 if health["summary"]["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
