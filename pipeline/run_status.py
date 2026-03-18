"""파이프라인 실행 상태 파일 읽기/쓰기. data/checkpoints/{date}/run_status.json"""
import json
import os
from datetime import date
from typing import Any


def _status_path(data_dir: str, d: date) -> str:
    return os.path.join(data_dir, "checkpoints", d.isoformat(), "run_status.json")


def write_run_status(data_dir: str, d: date, payload: dict[str, Any]) -> None:
    """해당 날짜의 run_status.json에 payload를 기록한다."""
    path = _status_path(data_dir, d)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def read_run_status(data_dir: str, d: date) -> dict[str, Any] | None:
    """해당 날짜의 run_status.json을 읽는다. 없으면 None."""
    path = _status_path(data_dir, d)
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
