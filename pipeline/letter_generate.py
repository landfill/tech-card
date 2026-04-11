"""레터 생성 에이전트. 분석·중복 제거 결과를 마크다운 본문으로."""
from pathlib import Path

from pipeline.agents import run_agent


def letter_generate(
    analyzed_payload: dict | list,
    skills_dir: str | Path,
    llm_client,
    data_dir: str | Path | None = None,
) -> str:
    """스킬 letter_generate + payload로 LLM 호출, 마크다운 본문 문자열 반환."""
    return run_agent("letter_generate", analyzed_payload, skills_dir, llm_client, data_dir=data_dir)
