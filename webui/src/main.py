import os

from fastapi import FastAPI

from .logging_setup import setup_logging

setup_logging(os.getenv("LOG_LEVEL", "INFO"))

app = FastAPI(title="Vizpatch WebUI", version="1.1.0")


@app.get("/healthz")
def healthz() -> dict:
    return {"status": "ok"}
