"""프롬프트 진화 엔진. 피드백 기반으로 skills/{agent}.md를 직접 개선."""
import difflib
import logging
import re
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Optional

from pipeline.agents import load_skill
from pipeline.feedback_store import load_feedback_since
from pipeline.prompt_version_store import save_evolution_log, get_latest_log

logger = logging.getLogger(__name__)

# --- 진화 대상 매핑: agent_name -> 반영할 피드백 유형 ---
EVOLUTION_TARGETS: dict[str, list[str]] = {
    "analyze": ["wrong_source", "stale", "missing_trend"],
    "letter_generate": ["tone", "structure", "quality", "wrong_source", "missing_trend"],
}

# --- 진화 조건 상수 ---
MIN_FEEDBACK_FOR_EVOLUTION = 5
EVOLUTION_COOLDOWN_DAYS = 3
FEEDBACK_LOOKBACK_DAYS = 30

# --- 메타프롬프트 ---
EVOLUTION_SYSTEM_PROMPT = """\
당신은 AI 프롬프트 엔지니어입니다. 기존 프롬프트(시스템 프롬프트)와 사용자 피드백을 분석하여, \
피드백을 반영한 개선된 버전의 프롬프트를 작성합니다.

## 핵심 원칙
1. **구조 보존**: 기존 프롬프트의 전체 구조(섹션, 헤딩, frontmatter)를 유지합니다. \
핵심 프레임워크를 바꾸지 않고, 세부 지시사항을 정교하게 다듬습니다.
2. **점진적 개선**: 한 번에 너무 많이 바꾸지 않습니다. 피드백이 직접 지적한 부분만 수정합니다.
3. **명시성 증가**: 모호한 지시를 구체적인 기준으로 대체합니다.
4. **하위 호환**: 기존 입출력 형식(JSON 스키마, 마크다운 구조 등)을 절대 변경하지 않습니다.

## 금지 사항
- 출력 형식(JSON 스키마, 필드명 등)을 변경하지 마세요.
- 프롬프트의 역할/목적을 바꾸지 마세요.
- 기존에 없던 완전히 새로운 섹션을 추가하지 마세요.
- 피드백과 무관한 부분을 수정하지 마세요.

## 출력 형식
반드시 아래 형식으로 출력하세요:

<evolved_prompt>
(개선된 프롬프트 전문 - frontmatter 포함)
</evolved_prompt>

<change_summary>
(변경 사항 요약 - 1~3문장)
</change_summary>
"""


def _build_evolution_user_message(
    agent_name: str,
    current_prompt: str,
    feedback_items: list[dict],
    feedback_summary: str,
) -> str:
    feedback_text = "\n".join(
        f"- [{item.get('type')}] {item.get('content', '')[:300]}"
        for item in feedback_items[:30]
    )
    return f"""\
## 대상 프롬프트: {agent_name}

### 현재 프롬프트 전문:
```
{current_prompt}
```

### 피드백 요약 ({feedback_summary}):
{feedback_text}

### 요청:
위 피드백을 반영하여 프롬프트를 개선해주세요. 구조를 보존하면서 문제점을 해결하세요.
"""


def should_evolve(
    data_dir: str,
    agent_name: str,
    anchor_date: date,
) -> tuple[bool, str]:
    """진화 조건 판정. 반환: (진화 여부, 사유)."""
    if agent_name not in EVOLUTION_TARGETS:
        return False, f"{agent_name}은 진화 대상이 아닙니다"

    target_types = EVOLUTION_TARGETS[agent_name]
    cutoff = anchor_date - timedelta(days=FEEDBACK_LOOKBACK_DAYS)
    all_feedback = load_feedback_since(data_dir, cutoff)
    relevant = [fb for fb in all_feedback if fb.get("type") in target_types]

    if len(relevant) < MIN_FEEDBACK_FOR_EVOLUTION:
        return False, f"피드백 부족 ({len(relevant)}/{MIN_FEEDBACK_FOR_EVOLUTION})"

    # 쿨다운 체크 (최근 로그 기준)
    latest = get_latest_log(data_dir, agent_name)
    if latest:
        ts = latest.get("timestamp", "")
        if ts:
            try:
                last_dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                days_since = (anchor_date - last_dt).days
                if days_since < EVOLUTION_COOLDOWN_DAYS:
                    return False, f"쿨다운 중 ({days_since}/{EVOLUTION_COOLDOWN_DAYS}일)"
            except Exception:
                pass

    type_counts = Counter(fb.get("type") for fb in relevant)
    summary = ", ".join(f"{t} {c}건" for t, c in type_counts.most_common())
    return True, f"피드백 {len(relevant)}건 ({summary})"


