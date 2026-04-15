"""카드뉴스 슬라이드 JSON 생성. 레터 마크다운을 입력으로 사용."""
import json
import re
from pathlib import Path

from pipeline.agents import run_agent
from pipeline.storage import letter_path


def card_generate(
    letter_md: str,
    date_str: str,
    skills_dir: str | Path,
    llm_client,
) -> dict:
    """스킬 card_generate + 레터 본문으로 LLM 호출, 카드 JSON(dict) 반환."""
    payload = {"letter_md": letter_md, "date": date_str}
    out = run_agent("card_generate", payload, skills_dir, llm_client)
    # 응답에서 JSON 블록만 추출 (```json ... ``` 또는 순수 JSON)
    text = out.strip()
    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if json_match:
        text = json_match.group(1).strip()
    parsed = json.loads(text)
    if not isinstance(parsed, dict) or "cards" not in parsed:
        raise ValueError("card_generate output must be a dict with 'cards' array")
    parsed["date"] = parsed.get("date") or date_str
    return parsed


def load_letter_for_date(data_dir: str, d) -> str:
    """해당 날짜 레터 마크다운 파일 내용 반환. 없으면 FileNotFoundError."""
    path = letter_path(data_dir, d)
    if not Path(path).is_file():
        raise FileNotFoundError(f"Letter not found: {path}")
    return Path(path).read_text(encoding="utf-8")
