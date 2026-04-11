"""피드백 제출 API."""
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel

from backend.paths import get_data_dir

router = APIRouter()


def _data_dir() -> Path:
    return get_data_dir()


class FeedbackCreate(BaseModel):
    issue_date: str
    type: str
    content: str


@router.get("/types")
def get_feedback_types():
    """사용 가능한 피드백 유형 목록."""
    from pipeline.feedback_store import VALID_FEEDBACK_TYPES
    return {"types": VALID_FEEDBACK_TYPES}


@router.post("")
def create_feedback(body: FeedbackCreate):
    """피드백 한 건 저장."""
    from pipeline.feedback_store import save_feedback
    from datetime import datetime
    try:
        d = datetime.strptime(body.issue_date, "%Y-%m-%d").date()
    except ValueError:
        from datetime import date
        d = date.today()
    save_feedback(str(_data_dir()), d, body.type, body.content)
    return {"ok": True}
