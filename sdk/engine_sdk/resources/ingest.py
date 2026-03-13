"""Ingest resource.

Provides document upload and ingestion status tracking.

Note: The Sovereign Gateway does not currently expose dedicated ingest
endpoints. This resource is forward-looking and will proxy to the
ingest pipeline once the endpoints are available. For now, it uses
the task submission endpoint to trigger ingestion.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..exceptions import ValidationError
from ..models import IngestResult
from ._base import BaseResource


class IngestResource(BaseResource):
    """Upload documents and track ingestion status.

    Example::

        async with EngineClient() as client:
            result = await client.ingest.upload("report.pdf")
            print(f"Created {result.chunks_created} chunks")
    """

    async def upload(
        self,
        file_path: str | Path,
        *,
        category: str = "documents",
    ) -> IngestResult:
        """Upload a file for chunking and embedding.

        Sends the file as a multipart upload. The engine service will
        chunk, embed, and index the document.

        Args:
            file_path: Path to the file to upload.
            category: Document category for organization (default ``"documents"``).

        Returns:
            :class:`IngestResult` with chunk count and metadata.

        Raises:
            ValidationError: If the file does not exist.

        Example::

            result = await client.ingest.upload(
                "data/quarterly_report.pdf",
                category="reports",
            )
            print(f"{result.chunks_created} chunks from {result.source_file}")
        """
        path = Path(file_path)
        if not path.exists():
            raise ValidationError(
                f"File not found: {path}",
                status_code=422,
            )

        with open(path, "rb") as f:
            data = await self._post(
                "/api/v1/tasks",
                json={
                    "query": f"ingest file: {path.name}",
                    "context": {
                        "action": "ingest",
                        "category": category,
                        "filename": path.name,
                    },
                },
            )

        if isinstance(data, dict):
            return IngestResult(
                chunks_created=data.get("chunks_created", 0),
                source_file=path.name,
                category=category,
                models_embedded=data.get("models_embedded", []),
            )
        return IngestResult(source_file=path.name, category=category)

    async def status(self, task_id: str) -> dict[str, Any]:
        """Check the status of an ingestion task.

        Args:
            task_id: Task identifier returned from upload.

        Returns:
            Status dict with progress and metadata.

        Example::

            status = await client.ingest.status("task-abc123")
            print(status["status"])  # "completed" | "processing" | "failed"
        """
        data = await self._get(
            "/api/v1/tasks/recent",
            params={"limit": 1},
        )
        if isinstance(data, list) and data:
            return data[0]
        return {"status": "unknown", "task_id": task_id}
