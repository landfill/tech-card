"""파이프라인 러너 테스트. Mock LLM·수집으로 전체 흐름 검증."""
import json
import logging
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

from pipeline.runner import _load_recent_7d_items, run_pipeline
from pipeline.storage import index_path


@pytest.fixture
def config_dir(tmp_path):
    (tmp_path / "sources.yaml").write_text("sources:\n  - id: r\n  type: rss\n  url: https://example.com/feed\n  enabled: true\n", encoding="utf-8")
    (tmp_path / "llm.yaml").write_text("provider: google\nmodel: gemini-3-flash-preview\n", encoding="utf-8")
    return tmp_path


@pytest.fixture
def skills_dir(tmp_path):
    for name in ["analyze", "summarize", "dedup", "letter_generate", "card_generate", "card_theme"]:
        (tmp_path / f"{name}.md").write_text(f"# {name}\nDo the task.", encoding="utf-8")
    return tmp_path


@pytest.fixture
def mock_llm():
    class Mock:
        def generate(self, system, user):
            if "analyze" in (system or "").lower():
                return json.dumps({"items": [{"title": "T", "summary": "S", "url": "https://x.com"}]})
            if "letter_generate" in (system or "").lower():
                return "# Newsletter\n\nContent."
            if "card_generate" in (system or "").lower():
                return json.dumps({
                    "date": "2025-02-26",
                    "cards": [{"type": "cover", "title": "T", "body": ["B"]}],
                })
            if "card_theme" in (system or "").lower():
                return "tech theme"
            return "[]"
    return Mock()


def test_run_pipeline_produces_letter(config_dir, skills_dir, tmp_path, mock_llm):
    """run_pipeline 후 letter 파일 생성 (수집은 mock)."""
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "subscribers.json").write_text("[]")
    with patch("pipeline.runner.generate_card_background", return_value=None):
        with patch("pipeline.runner.run_collect") as mock_collect:
            mock_collect.return_value = {"date": "2025-02-26", "items": [{"title": "A", "summary": "a", "url": "https://a.com"}], "sources_run": ["r"]}
            with patch("pipeline.runner.load_checkpoint") as mock_load:
                def load_side_effect(data_dir, d, stage):
                    if stage == "collect":
                        return {"items": [{"title": "A", "summary": "a", "url": "https://a.com"}]}
                    return None
                mock_load.side_effect = load_side_effect
                result = run_pipeline(
                    "2025-02-26",
                    str(config_dir),
                    str(data_dir),
                    str(skills_dir),
                    mock_llm,
                    force=True,
                )
    assert "letter_path" in result
    assert Path(result["letter_path"]).is_file()
    assert "Content." in Path(result["letter_path"]).read_text()


def test_run_pipeline_logs_operator_sequence(config_dir, skills_dir, tmp_path, mock_llm, caplog):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "subscribers.json").write_text("[]")
    caplog.set_level(logging.INFO, logger="pipeline.runner")

    with patch("pipeline.runner.generate_card_background", return_value=None):
        with patch("pipeline.runner.evolve_prompt") as mock_evolve:
            mock_evolve.return_value = None
            with patch("pipeline.runner.run_collect") as mock_collect:
                mock_collect.return_value = {"date": "2025-02-26", "items": [{"title": "A", "summary": "a", "url": "https://a.com"}], "sources_run": ["r"]}
                with patch("pipeline.runner.load_checkpoint") as mock_load:
                    def load_side_effect(data_dir, d, stage):
                        if stage == "collect":
                            return {"items": [{"title": "A", "summary": "a", "url": "https://a.com"}]}
                        return None
                    mock_load.side_effect = load_side_effect
                    run_pipeline(
                        "2025-02-26",
                        str(config_dir),
                        str(data_dir),
                        str(skills_dir),
                        mock_llm,
                        force=True,
                    )

    messages = [record.getMessage() for record in caplog.records]
    assert any("event=run_started" in message for message in messages)
    assert any("event=step_started step=collect" in message for message in messages)
    assert any("event=step_completed step=publish" in message for message in messages)
    assert any("event=run_completed" in message for message in messages)


def test_load_recent_7d_items_excludes_anchor_date(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    anchor = date(2026, 4, 13)
    same_day = Path(index_path(str(data_dir), anchor))
    same_day.parent.mkdir(parents=True, exist_ok=True)
    same_day.write_text(json.dumps({"items": [{"title": "current-day"}]}, ensure_ascii=False), encoding="utf-8")
    prev_day = Path(index_path(str(data_dir), date(2026, 4, 12)))
    prev_day.write_text(json.dumps({"items": [{"title": "previous-day"}]}, ensure_ascii=False), encoding="utf-8")

    items = _load_recent_7d_items(str(data_dir), anchor)

    titles = [item.get("title") for item in items]
    assert "previous-day" in titles
    assert "current-day" not in titles
