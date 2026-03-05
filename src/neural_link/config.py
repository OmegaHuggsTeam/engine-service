"""
Configuracao centralizada do Neural Link.
Le NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD do .env.
Fallback K8s: usa graph.client.get_neo4j_uri() para DNS interno.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Neo4j - URI com fallback K8s via graph.client
from .graph.client import get_neo4j_uri
NEO4J_URI = get_neo4j_uri()
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "neural_link_2024")
NEO4J_DATABASE = os.getenv("NEO4J_DATABASE", "neo4j")

# Timeouts
NEO4J_CONNECTION_TIMEOUT = int(os.getenv("NEO4J_CONNECTION_TIMEOUT", "5"))
NEO4J_MAX_TRANSACTION_RETRY_TIME = int(os.getenv("NEO4J_MAX_TRANSACTION_RETRY_TIME", "30"))


def get_neo4j_config() -> dict:
    """Retorna config do Neo4j como dict."""
    return {
        "uri": NEO4J_URI,
        "user": NEO4J_USER,
        "password": NEO4J_PASSWORD,
        "database": NEO4J_DATABASE,
    }
