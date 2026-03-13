FROM python:3.11-slim AS base

LABEL maintainer="OmegaHuggsTeam" \
      org.opencontainers.image.source="https://github.com/OmegaHuggsTeam/engine-service" \
      org.opencontainers.image.description="Sandbox container for journey condition evaluation nodes"

# Security: no extra packages, minimal layer count
RUN groupadd -r sandbox && useradd -r -g sandbox -d /home/sandbox -s /sbin/nologin sandbox \
    && mkdir -p /home/sandbox /tmp \
    && chown -R sandbox:sandbox /home/sandbox /tmp

WORKDIR /home/sandbox

COPY --chown=sandbox:sandbox run.py .

USER sandbox

ENV NODE_TYPE=condition \
    NODE_SUBTYPE="" \
    NODE_CONFIG="{}"

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=2 \
    CMD ["python", "-c", "import os, sys; sys.exit(0 if os.path.exists('/tmp/result.json') else 1)"]

CMD ["python", "run.py"]
