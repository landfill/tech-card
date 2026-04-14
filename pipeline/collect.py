"""수집 오케스트레이션. 소스별 병렬 실행, 실패 시 해당 소스만 스킵. crawl은 async 병렬(브라우저 1개·페이지 N개).
수집 후 기준일(date_str)에 발표된 항목만 남긴다. published가 없거나 다른 날짜면 제외해 당일 뉴스만 보장."""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime
from pathlib import Path

from pipeline.checkpoint import save_checkpoint
from pipeline.config import load_sources
from tools.fetch_crawl import fetch_crawl_async
from tools.fetch_hnrss import fetch_hnrss
from tools.fetch_rdt import fetch_rdt_search, fetch_rdt_subreddit
from tools.fetch_reddit_rss import fetch_reddit_rss
from tools.fetch_rss import fetch_rss
from tools.fetch_twitter import fetch_twitter_search
from pipeline.ops_logging import format_event

logger = logging.getLogger(__name__)


def _published_to_date(published: str) -> date | None:
    """published 문자열(ISO8601 등)에서 날짜만 추출. 파싱 실패·빈 문자열이면 None."""
    if not published or not isinstance(published, str):
        return None
    s = published.strip()
    if not s:
        return None
    try:
        if "T" in s:
            dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
            return dt.date()
        return date.fromisoformat(s[:10])
    except (ValueError, TypeError):
        return None


def _filter_items_by_date(items: list[dict], date_str: str) -> list[dict]:
    """기준일(date_str, YYYY-MM-DD)에 발표된 항목만 남긴다.
    published가 없거나 다른 날짜면 제외(크롤 소스는 published가 비어 있어 제외됨)."""
    try:
        target = date.fromisoformat(date_str)
    except ValueError:
        logger.warning("Invalid date_str %r, skipping date filter", date_str)
        return items
    kept = [i for i in items if _published_to_date(i.get("published") or "") == target]
    return kept


def _crawl_params(source: dict) -> tuple[str, str, list[str] | None, int]:
    """crawl 소스에서 url, source_id, heading_tags, max_items 추출."""
    sid = source.get("id") or ""
    url = source.get("url") or ""
    heading_tags = source.get("heading_tags")
    if isinstance(heading_tags, str):
        heading_tags = [t.strip() for t in heading_tags.split(",") if t.strip()]
    max_items = source.get("max_items")
    if isinstance(max_items, str) and max_items.isdigit():
        max_items = int(max_items)
    elif not isinstance(max_items, int):
        max_items = 50
    return (url, sid, heading_tags or None, max_items)


def _fetch_one(source: dict) -> tuple[str, list[dict]]:
    """소스 하나 수집. (source_id, items) 반환. 예외 시 (source_id, []) 및 로그. crawl 타입은 호출하지 않음."""
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
            feed = source.get("feed") or "frontpage"
            if not query and str(feed).lower() != "newest":
                return (sid, [])
            points_min = source.get("points_min")
            if isinstance(points_min, str) and points_min.isdigit():
                points_min = int(points_min)
            return (
                sid,
                fetch_hnrss(
                    query,
                    points_min=points_min,
                    source_id=sid,
                    feed=str(feed),
                ),
            )
        if stype == "reddit_rss":
            sub = source.get("subreddit") or ""
            if not sub:
                return (sid, [])
            return (sid, fetch_reddit_rss(sub, source_id=sid))
        if stype == "github_blog":
            url = source.get("url") or "https://github.blog/feed/"
            return (sid, fetch_rss(url, source_id=sid))
        if stype == "twitter_cli":
            query = source.get("query") or ""
            if not query:
                return (sid, [])
            max_items = int(source.get("max_items") or 30)
            search_type = source.get("search_type") or "Latest"
            return (sid, fetch_twitter_search(query, source_id=sid, max_items=max_items, search_type=search_type))
        if stype == "rdt_cli":
            query = source.get("query") or ""
            sub = source.get("subreddit") or ""
            max_items = int(source.get("max_items") or 30)
            sort = source.get("sort") or "new"
            time_filter = source.get("time_filter") or "day"
            if query:
                return (sid, fetch_rdt_search(query, source_id=sid, subreddit=sub, max_items=max_items, sort=sort, time_filter=time_filter))
            elif sub:
                return (sid, fetch_rdt_subreddit(sub, source_id=sid, max_items=max_items, sort=sort))
            return (sid, [])
        if stype == "crawl":
            # crawl은 run_collect에서 별도 async 병렬로 처리
            return (sid, [])
        # 미구현 타입은 무시
        logger.warning("Unknown source type %r for %s", stype, sid)
        return (sid, [])
    except Exception as e:
        logger.exception("Collect failed for %s: %s", sid, e)
        return (sid, [])


