"""LLM 설정 로드 테스트."""
import os
import tempfile
from pathlib import Path

import pytest

from pipeline.llm.config import load_llm_config


def test_load_llm_config_returns_provider_and_model():
    """provider, model 반환. api_key는 env에서."""
    yaml_content = """
provider: google
model: gemini-3-flash-preview
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        result = load_llm_config(path)
        assert result["provider"] == "google"
        assert result["model"] == "gemini-3-flash-preview"
        assert "api_key" in result
    finally:
        os.unlink(path)


def test_load_llm_config_openai():
    """openai provider 시 OPENAI_API_KEY 읽음."""
    yaml_content = "provider: openai\nmodel: gpt-5-mini\n"
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        os.environ["OPENAI_API_KEY"] = "sk-test"
        result = load_llm_config(path)
        assert result["provider"] == "openai"
        assert result["api_key"] == "sk-test"
    finally:
        os.environ.pop("OPENAI_API_KEY", None)
        os.unlink(path)


def test_load_llm_config_missing_provider_raises():
    """provider 또는 model 없으면 ValueError."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("provider: google\n")
        path = f.name
    try:
        with pytest.raises(ValueError, match="provider.*model"):
            load_llm_config(path)
    finally:
        os.unlink(path)


def test_load_llm_config_file_not_found():
    with pytest.raises(FileNotFoundError, match="not found"):
        load_llm_config(Path("/nonexistent/llm.yaml"))
