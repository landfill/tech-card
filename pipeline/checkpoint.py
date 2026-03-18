"""체크포인트 저장/로드. 경로: {data_dir}/checkpoints/YYYY-MM-DD/<stage>.json"""
import json
import os
from datetime import date


def _dir_for_date(data_dir: str, d: date) -> str:
    return os.path.join(data_dir, "checkpoints", d.isoformat())


def save_checkpoint(data_dir: str, d: date, stage: str, payload: dict) -> None:
    """해당 날짜·단계의 결과를 JSON으로 저장한다."""
    dirpath = _dir_for_date(data_dir, d)
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, f"{stage}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def load_checkpoint(data_dir: str, d: date, stage: str) -> dict | None:
    """해당 날짜·단계의 체크포인트를 읽는다. 없으면 None."""
    path = os.path.join(_dir_for_date(data_dir, d), f"{stage}.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def list_completed_stages(data_dir: str, d: date) -> list[str]:
    """해당 날짜에 저장된 단계 이름 목록을 반환한다."""
    dirpath = _dir_for_date(data_dir, d)
    if not os.path.isdir(dirpath):
        return []
    stages = []
    for name in os.listdir(dirpath):
        if name.endswith(".json") and name != "run_status.json":
            stages.append(name[:-5])  # .json 제거
    return stages


def clear_checkpoints_for_date(data_dir: str, d: date) -> None:
    """해당 날짜의 체크포인트 디렉터리 내 모든 파일을 삭제한다. 강제 재실행 시 사용."""
    dirpath = _dir_for_date(data_dir, d)
    if not os.path.isdir(dirpath):
        return
    for name in os.listdir(dirpath):
        path = os.path.join(dirpath, name)
        if os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass
