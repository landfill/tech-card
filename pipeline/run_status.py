"""Pipeline run-state persistence and lifecycle helpers."""
from __future__ import annotations

import errno
import json
import os
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Any

STALE_LOCK_TIMEOUT = timedelta(hours=6)
STALL_WARN_THRESHOLD = timedelta(minutes=5)

_SERVER_INSTANCE_ID = uuid.uuid4().hex
_OWNER_STARTED_AT = datetime.now(UTC)


def _status_path(data_dir: str, d: date) -> str:
    return os.path.join(data_dir, "checkpoints", d.isoformat(), "run_status.json")


def _utcnow() -> datetime:
    return datetime.now(UTC)


def _isoformat(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_datetime(raw: Any) -> datetime | None:
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(UTC)
    except ValueError:
        return None


def _current_owner_identity() -> dict[str, Any]:
    return {
        "server_instance_id": _SERVER_INSTANCE_ID,
        "pid": os.getpid(),
        "owner_started_at": _isoformat(_OWNER_STARTED_AT),
    }


def _probe_pid(pid: Any) -> str:
    try:
        pid_int = int(pid)
    except (TypeError, ValueError):
        return "missing"

    if pid_int <= 0:
        return "missing"

    try:
        os.kill(pid_int, 0)
    except ProcessLookupError:
        return "missing"
    except PermissionError:
        return "ambiguous"
    except OSError as exc:
        if exc.errno == errno.ESRCH:
            return "missing"
        if exc.errno == errno.EPERM:
            return "ambiguous"
        return "ambiguous"
    return "alive"


def _load_status(path: str) -> dict[str, Any] | None:
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        return None
    return payload


def _save_status(path: str, payload: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _normalize_status(payload: dict[str, Any]) -> dict[str, Any]:
    out = dict(payload)
    if not out.get("run_started_at") and out.get("started_at"):
        out["run_started_at"] = out["started_at"]
    if not out.get("last_event_at") and out.get("started_at"):
        out["last_event_at"] = out["started_at"]
    out.setdefault("running", False)
    out.setdefault("current_step", None)
    out.setdefault("error", None)
    out.setdefault("stalled", False)
    out.setdefault("suspected_stale", False)
    out.setdefault("stall_seconds", 0)
    return out


def _read_raw_status(data_dir: str, d: date) -> dict[str, Any] | None:
    return _load_status(_status_path(data_dir, d))


def _update_status(data_dir: str, d: date, updater) -> dict[str, Any]:
    path = _status_path(data_dir, d)
    status = _normalize_status(_load_status(path) or {})
    updated = updater(status)
    _save_status(path, updated)
    return updated


def write_run_status(data_dir: str, d: date, payload: dict[str, Any]) -> None:
    """Persist a raw status payload for compatibility."""
    path = _status_path(data_dir, d)
    _save_status(path, payload)


def start_run(data_dir: str, d: date, run_id: str | None = None) -> dict[str, Any]:
    now = _utcnow()
    owner = _current_owner_identity()

    def _apply(_: dict[str, Any]) -> dict[str, Any]:
        return {
            "running": True,
            "run_id": run_id or uuid.uuid4().hex,
            "server_instance_id": owner["server_instance_id"],
            "pid": owner["pid"],
            "owner_started_at": owner["owner_started_at"],
            "run_started_at": _isoformat(now),
            "current_step": None,
            "current_step_started_at": None,
            "last_event_at": _isoformat(now),
            "stalled": False,
            "stall_seconds": 0,
            "suspected_stale": False,
            "stale_cleared_at": None,
            "stall_reported_at": None,
            "last_result": None,
            "error": None,
        }

    return _update_status(data_dir, d, _apply)


def mark_step_started(data_dir: str, d: date, step_id: str) -> dict[str, Any]:
    now = _utcnow()

    def _apply(status: dict[str, Any]) -> dict[str, Any]:
        status["running"] = True
        status["current_step"] = step_id
        status["current_step_started_at"] = _isoformat(now)
        status["last_event_at"] = _isoformat(now)
        status["stalled"] = False
        status["suspected_stale"] = False
        status["stall_seconds"] = 0
        status["stall_reported_at"] = None
        status["error"] = None
        return status

    return _update_status(data_dir, d, _apply)


def mark_progress(data_dir: str, d: date, step_id: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    now = _utcnow()

    def _apply(status: dict[str, Any]) -> dict[str, Any]:
        status["running"] = True
        status["current_step"] = step_id
        if not status.get("current_step_started_at"):
            status["current_step_started_at"] = _isoformat(now)
        status["last_event_at"] = _isoformat(now)
        status["stalled"] = False
        status["suspected_stale"] = False
        status["stall_seconds"] = 0
        status["stall_reported_at"] = None
        if detail:
            status["last_result"] = detail
            if "chunk_index" in detail:
                status["chunk_index"] = detail["chunk_index"]
            if "chunk_total" in detail:
                status["chunk_total"] = detail["chunk_total"]
        return status

    return _update_status(data_dir, d, _apply)


def mark_step_finished(data_dir: str, d: date, step_id: str, detail: dict[str, Any] | None = None) -> dict[str, Any]:
    now = _utcnow()

    def _apply(status: dict[str, Any]) -> dict[str, Any]:
        status["current_step"] = step_id
        status["last_event_at"] = _isoformat(now)
        status["stalled"] = False
        status["suspected_stale"] = False
        status["stall_seconds"] = 0
        status["stall_reported_at"] = None
        status["error"] = None
        if detail is not None:
            status["last_result"] = detail
        return status

    return _update_status(data_dir, d, _apply)


def mark_run_finished(data_dir: str, d: date, last_result: dict[str, Any] | None = None) -> dict[str, Any]:
    now = _utcnow()

    def _apply(status: dict[str, Any]) -> dict[str, Any]:
        status["running"] = False
        status["current_step"] = None
        status["current_step_started_at"] = None
        status["last_event_at"] = _isoformat(now)
        status["stalled"] = False
        status["suspected_stale"] = False
        status["stall_seconds"] = 0
        status["stall_reported_at"] = None
        status["error"] = None
        if last_result is not None:
            status["last_result"] = last_result
        return status

    return _update_status(data_dir, d, _apply)


def mark_run_failed(data_dir: str, d: date, step_id: str | None, error: str, last_result: dict[str, Any] | None = None) -> dict[str, Any]:
    now = _utcnow()

    def _apply(status: dict[str, Any]) -> dict[str, Any]:
        status["running"] = False
        status["current_step"] = step_id
        status["last_event_at"] = _isoformat(now)
        status["stalled"] = False
        status["suspected_stale"] = False
        status["stall_seconds"] = 0
        status["error"] = error
        if last_result is not None:
            status["last_result"] = last_result
        return status

    return _update_status(data_dir, d, _apply)


def clear_run_lock(data_dir: str, d: date, error: str = "stale_lock_cleared") -> dict[str, Any]:
    now = _utcnow()

    def _apply(status: dict[str, Any]) -> dict[str, Any]:
        status["running"] = False
        status["stalled"] = False
        status["suspected_stale"] = True
        status["stall_seconds"] = 0
        status["error"] = error
        status["stale_cleared_at"] = _isoformat(now)
        status["last_event_at"] = _isoformat(now)
        return status

    return _update_status(data_dir, d, _apply)


def _owner_matches_current(status: dict[str, Any]) -> bool:
    owner = _current_owner_identity()
    return (
        status.get("server_instance_id") == owner["server_instance_id"]
        and status.get("pid") == owner["pid"]
        and status.get("owner_started_at") == owner["owner_started_at"]
    )


def _evaluate_status_health(data_dir: str, d: date, status: dict[str, Any]) -> dict[str, Any]:
    normalized = _normalize_status(status)
    if not normalized.get("running"):
        return normalized

    now = _utcnow()
    last_event_at = _parse_datetime(normalized.get("last_event_at"))
    if last_event_at is None:
        return normalized

    age = now - last_event_at
    normalized["stall_seconds"] = max(0, int(age.total_seconds()))
    normalized["suspected_stale"] = age > STALE_LOCK_TIMEOUT
    normalized["stalled"] = STALL_WARN_THRESHOLD < age <= STALE_LOCK_TIMEOUT

    if normalized["stalled"] and not normalized.get("stall_reported_at"):
        normalized["stall_reported_at"] = _isoformat(now)

    if age <= STALE_LOCK_TIMEOUT:
        return normalized

    if _owner_matches_current(normalized):
        return normalized

    probe = _probe_pid(normalized.get("pid"))
    if probe == "alive":
        return normalized
    if probe == "ambiguous":
        return normalized

    normalized["running"] = False
    normalized["error"] = "stale_lock_cleared"
    normalized["stale_cleared_at"] = _isoformat(now)
    normalized["last_event_at"] = _isoformat(now)
    normalized["stalled"] = False
    normalized["stall_seconds"] = 0
    return normalized


def read_run_status(data_dir: str, d: date) -> dict[str, Any] | None:
    """Read current run status and apply stale/stall evaluation."""
    path = _status_path(data_dir, d)
    payload = _load_status(path)
    if payload is None:
        return None

    evaluated = _evaluate_status_health(data_dir, d, payload)
    if evaluated != payload:
        _save_status(path, evaluated)
    return evaluated