def evolve_prompt(
    agent_name: str,
    data_dir: str,
    skills_dir: str | Path,
    llm_client,
    anchor_date: date,
    force: bool = False,
) -> Optional[bool]:
    """프롬프트 진화 실행. skills/{agent}.md를 직접 개선하고 로그 저장.
    반환: True(성공) / None(스킵·실패)."""
    if not force:
        should, reason = should_evolve(data_dir, agent_name, anchor_date)
        if not should:
            logger.info("진화 스킵 (%s): %s", agent_name, reason)
            return None

    skills_dir = Path(skills_dir)

    # 1. 현재 프롬프트 로드 (skills/*.md)
    current_prompt = load_skill(skills_dir, agent_name)

    # 2. 관련 피드백 수집
    target_types = EVOLUTION_TARGETS.get(agent_name, [])
    cutoff = anchor_date - timedelta(days=FEEDBACK_LOOKBACK_DAYS)
    all_feedback = load_feedback_since(data_dir, cutoff)
    relevant = [fb for fb in all_feedback if fb.get("type") in target_types]

    type_counts = Counter(fb.get("type") for fb in relevant)
    feedback_summary = f"총 {len(relevant)}건 - " + ", ".join(
        f"{t} {c}건" for t, c in type_counts.most_common()
    )

    # 3. 메타프롬프트로 LLM 호출
    user_msg = _build_evolution_user_message(
        agent_name, current_prompt, relevant, feedback_summary
    )
    raw_output = llm_client.generate(
        system=EVOLUTION_SYSTEM_PROMPT,
        user=user_msg,
    )

    # 4. 파싱 및 검증
    evolved_prompt = _extract_evolved_prompt(raw_output)
    change_summary = _extract_change_summary(raw_output)

    if not evolved_prompt:
        logger.error("진화 실패 (%s): 프롬프트 추출 불가", agent_name)
        return None

    if not _validate_evolution(current_prompt, evolved_prompt, agent_name):
        logger.error("진화 실패 (%s): 검증 실패", agent_name)
        return None

    # 5. diff 생성
    diff_preview = _generate_diff(current_prompt, evolved_prompt)

    # 6. skills/{agent}.md 직접 덮어쓰기
    skill_path = skills_dir / f"{agent_name}.md"
    skill_path.write_text(evolved_prompt + "\n", encoding="utf-8")

    # 7. 변경 이력 로그 저장 (이전 내용 보관)
    log_entry = {
        "feedback_count": len(relevant),
        "feedback_summary": feedback_summary,
        "feedback_types": dict(type_counts),
        "feedback_items": relevant[:30],
        "change_summary": change_summary or "변경 사항 요약 없음",
        "diff_preview": diff_preview,
        "previous_prompt": current_prompt,
    }
    save_evolution_log(data_dir, agent_name, log_entry)
    logger.info("프롬프트 진화 완료: skills/%s.md 업데이트", agent_name)
    return True


def _extract_evolved_prompt(raw: str) -> Optional[str]:
    match = re.search(
        r"<evolved_prompt>\s*(.*?)\s*</evolved_prompt>",
        raw,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return None


def _extract_change_summary(raw: str) -> Optional[str]:
    match = re.search(
        r"<change_summary>\s*(.*?)\s*</change_summary>",
        raw,
        re.DOTALL,
    )
    if match:
        return match.group(1).strip()
    return None


def _validate_evolution(original: str, evolved: str, agent_name: str) -> bool:
    """진화 결과 검증. 핵심 구조가 보존되었는지 확인."""
    if not evolved or len(evolved) < 50:
        return False

    similarity = difflib.SequenceMatcher(None, original, evolved).ratio()
    if similarity < 0.3:
        logger.warning("진화 거부: 유사도 %.2f (최소 0.3)", similarity)
        return False

    if len(evolved) > len(original) * 5:
        logger.warning("진화 거부: 길이 초과 (%d > %d * 5)", len(evolved), len(original))
        return False

    if agent_name == "analyze":
        if "JSON" not in evolved.upper():
            return False
    elif agent_name == "letter_generate":
        if "마크다운" not in evolved and "markdown" not in evolved.lower():
            return False

    return True


def _generate_diff(original: str, evolved: str) -> str:
    diff = difflib.unified_diff(
        original.splitlines(keepends=True),
        evolved.splitlines(keepends=True),
        fromfile="before",
        tofile="after",
        lineterm="",
    )
    return "\n".join(diff)[:3000]
