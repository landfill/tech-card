"""파이프라인 산출물 자동 git commit & push."""
import logging
import subprocess
from datetime import date
from pathlib import Path

logger = logging.getLogger(__name__)

# 커밋 대상 경로 (data/ 하위 산출물)
COMMIT_PATHS = [
    "data/letters",
    "data/cards",
    "data/index",
    "data/weekly",
    "data/checkpoints",
    "data/feedback",
    "data/prompt_evolution_log",
]


def _run(cmd: list[str], cwd: str) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=30)


def auto_push(data_dir: str, push_date: date | None = None) -> dict:
    """산출물을 git add → commit → push. 반환: {committed, pushed, message, error}."""
    # git rev-parse로 정확한 repo root 탐색
    data_path = Path(data_dir).resolve()
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(data_path) if data_path.is_dir() else str(data_path.parent),
            capture_output=True, text=True, timeout=5,
        )
        repo_root = result.stdout.strip()
        if result.returncode != 0 or not repo_root:
            return {"committed": False, "pushed": False, "error": "git 저장소를 찾을 수 없음"}
    except Exception as e:
        return {"committed": False, "pushed": False, "error": str(e)}
    d = push_date or date.today()
    commit_msg = f"{d.month}/{d.day}"

    # 1. git add (존재하는 경로만)
    paths_to_add = [p for p in COMMIT_PATHS if Path(repo_root, p).exists()]
    if not paths_to_add:
        return {"committed": False, "pushed": False, "message": "커밋 대상 없음"}

    result = _run(["git", "add"] + paths_to_add, cwd=repo_root)
    if result.returncode != 0:
        return {"committed": False, "pushed": False, "error": result.stderr.strip()}

    # 2. 변경사항 있는지 확인
    diff = _run(["git", "diff", "--cached", "--quiet"], cwd=repo_root)
    if diff.returncode == 0:
        return {"committed": False, "pushed": False, "message": "변경사항 없음"}

    # 3. commit
    result = _run(["git", "commit", "-m", commit_msg], cwd=repo_root)
    if result.returncode != 0:
        return {"committed": False, "pushed": False, "error": result.stderr.strip()}
    logger.info("커밋 완료: %s", commit_msg)

    # 4. push
    result = _run(["git", "push"], cwd=repo_root)
    if result.returncode != 0:
        return {"committed": True, "pushed": False, "message": commit_msg, "error": result.stderr.strip()}

    logger.info("푸시 완료: %s", commit_msg)
    return {"committed": True, "pushed": True, "message": commit_msg}
