"""레터 생성 에이전트. 분석·중복 제거 결과를 마크다운 본문으로."""
from pathlib import Path
import re

from pipeline.agents import run_agent

LINK_PLACEHOLDER_RE = re.compile(
    r"(원문|뉴스|레딧|관련|각\s*항목|각\s*프로젝트)[^()\n]{0,20}링크\s*참조"
)


def validate_letter_links(letter_md: str) -> None:
    """Fail generation when the letter claims links exist without rendering them."""
    match = LINK_PLACEHOLDER_RE.search(letter_md)
    if match:
        raise ValueError(f"Letter contains unresolved link placeholder: {match.group(0)}")


def letter_generate(
    analyzed_payload: dict | list,
    skills_dir: str | Path,
    llm_client,
) -> str:
    """스킬 letter_generate + payload로 LLM 호출, 마크다운 본문 문자열 반환."""
    letter_md = run_agent("letter_generate", analyzed_payload, skills_dir, llm_client)
    validate_letter_links(letter_md)
    return letter_md
