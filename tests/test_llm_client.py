"""get_llm_client 테스트."""
import logging
import tempfile
from pathlib import Path

import pytest

from pipeline.llm.adapters.gemini import GeminiAdapter
from pipeline.llm.adapters.openai import OpenAIAdapter
from pipeline.llm.client import get_llm_client


def test_get_llm_client_google_returns_gemini_adapter():
    """provider=google 이면 GeminiAdapter 인스턴스 반환."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("provider: google\nmodel: gemini-3-flash-preview\n")
        path = f.name
    try:
        client = get_llm_client(path)
        assert isinstance(client, GeminiAdapter)
    finally:
        Path(path).unlink(missing_ok=True)


def test_get_llm_client_openai_returns_openai_adapter():
    """provider=openai 이면 OpenAIAdapter 인스턴스 반환."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("provider: openai\nmodel: gpt-5-mini\n")
        path = f.name
    try:
        client = get_llm_client(path)
        assert isinstance(client, OpenAIAdapter)
    finally:
        Path(path).unlink(missing_ok=True)


def test_get_llm_client_unknown_provider_raises():
    """지원하지 않는 provider면 ValueError."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("provider: anthropic\nmodel: claude-3\n")
        path = f.name
    try:
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            get_llm_client(path)
    finally:
        Path(path).unlink(missing_ok=True)


def test_get_llm_client_logs_provider_and_model(monkeypatch, caplog):
    class FakeGeminiAdapter:
        def __init__(self, model: str, api_key: str):
            self.model = model
            self.api_key = api_key

    monkeypatch.setattr("pipeline.llm.client.GeminiAdapter", FakeGeminiAdapter)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("provider: google\nmodel: gemini-3-flash-preview\n")
        path = f.name
    try:
        monkeypatch.setenv("GOOGLE_API_KEY", "abc123")
        caplog.set_level(logging.INFO, logger="pipeline.llm.client")
        client = get_llm_client(path)
        assert isinstance(client, FakeGeminiAdapter)
    finally:
        Path(path).unlink(missing_ok=True)

    messages = [record.getMessage() for record in caplog.records]
    assert any("event=llm_client_ready" in message for message in messages)
    assert any("provider=google" in message and "model=gemini-3-flash-preview" in message for message in messages)
