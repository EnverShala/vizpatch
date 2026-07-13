import logging
import os
import stat
from pathlib import Path

from dotenv import dotenv_values

MASKED = "****"
SECRET_KEYS = {"IMAP_PASSWORD", "ANTHROPIC_API_KEY", "WEBUI_PASSWORD"}

logger = logging.getLogger(__name__)


def read_env_masked() -> dict[str, str]:
    env_path = Path(os.getenv("WEBUI_ENV_PATH", "/config/.env"))
    values = dotenv_values(env_path)
    return {
        k: (MASKED if k in SECRET_KEYS and v else v or "")
        for k, v in values.items()
    }


def write_env(updates: dict[str, str]) -> None:
    env_path = Path(os.getenv("WEBUI_ENV_PATH", "/config/.env"))
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines(keepends=True)
    else:
        lines = []
    seen_keys: set[str] = set()
    new_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            new_lines.append(line)
            continue
        if "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            seen_keys.add(key)
        else:
            new_lines.append(line)

    for key in updates:
        if key not in seen_keys:
            new_lines.append(f"{key}={updates[key]}\n")

    env_path.write_text("".join(new_lines), encoding="utf-8")
    try:
        os.chmod(env_path, stat.S_IRUSR | stat.S_IWUSR)  # 0o600
    except PermissionError as e:
        logger.warning("chmod_failed", extra={"path": str(env_path), "error": str(e)})


def read_context_md() -> str:
    context_path = Path(os.getenv("WEBUI_CONTEXT_PATH", "/config/context.md"))
    if context_path.exists():
        return context_path.read_text(encoding="utf-8")
    return ""


def write_context_md_atomic(content: str) -> None:
    context_path = Path(os.getenv("WEBUI_CONTEXT_PATH", "/config/context.md"))
    tmp = context_path.with_suffix(".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, context_path)
