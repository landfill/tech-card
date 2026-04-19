"""Weekly router status response tests."""
from datetime import date
from pathlib import Path

from backend.routers import weekly as weekly_router
from fastapi import BackgroundTasks


def test_build_weekly_status_response_marks_running_without_artifacts(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    weekly_dir = data_dir / "weekly"
    weekly_dir.mkdir(parents=True)

    monkeypatch.setattr(weekly_router, "_data_dir", lambda: data_dir)

    response = weekly_router._build_weekly_status_response("2026-W16")

    assert response == {
        "week_id": "2026-W16",
        "exists": False,
        "status": "running",
        "letter_ready": False,
        "letter_updated_at": None,
        "meta_ready": False,
        "meta_updated_at": None,
        "cards_ready": False,
        "cards_updated_at": None,
        "publish_result": None,
    }


def test_build_weekly_status_response_marks_completed_with_publish_result(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    weekly_dir = data_dir / "weekly"
    weekly_dir.mkdir(parents=True)
    (weekly_dir / "2026-W16.md").write_text("# Weekly", encoding="utf-8")
    (weekly_dir / "2026-W16-meta.json").write_text('{"week":"2026-W16"}', encoding="utf-8")
    (weekly_dir / "2026-W16-cards.json").write_text('{"cards":[]}', encoding="utf-8")

    checkpoint_dir = data_dir / "checkpoints" / "2026-04-13"
    checkpoint_dir.mkdir(parents=True)
    (checkpoint_dir / "weekly_2026-W16_publish.json").write_text(
        '{"sent": true, "recipients": 1, "error": null}',
        encoding="utf-8",
    )

    monkeypatch.setattr(weekly_router, "_data_dir", lambda: data_dir)

    response = weekly_router._build_weekly_status_response("2026-W16")

    assert response == {
        "week_id": "2026-W16",
        "exists": True,
        "status": "completed",
        "letter_ready": True,
        "letter_updated_at": (weekly_dir / "2026-W16.md").stat().st_mtime,
        "meta_ready": True,
        "meta_updated_at": (weekly_dir / "2026-W16-meta.json").stat().st_mtime,
        "cards_ready": True,
        "cards_updated_at": (weekly_dir / "2026-W16-cards.json").stat().st_mtime,
        "publish_result": {"sent": True, "recipients": 1, "error": None},
    }


def test_post_run_weekly_returns_started_at(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir(parents=True)
    monkeypatch.setattr(weekly_router, "_data_dir", lambda: data_dir)

    response = weekly_router.post_run_weekly(
        weekly_router.WeeklyRunBody(date="2026-04-19", force=True),
        BackgroundTasks(),
    )

    assert response["message"] == "started"
    assert response["week_id"] == "2026-W16"
    assert isinstance(response["started_at"], str)
    assert date.fromisoformat(response["started_at"][:10]) == date(2026, 4, 19)
