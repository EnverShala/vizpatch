"""Pytest fixtures for Vizpatch tests."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from src.config import Config


@pytest.fixture
def tmp_db(tmp_path: Path) -> Path:
    return tmp_path / "state.db"


@pytest.fixture
def mock_config(tmp_path: Path) -> Config:
    """Config with prompts loaded from repo, dummy IMAP/LLM creds."""
    repo_root = Path(__file__).resolve().parents[1]
    prompts_dir = repo_root / "prompts"

    prompt_classify = (prompts_dir / "classify.txt").read_text(encoding="utf-8")
    prompt_generate = (prompts_dir / "generate.txt").read_text(encoding="utf-8")

    return Config(
        imap_host="imap.test.local",
        imap_port=993,
        imap_use_ssl=True,
        imap_user="test@example.com",
        imap_password="dummy",
        imap_drafts_folder="Drafts",
        imap_drafts_folder_explicit=True,
        imap_sent_folder="Sent",
        imap_inbox_folder="INBOX",
        poll_interval_seconds=300,
        backfill_days=1,
        own_email_address="test@example.com",
        own_display_name="Test User",
        anthropic_api_key="sk-ant-test",
        model_classify="claude-haiku-4-5",
        model_draft="claude-sonnet-4-6",
        llm_max_tokens_draft=600,
        llm_temperature_draft=0.3,
        enable_pii_redaction=True,
        log_level="INFO",
        context_file=tmp_path / "context.md",
        state_db=tmp_path / "state.db",
        prompts_dir=prompts_dir,
        context_md="# Firmen-Kontext für Test-Tankstelle\n\n## About\nEine Test-Tankstelle.\n\n## Öffnungszeiten\nMo-Fr 8-20\n\n## Signatur\nMax Muster, Test-Tankstelle",
        prompt_classify=prompt_classify,
        prompt_generate=prompt_generate,
    )


class _FakeMessagesResponse:
    def __init__(self, text: str):
        self.content = [MagicMock(text=text)]


@pytest.fixture
def mock_anthropic_classify_reply_needed():
    client = MagicMock()
    client.messages.create.return_value = _FakeMessagesResponse("REPLY_NEEDED")
    return client


@pytest.fixture
def mock_anthropic_classify_ignore():
    client = MagicMock()
    client.messages.create.return_value = _FakeMessagesResponse("IGNORE")
    return client


@pytest.fixture
def mock_anthropic_generate():
    client = MagicMock()
    client.messages.create.return_value = _FakeMessagesResponse(
        "Sehr geehrter Kunde,\n\nvielen Dank für Ihre Anfrage.\nWir haben Mo–Fr von 8 bis 20 Uhr geöffnet.\n\nMit freundlichen Grüßen\nMax Muster"
    )
    return client
