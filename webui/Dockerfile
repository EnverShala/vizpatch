FROM python:3.13-slim

# Docker-CLI + compose-plugin (Pitfall 7: für subprocess-Fallback in Update-Flow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

RUN useradd --uid 1000 --create-home --shell /bin/bash webui

WORKDIR /app

# Layer-Caching: Dependencies zuerst
COPY pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py && pip install --no-cache-dir .

# App code
COPY src/ ./src/

RUN mkdir -p /config && chown -R webui:webui /config /app

USER webui
EXPOSE 8080
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
