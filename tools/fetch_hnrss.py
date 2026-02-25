"""hnrss.org 피드 수집. 쿼리·점수 필터로 Hacker News RSS."""
import urllib.parse

from tools.fetch_rss import fetch_rss

HNRSS_BASE = "https://hnrss.org/frontpage"


def fetch_hnrss(
    query: str,
    points_min: int | None = None,
    source_id: str = "",
) -> list[dict]:
    """hnrss.org frontpage 검색 RSS. query 필수, points_min 선택."""
    params = {"q": query}
    if points_min is not None:
        params["points"] = str(points_min)
    url = f"{HNRSS_BASE}?{urllib.parse.urlencode(params)}"
    return fetch_rss(url, source_id=source_id)
