"""진화 로그 저장소. data/prompt_evolution_log/{agent}/TIMESTAMP.json 관리.
프롬프트 자체는 skills/{agent}.md에 직접 기록되며, 이 모듈은 변경 이력(이전 내용·diff·사유)만 보관한다."""
import json
import os
from datetime import datetime, timezone
from typing import Optional


def _log_dir(data_dir: str, agent_name: str) -> str:
    return os.path.join(data_dir, "prompt_evolution_log", agent_name)


def save_evolution_log(
    data_dir: str,
    agent_name: str,
    log_entry: dict,
) -> str:
    """진화 로그 저장. 반환: 로그 파일명 (TIMESTAMP.json)."""
    ldir = _log_dir(data_dir, agent_name)
    os.makedirs(ldir, exist_ok=True)
    ts = datetime.now(timezone.utc)
    log_entry["timestamp"] = ts.isoformat()
    log_entry["agent_name"] = agent_name
    filename = ts.strftime("%Y-%m-%dT%H-%M-%S") + ".json"
    path = os.path.join(ldir, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(log_entry, f, ensure_ascii=False, indent=2)
    return filename


def list_evolution_logs(data_dir: str, agent_name: str) -> list[dict]:
    """해당 에이전트의 진화 로그 목록 반환. 최신순."""
    ldir = _log_dir(data_dir, agent_name)
    if not os.path.isdir(ldir):
        return []
    results = []
    for name in sorted(os.listdir(ldir), reverse=True):
        if not name.endswith(".json"):
            continue
        try:
            with open(os.path.join(ldir, name), encoding="utf-8") as f:
                results.append(json.load(f))
        except Exception:
            pass
    return results


def get_latest_log(data_dir: str, agent_name: str) -> Optional[dict]:
    """가장 최근 진화 로그 반환. 없으면 None."""
    logs = list_evolution_logs(data_dir, agent_name)
    return logs[0] if logs else None
