"""
Injeta o workflow K8s Pod Failure no n8n via API.

Uso (após n8n estar rodando):
  N8N_API_URL=http://localhost:5678 N8N_API_KEY=xxx python tools/inject_n8n_workflow.py

Ou no cluster:
  N8N_API_URL=http://n8n:5678 N8N_API_KEY=xxx python tools/inject_n8n_workflow.py
"""

import json
import os
import sys
from pathlib import Path

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_PATH = PROJECT_ROOT / "data" / "workflows" / "k8s_pod_failure_feedback.json"


def main() -> int:
    api_url = os.environ.get("N8N_API_URL", "http://localhost:5678").rstrip("/")
    api_key = os.environ.get("N8N_API_KEY", "")
    if not api_key:
        print("N8N_API_KEY não configurado. Defina no ambiente.")
        return 1

    if not WORKFLOW_PATH.exists():
        print(f"Workflow não encontrado: {WORKFLOW_PATH}")
        return 1

    workflow = json.loads(WORKFLOW_PATH.read_text(encoding="utf-8"))
    # Remove credenciais do import (será configurado no n8n)
    for node in workflow.get("nodes", []):
        node.pop("credentials", None)

    headers = {"Content-Type": "application/json", "X-N8N-API-KEY": api_key}
    url = f"{api_url}/api/v1/workflows"

    try:
        with httpx.Client(timeout=30) as client:
            r = client.post(url, json=workflow, headers=headers)
            if r.status_code not in (200, 201):
                print(f"Erro {r.status_code}: {r.text[:300]}")
                return 1

            data = r.json()
            wf_id = data.get("id", data.get("data", {}).get("id", "?"))
            print(f"Workflow injetado. ID: {wf_id}")

            # Ativar workflow para o webhook funcionar (PATCH com active: true)
            activate_url = f"{url}/{wf_id}"
            r2 = client.patch(activate_url, json={"active": True}, headers=headers)
            if r2.status_code in (200, 201):
                print("Workflow ativado.")
            else:
                print(f"Aviso: ativação retornou {r2.status_code}. Ative manualmente no n8n.")

            print(f"Webhook: {api_url}/webhook/k8s-pod-failure")
            return 0
    except Exception as e:
        print(f"Falha: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
