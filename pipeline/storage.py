"""레터/인덱스 경로 및 7일 날짜 유틸."""
import os
from datetime import date, timedelta


def letter_path(data_dir: str, d: date) -> str:
    """발행본 마크다운 파일 경로."""
    return os.path.join(data_dir, "letters", f"{d.isoformat()}.md")


def index_path(data_dir: str, d: date) -> str:
    """해당 날짜 인덱스(제목·키워드) JSON 경로."""
    return os.path.join(data_dir, "index", f"{d.isoformat()}.json")


def card_path(data_dir: str, d: date) -> str:
    """해당 날짜 카드뉴스 JSON 경로."""
    return os.path.join(data_dir, "cards", f"{d.isoformat()}.json")


def card_bg_image_path(data_dir: str, d: date) -> str:
    """해당 날짜 카드 배경 이미지 경로 (1호당 1장). 파일명 YYYYMMDD.png."""
    yyyymmdd = d.strftime("%Y%m%d")
    return os.path.join(data_dir, "cards", f"{yyyymmdd}.png")


def recent_7d_dates(anchor: date) -> list[date]:
    """anchor 기준 과거 7일(anchor 포함) 날짜 리스트. 오래된 순."""
    return [anchor - timedelta(days=(6 - i)) for i in range(7)]


# ─── 주간 레터 경로 유틸 ───


def get_week_id(d: date) -> str:
    """ISO 주차 문자열 반환. 예: 2026-W15"""
    iso = d.isocalendar()
    return f"{iso[0]}-W{iso[1]:02d}"


def get_week_dates(d: date) -> list[date]:
    """d가 포함된 주의 월~일 날짜 리스트 (7개). 월요일 시작."""
    monday = d - timedelta(days=d.weekday())
    return [monday + timedelta(days=i) for i in range(7)]


def weekly_letter_path(data_dir: str, week_id: str) -> str:
    """주간 레터 마크다운 경로. 예: data/weekly/2026-W15.md"""
    return os.path.join(data_dir, "weekly", f"{week_id}.md")


def weekly_meta_path(data_dir: str, week_id: str) -> str:
    """주간 메타 JSON 경로. 예: data/weekly/2026-W15-meta.json"""
    return os.path.join(data_dir, "weekly", f"{week_id}-meta.json")


def weekly_card_path(data_dir: str, week_id: str) -> str:
    """주간 카드뉴스 JSON 경로. 예: data/weekly/2026-W15-cards.json"""
    return os.path.join(data_dir, "weekly", f"{week_id}-cards.json")
