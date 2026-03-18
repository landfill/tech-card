"""백엔드 공통 경로. DATA_DIR 환경 변수 지원으로 재기동 시에도 동일한 데이터 디렉터리 사용."""
import os
from pathlib import Path

from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드 (실행 위치와 무관)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


def get_data_dir() -> Path:
    """데이터 디렉터리. DATA_DIR이 있으면 사용(절대/상대), 없으면 프로젝트 루트/data."""
    raw = os.environ.get("DATA_DIR", "").strip()
    if not raw:
        return _PROJECT_ROOT / "data"
    p = Path(raw).expanduser()
    if not p.is_absolute():
        p = (_PROJECT_ROOT / p).resolve()
    return p


def get_config_dir() -> Path:
    """설정 디렉터리 (프로젝트 루트/config)."""
    return _PROJECT_ROOT / "config"
