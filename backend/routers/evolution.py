"""프롬프트 진화 관리 API."""
from datetime import date, datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.paths import get_data_dir

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


@router.get("/versions/{agent_name}")
def get_versions(agent_name: str):
    """해당 에이전트의 프롬프트 버전 이력."""
    from pipeline.prompt_version_store import list_versions
    versions = list_versions(str(_data_dir()), agent_name)
    return {"agent_name": agent_name, "versions": versions}


@router.get("/current/{agent_name}")
def get_current_prompt(agent_name: str):
    """현재 활성 프롬프트 내용 반환 (진화 버전 또는 base)."""
    from pipeline.prompt_version_store import load_active_prompt, get_latest_version
    data_dir = str(_data_dir())
    version = get_latest_version(data_dir, agent_name)
    prompt = load_active_prompt(data_dir, agent_name)
    if prompt is None:
        skills_dir = Path(_data_dir()).parent / "skills"
        skill_path = skills_dir / f"{agent_name}.md"
        if not skill_path.is_file():
            raise HTTPException(status_code=404, detail=f"Agent {agent_name} not found")
        prompt = skill_path.read_text(encoding="utf-8").strip()
        return {"agent_name": agent_name, "version": "base", "prompt": prompt}
    return {"agent_name": agent_name, "version": f"v{version:03d}", "prompt": prompt}


@router.get("/diff/{agent_name}/{version}")
def get_version_diff(agent_name: str, version: int):
    """특정 버전의 diff 및 메타데이터."""
    from pipeline.prompt_version_store import list_versions
    versions = list_versions(str(_data_dir()), agent_name)
    for v in versions:
        if v.get("version") == version:
            return v
    raise HTTPException(status_code=404, detail=f"Version {version} not found")


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
    config_dir = data_dir.parent / "config"
    skills_dir = data_dir.parent / "skills"
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)

    try:
        anchor = date.fromisoformat(body.date) if body.date else date.today()
    except ValueError:
        anchor = date.today()

    version = evolve_prompt(
        agent_name=body.agent_name,
        data_dir=str(data_dir),
        skills_dir=skills_dir,
        llm_client=llm_client,
        anchor_date=anchor,
        force=body.force,
    )

    if version is None:
        return {"evolved": False, "reason": "진화 조건 미충족 또는 실패"}
    return {"evolved": True, "version": version, "agent_name": body.agent_name}


@router.post("/rollback")
def trigger_rollback(body: RollbackBody):
    """롤백 실행."""
    from pipeline.prompt_version_store import rollback, get_latest_version

    data_dir = str(_data_dir())
    current = get_latest_version(data_dir, body.agent_name)
    if current is None:
        raise HTTPException(status_code=400, detail="이미 base 상태입니다")

    prev = rollback(data_dir, body.agent_name, body.reason)
    if prev is None:
        return {"rolled_back_from": f"v{current:03d}", "now": "base"}
    return {"rolled_back_from": f"v{current:03d}", "now": f"v{prev:03d}"}
