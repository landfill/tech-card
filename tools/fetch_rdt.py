"""Reddit 수집. rdt-cli 우선 사용, 실패 시 Reddit JSON API 직접 호출로 fallback.
rdt-cli: pipx install rdt-cli. Keychain 문제로 blocking될 수 있어 timeout 짧게 설정."""
import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone

import httpx

logger = logging.getLogger(__name__)

_REDDIT_UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"


def _parse_post(post: dict, source_id: str) -> dict | None:
    """Reddit 포스트를 공통 스키마로 변환."""
    title = (post.get("title") or "").strip()
    if not title:
        return None

    permalink = post.get("permalink") or ""
    url = f"https://www.reddit.com{permalink}" if permalink.startswith("/") else permalink
    if not url:
        url = post.get("url") or ""

    selftext = post.get("selftext") or post.get("body") or ""
    subreddit = post.get("subreddit") or ""
    author = post.get("author") or ""
    score = post.get("score") or post.get("ups") or 0
    num_comments = post.get("num_comments") or 0

    summary_parts = []
    if subreddit:
        summary_parts.append(f"r/{subreddit}")
    if author:
        summary_parts.append(f"u/{author}")
    if score:
        summary_parts.append(f"score:{score}")
    if num_comments:
        summary_parts.append(f"comments:{num_comments}")
    meta = " | ".join(summary_parts)

    body = selftext[:400] if selftext else ""
    summary = f"{meta}\n{body}".strip() if meta else body

    published = ""
    created_utc = post.get("created_utc") or post.get("created")
    if created_utc:
        try:
            if isinstance(created_utc, (int, float)):
                dt = datetime.fromtimestamp(created_utc, tz=timezone.utc)
                published = dt.isoformat()
            elif isinstance(created_utc, str):
                published = created_utc
        except (ValueError, OSError):
            pass

    return {
        "source_id": source_id,
        "title": title,
        "url": url,
        "summary": summary,
        "published": published,
    }


# ─── Reddit JSON API (fallback) ───


def _reddit_api_search(
    query: str,
    subreddit: str = "",
    sort: str = "new",
    time_filter: str = "day",
    limit: int = 30,
) -> list[dict]:
    """Reddit JSON API로 직접 검색. 인증 불필요."""
    if subreddit:
        url = f"https://www.reddit.com/r/{subreddit}/search.json"
        params = {"q": query, "sort": sort, "t": time_filter, "limit": limit, "restrict_sr": "on"}
    else:
        url = "https://www.reddit.com/search.json"
        params = {"q": query, "sort": sort, "t": time_filter, "limit": limit}

    r = httpx.get(url, params=params, headers={"User-Agent": _REDDIT_UA}, timeout=10, follow_redirects=True)
    r.raise_for_status()
    children = r.json().get("data", {}).get("children", [])
    return [c.get("data", {}) for c in children]


def _reddit_api_subreddit(
    subreddit: str,
    sort: str = "new",
    limit: int = 30,
) -> list[dict]:
    """Reddit JSON API로 서브레딧 최신 글 수집."""
    url = f"https://www.reddit.com/r/{subreddit}/{sort}.json"
    params = {"limit": limit}

    r = httpx.get(url, params=params, headers={"User-Agent": _REDDIT_UA}, timeout=10, follow_redirects=True)
    r.raise_for_status()
    children = r.json().get("data", {}).get("children", [])
    return [c.get("data", {}) for c in children]


# ─── rdt-cli wrapper ───


def _run_rdt(cmd: list[str], source_id: str) -> list[dict] | None:
    """rdt-cli 명령 실행. 성공 시 포스트 리스트, 실패/timeout 시 None (fallback 유도)."""
    if not shutil.which("rdt"):
        return None

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
    except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception):
        return None

    posts = []
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            posts = inner
        elif isinstance(inner, dict):
            posts = inner.get("posts", [])
        if not posts:
            posts = data.get("posts", [])
    elif isinstance(data, list):
        posts = data

    return posts


# ─── 공개 API ───


def fetch_rdt_search(
    query: str,
    source_id: str = "",
    subreddit: str = "",
    max_items: int = 30,
    sort: str = "new",
    time_filter: str = "day",
) -> list[dict]:
    """Reddit 검색. rdt-cli 우선, 실패 시 JSON API fallback."""
    # rdt-cli 시도
    cmd = ["rdt", "search", query, "-s", sort, "-t", time_filter, "--json"]
    if subreddit:
        cmd.extend(["-r", subreddit])
    raw = _run_rdt(cmd, source_id)

    if raw is None:
        # fallback: Reddit JSON API
        try:
            raw = _reddit_api_search(query, subreddit=subreddit, sort=sort, time_filter=time_filter, limit=max_items)
            logger.info("reddit API search '%s': %d posts (fallback)", query, len(raw))
        except Exception as e:
            logger.warning("reddit API search failed (%s): %s", source_id, e)
            return []

    results = []
    for p in raw[:max_items]:
        parsed = _parse_post(p, source_id)
        if parsed:
            results.append(parsed)

    logger.info("rdt search '%s': %d items", query, len(results))
    return results


def fetch_rdt_subreddit(
    subreddit: str,
    source_id: str = "",
    max_items: int = 30,
    sort: str = "new",
) -> list[dict]:
    """서브레딧 최신 글. rdt-cli 우선, 실패 시 JSON API fallback."""
    cmd = ["rdt", "sub", subreddit, "-s", sort, "--json"]
    raw = _run_rdt(cmd, source_id)

    if raw is None:
        try:
            raw = _reddit_api_subreddit(subreddit, sort=sort, limit=max_items)
            logger.info("reddit API r/%s: %d posts (fallback)", subreddit, len(raw))
        except Exception as e:
            logger.warning("reddit API sub failed (%s): %s", source_id, e)
            return []

    results = []
    for p in raw[:max_items]:
        parsed = _parse_post(p, source_id)
        if parsed:
            results.append(parsed)

    logger.info("rdt sub r/%s: %d items", subreddit, len(results))
    return results