async def _crawl_all_parallel(crawl_sources: list[dict]) -> list[tuple[str, list[dict]]]:
    """crawl 소스들을 브라우저 1개·페이지 N개로 비동기 병렬 수집. [(source_id, items), ...] 반환."""
    if not crawl_sources:
        return []
    from playwright.async_api import async_playwright

    async def one(s):
        url, sid, heading_tags, max_items = _crawl_params(s)
        if not url:
            return (sid, [])
        items = await fetch_crawl_async(
            url,
            sid,
            heading_tags=heading_tags,
            max_items=max_items,
            browser=browser,
        )
        return (sid, items)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        try:
            results = await asyncio.gather(
                *[one(s) for s in crawl_sources],
                return_exceptions=True,
            )
        finally:
            await browser.close()

    out = []
    for s, r in zip(crawl_sources, results):
        sid = s.get("id") or ""
        if isinstance(r, Exception):
            logger.exception("Crawl failed for %s: %s", sid, r)
            out.append((sid, []))
        else:
            out.append(r)
    return out


def run_collect(
    sources_config_path: str | Path,
    data_dir: str | Path,
    date_str: str,
    max_workers: int = 4,
) -> dict:
    """sources.yaml에서 enabled 소스만 로드해 병렬 수집 후 결과 병합.
    non-crawl: ThreadPoolExecutor로 병렬. crawl: async_playwright + 브라우저 1개·페이지 N개 병렬.
    반환: { "date": date_str, "items": [ ... ], "sources_run": [ id, ... ] }
    체크포인트에 저장: data_dir/checkpoints/{date}/collect.json
    """
    sources = load_sources(sources_config_path)
    data_dir = Path(data_dir)
    crawl_sources = [s for s in sources if (s.get("type") or "").strip().lower() == "crawl"]
    non_crawl_sources = [s for s in sources if (s.get("type") or "").strip().lower() != "crawl"]

    all_items = []
    sources_run = []

    # non-crawl: 기존 스레드 풀 병렬
    if non_crawl_sources:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(_fetch_one, s): s for s in non_crawl_sources}
            for fut in as_completed(futures):
                source = futures[fut]
                sid, items = fut.result()
                sources_run.append(sid)
                all_items.extend(items)
                logger.info(
                    format_event(
                        "source_fetch_succeeded",
                        source_id=sid,
                        source_type=(source.get("type") or "").strip().lower(),
                        items=len(items),
                    )
                )

    # crawl: async 브라우저 1개·페이지 N개 병렬
    if crawl_sources:
        crawl_results = asyncio.run(_crawl_all_parallel(crawl_sources))
        crawl_types = {str(s.get("id") or ""): (s.get("type") or "").strip().lower() for s in crawl_sources}
        for sid, items in crawl_results:
            sources_run.append(sid)
            all_items.extend(items)
            logger.info(
                format_event(
                    "source_fetch_succeeded",
                    source_id=sid,
                    source_type=crawl_types.get(sid, "crawl"),
                    items=len(items),
                )
            )

    # 기준일(date_str)에 발표된 항목만 남김 — 당일 뉴스만 보장
    before = len(all_items)
    all_items = _filter_items_by_date(all_items, date_str)
    dropped = before - len(all_items)
    if dropped > 0:
        logger.info("Date filter %s: kept %d items, dropped %d (published not on target date)", date_str, len(all_items), dropped)
    logger.info(
        format_event(
            "collect_completed",
            date=date_str,
            sources=len(sources_run),
            items=len(all_items),
            dropped=dropped,
        )
    )

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
