"""RSS/Atom 수집. 공통 스키마: title, url, summary, published."""
import feedparser
from datetime import datetime, timezone


def fetch_rss(url: str, source_id: str = "") -> list[dict]:
    """URL에서 RSS/Atom 피드를 파싱해 항목 리스트 반환.
    각 항목: source_id, title, url, summary, published (ISO8601 또는 빈 문자열).
    """
    fp = feedparser.parse(url)
    results = []
    for e in fp.entries:
        link = e.get("link") or ""
        title = (e.get("title") or "").strip()
        summary = ""
        if e.get("summary"):
            summary = (e.get("summary") or "").strip()
        elif e.get("description"):
            summary = (e.get("description") or "").strip()
        published = ""
        if e.get("published_parsed"):
            try:
                t = e.published_parsed
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                published = dt.isoformat()
            except Exception:
                published = e.get("published") or ""
        elif e.get("updated_parsed"):
            try:
                t = e.updated_parsed
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                published = dt.isoformat()
            except Exception:
                published = e.get("updated") or ""
        else:
            published = e.get("published") or e.get("updated") or ""
        results.append({
            "source_id": source_id,
            "title": title,
            "url": link,
            "summary": summary,
            "published": published,
        })
    return results
