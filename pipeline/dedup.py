"""의미적 중복 제거. 7일 인덱스와 유사도 비교 후 LLM으로 최종 판정."""
import json
import re
from pathlib import Path


def _normalize(text: str) -> str:
    t = (text or "").lower().strip()
    t = re.sub(r"\s+", " ", t)
    return t


def _word_set(text: str) -> set[str]:
    return set(re.findall(r"\w+", _normalize(text), re.ASCII))


def _similarity(a: str, b: str) -> float:
    """0~1. Jaccard on word sets."""
    sa, sb = _word_set(a), _word_set(b)
    if not sa and not sb:
        return 0.0
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def dedup(
    candidates: list[dict],
    recent_7d_items: list[dict],
    llm_client,
    threshold: float = 0.5,
) -> list[dict]:
    """후보 항목 중 recent_7d_items와 실질 중복인 것은 제외. threshold 이상 유사하면 LLM에 질의."""
    recent_titles = [(_normalize((r.get("title") or "") + " " + (r.get("summary") or "")), r) for r in recent_7d_items]
    keep = []
    for c in candidates:
        title_summary = _normalize((c.get("title") or "") + " " + (c.get("summary") or ""))
        is_dup = False
        for (rs, _) in recent_titles:
            sim = _similarity(title_summary, rs)
            if sim >= threshold:
                # LLM에 "이 후보가 지난 7일 내용과 실질 동일한가?" 질의 (선택)
                try:
                    ans = llm_client.generate(
                        system="Answer only YES or NO. Is the following candidate essentially the same news as the recent item (no new version/feature)?",
                        user=json.dumps({"candidate": title_summary[:500], "recent": rs[:500]}),
                    )
                    if "yes" in ans.strip().lower():
                        is_dup = True
                        break
                except Exception:
                    pass
                if sim >= 0.7:
                    is_dup = True
                    break
        if not is_dup:
            keep.append(c)
    return keep
