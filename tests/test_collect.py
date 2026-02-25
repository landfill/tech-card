"""수집 오케스트레이션 테스트."""
import tempfile
from pathlib import Path

import pytest

from pipeline.collect import run_collect


@pytest.fixture
def sources_yaml(tmp_path):
    """enabled 소스 2개: rss(anthropic), reddit_rss."""
    p = tmp_path / "sources.yaml"
    p.write_text("""
sources:
  - id: rss-one
    type: rss
    url: https://www.anthropic.com/news.xml
    enabled: true
  - id: reddit-one
    type: reddit_rss
    subreddit: ClaudeAI
    enabled: true
""", encoding="utf-8")
    return str(p)


@pytest.fixture
def data_dir(tmp_path):
    return str(tmp_path)


def test_run_collect_returns_payload(sources_yaml, data_dir):
    """run_collect는 date, items, sources_run을 담은 payload 반환."""
    result = run_collect(sources_yaml, data_dir, "2025-02-25", max_workers=2)
    assert "date" in result
    assert result["date"] == "2025-02-25"
    assert "items" in result
    assert isinstance(result["items"], list)
    assert "sources_run" in result
    assert "rss-one" in result["sources_run"]
    assert "reddit-one" in result["sources_run"]


def test_run_collect_saves_checkpoint(sources_yaml, data_dir):
    """체크포인트에 collect.json 저장."""
    run_collect(sources_yaml, data_dir, "2025-02-25", max_workers=2)
    cp = Path(data_dir) / "checkpoints" / "2025-02-25" / "collect.json"
    assert cp.is_file()
    import json
    data = json.loads(cp.read_text())
    assert data["date"] == "2025-02-25"
    assert "items" in data
