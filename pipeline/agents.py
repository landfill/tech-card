"""스킬 기반 에이전트 러너. skills/<name>.md를 system으로, payload를 user로 LLM 호출."""
import json
import logging
from pathlib import Path

from pipeline.ops_logging import format_event

logger = logging.getLogger(__name__)


def load_skill(skills_dir: str | Path, agent_name: str) -> str:
    """skills_dir/agent_name.md 반환."""
    path = Path(skills_dir) / f"{agent_name}.md"
    if not path.is_file():
        raise FileNotFoundError(f"Skill not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def run_agent(
    agent_name: str,
    input_payload: dict | list,
    skills_dir: str | Path,
    llm_client,
    extra_system_suffix: str = "",
) -> str:
    """에이전트 실행: 스킬 마크다운을 system으로, input_payload를 JSON user 메시지로 LLM 호출."""
    system = load_skill(skills_dir, agent_name)
    if extra_system_suffix:
        system = system + "\n\n" + extra_system_suffix
    user = json.dumps(input_payload, ensure_ascii=False, indent=2)
    logger.info(format_event("llm_call_started", agent=agent_name))
    try:
        output = llm_client.generate(system=system, user=user)
    except Exception as exc:
        logger.exception(format_event("llm_call_failed", agent=agent_name, error=str(exc)))
        raise
    logger.info(format_event("llm_call_succeeded", agent=agent_name, output_chars=len(output or "")))
    return output
