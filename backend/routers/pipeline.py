"""파이프라인 상태·실행 API."""
from datetime import date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from pipeline.checkpoint import clear_checkpoints_for_date, list_completed_stages
from pipeline.run_status import (
    mark_progress,
    mark_run_failed,
    mark_run_finished,
    mark_step_finished,
    mark_step_started,
    read_run_status,
    start_run,
)
from pipeline.runner import PIPELINE_STEPS, run_pipeline, run_step

from backend.paths import get_data_dir

router = APIRouter()

STEP_NAMES = {
    "collect": "수집",
    "analyze": "분석",
    "summarize": "요약",
    "dedup": "중복 제거",
    "letter_generate": "레터 생성",
    "card_generate": "카드 생성",
    "card_backgrounds": "카드 배경",
    "publish": "메일 발송",
}


def _root() -> Path:
    return Path(__file__).resolve().parent.parent.parent


def _data_dir() -> Path:
    return get_data_dir()


def _config_dir() -> Path:
    return _root() / "config"


def _skills_dir() -> Path:
    return _root() / "skills"


def _get_llm_client():
    from pipeline.llm.client import get_llm_client
    config_dir = _config_dir()
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    return get_llm_client(llm_path)


def _progress_callback_factory(data_dir: Path, d: date):
    def progress_callback(step_id: str, status: str, detail: dict | None) -> None:
        if status == "started":
            mark_step_started(str(data_dir), d, step_id)
        elif status == "progress":
            mark_progress(str(data_dir), d, step_id, detail)
        elif status == "completed":
            mark_step_finished(str(data_dir), d, step_id, detail)
        elif status == "failed":
            error = detail.get("error") if detail else "step_failed"
            last_result = detail if detail else None
            mark_run_failed(str(data_dir), d, step_id, error or "step_failed", last_result)

    return progress_callback


def _build_status_response(date_str: str) -> dict:
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    data_dir = _data_dir()
    run = read_run_status(str(data_dir), d)
    completed = list_completed_stages(str(data_dir), d)
    completed = [s for s in completed if s in PIPELINE_STEPS]
    is_running = run.get("running", False) if run else False
    current_step = run.get("current_step") if run else None
    steps = []
    for sid in PIPELINE_STEPS:
        name = STEP_NAMES.get(sid, sid)
        if sid == current_step and is_running:
            status = "running"
            detail = {}
            if run.get("chunk_index") is not None and run.get("chunk_total") is not None:
                detail["chunk_index"] = run["chunk_index"]
                detail["chunk_total"] = run["chunk_total"]
            if run.get("stalled") is not None:
                detail["stalled"] = run.get("stalled", False)
            if run.get("stall_seconds") is not None:
                detail["stall_seconds"] = run.get("stall_seconds", 0)
            if run.get("last_result") is not None:
                detail["last_result"] = run.get("last_result")
        elif run and run.get("error") and sid == current_step:
            status = "failed"
            detail = {"error": run.get("error")}
        elif sid in completed:
            status = "completed"
            detail = {}
        else:
            status = "pending"
            detail = {}
        steps.append({"id": sid, "name": name, "status": status, "detail": detail})
    return {
        "date": date_str,
        "is_running": is_running,
        "run_status": run or {},
        "steps": steps,
    }


def _default_date() -> str:
    """날짜 미지정 시 전일(최근 1일치) 반환."""
    return (date.today() - timedelta(days=1)).isoformat()


@router.get("/status")
def get_status(date: str | None = None):
    """해당 날짜 파이프라인 단계별 상태. date 생략 시 전일(최근 1일치) 사용."""
    date_str = date or _default_date()
    return _build_status_response(date_str)


class RunBody(BaseModel):
    date: str | None = None  # 생략 시 전일(최근 1일치) 사용
    force: bool = False


class RunStepBody(BaseModel):
    date: str | None = None  # 생략 시 전일(최근 1일치) 사용
    step: str
    mode: str  # "only" | "from"


def _run_pipeline_task(date_str: str, force: bool, from_step: str | None) -> None:
    data_dir = _data_dir()
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        mark_run_failed(str(data_dir), date.today(), None, "Invalid date")
        return
    config_dir = _config_dir()
    skills_dir = _skills_dir()
    llm_client = _get_llm_client()
    progress_callback = _progress_callback_factory(data_dir, d)
    try:
        run_pipeline(
            date_str,
            config_dir,
            data_dir,
            skills_dir,
            llm_client,
            force=force,
            from_step=from_step,
            progress_callback=progress_callback,
        )
    except Exception as e:
        mark_run_failed(str(data_dir), d, None, str(e))
        raise
    # 파이프라인 완료 후 자동 git push
    try:
        from pipeline.git_push import auto_push
        auto_push(str(data_dir), d)
    except Exception:
        pass  # push 실패는 파이프라인 성공에 영향 주지 않음
    mark_run_finished(str(data_dir), d)


def _run_single_step_task(date_str: str, step_id: str, force: bool) -> None:
    data_dir = _data_dir()
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        mark_run_failed(str(data_dir), date.today(), step_id, "Invalid date")
        return
    config_dir = _config_dir()
    skills_dir = _skills_dir()
    llm_client = _get_llm_client()
    progress_callback = _progress_callback_factory(data_dir, d)
    try:
        run_step(
            step_id,
            date_str,
            config_dir,
            data_dir,
            skills_dir,
            llm_client,
            force=force,
            progress_callback=progress_callback,
        )
    except Exception as e:
        mark_run_failed(str(data_dir), d, step_id, str(e))
        raise
    mark_run_finished(str(data_dir), d)


@router.post("/run", status_code=202)
def post_run(body: RunBody, background_tasks: BackgroundTasks):
    """파이프라인 전체 실행 (백그라운드). date 생략 시 전일(최근 1일치) 사용."""
    date_str = body.date or _default_date()
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    data_dir = _data_dir()
    run = read_run_status(str(data_dir), d)
    if run and run.get("running"):
        raise HTTPException(status_code=409, detail="already_running")
    # 강제 재실행 시: 기존 체크포인트를 비워서 중단 후 재진입 시 완료/대기 상태가 정확히 보이도록 함
    if body.force:
        clear_checkpoints_for_date(str(data_dir), d)
    start_run(str(data_dir), d)
    background_tasks.add_task(_run_pipeline_task, date_str, body.force, None)
    return {"message": "started", "date": date_str}


@router.post("/run-step", status_code=202)
def post_run_step(body: RunStepBody, background_tasks: BackgroundTasks):
    """단계만 실행 또는 해당 단계부터 끝까지 실행. date 생략 시 전일(최근 1일치) 사용."""
    if body.step not in PIPELINE_STEPS:
        raise HTTPException(status_code=400, detail=f"Invalid step. Must be one of {PIPELINE_STEPS}")
    if body.mode not in ("only", "from"):
        raise HTTPException(status_code=400, detail="mode must be 'only' or 'from'")
    date_str = body.date or _default_date()
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    data_dir = _data_dir()
    run = read_run_status(str(data_dir), d)
    if run and run.get("running"):
        raise HTTPException(status_code=409, detail="already_running")
    start_run(str(data_dir), d)
    if body.mode == "only":
        background_tasks.add_task(_run_single_step_task, date_str, body.step, True)
    else:
        background_tasks.add_task(_run_pipeline_task, date_str, True, body.step)
    return {"message": "started", "date": date_str, "step": body.step, "mode": body.mode}
