"""소스 설정 로더 테스트."""
import os
import tempfile

import pytest

from pipeline.config import load_sources


def test_load_sources_returns_list_of_enabled_only():
    """load_sources()는 YAML에서 sources를 읽고 enabled가 True인 항목만 반환한다."""
    yaml_content = """
sources:
  - id: a
    type: rss
    url: https://a.com/feed
    enabled: true
  - id: b
    type: github
    repo: x/y
    enabled: false
  - id: c
    type: rss
    url: https://c.com/feed
    enabled: true
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        result = load_sources(path)
        assert isinstance(result, list)
        assert len(result) == 2
        ids = [s["id"] for s in result]
        assert "a" in ids
        assert "c" in ids
        assert "b" not in ids
    finally:
        os.unlink(path)


def test_load_sources_real_config():
    """실제 config/sources.yaml에서 enabled인 소스만 반환."""
    path = os.path.join(os.path.dirname(__file__), "..", "config", "sources.yaml")
    path = os.path.abspath(path)
    result = load_sources(path)
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(s.get("enabled") is True for s in result)
