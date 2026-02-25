"""레터/인덱스 경로 및 7일 날짜 유틸."""
import os
from datetime import date, timedelta


def letter_path(data_dir: str, d: date) -> str:
    """발행본 마크다운 파일 경로."""
    return os.path.join(data_dir, "letters", f"{d.isoformat()}.md")


def index_path(data_dir: str, d: date) -> str:
    """해당 날짜 인덱스(제목·키워드) JSON 경로."""
    return os.path.join(data_dir, "index", f"{d.isoformat()}.json")


def recent_7d_dates(anchor: date) -> list[date]:
    """anchor 기준 과거 7일(anchor 포함) 날짜 리스트. 오래된 순."""
    return [anchor - timedelta(days=(6 - i)) for i in range(7)]
