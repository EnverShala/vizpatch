FROM python:3.13-slim

# Docker-CLI + compose-plugin (Pitfall 7: für subprocess-Fallback in Update-Flow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg \
    && install -m 0755 -d /etc/apt/keyrings \
    && curl -fsSL https://download.docker.com/linux/debian/gpg | gpg --dearmor -o /etc/apt/keyrings/docker.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/debian bookworm stable" > /etc/apt/sources.list.d/docker.list \
    && apt-get update && apt-get install -y --no-install-recommends docker-ce-cli docker-compose-plugin \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Layer-Caching: Dependencies zuerst
COPY pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py && pip install --no-cache-dir .

# App code
COPY src/ ./src/
COPY static/ ./static/
COPY prompts/ ./prompts/

# Entrypoint: seed /config/.env und /config/context.md falls fehlend (Zero-Config-Bootstrap)
COPY docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

RUN mkdir -p /config

EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
