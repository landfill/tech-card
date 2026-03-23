"""hnrss URL 조합 단위 테스트."""
from unittest.mock import patch

from tools.fetch_hnrss import fetch_hnrss


@patch("tools.fetch_hnrss.fetch_rss")
def test_hnrss_newest_without_query(mock_rss):
    mock_rss.return_value = []
    fetch_hnrss("", source_id="x", feed="newest")
    mock_rss.assert_called_once_with("https://hnrss.org/newest", source_id="x")


@patch("tools.fetch_hnrss.fetch_rss")
def test_hnrss_frontpage_with_query(mock_rss):
    mock_rss.return_value = []
    fetch_hnrss("AI", points_min=5, source_id="y", feed="frontpage")
    called_url = mock_rss.call_args[0][0]
    assert called_url.startswith("https://hnrss.org/frontpage?")
    assert "q=AI" in called_url
    assert "points=5" in called_url
