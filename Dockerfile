# Bunker - Sentinela/Agentes + ChromaDB + Neo4j + Evidence Server
# Multi-stage para imagem otimizada

FROM python:3.12-slim AS builder

WORKDIR /build

# Instala dependências de build
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements-docker.txt .
RUN pip install --no-cache-dir --user -r requirements-docker.txt

# Stage final
FROM python:3.12-slim

WORKDIR /app

# Dependências runtime (sem build-essential)
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copia pacotes do builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Código da aplicação
COPY src/ ./src/
COPY tools/ ./tools/
COPY requirements-docker.txt .
RUN mkdir -p data/chunks data/raw temp/evidence

# Variáveis padrão (sobrescritas pelo docker-compose)
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# ChromaDB remoto (usar serviço chroma)
ENV CHROMA_HOST=chroma
ENV CHROMA_PORT=8000

# Neo4j (usar serviço neo4j)
ENV NEO4J_URI=bolt://neo4j:7687
ENV NEO4J_USER=neo4j
ENV NEO4J_PASSWORD=neural_link_2024

# Evidence Server URL (para IFTTT)
ENV EVIDENCE_SERVER_HOST=evidence
ENV EVIDENCE_SERVER_PORT=5000

# Healthcheck (ping ChromaDB)
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD python -c "import os,sys,httpx; h=os.getenv('CHROMA_HOST','chroma'); p=os.getenv('CHROMA_PORT','8000'); r=httpx.get(f'http://{h}:{p}/api/v2/heartbeat',timeout=5); sys.exit(0 if r.status_code==200 else 1)"

# Default: Telegram Command Handler (pode ser sobrescrito)
CMD ["python", "-m", "src.neural_link.telemetry.telegram_command_handler"]
