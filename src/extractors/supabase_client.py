"""
Cliente Supabase para gestão de API Keys.

CRUD operations e teste de conectividade para chaves armazenadas.
"""

import os
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.extractors.validators import validate_api_key, ValidationError
from src.utils.logger import get_logger
from src.utils.retry import retry

# Carrega .env
PROJECT_ROOT = Path(__file__).parent.parent.parent
load_dotenv(PROJECT_ROOT / ".env")

logger = get_logger(__name__)


class SupabaseClientError(Exception):
    """Erro do cliente Supabase."""
    pass


class SupabaseAPIKeyManager:
    """Gerenciador de API Keys no Supabase."""

    def __init__(
        self,
        supabase_url: str | None = None,
        supabase_key: str | None = None,
        table_name: str = "api_keys",
    ):
        """
        Inicializa cliente Supabase.

        Args:
            supabase_url: URL do projeto Supabase
            supabase_key: Chave de API do Supabase
            table_name: Nome da tabela (padrão: api_keys)
        """
        self.supabase_url = supabase_url or os.getenv("SUPABASE_URL")
        self.supabase_key = supabase_key or os.getenv("SUPABASE_KEY")
        self.table_name = table_name

        if not self.supabase_url or not self.supabase_key:
            raise SupabaseClientError(
                "Configure SUPABASE_URL e SUPABASE_KEY no .env"
            )

        try:
            from supabase import create_client, Client

            self.client: Client = create_client(self.supabase_url, self.supabase_key)
            logger.info("Cliente Supabase inicializado com sucesso")
        except ImportError:
            raise SupabaseClientError(
                "Instale o cliente Supabase: pip install supabase"
            )
        except Exception as e:
            raise SupabaseClientError(f"Erro ao conectar ao Supabase: {e}") from e

    @retry(max_attempts=2, backoff_factor=2)
    def create_key(
        self,
        platform: str,
        key_value: str,
        validate: bool = True,
        metadata: dict[str, Any] | None = None,
    ) -> dict:
        """
        Cria nova API key no Supabase.

        Args:
            platform: Plataforma (groq, openai, etc.)
            key_value: Valor da API key
            validate: Se True, valida antes de salvar
            metadata: Metadata adicional (JSON)

        Returns:
            Registro criado

        Raises:
            ValidationError: Se validação falhar
            SupabaseClientError: Se erro ao salvar
        """
        logger.info(f"Criando API key para plataforma '{platform}'...")

        # Validar chave antes de salvar
        validation_result = None
        if validate:
            try:
                validation_result = validate_api_key(key_value, platform)
            except ValidationError as e:
                logger.error(f"Validação falhou: {e}")
                raise

        # Extrair prefixo da chave (primeiros 10 caracteres)
        key_prefix = key_value[:10] if len(key_value) >= 10 else key_value

        # Preparar dados
        now = datetime.utcnow().isoformat()
        data = {
            "platform": platform,
            "key_value": key_value,
            "key_prefix": key_prefix,
            "created_at": now,
            "validated_at": now if validate else None,
            "last_tested_at": now if validate else None,
            "status": "active",
            "metadata": {
                **(metadata or {}),
                "validation": validation_result,
            },
        }

        try:
            response = self.client.table(self.table_name).insert(data).execute()

            if not response.data:
                raise SupabaseClientError("Nenhum dado retornado após insert")

            logger.info(f"API key criada com sucesso: {response.data[0]['id']}")
            return response.data[0]

        except Exception as e:
            error_msg = str(e).lower()
            if "duplicate" in error_msg or "unique" in error_msg:
                raise SupabaseClientError(
                    f"Chave já existe para plataforma '{platform}' com prefixo '{key_prefix}'"
                ) from e
            raise SupabaseClientError(f"Erro ao criar chave: {e}") from e

    @retry(max_attempts=2, backoff_factor=2)
    def get_keys(
        self,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[dict]:
        """
        Busca API keys no Supabase.

        Args:
            platform: Filtrar por plataforma (opcional)
            status: Filtrar por status (active, expired, revoked)

        Returns:
            Lista de registros
        """
        logger.info(f"Buscando chaves (platform={platform}, status={status})...")

        try:
            query = self.client.table(self.table_name).select("*")

            if platform:
                query = query.eq("platform", platform)
            if status:
                query = query.eq("status", status)

            response = query.execute()
            logger.info(f"Encontradas {len(response.data)} chaves")
            return response.data

        except Exception as e:
            raise SupabaseClientError(f"Erro ao buscar chaves: {e}") from e

    @retry(max_attempts=2, backoff_factor=2)
    def update_key(self, key_id: str, updates: dict[str, Any]) -> dict:
        """
        Atualiza API key no Supabase.

        Args:
            key_id: UUID da chave
            updates: Campos a atualizar

        Returns:
            Registro atualizado
        """
        logger.info(f"Atualizando chave {key_id}...")

        try:
            response = (
                self.client.table(self.table_name)
                .update(updates)
                .eq("id", key_id)
                .execute()
            )

            if not response.data:
                raise SupabaseClientError(f"Chave não encontrada: {key_id}")

            logger.info(f"Chave atualizada: {key_id}")
            return response.data[0]

        except Exception as e:
            raise SupabaseClientError(f"Erro ao atualizar chave: {e}") from e

    @retry(max_attempts=2, backoff_factor=2)
    def delete_key(self, key_id: str, soft: bool = True) -> dict:
        """
        Deleta API key do Supabase.

        Args:
            key_id: UUID da chave
            soft: Se True, apenas marca como revoked (padrão)

        Returns:
            Registro deletado/atualizado
        """
        logger.info(f"Deletando chave {key_id} (soft={soft})...")

        if soft:
            # Soft delete: atualizar status para revoked
            return self.update_key(key_id, {"status": "revoked"})
        else:
            # Hard delete: remover do banco
            try:
                response = (
                    self.client.table(self.table_name)
                    .delete()
                    .eq("id", key_id)
                    .execute()
                )

                if not response.data:
                    raise SupabaseClientError(f"Chave não encontrada: {key_id}")

                logger.info(f"Chave deletada: {key_id}")
                return response.data[0]

            except Exception as e:
                raise SupabaseClientError(f"Erro ao deletar chave: {e}") from e

    def test_key(self, key_id: str) -> dict:
        """
        Testa conectividade de uma chave existente.

        Args:
            key_id: UUID da chave

        Returns:
            Resultado do teste
        """
        logger.info(f"Testando chave {key_id}...")

        # Buscar chave
        keys = self.get_keys()
        key_record = next((k for k in keys if k["id"] == key_id), None)

        if not key_record:
            raise SupabaseClientError(f"Chave não encontrada: {key_id}")

        platform = key_record["platform"]
        key_value = key_record["key_value"]

        # Validar conectividade
        try:
            result = validate_api_key(key_value, platform)

            # Atualizar last_tested_at
            self.update_key(
                key_id,
                {
                    "last_tested_at": datetime.utcnow().isoformat(),
                    "status": "active",
                },
            )

            logger.info(f"Teste bem-sucedido para chave {key_id}")
            return result

        except ValidationError as e:
            # Atualizar status para expired
            self.update_key(
                key_id,
                {
                    "last_tested_at": datetime.utcnow().isoformat(),
                    "status": "expired",
                },
            )

            logger.error(f"Teste falhou para chave {key_id}: {e}")
            raise

    def test_all_keys(self, platform: str | None = None) -> dict:
        """
        Testa todas as chaves ativas.

        Args:
            platform: Filtrar por plataforma (opcional)

        Returns:
            Relatório com resultados
        """
        logger.info("Testando todas as chaves ativas...")

        keys = self.get_keys(platform=platform, status="active")
        results = {"total": len(keys), "success": 0, "failed": 0, "errors": []}

        for key in keys:
            try:
                self.test_key(key["id"])
                results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                results["errors"].append(
                    {
                        "key_id": key["id"],
                        "platform": key["platform"],
                        "error": str(e),
                    }
                )

        logger.info(
            f"Teste completo: {results['success']}/{results['total']} chaves válidas"
        )
        return results


def main():
    """Ponto de entrada via linha de comando."""
    import argparse

    parser = argparse.ArgumentParser(description="Gerencia API Keys no Supabase")
    parser.add_argument("--test-all", action="store_true", help="Testar todas as chaves")
    parser.add_argument("--platform", help="Filtrar por plataforma")
    parser.add_argument("--list", action="store_true", help="Listar chaves")
    args = parser.parse_args()

    try:
        manager = SupabaseAPIKeyManager()

        if args.test_all:
            results = manager.test_all_keys(platform=args.platform)
            print(f"✅ Sucesso: {results['success']}/{results['total']}")
            if results["errors"]:
                print(f"❌ Falhas: {results['failed']}")
                for err in results["errors"]:
                    print(f"  - {err['platform']} ({err['key_id']}): {err['error']}")

        elif args.list:
            keys = manager.get_keys(platform=args.platform)
            print(f"Total: {len(keys)} chaves")
            for key in keys:
                print(
                    f"  - {key['platform']}: {key['key_prefix']}... "
                    f"(status: {key['status']}, criado: {key['created_at']})"
                )

        else:
            parser.print_help()

    except SupabaseClientError as e:
        print(f"❌ Erro: {e}")
        exit(1)


if __name__ == "__main__":
    main()
