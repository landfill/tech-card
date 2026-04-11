"""프롬프트 버전 저장소. data/prompt_versions/{agent}/v{NNN}.md 관리."""
import json
import os
from datetime import datetime, timezone
from typing import Optional


def _versions_dir(data_dir: str, agent_name: str) -> str:
    return os.path.join(data_dir, "prompt_versions", agent_name)


def _log_dir(data_dir: str, agent_name: str) -> str:
    return os.path.join(data_dir, "prompt_evolution_log", agent_name)


def _version_filename(version: int) -> str:
    return f"v{version:03d}.md"


def _log_filename(version: int) -> str:
    return f"v{version:03d}.json"


def get_latest_version(data_dir: str, agent_name: str) -> Optional[int]:
    """해당 에이전트의 최신 활성 버전 번호 반환. 없으면 None (base 사용)."""
    log_path = _log_dir(data_dir, agent_name)
    if not os.path.isdir(log_path):
        return None
    versions = []
    for name in os.listdir(log_path):
        if not name.endswith(".json"):
            continue
        fpath = os.path.join(log_path, name)
        try:
            with open(fpath, encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("status") == "active":
                versions.append(meta["version"])
        except Exception:
            pass
    return max(versions) if versions else None


def load_evolved_prompt(data_dir: str, agent_name: str, version: int) -> Optional[str]:
    """특정 버전의 진화된 프롬프트 본문 반환. 없으면 None."""
    path = os.path.join(_versions_dir(data_dir, agent_name), _version_filename(version))
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as f:
        return f.read().strip()


def load_active_prompt(data_dir: str, agent_name: str) -> Optional[str]:
    """최신 활성 버전 프롬프트 반환. 없으면 None (base 사용해야 함)."""
    version = get_latest_version(data_dir, agent_name)
    if version is None:
        return None
    return load_evolved_prompt(data_dir, agent_name, version)


def save_evolved_prompt(
    data_dir: str,
    agent_name: str,
    prompt_text: str,
    evolution_log: dict,
) -> int:
    """새 버전 저장. 이전 활성 버전은 superseded로 변경. 반환: 새 버전 번호."""
    vdir = _versions_dir(data_dir, agent_name)
    os.makedirs(vdir, exist_ok=True)

    existing = []
    for n in os.listdir(vdir):
        if n.startswith("v") and n.endswith(".md") and len(n) == 7:
            try:
                existing.append(int(n[1:4]))
            except ValueError:
                pass
    next_version = (max(existing) + 1) if existing else 1

    # 이전 활성 버전 → superseded
    current = get_latest_version(data_dir, agent_name)
    if current is not None:
        _update_log_status(data_dir, agent_name, current, "superseded")

    # 프롬프트 파일 저장
    prompt_path = os.path.join(vdir, _version_filename(next_version))
    with open(prompt_path, "w", encoding="utf-8") as f:
        f.write(prompt_text)

    # 로그 저장
    ldir = _log_dir(data_dir, agent_name)
    os.makedirs(ldir, exist_ok=True)
    evolution_log["version"] = next_version
    evolution_log["status"] = "active"
    evolution_log["created_at"] = datetime.now(timezone.utc).isoformat()
    log_path = os.path.join(ldir, _log_filename(next_version))
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(evolution_log, f, ensure_ascii=False, indent=2)

    return next_version


def rollback(data_dir: str, agent_name: str, reason: str = "") -> Optional[int]:
    """현재 활성 버전을 rolled_back으로 변경.
    이전 버전이 있으면 active로 복원. 반환: 새 활성 버전 (None이면 base 복귀)."""
    current = get_latest_version(data_dir, agent_name)
    if current is None:
        return None
    _update_log_status(data_dir, agent_name, current, "rolled_back", reason)

    log_path = _log_dir(data_dir, agent_name)
    candidates = []
    for name in os.listdir(log_path):
        if not name.endswith(".json"):
            continue
        fpath = os.path.join(log_path, name)
        try:
            with open(fpath, encoding="utf-8") as f:
                meta = json.load(f)
            if meta.get("status") == "superseded" and meta["version"] < current:
                candidates.append(meta["version"])
        except Exception:
            pass

    if candidates:
        prev = max(candidates)
        _update_log_status(data_dir, agent_name, prev, "active")
        return prev
    return None


def _update_log_status(
    data_dir: str, agent_name: str, version: int, status: str, reason: str = ""
) -> None:
    log_path = os.path.join(_log_dir(data_dir, agent_name), _log_filename(version))
    if not os.path.isfile(log_path):
        return
    with open(log_path, encoding="utf-8") as f:
        meta = json.load(f)
    meta["status"] = status
    if status == "rolled_back":
        meta["rolled_back_at"] = datetime.now(timezone.utc).isoformat()
        meta["rollback_reason"] = reason
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)


def list_versions(data_dir: str, agent_name: str) -> list[dict]:
    """해당 에이전트의 모든 버전 메타데이터 목록 반환. 최신순."""
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
