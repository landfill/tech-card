"""run_status lifecycle contract."""
import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from pipeline import run_status as rs


def _status_path(data_dir: Path, d: date) -> Path:
    return data_dir / "checkpoints" / d.isoformat() / "run_status.json"


def _write_payload(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def test_start_run_records_metadata(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    now = datetime(2026, 4, 13, 1, 2, 3, tzinfo=UTC)
    monkeypatch.setattr(rs, "_utcnow", lambda: now)
    monkeypatch.setattr(
        rs,
        "_current_owner_identity",
        lambda: {
            "server_instance_id": "srv-1",
            "pid": 4321,
            "owner_started_at": "2026-04-13T01:00:00Z",
        },
    )

    rs.start_run(str(data_dir), d, run_id="run-1")
    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["running"] is True
    assert out["run_id"] == "run-1"
    assert out["server_instance_id"] == "srv-1"
    assert out["pid"] == 4321
    assert out["owner_started_at"] == "2026-04-13T01:00:00Z"
    assert out["run_started_at"] == "2026-04-13T01:02:03Z"
    assert out["last_event_at"] == "2026-04-13T01:02:03Z"


def test_mark_progress_updates_last_result(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    started = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    progressed = datetime(2026, 4, 13, 1, 4, 0, tzinfo=UTC)
    monkeypatch.setattr(rs, "_current_owner_identity", lambda: {"server_instance_id": "srv-1", "pid": 123, "owner_started_at": "2026-04-13T00:59:00Z"})
    monkeypatch.setattr(rs, "_utcnow", lambda: started)
    rs.start_run(str(data_dir), d, run_id="run-1")
    rs.mark_step_started(str(data_dir), d, "analyze")

    monkeypatch.setattr(rs, "_utcnow", lambda: progressed)
    rs.mark_progress(str(data_dir), d, "analyze", {"chunk_index": 2, "chunk_total": 5})
    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["current_step"] == "analyze"
    assert out["last_event_at"] == "2026-04-13T01:04:00Z"
    assert out["last_result"] == {"chunk_index": 2, "chunk_total": 5}


def test_mark_step_started_clears_previous_step_progress_fields(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    started = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    progressed = datetime(2026, 4, 13, 1, 4, 0, tzinfo=UTC)
    next_step = datetime(2026, 4, 13, 1, 6, 0, tzinfo=UTC)
    monkeypatch.setattr(
        rs,
        "_current_owner_identity",
        lambda: {"server_instance_id": "srv-1", "pid": 123, "owner_started_at": "2026-04-13T00:59:00Z"},
    )
    monkeypatch.setattr(rs, "_utcnow", lambda: started)
    rs.start_run(str(data_dir), d, run_id="run-1")
    rs.mark_step_started(str(data_dir), d, "analyze")

    monkeypatch.setattr(rs, "_utcnow", lambda: progressed)
    rs.mark_progress(str(data_dir), d, "analyze", {"chunk_index": 2, "chunk_total": 5, "items_count": 10})

    monkeypatch.setattr(rs, "_utcnow", lambda: next_step)
    rs.mark_step_started(str(data_dir), d, "summarize")
    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["current_step"] == "summarize"
    assert out.get("chunk_index") is None
    assert out.get("chunk_total") is None
    assert out["last_result"] is None


def test_read_run_status_marks_stalled_without_clearing(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    last_event = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    now = last_event + rs.STALL_WARN_THRESHOLD + timedelta(seconds=30)
    payload = {
        "running": True,
        "run_id": "run-1",
        "current_step": "analyze",
        "run_started_at": "2026-04-13T00:50:00Z",
        "last_event_at": "2026-04-13T01:00:00Z",
        "server_instance_id": "srv-old",
        "pid": 99,
        "owner_started_at": "2026-04-13T00:49:00Z",
        "error": None,
    }
    _write_payload(_status_path(data_dir, d), payload)
    monkeypatch.setattr(rs, "_utcnow", lambda: now)
    monkeypatch.setattr(rs, "_current_owner_identity", lambda: {"server_instance_id": "srv-new", "pid": 100, "owner_started_at": "2026-04-13T01:10:00Z"})
    monkeypatch.setattr(rs, "_probe_pid", lambda pid: "alive")

    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["running"] is True
    assert out["stalled"] is True
    assert out["suspected_stale"] is False
    assert out["stall_seconds"] >= int(rs.STALL_WARN_THRESHOLD.total_seconds())
    persisted = json.loads(_status_path(data_dir, d).read_text(encoding="utf-8"))
    assert persisted == payload


def test_read_run_status_clears_orphaned_run_after_restart(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    last_event = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    now = last_event + timedelta(minutes=2)
    payload = {
        "running": True,
        "run_id": "run-1",
        "current_step": "dedup",
        "run_started_at": "2026-04-13T00:58:00Z",
        "last_event_at": "2026-04-13T01:00:00Z",
        "server_instance_id": "srv-old",
        "pid": 5127,
        "owner_started_at": "2026-04-13T00:57:00Z",
        "error": None,
    }
    _write_payload(_status_path(data_dir, d), payload)
    monkeypatch.setattr(rs, "_utcnow", lambda: now)
    monkeypatch.setattr(
        rs,
        "_current_owner_identity",
        lambda: {"server_instance_id": "srv-new", "pid": 93648, "owner_started_at": "2026-04-13T01:01:00Z"},
    )
    monkeypatch.setattr(rs, "_probe_pid", lambda pid: "missing")

    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["running"] is False
    assert out["current_step"] == "dedup"
    assert out["error"] == "orphaned_run_cleared"
    assert out["stale_cleared_at"] == "2026-04-13T01:02:00Z"


def test_read_run_status_does_not_persist_stale_clear_side_effects(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    old = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    now = old + rs.STALE_LOCK_TIMEOUT + timedelta(minutes=1)
    payload = {
        "running": True,
        "run_id": "run-1",
        "current_step": "publish",
        "run_started_at": "2026-04-13T00:00:00Z",
        "last_event_at": "2026-04-13T01:00:00Z",
        "server_instance_id": "srv-old",
        "pid": 321,
        "owner_started_at": "2026-04-13T00:00:00Z",
        "error": None,
    }
    status_path = _status_path(data_dir, d)
    _write_payload(status_path, payload)
    monkeypatch.setattr(rs, "_utcnow", lambda: now)
    monkeypatch.setattr(
        rs,
        "_current_owner_identity",
        lambda: {"server_instance_id": "srv-new", "pid": 654, "owner_started_at": "2026-04-13T06:59:00Z"},
    )
    monkeypatch.setattr(rs, "_probe_pid", lambda pid: "missing")

    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["running"] is False
    persisted = json.loads(status_path.read_text(encoding="utf-8"))
    assert persisted == payload


def test_read_run_status_clears_stale_lock_without_live_owner(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    old = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    now = old + rs.STALE_LOCK_TIMEOUT + timedelta(minutes=1)
    payload = {
        "running": True,
        "run_id": "run-1",
        "current_step": "publish",
        "run_started_at": "2026-04-13T00:00:00Z",
        "last_event_at": "2026-04-13T01:00:00Z",
        "server_instance_id": "srv-old",
        "pid": 321,
        "owner_started_at": "2026-04-13T00:00:00Z",
        "error": None,
    }
    _write_payload(_status_path(data_dir, d), payload)
    monkeypatch.setattr(rs, "_utcnow", lambda: now)
    monkeypatch.setattr(rs, "_current_owner_identity", lambda: {"server_instance_id": "srv-new", "pid": 654, "owner_started_at": "2026-04-13T06:59:00Z"})
    monkeypatch.setattr(rs, "_probe_pid", lambda pid: "missing")

    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["running"] is False
    assert out["current_step"] == "publish"
    assert out["suspected_stale"] is True
    assert out["error"] == "stale_lock_cleared"
    assert out["stale_cleared_at"] == "2026-04-13T07:01:00Z"


def test_read_run_status_does_not_clear_stale_lock_with_live_owner(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    d = date(2026, 4, 13)
    old = datetime(2026, 4, 13, 1, 0, 0, tzinfo=UTC)
    now = old + rs.STALE_LOCK_TIMEOUT + timedelta(minutes=1)
    payload = {
        "running": True,
        "run_id": "run-1",
        "current_step": "publish",
        "run_started_at": "2026-04-13T00:00:00Z",
        "last_event_at": "2026-04-13T01:00:00Z",
        "server_instance_id": "srv-live",
        "pid": 321,
        "owner_started_at": "2026-04-13T00:00:00Z",
        "error": None,
    }
    _write_payload(_status_path(data_dir, d), payload)
    monkeypatch.setattr(rs, "_utcnow", lambda: now)
    monkeypatch.setattr(rs, "_current_owner_identity", lambda: {"server_instance_id": "srv-live", "pid": 321, "owner_started_at": "2026-04-13T00:00:00Z"})
    monkeypatch.setattr(rs, "_probe_pid", lambda pid: "alive")

    out = rs.read_run_status(str(data_dir), d)

    assert out is not None
    assert out["running"] is True
    assert out["suspected_stale"] is True
    assert out.get("stale_cleared_at") is None
    assert out.get("error") is None
