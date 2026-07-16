import pytest

from src.llm_detect import detect_llm_provider


def test_detect_anthropic_prefix():
    assert detect_llm_provider("sk-ant-api03-abc123") == "anthropic"


def test_detect_google_prefix():
    assert detect_llm_provider("AIzaSyABCDEFGHIJKLMNOP") == "google"


def test_detect_openai_prefix_generic_sk():
    assert detect_llm_provider("sk-abc123") == "openai"


def test_detect_openai_prefix_sk_proj():
    assert detect_llm_provider("sk-proj-abc123") == "openai"


def test_detect_strips_whitespace():
    assert detect_llm_provider("   sk-ant-api03-abc123   ") == "anthropic"
    assert detect_llm_provider("  AIzaXYZ  ") == "google"


def test_detect_unknown_format_returns_none():
    assert detect_llm_provider("foobar") is None
    assert detect_llm_provider("hf_abc123") is None


def test_detect_empty_or_none_returns_none():
    assert detect_llm_provider("") is None
    assert detect_llm_provider("   ") is None
    assert detect_llm_provider(None) is None
