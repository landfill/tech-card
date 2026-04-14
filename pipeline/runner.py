"""파이프라인 러너. collect → analyze → summarize → dedup → letter_generate, 체크포인트 연동."""
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date
from pathlib import Path
from typing import Callable

from pipeline.checkpoint import load_checkpoint, save_checkpoint
from pipeline.collect import run_collect
from pipeline.dedup import dedup
from pipeline.letter_generate import letter_generate
from pipeline.storage import letter_path, recent_7d_dates, index_path, card_path
from pipeline import agents
from pipeline.card_generate import card_generate as run_card_generate, load_letter_for_date
from pipeline.card_backgrounds import generate_card_background, update_card_json_bg
from pipeline.prompt_evolution import evolve_prompt, EVOLUTION_TARGETS
from pipeline.ops_logging import format_event

logger = logging.getLogger(__name__)

PIPELINE_STEPS = [
    "collect",
    "analyze",
    "summarize",
    "dedup",
    "letter_generate",
    "card_generate",
    "card_backgrounds",
    "publish",
]

# 분석 단계: 청크당 항목 수, 동시 LLM 호출 수 (병렬 에이전트)
ANALYZE_CHUNK_SIZE = 80
ANALYZE_MAX_WORKERS = 4

ProgressCallback = Callable[[str, str, dict | None], None]  # (step_id, status, detail)


def _load_recent_7d_items(data_dir: str, anchor: date) -> list[dict]:
    """과거 7일 인덱스에서 제목·요약 항목 수집."""
    items: list[dict] = []
    for d in recent_7d_dates(anchor):
        path = index_path(data_dir, d)
        if Path(path).is_file():
            try:
                data = json.loads(Path(path).read_text(encoding="utf-8"))
                raw = data.get("items") if isinstance(data, dict) else data
                if isinstance(raw, list):
                    items.extend(x for x in raw if isinstance(x, dict))
            except Exception:
                pass
    return items


def _run_analyze_chunk(
    chunk: list[dict],
    skills_dir: Path,
    llm_client,
    data_dir: Path,
) -> list[dict]:
    """청크 하나에 대해 analyze 에이전트 실행. 반환: items 리스트."""
    out = agents.run_agent(
        "analyze",
        {"items": chunk},
        skills_dir,
        llm_client,
        data_dir=str(data_dir),
    )
    try:
        parsed = json.loads(out)
        if isinstance(parsed, list):
            return parsed
        if isinstance(parsed, dict) and "items" in parsed:
            return parsed["items"] or []
        return []
    except json.JSONDecodeError:
        logger.warning("Analyze chunk returned invalid JSON, skipping")
        return []


