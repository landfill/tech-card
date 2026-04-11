"""주간 레터 API."""
import json
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from backend.paths import get_data_dir, get_config_dir
from pipeline.storage import weekly_card_path, weekly_letter_path, weekly_meta_path

router = APIRouter()


def _data_dir() -> Path:
    return get_data_dir()


def _weekly_dir() -> Path:
    return _data_dir() / "weekly"


@router.get("")
def list_weekly():
    """주간 레터 목록. 예: ["2026-W15", "2026-W14", ...]"""
    d = _weekly_dir()
    if not d.is_dir():
        return []
    weeks = set()
    for f in d.glob("*.md"):
        weeks.add(f.stem)  # 2026-W15
    return sorted(weeks, reverse=True)


@router.get("/{week_id}", response_class=PlainTextResponse)
def get_weekly_letter(week_id: str):
    """주간 레터 마크다운 본문."""
    path = Path(weekly_letter_path(str(_data_dir()), week_id))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Weekly letter not found")
    return path.read_text(encoding="utf-8")


@router.get("/{week_id}/meta")
def get_weekly_meta(week_id: str):
    """주간 메타 JSON (트렌드맵, 카테고리 통계, Top5)."""
    path = Path(weekly_meta_path(str(_data_dir()), week_id))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Weekly meta not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/{week_id}/cards")
def get_weekly_cards(week_id: str):
    """주간 카드뉴스 JSON."""
    path = Path(weekly_card_path(str(_data_dir()), week_id))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Weekly cards not found")
    return json.loads(path.read_text(encoding="utf-8"))


class WeeklyRunBody(BaseModel):
    date: str | None = None  # 해당 날짜가 포함된 주. 생략 시 직전 완료 주
    force: bool = False


def _run_weekly_task(anchor_date: date, force: bool) -> None:
    from pipeline.weekly_runner import run_weekly_pipeline
    from pipeline.llm.client import get_llm_client

    config_dir = get_config_dir()
    skills_dir = config_dir.parent / "skills"
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)

    run_weekly_pipeline(
        anchor_date=anchor_date,
        data_dir=str(_data_dir()),
        skills_dir=skills_dir,
        llm_client=llm_client,
        force=force,
    )
    try:
        from pipeline.git_push import auto_push
        auto_push(str(_data_dir()), anchor_date)
    except Exception:
        pass


@router.post("/run", status_code=202)
def post_run_weekly(body: WeeklyRunBody, background_tasks: BackgroundTasks):
    """주간 파이프라인 실행 (백그라운드)."""
    if body.date:
        try:
            anchor = date.fromisoformat(body.date)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date")
    else:
        anchor = date.today() - timedelta(days=1)
    background_tasks.add_task(_run_weekly_task, anchor, body.force)
    from pipeline.storage import get_week_id
    return {"message": "started", "week_id": get_week_id(anchor)}
