"""피드백 제출 API."""
import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel

from backend.paths import get_config_dir, get_data_dir

router = APIRouter()
logger = logging.getLogger(__name__)


def _data_dir() -> Path:
    return get_data_dir()


class FeedbackCreate(BaseModel):
    issue_date: str
    type: str
    content: str


def _trigger_evolution(feedback_type: str) -> None:
    """피드백 타입과 연관된 에이전트를 즉시 진화 (force=True)."""
    from datetime import date
    from pipeline.prompt_evolution import EVOLUTION_TARGETS, evolve_prompt
    from pipeline.llm.client import get_llm_client

    data_dir = _data_dir()
    skills_dir = data_dir.parent / "skills"
    config_dir = get_config_dir()
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"

    try:
        llm_client = get_llm_client(llm_path)
    except Exception as e:
        logger.warning("피드백 진화 스킵 — LLM 클라이언트 초기화 실패: %s", e)
        return

    for agent_name, target_types in EVOLUTION_TARGETS.items():
        if feedback_type not in target_types:
            continue
        try:
            version = evolve_prompt(
                agent_name=agent_name,
                data_dir=str(data_dir),
                skills_dir=skills_dir,
                llm_client=llm_client,
                anchor_date=date.today(),
                force=True,
            )
            if version is not None:
                logger.info("피드백 진화 완료: %s v%03d", agent_name, version)
        except Exception as e:
            logger.warning("피드백 진화 실패 (%s): %s", agent_name, e)


@router.get("/types")
def get_feedback_types():
    """사용 가능한 피드백 유형 목록."""
    from pipeline.feedback_store import VALID_FEEDBACK_TYPES
    return {"types": VALID_FEEDBACK_TYPES}


@router.post("")
def create_feedback(body: FeedbackCreate, background_tasks: BackgroundTasks):
    """피드백 한 건 저장 후 연관 에이전트 프롬프트를 백그라운드에서 즉시 진화."""
    from pipeline.feedback_store import save_feedback
    from datetime import datetime
    try:
        d = datetime.strptime(body.issue_date, "%Y-%m-%d").date()
    except ValueError:
        from datetime import date
        d = date.today()
    save_feedback(str(_data_dir()), d, body.type, body.content)
    background_tasks.add_task(_trigger_evolution, body.type)
    return {"ok": True}
