"""
Evidence Server - Servidor local para servir evidência visual temporariamente.

Serve a imagem de última falha em http://localhost:5000/evidence/last_fail.png
para integração com IFTTT (value3) e expansão futura via Ngrok/Cloudflare Tunnel.

Uso:
    python -m src.neural_link.services.evidence_server
"""

import logging
import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, Response

logger = logging.getLogger(__name__)

DEFAULT_EVIDENCE_DIR = Path("temp/evidence")
EVIDENCE_FILENAME = "last_fail.png"

app = FastAPI(title="Evidence Server", version="0.1.0")


def _evidence_path() -> Path:
    """Caminho do arquivo de evidência."""
    base = os.environ.get("EVIDENCE_DIR", str(DEFAULT_EVIDENCE_DIR))
    return Path(base) / EVIDENCE_FILENAME


@app.get("/evidence/last_fail.png")
def get_last_fail_evidence() -> Response:
    """
    Serve a imagem da última falha visual.
    Retorna 404 se o arquivo não existir.
    """
    path = _evidence_path()
    if not path.exists():
        return Response(status_code=404, content="Evidence not found")
    return FileResponse(
        path,
        media_type="image/png",
        filename=EVIDENCE_FILENAME,
    )


@app.get("/health")
def health() -> dict:
    """Health check para monitoramento."""
    return {"status": "ok", "service": "evidence_server"}


def get_evidence_url() -> str:
    """
    Retorna a URL base para evidência (para uso em IFTTT value3).
    """
    host = os.environ.get("EVIDENCE_SERVER_HOST", "localhost")
    port = int(os.environ.get("EVIDENCE_SERVER_PORT", "5000"))
    return f"http://{host}:{port}/evidence/last_fail.png"


def run_server(host: str = "127.0.0.1", port: int = 5000) -> None:
    """Inicia o servidor."""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    host = os.environ.get("EVIDENCE_SERVER_HOST", "127.0.0.1")
    port = int(os.environ.get("EVIDENCE_SERVER_PORT", "5000"))
    logger.info("Evidence Server starting at http://%s:%d/evidence/last_fail.png", host, port)
    run_server(host=host, port=port)
