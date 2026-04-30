"""피드백 제출 API."""
from datetime import date, datetime

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.services.feedback import (
    FeedbackEvolutionBusyError,
    FeedbackTransactionError,
    submit_feedback,
)

router = APIRouter()


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
    """피드백 저장과 연관 프롬프트 진화를 동기적으로 완료한다."""
    try:
        d = datetime.strptime(body.issue_date, "%Y-%m-%d").date()
    except ValueError:
        d = date.today()
    try:
        return submit_feedback(issue_date=d, feedback_type=body.type, content=body.content)
    except FeedbackEvolutionBusyError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except FeedbackTransactionError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
