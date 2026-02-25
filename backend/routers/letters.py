"""발송 내역 API."""
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

router = APIRouter()

# DATA_DIR은 main에서 설정하거나 env에서. 여기서는 상대 경로
def _data_dir() -> Path:
    return Path(__file__).resolve().parent.parent.parent / "data"


@router.get("")
def list_letters():
    """발송된 레터 날짜 목록 (날짜순)."""
    letters_dir = _data_dir() / "letters"
    if not letters_dir.is_dir():
        return []
    dates = []
    for f in letters_dir.glob("*.md"):
        try:
            dates.append(f.stem)
        except Exception:
            pass
    return sorted(dates, reverse=True)


@router.get("/by-weekday")
def list_letters_by_weekday():
    """요일별 그룹."""
    letters_dir = _data_dir() / "letters"
    if not letters_dir.is_dir():
        return {}
    weekdays = "월화수목금토일"
    by_wd = {w: [] for w in weekdays}
    for f in sorted(letters_dir.glob("*.md"), key=lambda x: x.stem, reverse=True):
        try:
            from datetime import datetime
            d = datetime.strptime(f.stem, "%Y-%m-%d")
            wd = weekdays[d.weekday()]
            by_wd[wd].append(f.stem)
        except Exception:
            pass
    return by_wd


@router.get("/{date}", response_class=PlainTextResponse)
def get_letter(date: str):
    """해당 날짜 레터 마크다운 본문."""
    letters_dir = _data_dir() / "letters"
    path = letters_dir / f"{date}.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Letter not found")
    return path.read_text(encoding="utf-8")
