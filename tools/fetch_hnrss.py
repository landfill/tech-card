"""hnrss.org 피드 수집. 쿼리·점수 필터로 Hacker News RSS."""
import urllib.parse

from tools.fetch_rss import fetch_rss

# https://hnrss.org/ — frontpage(기본), newest(YC Newest와 동일 흐름)
HNRSS_BASES = {
    "frontpage": "https://hnrss.org/frontpage",
    "newest": "https://hnrss.org/newest",
}


def fetch_hnrss(
    query: str,
    points_min: int | None = None,
    source_id: str = "",
    *,
    feed: str = "frontpage",
) -> list[dict]:
    """hnrss.org RSS. feed: frontpage | newest. query가 비면 해당 피드 전체(필터 없음). points_min은 frontpage 검색에만 의미 있음."""
    base = HNRSS_BASES.get((feed or "frontpage").strip().lower(), HNRSS_BASES["frontpage"])
    q = (query or "").strip()
    params: dict[str, str] = {}
    if q:
        params["q"] = q
    if points_min is not None:
        params["points"] = str(points_min)
    url = base if not params else f"{base}?{urllib.parse.urlencode(params)}"
    return fetch_rss(url, source_id=source_id)
