"""프롬프트 진화 관리 API."""
from datetime import date
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.paths import get_config_dir, get_data_dir

router = APIRouter()


def _data_dir() -> Path:
    return get_data_dir()


class EvolveBody(BaseModel):
    agent_name: str
    date: str | None = None
    force: bool = False


class RollbackBody(BaseModel):
    agent_name: str
    reason: str = ""


@router.get("/logs/{agent_name}")
def get_logs(agent_name: str):
    """해당 에이전트의 진화 이력 목록 (최신순)."""
    from pipeline.prompt_version_store import list_evolution_logs
    logs = list_evolution_logs(str(_data_dir()), agent_name)
    return {"agent_name": agent_name, "logs": logs}


@router.get("/current/{agent_name}")
def get_current_prompt(agent_name: str):
    """현재 활성 프롬프트 내용 반환 (skills/{agent}.md)."""
    skills_dir = _data_dir().parent / "skills"
    skill_path = skills_dir / f"{agent_name}.md"
    if not skill_path.is_file():
        raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
    prompt = skill_path.read_text(encoding="utf-8").strip()
    from pipeline.prompt_version_store import get_latest_log
    latest = get_latest_log(str(_data_dir()), agent_name)
    evolved_at = latest.get("timestamp") if latest else None
    return {"agent_name": agent_name, "prompt": prompt, "last_evolved_at": evolved_at}


@router.post("/evolve")
def trigger_evolution(body: EvolveBody):
    """수동 진화 트리거."""
    from pipeline.prompt_evolution import evolve_prompt, EVOLUTION_TARGETS
    from pipeline.llm.client import get_llm_client

    if body.agent_name not in EVOLUTION_TARGETS:
        raise HTTPException(
            status_code=400,
            detail=f"{body.agent_name}은 진화 대상이 아닙니다. 가능: {list(EVOLUTION_TARGETS.keys())}",
        )

    data_dir = _data_dir()
    config_dir = get_config_dir()
    skills_dir = data_dir.parent / "skills"
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)

    try:
        anchor = date.fromisoformat(body.date) if body.date else date.today()
    except ValueError:
        anchor = date.today()

    result = evolve_prompt(
        agent_name=body.agent_name,
        data_dir=str(data_dir),
        skills_dir=skills_dir,
        llm_client=llm_client,
        anchor_date=anchor,
        force=body.force,
    )

    if result is None:
        return {"evolved": False, "reason": "진화 조건 미충족 또는 실패"}
    return {"evolved": True, "agent_name": body.agent_name, "skill_path": f"skills/{body.agent_name}.md"}


@router.post("/rollback")
def trigger_rollback(body: RollbackBody):
    """가장 최근 진화 이전 상태로 skills/{agent}.md 복원."""
    from pipeline.prompt_version_store import get_latest_log

    data_dir = _data_dir()
    skills_dir = data_dir.parent / "skills"
    latest = get_latest_log(str(data_dir), body.agent_name)

    if latest is None:
        raise HTTPException(status_code=400, detail="진화 이력이 없습니다. 롤백할 이전 상태가 없습니다.")

    previous_prompt = latest.get("previous_prompt")
    if not previous_prompt:
        raise HTTPException(status_code=400, detail="이전 프롬프트 내용이 로그에 없습니다.")

    skill_path = skills_dir / f"{body.agent_name}.md"
    skill_path.write_text(previous_prompt + "\n", encoding="utf-8")

    rolled_back_at = latest.get("timestamp", "")
    return {
        "rolled_back": True,
        "agent_name": body.agent_name,
        "restored_from": rolled_back_at,
        "skill_path": f"skills/{body.agent_name}.md",
    }
