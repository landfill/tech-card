"""X/Twitter 수집. twitter-cli (pipx install twitter-cli) 의 검색 기능을 활용.
설치 안 되어 있으면 빈 리스트 반환 (파이프라인 중단 방지)."""
import json
import logging
import shutil
import subprocess
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _parse_tweet(tweet: dict, source_id: str) -> dict | None:
    """twitter-cli JSON 트윗을 공통 스키마로 변환."""
    text = tweet.get("full_text") or tweet.get("text") or ""
    screen_name = ""
    author = tweet.get("author")
    user = tweet.get("user")
    if isinstance(author, dict):
        screen_name = author.get("screenName") or author.get("screen_name") or author.get("name") or ""
    elif isinstance(user, dict):
        screen_name = user.get("screenName") or user.get("screen_name") or user.get("name") or ""

    tweet_id = str(tweet.get("id") or tweet.get("id_str") or tweet.get("rest_id") or "")
    url = f"https://x.com/{screen_name}/status/{tweet_id}" if tweet_id and screen_name else ""

    published = ""
    created = tweet.get("createdAtISO") or tweet.get("createdAt") or tweet.get("created_at") or ""
    if created:
        try:
            if "T" in created:
                dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(created, "%a %b %d %H:%M:%S %z %Y")
            published = dt.isoformat()
        except (ValueError, TypeError):
            published = created

    title = text[:120].replace("\n", " ").strip()
    if len(text) > 120:
        title += "..."

    return {
        "source_id": source_id,
        "title": f"@{screen_name}: {title}" if screen_name else title,
        "url": url,
        "summary": text[:500],
        "published": published,
    }


def fetch_twitter_search(
    query: str,
    source_id: str = "",
    max_items: int = 30,
    search_type: str = "Latest",
) -> list[dict]:
    """twitter-cli search로 트윗 검색. 공통 스키마 리스트 반환.
    twitter-cli 미설치 시 빈 리스트."""
    if not shutil.which("twitter"):
        logger.warning("twitter-cli not installed, skipping %s", source_id)
        return []

    cmd = [
        "twitter", "search", query,
        "-t", search_type,
        "--max", str(max_items),
        "--json",
    ]
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            logger.warning("twitter search failed (%s): %s", source_id, stderr[:200])
            return []

        data = json.loads(result.stdout)
    except subprocess.TimeoutExpired:
        logger.warning("twitter search timeout for %s", source_id)
        return []
    except (json.JSONDecodeError, Exception) as e:
        logger.warning("twitter search parse error (%s): %s", source_id, e)
        return []

    # twitter-cli JSON: envelope {ok, data: [...]} or {ok, data: {tweets: [...]}} or raw list
    tweets = []
    if isinstance(data, dict):
        inner = data.get("data")
        if isinstance(inner, list):
            tweets = inner
        elif isinstance(inner, dict):
            tweets = inner.get("tweets", [])
        if not tweets:
            tweets = data.get("tweets", [])
    elif isinstance(data, list):
        tweets = data

    results = []
    for t in tweets[:max_items]:
        parsed = _parse_tweet(t, source_id)
        if parsed and parsed.get("title"):
            results.append(parsed)

    logger.info("twitter search '%s': %d tweets", query, len(results))
    return results
