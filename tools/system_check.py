"""
System Check - Verificação de saúde do Sovereign AI Command Center.

Ping em todas as 12 rotas do Gateway e valida Neo4j retornando o grafo de serviços.
Uso: python tools/system_check.py [--gateway-url URL]
"""

import argparse
import json
import sys
from pathlib import Path

# Carrega .env e PYTHONPATH
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))
try:
    from dotenv import load_dotenv
    load_dotenv(_project_root / ".env")
except ImportError:
    pass

import httpx

DEFAULT_GATEWAY = "http://localhost:8766"
TIMEOUT = 15
CLUSTER_HEALTH_TIMEOUT = 30  # cluster/health faz múltiplos checks

# 9 rotas REST (WebSockets são validadas por connect/disconnect separado)
# (method, path, name, kwargs) - kwargs pode incluir timeout_override
REST_ROUTES = [
    ("GET", "/api/v1/agents", "list_agents", {}),
    ("GET", "/api/v1/agents/test-agent/history", "agent_history", {}),
    ("POST", "/api/v1/tasks", "submit_task", {"json": {"query": "ping"}}),
    ("GET", "/api/v1/tasks/recent", "recent_tasks", {}),
    ("GET", "/api/v1/rag/search", "rag_search", {"params": {"q": "n8n"}}),
    ("GET", "/api/v1/graph/explore", "graph_explore", {"params": {"center": "test", "depth": 1}}),
    ("GET", "/api/v1/graph/services", "graph_services", {}),
    ("GET", "/api/v1/cluster/health", "cluster_health", {"timeout": 30}),
    ("POST", "/api/v1/flows/compose", "compose_flow", {"json": {"objective": "test"}}),
]

WS_ROUTES = [
    "/api/v1/ws/telemetry",
    "/api/v1/ws/agent-health",
    "/api/v1/ws/flow-events",
]


def check_rest_route(base_url: str, method: str, path: str, name: str, kwargs: dict) -> tuple[bool, str]:
    """Verifica uma rota REST. Retorna (ok, mensagem)."""
    url = f"{base_url.rstrip('/')}{path}"
    req_kwargs = {k: v for k, v in kwargs.items() if k != "timeout"}
    timeout = kwargs.get("timeout", TIMEOUT)
    try:
        with httpx.Client(timeout=timeout) as client:
            if method == "GET":
                r = client.get(url, **req_kwargs)
            else:
                r = client.post(url, **req_kwargs)
        if r.status_code < 500:
            return True, f"HTTP {r.status_code}"
        return False, f"HTTP {r.status_code}: {r.text[:100]}"
    except Exception as e:
        return False, str(e)[:80]


def check_ws_route(base_url: str, path: str) -> tuple[bool, str]:
    """Verifica WebSocket (connect + disconnect)."""
    try:
        import asyncio
        import websockets
    except ImportError:
        return False, "websockets não instalado (pip install websockets)"

    ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://").rstrip("/") + path

    async def _connect():
        async with websockets.connect(ws_url, close_timeout=2) as ws:
            await asyncio.sleep(0.3)
            return True

    try:
        asyncio.run(_connect())
        return True, "WS OK"
    except Exception as e:
        return False, str(e)[:80]


def validate_neo4j_graph(base_url: str) -> tuple[bool, str]:
    """Valida se Neo4j retorna o grafo de serviços corretamente."""
    url = f"{base_url.rstrip('/')}/api/v1/graph/services"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(url)
        if r.status_code != 200:
            return False, f"HTTP {r.status_code}"
        data = r.json()
        if not isinstance(data, list):
            return False, "Resposta não é lista"
        # Grafo pode estar vazio (sem Services ainda) - isso é válido
        return True, f"{len(data)} serviços no grafo"
    except Exception as e:
        return False, str(e)[:80]


def run_checks(base_url: str, skip_ws: bool = False) -> dict:
    """Executa todas as verificações."""
    results = {"rest": [], "ws": [], "neo4j": {}, "summary": {"ok": 0, "fail": 0}}

    for method, path, name, kwargs in REST_ROUTES:
        ok, msg = check_rest_route(base_url, method, path, name, kwargs)
        results["rest"].append({"route": f"{method} {path}", "ok": ok, "detail": msg})
        if ok:
            results["summary"]["ok"] += 1
        else:
            results["summary"]["fail"] += 1

    if not skip_ws:
        for path in WS_ROUTES:
            ok, msg = check_ws_route(base_url, path)
            results["ws"].append({"route": path, "ok": ok, "detail": msg})
            if ok:
                results["summary"]["ok"] += 1
            else:
                results["summary"]["fail"] += 1

    neo4j_ok, neo4j_msg = validate_neo4j_graph(base_url)
    results["neo4j"] = {"ok": neo4j_ok, "detail": neo4j_msg}
    if neo4j_ok:
        results["summary"]["ok"] += 1
    else:
        results["summary"]["fail"] += 1

    return results


def main():
    parser = argparse.ArgumentParser(description="System check do Sovereign AI Command Center")
    parser.add_argument("--gateway-url", default=DEFAULT_GATEWAY, help=f"URL do Gateway (default: {DEFAULT_GATEWAY})")
    parser.add_argument("--skip-ws", action="store_true", help="Pular verificação de WebSockets")
    parser.add_argument("--json", action="store_true", help="Saída em JSON")
    args = parser.parse_args()

    print(f"[CHECK] Verificando Gateway em {args.gateway_url}...")
    results = run_checks(args.gateway_url, skip_ws=args.skip_ws)

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0 if results["summary"]["fail"] == 0 else 1

    # Saída legível
    print("\n--- Rotas REST ---")
    for r in results["rest"]:
        icon = "[OK]" if r["ok"] else "[FAIL]"
        print(f"  {icon} {r['route']}: {r['detail']}")

    if results["ws"]:
        print("\n--- WebSockets ---")
        for r in results["ws"]:
            icon = "[OK]" if r["ok"] else "[FAIL]"
            print(f"  {icon} {r['route']}: {r['detail']}")

    print("\n--- Neo4j Grafo de Serviços ---")
    n = results["neo4j"]
    icon = "[OK]" if n["ok"] else "[FAIL]"
    print(f"  {icon} {n['detail']}")

    s = results["summary"]
    print(f"\nResumo: {s['ok']} OK, {s['fail']} FALHA")
    return 0 if s["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
