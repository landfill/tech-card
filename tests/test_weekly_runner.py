"""Weekly runner observability tests."""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from pipeline import publish as publish_module
from pipeline.weekly_runner import run_weekly_pipeline


def test_run_weekly_pipeline_logs_operator_events(tmp_path: Path, monkeypatch, caplog) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    skills_dir = tmp_path / "skills"
    skills_dir.mkdir()

    week_dates = [date(2026, 4, 6) + timedelta(days=i) for i in range(7)]
    monkeypatch.setattr("pipeline.weekly_runner.get_week_dates", lambda anchor: week_dates)
    monkeypatch.setattr("pipeline.weekly_runner.get_week_id", lambda anchor: "2026-W15")
    monkeypatch.setattr(
        "pipeline.weekly_runner._load_week_data",
        lambda *args, **kwargs: {
            "total_count": 3,
            "filtered_count": 2,
            "filtered_items": [
                {"title": "A", "category": "에이전틱 코딩", "impact": "high", "url": "https://a", "_date": "2026-04-06"},
                {"title": "B", "category": "GitHub", "impact": "medium", "url": "https://b", "_date": "2026-04-07"},
            ],
            "daily_letters": {"2026-04-06": "# Monday"},
        },
    )
    monkeypatch.setattr("pipeline.weekly_runner._load_prev_week_meta", lambda *args, **kwargs: None)
    monkeypatch.setattr("pipeline.weekly_runner.load_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr("pipeline.weekly_runner.save_checkpoint", lambda *args, **kwargs: None)
    monkeypatch.setattr("pipeline.weekly_runner.weekly_meta_path", lambda data_dir, week_id: str(tmp_path / f"{week_id}-meta.json"))
    monkeypatch.setattr("pipeline.weekly_runner.weekly_letter_path", lambda data_dir, week_id: str(tmp_path / f"{week_id}.md"))
    monkeypatch.setattr("pipeline.weekly_runner.weekly_card_path", lambda data_dir, week_id: str(tmp_path / f"{week_id}-cards.json"))
    monkeypatch.setattr(
        "pipeline.weekly_runner.agents.run_agent",
        lambda agent_name, payload, skills_dir, llm_client, data_dir=None: (
            json.dumps({"trend_map": [], "top5": []})
            if agent_name == "weekly_analyze"
            else "# Weekly Letter"
            if agent_name == "weekly_generate"
            else json.dumps({"cards": [{"type": "cover", "title": "T", "body": ["B"]}]})
        ),
    )
    monkeypatch.setattr(publish_module, "publish_weekly", lambda week_id, data_dir: {"sent": True, "recipients": 1, "error": None})
    caplog.set_level(logging.INFO, logger="pipeline.weekly_runner")

    result = run_weekly_pipeline(
        anchor_date=date(2026, 4, 10),
        data_dir=data_dir,
        skills_dir=skills_dir,
        llm_client=object(),
        force=True,
    )

    assert result["week_id"] == "2026-W15"
    messages = [record.getMessage() for record in caplog.records]
    assert any("event=weekly_run_started" in message for message in messages)
    assert any("event=weekly_step_started step=weekly_collect" in message for message in messages)
    assert any("event=weekly_step_completed step=weekly_publish" in message for message in messages)
    assert any("event=weekly_run_completed" in message for message in messages)
