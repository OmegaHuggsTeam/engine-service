FROM python:3.11-slim AS base

LABEL maintainer="OmegaHuggsTeam" \
      org.opencontainers.image.source="https://github.com/OmegaHuggsTeam/engine-service" \
      org.opencontainers.image.description="Sandbox container for journey action execution nodes (CRM actions)"

# Install only curl for HTTP client capability, then clean up
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r sandbox && useradd -r -g sandbox -d /home/sandbox -s /sbin/nologin sandbox \
    && mkdir -p /home/sandbox /tmp \
    && chown -R sandbox:sandbox /home/sandbox /tmp

WORKDIR /home/sandbox

COPY --chown=sandbox:sandbox run.py .
COPY --chown=sandbox:sandbox requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

USER sandbox

ENV NODE_TYPE=action \
    NODE_SUBTYPE="" \
    NODE_CONFIG="{}" \
    CRM_API_URL="" \
    CRM_API_TOKEN=""

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=2 \
    CMD ["python", "-c", "import os, sys; sys.exit(0 if os.path.exists('/tmp/result.json') else 1)"]

CMD ["python", "run.py"]
