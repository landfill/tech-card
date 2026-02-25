"""파이프라인 러너. collect → analyze → summarize → dedup → letter_generate, 체크포인트 연동."""
import json
import logging
from datetime import date, timedelta
from pathlib import Path

from pipeline.checkpoint import load_checkpoint, save_checkpoint
from pipeline.collect import run_collect
from pipeline.dedup import dedup
from pipeline.feedback_store import load_feedback_since
from pipeline.letter_generate import letter_generate
from pipeline.storage import letter_path, recent_7d_dates, index_path
from pipeline import agents

logger = logging.getLogger(__name__)


def _load_recent_7d_items(data_dir: str, anchor: date) -> list[dict]:
    """과거 7일 인덱스에서 제목·요약 항목 수집."""
    items = []
    for d in recent_7d_dates(anchor):
        path = index_path(data_dir, d)
        if Path(path).is_file():
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                items.extend(data.get("items") or data if isinstance(data, dict) else data)
            except Exception:
                pass
    return items


def run_pipeline(
    date_str: str,
    config_dir: str | Path,
    data_dir: str | Path,
    skills_dir: str | Path,
    llm_client,
    force: bool = False,
) -> dict:
    """단계: collect → analyze → summarize → dedup → letter_generate. 체크포인트 있으면 스킵(force 시 덮어쓰기)."""
    config_dir = Path(config_dir)
    data_dir = Path(data_dir)
    skills_dir = Path(skills_dir)
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()
    sources_path = config_dir / "sources.yaml"

    # Collect
    cp = None if force else load_checkpoint(str(data_dir), d, "collect")
    if cp is None:
        run_collect(sources_path, str(data_dir), date_str)
        cp = load_checkpoint(str(data_dir), d, "collect")
    collect_items = (cp or {}).get("items") or []

    # Analyze
    analyze_cp = None if force else load_checkpoint(str(data_dir), d, "analyze")
    feedback_suffix = ""
    try:
        cutoff = d - timedelta(days=7)
        feedback_items = load_feedback_since(str(data_dir), cutoff)
        if feedback_items:
            feedback_suffix = "최근 피드백 (수집/분석 개선에 반영할 것):\n" + "\n".join(
                f"- [{x.get('type')}] {x.get('content', '')[:200]}" for x in feedback_items[:15]
            )
    except Exception:
        pass
    if analyze_cp is None:
        analyze_out = agents.run_agent("analyze", {"items": collect_items}, skills_dir, llm_client, extra_system_suffix=feedback_suffix)
        try:
            analyze_cp = json.loads(analyze_out)
        except json.JSONDecodeError:
            analyze_cp = {"raw": analyze_out, "items": []}
        save_checkpoint(str(data_dir), d, "analyze", analyze_cp if isinstance(analyze_cp, dict) else {"raw": analyze_cp})
    analyzed = analyze_cp.get("items") if isinstance(analyze_cp, dict) else []

    # Summarize
    summarize_cp = None if force else load_checkpoint(str(data_dir), d, "summarize")
    if summarize_cp is None:
        sum_out = agents.run_agent("summarize", {"items": analyzed or collect_items}, skills_dir, llm_client)
        summarize_cp = {"raw": sum_out}
        save_checkpoint(str(data_dir), d, "summarize", summarize_cp)

    # Dedup
    recent = _load_recent_7d_items(str(data_dir), d)
    candidates = analyzed or [{"title": x.get("title"), "summary": x.get("summary")} for x in collect_items[:50]]
    deduped = dedup(candidates, recent, llm_client, threshold=0.5)
    save_checkpoint(str(data_dir), d, "dedup", {"items": deduped})

    # Letter generate
    letter_md = letter_generate({"items": deduped}, skills_dir, llm_client)
    letter_file = letter_path(str(data_dir), d)
    Path(letter_file).parent.mkdir(parents=True, exist_ok=True)
    Path(letter_file).write_text(letter_md, encoding="utf-8")
    save_checkpoint(str(data_dir), d, "letter_generate", {"path": letter_file})
    # 인덱스 저장 (7일 중복 제거용)
    index_file = index_path(str(data_dir), d)
    Path(index_file).parent.mkdir(parents=True, exist_ok=True)
    Path(index_file).write_text(
        json.dumps({"items": [{"title": x.get("title"), "summary": x.get("summary")} for x in deduped]}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"letter_path": letter_file, "items_count": len(deduped)}