def run_step(
    step_id: str,
    date_str: str,
    config_dir: Path,
    data_dir: Path,
    skills_dir: Path,
    llm_client,
    force: bool = False,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """해당 단계만 실행. 이전 단계는 체크포인트에서 로드. 반환: 해당 단계 결과 요약."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()
    sources_path = config_dir / "sources.yaml"

    def cb(status: str, detail: dict | None = None) -> None:
        if status == "progress":
            logger.info(format_event("step_progress", step=step_id, date=date_str, detail=detail or {}))
        if progress_callback:
            progress_callback(step_id, status, detail)

    if step_id == "collect":
        cb("started", None)
        cp = None if force else load_checkpoint(str(data_dir), d, "collect")
        if cp is None:
            run_collect(sources_path, str(data_dir), date_str)
            cp = load_checkpoint(str(data_dir), d, "collect")
        collect_items = (cp or {}).get("items") or []
        cb("completed", {"items_count": len(collect_items)})
        return {"items_count": len(collect_items)}

    if step_id == "analyze":
        cb("started", None)
        cp = load_checkpoint(str(data_dir), d, "collect")
        collect_items = (cp or {}).get("items") or []
        analyze_cp = None if force else load_checkpoint(str(data_dir), d, "analyze")
        if analyze_cp is None:
            analyzed = []
            chunks = [
                collect_items[i : i + ANALYZE_CHUNK_SIZE]
                for i in range(0, len(collect_items), ANALYZE_CHUNK_SIZE)
            ]
            num_chunks = len(chunks)
            with ThreadPoolExecutor(max_workers=ANALYZE_MAX_WORKERS) as ex:
                futures = {
                    ex.submit(
                        _run_analyze_chunk,
                        chunk,
                        skills_dir,
                        llm_client,
                        data_dir,
                    ): i
                    for i, chunk in enumerate(chunks)
                }
                for fut in as_completed(futures):
                    try:
                        chunk_index = futures[fut]
                        cb("progress", {"chunk_index": chunk_index + 1, "chunk_total": num_chunks})
                        analyzed.extend(fut.result())
                    except Exception as e:
                        logger.exception("Analyze chunk failed: %s", e)
            analyze_cp = {"items": analyzed, "chunks": num_chunks}
            save_checkpoint(str(data_dir), d, "analyze", analyze_cp)
        else:
            analyzed = analyze_cp.get("items") if isinstance(analyze_cp, dict) else []
            if isinstance(analyze_cp, list):
                analyzed = analyze_cp
        cb("completed", {"items_count": len(analyzed)})
        return {"items_count": len(analyzed)}

    if step_id == "summarize":
        cb("started", None)
        analyze_cp = load_checkpoint(str(data_dir), d, "analyze")
        collect_cp = load_checkpoint(str(data_dir), d, "collect")
        collect_items = (collect_cp or {}).get("items") or []
        analyzed = (analyze_cp.get("items") if isinstance(analyze_cp, dict) else []) if analyze_cp else []
        summarize_cp = None if force else load_checkpoint(str(data_dir), d, "summarize")
        if summarize_cp is None:
            sum_out = agents.run_agent("summarize", {"items": analyzed or collect_items}, skills_dir, llm_client, data_dir=str(data_dir))
            summarize_cp = {"raw": sum_out}
            save_checkpoint(str(data_dir), d, "summarize", summarize_cp)
        cb("completed", {})
        return {}

    if step_id == "dedup":
        cb("started", None)
        recent = _load_recent_7d_items(str(data_dir), d)
        analyze_cp = load_checkpoint(str(data_dir), d, "analyze")
        collect_cp = load_checkpoint(str(data_dir), d, "collect")
        collect_items = (collect_cp or {}).get("items") or []
        analyzed = (analyze_cp.get("items") if isinstance(analyze_cp, dict) else []) if analyze_cp else []
        candidates = analyzed or [{"title": x.get("title"), "summary": x.get("summary")} for x in collect_items[:50]]
        deduped = dedup(
            candidates,
            recent,
            llm_client,
            threshold=0.5,
            progress_callback=lambda detail: cb("progress", detail),
        )
        save_checkpoint(str(data_dir), d, "dedup", {"items": deduped})
        cb("completed", {"items_count": len(deduped)})
        return {"items_count": len(deduped)}

    if step_id == "letter_generate":
        cb("started", None)
        dedup_cp = load_checkpoint(str(data_dir), d, "dedup")
        deduped = (dedup_cp or {}).get("items") or []
        letter_md = letter_generate(
            {"items": deduped, "date": date_str},
            skills_dir,
            llm_client,
            data_dir=str(data_dir),
        )
        letter_file = letter_path(str(data_dir), d)
        Path(letter_file).parent.mkdir(parents=True, exist_ok=True)
        Path(letter_file).write_text(letter_md, encoding="utf-8")
        save_checkpoint(str(data_dir), d, "letter_generate", {"path": letter_file})
        index_file = index_path(str(data_dir), d)
        Path(index_file).parent.mkdir(parents=True, exist_ok=True)
        Path(index_file).write_text(
            json.dumps({"items": [{"title": x.get("title"), "summary": x.get("summary"), "category": x.get("category", ""), "impact": x.get("impact", ""), "url": x.get("url", ""), "source_id": x.get("source_id", "")} for x in deduped]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        cb("completed", {"letter_path": letter_file, "items_count": len(deduped)})
        return {"letter_path": letter_file, "items_count": len(deduped)}

    if step_id == "card_generate":
        cb("started", None)
        letter_md = load_letter_for_date(str(data_dir), d)
        card_data = run_card_generate(letter_md, date_str, skills_dir, llm_client, data_dir=str(data_dir))
        card_file = card_path(str(data_dir), d)
        Path(card_file).parent.mkdir(parents=True, exist_ok=True)
        Path(card_file).write_text(
            json.dumps(card_data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        save_checkpoint(str(data_dir), d, "card_generate", {"path": card_file})
        cb("completed", {"card_path": card_file, "cards_count": len(card_data.get("cards", []))})
        return {"card_path": card_file, "cards_count": len(card_data.get("cards", []))}

    if step_id == "card_backgrounds":
        cb("started", None)
        letter_md = load_letter_for_date(str(data_dir), d)
        bg_filename = generate_card_background(
            letter_md, str(data_dir), d, skills_dir, llm_client, config_dir
        )
        update_card_json_bg(str(data_dir), d, bg_filename)
        save_checkpoint(str(data_dir), d, "card_backgrounds", {"bgImage": bg_filename})
        cb("completed", {"bgImage": bg_filename})
        return {"bgImage": bg_filename}

    if step_id == "publish":
        cb("started", None)
        from pipeline.publish import publish
        result = publish(date_str, str(data_dir))
        save_checkpoint(str(data_dir), d, "publish", result)
        cb("completed", result)
        return result

    raise ValueError(f"Unknown step: {step_id}")


def run_pipeline(
    date_str: str,
    config_dir: str | Path,
    data_dir: str | Path,
    skills_dir: str | Path,
    llm_client,
    force: bool = False,
    from_step: str | None = None,
    progress_callback: ProgressCallback | None = None,
) -> dict:
    """단계: collect → … → letter_generate → card_generate → card_backgrounds. from_step 있으면 해당 단계부터 끝까지. 체크포인트 있으면 스킵(force 시 덮어쓰기)."""
    config_dir = Path(config_dir)
    data_dir = Path(data_dir)
    skills_dir = Path(skills_dir)
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        d = date.today()

    logger.info(format_event("run_started", date=date_str, from_step=from_step or "full", force=force))

    steps_to_run = PIPELINE_STEPS
    if from_step:
        if from_step not in PIPELINE_STEPS:
            raise ValueError(f"Unknown from_step: {from_step}")
        idx = PIPELINE_STEPS.index(from_step)
        steps_to_run = PIPELINE_STEPS[idx:]

    # 프롬프트 진화 체크 (파이프라인 실행 전 1회)
    try:
        for agent_name in EVOLUTION_TARGETS:
            evolve_prompt(
                agent_name=agent_name,
                data_dir=str(data_dir),
                skills_dir=skills_dir,
                llm_client=llm_client,
                anchor_date=d,
            )
    except Exception as e:
        logger.warning("프롬프트 진화 체크 실패 (무시): %s", e)

    for step_id in steps_to_run:
        try:
            logger.info(format_event("step_started", step=step_id, date=date_str))
            run_step(
                step_id,
                date_str,
                config_dir,
                data_dir,
                skills_dir,
                llm_client,
                force=force,
                progress_callback=progress_callback,
            )
            cp = load_checkpoint(str(data_dir), d, step_id)
            detail = cp if isinstance(cp, dict) else None
            logger.info(format_event("step_completed", step=step_id, date=date_str, detail=detail))
        except Exception as e:
            logger.error(format_event("step_failed", step=step_id, date=date_str, error=str(e)))
            if progress_callback:
                progress_callback(step_id, "failed", {"error": str(e)})
            raise

    letter_file = letter_path(str(data_dir), d)
    dedup_cp = load_checkpoint(str(data_dir), d, "dedup")
    items_count = len((dedup_cp or {}).get("items") or [])
    result = {"letter_path": letter_file, "items_count": items_count}
    card_file = card_path(str(data_dir), d)
    if Path(card_file).is_file():
        result["card_path"] = card_file
    logger.info(format_event("run_completed", date=date_str, items_count=items_count, card_path=result.get("card_path")))
    return result
