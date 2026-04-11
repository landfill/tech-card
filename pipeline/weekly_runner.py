"""주간 통합 인사이트 레터 파이프라인.
에이전틱 코딩 & 프론티어 모델 + GitHub & 인프라 트렌드에 집중."""
import json
import logging
import re
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from pipeline import agents
from pipeline.checkpoint import load_checkpoint, save_checkpoint
from pipeline.storage import (
    get_week_dates,
    get_week_id,
    index_path,
    letter_path,
    weekly_card_path,
    weekly_letter_path,
    weekly_meta_path,
)

logger = logging.getLogger(__name__)

WEEKLY_CATEGORIES = [
    "에이전틱 코딩",
    "프론티어 모델",
    "GitHub",
    "인프라 트렌드",
    "CI/CD",
    "오픈소스",
]

WEEKLY_STEPS = [
    "weekly_collect",
    "weekly_analyze",
    "weekly_generate",
    "weekly_card",
]


def _matches_weekly_category(category: str) -> bool:
    """카테고리가 주간 대상(에이전틱 코딩, 인프라)에 해당하는지 부분 매칭."""
    if not category:
        return False
    cat_lower = category.lower()
    for kw in WEEKLY_CATEGORIES:
        if kw.lower() in cat_lower:
            return True
    return False


def _load_week_data(data_dir: str, week_dates: list[date]) -> dict:
    """7일분 index items + letter 본문 수집. 카테고리 필터링 적용."""
    all_items = []
    daily_letters = {}
    daily_items = {}

    for d in week_dates:
        # analyze 체크포인트 우선 (category/impact 포함), fallback으로 index
        items = None
        analyze_cp = load_checkpoint(data_dir, d, "analyze")
        if analyze_cp:
            raw = analyze_cp.get("items") if isinstance(analyze_cp, dict) else analyze_cp
            if isinstance(raw, list) and raw:
                items = raw
        if items is None:
            idx_file = index_path(data_dir, d)
            if Path(idx_file).is_file():
                try:
                    data = json.loads(Path(idx_file).read_text(encoding="utf-8"))
                    raw = data.get("items", []) if isinstance(data, dict) else data
                    if isinstance(raw, list):
                        items = raw
                except Exception:
                    pass
        if items:
            for item in items:
                item["_date"] = d.isoformat()
            all_items.extend(items)
            daily_items[d.isoformat()] = items

        # letter
        lt_file = letter_path(data_dir, d)
        if Path(lt_file).is_file():
            try:
                daily_letters[d.isoformat()] = Path(lt_file).read_text(encoding="utf-8")
            except Exception:
                pass

    total = len(all_items)
    filtered = [i for i in all_items if _matches_weekly_category(i.get("category", ""))]

    return {
        "all_items": all_items,
        "filtered_items": filtered,
        "daily_letters": daily_letters,
        "daily_items": daily_items,
        "total_count": total,
        "filtered_count": len(filtered),
    }


def _load_prev_week_meta(data_dir: str, week_id: str) -> Optional[dict]:
    """전주 메타 JSON 로드. 없으면 None."""
    # week_id에서 전주 계산
    parts = week_id.split("-W")
    if len(parts) != 2:
        return None
    try:
        year = int(parts[0])
        week_num = int(parts[1])
        if week_num > 1:
            prev_id = f"{year}-W{week_num - 1:02d}"
        else:
            prev_id = f"{year - 1}-W52"
    except ValueError:
        return None
    path = weekly_meta_path(data_dir, prev_id)
    if not Path(path).is_file():
        return None
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except Exception:
        return None


