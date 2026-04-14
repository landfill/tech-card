"""Pipeline router status response tests."""
from datetime import date
from pathlib import Path

from backend.routers import pipeline as pipeline_router


def test_build_status_response_includes_additive_run_status_fields(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    run_status = {
        "running": True,
        "current_step": "analyze",
        "run_id": "run-1",
        "server_instance_id": "srv-1",
        "pid": 123,
        "owner_started_at": "2026-04-13T00:00:00Z",
        "run_started_at": "2026-04-13T00:01:00Z",
        "current_step_started_at": "2026-04-13T00:02:00Z",
        "last_event_at": "2026-04-13T00:03:00Z",
        "stalled": True,
        "stall_seconds": 420,
        "suspected_stale": False,
        "stale_cleared_at": None,
        "stall_reported_at": "2026-04-13T00:08:00Z",
        "last_result": {"chunk_index": 2, "chunk_total": 5},
        "chunk_index": 2,
        "chunk_total": 5,
        "error": None,
    }
    monkeypatch.setattr(pipeline_router, "_data_dir", lambda: data_dir)
    monkeypatch.setattr(pipeline_router, "read_run_status", lambda *_: run_status)

    response = pipeline_router._build_status_response(d.isoformat())

    assert response["run_status"]["run_id"] == "run-1"
    assert response["run_status"]["server_instance_id"] == "srv-1"
    assert response["run_status"]["pid"] == 123
    assert response["run_status"]["current_step_started_at"] == "2026-04-13T00:02:00Z"
    assert response["run_status"]["last_event_at"] == "2026-04-13T00:03:00Z"
    assert response["run_status"]["stalled"] is True
    assert response["run_status"]["stall_seconds"] == 420
    assert response["run_status"]["last_result"] == {"chunk_index": 2, "chunk_total": 5}


def test_build_status_response_adds_stall_detail_to_current_step(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    run_status = {
        "running": True,
        "current_step": "publish",
        "run_id": "run-1",
        "run_started_at": "2026-04-13T00:01:00Z",
        "current_step_started_at": "2026-04-13T00:05:00Z",
        "last_event_at": "2026-04-13T00:06:00Z",
        "stalled": True,
        "stall_seconds": 601,
        "last_result": {"sent": False, "error": "SMTP timeout"},
        "error": None,
    }
    monkeypatch.setattr(pipeline_router, "_data_dir", lambda: data_dir)
    monkeypatch.setattr(pipeline_router, "read_run_status", lambda *_: run_status)

    response = pipeline_router._build_status_response(d.isoformat())
    current = next(step for step in response["steps"] if step["id"] == "publish")

    assert current["status"] == "running"
    assert current["detail"]["stalled"] is True
    assert current["detail"]["stall_seconds"] == 601
    assert current["detail"]["last_result"] == {"sent": False, "error": "SMTP timeout"}
