"""
GraphManager - Wrapper thread-safe do driver Neo4j.
Singleton com connection pooling e retry automatico.
"""

import logging
import threading
from contextlib import contextmanager
from typing import Any

from ..config import get_neo4j_config, NEO4J_CONNECTION_TIMEOUT, NEO4J_MAX_TRANSACTION_RETRY_TIME

logger = logging.getLogger(__name__)

_instance = None
_instance_lock = threading.Lock()


class GraphManager:
    """
    Wrapper thread-safe para o driver Neo4j.
    Usa singleton pattern para compartilhar o connection pool.
    """

    def __init__(self, uri: str, user: str, password: str, database: str = "neo4j"):
        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(
            uri,
            auth=(user, password),
            connection_timeout=NEO4J_CONNECTION_TIMEOUT,
            max_transaction_retry_time=NEO4J_MAX_TRANSACTION_RETRY_TIME,
        )
        self._database = database
        self._lock = threading.Lock()
        logger.info(f"GraphManager connected to {uri}")

    @classmethod
    def from_env(cls) -> "GraphManager":
        """Cria GraphManager a partir das variaveis de ambiente."""
        global _instance
        with _instance_lock:
            if _instance is None:
                cfg = get_neo4j_config()
                _instance = cls(
                    uri=cfg["uri"],
                    user=cfg["user"],
                    password=cfg["password"],
                    database=cfg["database"],
                )
            return _instance

    @classmethod
    def reset_instance(cls):
        """Reset singleton (para testes)."""
        global _instance
        with _instance_lock:
            if _instance is not None:
                _instance.close()
                _instance = None

    def close(self):
        """Fecha o driver."""
        if self._driver:
            self._driver.close()
            logger.info("GraphManager connection closed")

    def verify_connectivity(self) -> bool:
        """Verifica se o Neo4j esta acessivel."""
        try:
            self._driver.verify_connectivity()
            return True
        except Exception as e:
            logger.error(f"Neo4j connectivity check failed: {e}")
            return False

    @contextmanager
    def session(self):
        """Context manager para sessao Neo4j."""
        session = self._driver.session(database=self._database)
        try:
            yield session
        finally:
            session.close()

    def execute_read(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Executa query de leitura e retorna lista de dicts."""
        with self.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]

    def execute_write(self, query: str, parameters: dict | None = None) -> list[dict]:
        """Executa query de escrita e retorna lista de dicts."""
        with self.session() as session:
            result = session.run(query, parameters or {})
            records = [record.data() for record in result]
            return records

    def execute_write_batch(self, queries: list[tuple[str, dict]]) -> int:
        """
        Executa multiplas queries de escrita em uma transacao.
        queries: lista de (cypher_query, parameters)
        Retorna numero de queries executadas.
        """
        with self.session() as session:
            with session.begin_transaction() as tx:
                count = 0
                for query, params in queries:
                    tx.run(query, params)
                    count += 1
                tx.commit()
                return count

    def run_cypher(self, query: str, parameters: dict | None = None) -> Any:
        """Executa query generico (para schema creation, etc.)."""
        with self.session() as session:
            return session.run(query, parameters or {})
