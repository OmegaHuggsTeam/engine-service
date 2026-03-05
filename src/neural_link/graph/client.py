"""
Client Neo4j - conexão com fallback DNS K8s (neo4j:7687).
Aceita nomes de serviço do Kubernetes (DNS interno CoreDNS) como fallback.
"""

import os


def _is_kubernetes() -> bool:
    """Detecta execução dentro de um cluster Kubernetes (K3s)."""
    return bool(os.getenv("KUBERNETES_SERVICE_HOST"))


def get_neo4j_uri() -> str:
    """
    URI do Neo4j.
    Fallback K8s: bolt://neo4j:7687 (DNS interno do cluster).
    """
    uri = os.getenv("NEO4J_URI")
    if uri:
        return uri
    if _is_kubernetes():
        return "bolt://neo4j:7687"
    return "bolt://localhost:7687"
