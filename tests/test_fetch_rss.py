"""RSS 수집 테스트."""
import pytest

from tools.fetch_rss import fetch_rss


def test_fetch_rss_returns_list():
    """fetch_rss(url)는 항목 리스트를 반환하며, 각 항목에 title, url, summary, published가 있다."""
    # 공개 RSS (Anthropic news - 소량)
    url = "https://www.anthropic.com/news.xml"
    result = fetch_rss(url, source_id="anthropic")
    assert isinstance(result, list)
    for item in result[:3]:
        assert "title" in item
        assert "url" in item
        assert "summary" in item
        assert "published" in item
        assert item.get("source_id") == "anthropic"


def test_fetch_rss_empty_source_id():
    """source_id 없이 호출 시 빈 문자열로 들어감."""
    url = "https://www.anthropic.com/news.xml"
    result = fetch_rss(url)
    assert isinstance(result, list)
    if result:
        assert result[0].get("source_id") == ""
