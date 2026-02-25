"""수집 오케스트레이션. 소스별 병렬 실행, 실패 시 해당 소스만 스킵."""
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

from pipeline.checkpoint import save_checkpoint
from pipeline.config import load_sources
from tools.fetch_hnrss import fetch_hnrss
from tools.fetch_reddit_rss import fetch_reddit_rss
from tools.fetch_rss import fetch_rss

logger = logging.getLogger(__name__)


def _fetch_one(source: dict) -> tuple[str, list[dict]]:
    """소스 하나 수집. (source_id, items) 반환. 예외 시 (source_id, []) 및 로그."""
    sid = source.get("id") or ""
    stype = (source.get("type") or "").strip().lower()
    try:
        if stype == "rss":
            url = source.get("url") or ""
            if not url:
                return (sid, [])
            return (sid, fetch_rss(url, source_id=sid))
        if stype == "hnrss":
            query = source.get("query") or ""
            if not query:
                return (sid, [])
            points_min = source.get("points_min")
            if isinstance(points_min, str) and points_min.isdigit():
                points_min = int(points_min)
            return (sid, fetch_hnrss(query, points_min=points_min, source_id=sid))
        if stype == "reddit_rss":
            sub = source.get("subreddit") or ""
            if not sub:
                return (sid, [])
            return (sid, fetch_reddit_rss(sub, source_id=sid))
        if stype == "github_blog":
            url = source.get("url") or "https://github.blog/feed/"
            return (sid, fetch_rss(url, source_id=sid))
        # 미구현 타입은 무시
        logger.warning("Unknown source type %r for %s", stype, sid)
        return (sid, [])
    except Exception as e:
        logger.exception("Collect failed for %s: %s", sid, e)
        return (sid, [])


def run_collect(
    sources_config_path: str | Path,
    data_dir: str | Path,
    date_str: str,
    max_workers: int = 4,
) -> dict:
    """sources.yaml에서 enabled 소스만 로드해 병렬 수집 후 결과 병합.
    반환: { "date": date_str, "items": [ ... ], "sources_run": [ id, ... ] }
    체크포인트에 저장: data_dir/checkpoints/{date}/collect.json
    """
    sources = load_sources(sources_config_path)
    data_dir = Path(data_dir)
    all_items = []
    sources_run = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = {ex.submit(_fetch_one, s): s for s in sources}
        for fut in as_completed(futures):
            sid, items = fut.result()
            sources_run.append(sid)
            all_items.extend(items)
    payload = {
        "date": date_str,
        "items": all_items,
        "sources_run": sources_run,
    }
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        d = datetime.now().date()
    save_checkpoint(str(data_dir), d, "collect", payload)
    return payload
