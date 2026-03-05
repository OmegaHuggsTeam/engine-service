# Kiro Cortex - Imagem base para webhook + Groq
FROM python:3.11-slim

WORKDIR /app

COPY automation_hub/ /app/automation_hub/

RUN pip install --no-cache-dir fastapi uvicorn python-dotenv groq PyYAML google-generativeai

EXPOSE 8765

# Default: webhook
CMD ["python", "automation_hub/bridge/webhook_listener.py", "8765"]
