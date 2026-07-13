FROM python:3.13-slim

# Non-root user
RUN useradd --uid 1000 --create-home --shell /bin/bash vizpatch

WORKDIR /app

# System deps für pip build (schlank)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Dependencies zuerst (Layer-Caching)
COPY pyproject.toml ./
RUN mkdir -p src && touch src/__init__.py && pip install --no-cache-dir .

# App code (überschreibt Stub)
COPY src/ ./src/

# Persistente Verzeichnisse
RUN mkdir -p /data /config && chown -R vizpatch:vizpatch /data /config /app
VOLUME /data
VOLUME /config

USER vizpatch

CMD ["python", "-m", "src.main"]