def run_weekly_pipeline(
    anchor_date: date,
    data_dir: str | Path,
    skills_dir: str | Path,
    llm_client,
    force: bool = False,
) -> dict:
    """주간 파이프라인 실행. anchor_date가 포함된 주(월~일) 기준."""
    data_dir = str(data_dir)
    skills_dir = Path(skills_dir)
    week_dates = get_week_dates(anchor_date)
    week_id = get_week_id(anchor_date)
    date_range = [week_dates[0].isoformat(), week_dates[-1].isoformat()]

    logger.info("주간 파이프라인 시작: %s (%s ~ %s)", week_id, date_range[0], date_range[1])

    # ─── weekly_collect ───
    collect_cp = None if force else load_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_collect")
    if collect_cp is None:
        week_data = _load_week_data(data_dir, week_dates)
        collect_cp = {
            "week_id": week_id,
            "date_range": date_range,
            "total_items": week_data["total_count"],
            "filtered_items_count": week_data["filtered_count"],
            "items": week_data["filtered_items"],
            "daily_letters": week_data["daily_letters"],
        }
        save_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_collect", collect_cp)
    logger.info("weekly_collect: %d items (filtered from %d)",
                collect_cp.get("filtered_items_count", 0), collect_cp.get("total_items", 0))

    # ─── weekly_analyze ───
    analyze_cp = None if force else load_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_analyze")
    if analyze_cp is None:
        items = collect_cp.get("items", [])
        prev_meta = _load_prev_week_meta(data_dir, week_id)
        payload = {
            "week": week_id,
            "date_range": date_range,
            "total_items": collect_cp.get("total_items", 0),
            "filtered_items": len(items),
            "items_by_date": {},
        }
        # 날짜별 그룹핑
        for item in items:
            d = item.get("_date", "")
            if d not in payload["items_by_date"]:
                payload["items_by_date"][d] = []
            payload["items_by_date"][d].append({
                "title": item.get("title", ""),
                "category": item.get("category", ""),
                "impact": item.get("impact", ""),
                "url": item.get("url", ""),
            })
        if prev_meta:
            payload["prev_week_meta"] = {
                "trend_map": prev_meta.get("trend_map", []),
                "top5": prev_meta.get("top5", []),
            }

        raw = agents.run_agent("weekly_analyze", payload, skills_dir, llm_client, data_dir=data_dir)
        # JSON 파싱
        text = raw.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            text = json_match.group(1).strip()
        try:
            meta = json.loads(text)
        except json.JSONDecodeError:
            logger.error("weekly_analyze JSON 파싱 실패")
            meta = {"week": week_id, "error": "parse_failed", "raw": raw[:500]}

        analyze_cp = meta
        save_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_analyze", analyze_cp)

    # 메타 JSON 저장
    meta_file = weekly_meta_path(data_dir, week_id)
    Path(meta_file).parent.mkdir(parents=True, exist_ok=True)
    Path(meta_file).write_text(json.dumps(analyze_cp, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("weekly_analyze: meta saved -> %s", meta_file)

    # ─── weekly_generate ───
    generate_cp = None if force else load_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_generate")
    if generate_cp is None:
        daily_letters = collect_cp.get("daily_letters", {})
        letters_text = ""
        for d_str in sorted(daily_letters.keys()):
            letters_text += f"\n\n--- {d_str} ---\n{daily_letters[d_str][:3000]}"

        gen_payload = {
            "weekly_meta": analyze_cp,
            "daily_letters": letters_text[:15000],
        }
        letter_md = agents.run_agent("weekly_generate", gen_payload, skills_dir, llm_client, data_dir=data_dir)

        letter_file = weekly_letter_path(data_dir, week_id)
        Path(letter_file).parent.mkdir(parents=True, exist_ok=True)
        Path(letter_file).write_text(letter_md, encoding="utf-8")
        generate_cp = {"path": letter_file}
        save_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_generate", generate_cp)
    logger.info("weekly_generate: letter saved")

    # ─── weekly_card ───
    card_cp = None if force else load_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_card")
    if card_cp is None:
        letter_file = weekly_letter_path(data_dir, week_id)
        letter_md = Path(letter_file).read_text(encoding="utf-8")
        card_payload = {"letter_md": letter_md, "date": week_id}
        raw = agents.run_agent("card_generate", card_payload, skills_dir, llm_client, data_dir=data_dir)
        text = raw.strip()
        json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if json_match:
            text = json_match.group(1).strip()
        try:
            card_data = json.loads(text)
        except json.JSONDecodeError:
            card_data = {"cards": [], "error": "parse_failed"}

        card_file = weekly_card_path(data_dir, week_id)
        Path(card_file).parent.mkdir(parents=True, exist_ok=True)
        Path(card_file).write_text(json.dumps(card_data, ensure_ascii=False, indent=2), encoding="utf-8")
        card_cp = {"path": card_file}
        save_checkpoint(data_dir, week_dates[0], f"weekly_{week_id}_card", card_cp)
    logger.info("weekly_card: cards saved")

    return {
        "week_id": week_id,
        "date_range": date_range,
        "letter_path": weekly_letter_path(data_dir, week_id),
        "meta_path": weekly_meta_path(data_dir, week_id),
    }
