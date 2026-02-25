"""Reddit 서브레딧 RSS. URL은 .../r/{subreddit}.rss"""
from tools.fetch_rss import fetch_rss

REDDIT_RSS_TEMPLATE = "https://www.reddit.com/r/{subreddit}.rss"


def fetch_reddit_rss(subreddit: str, source_id: str = "") -> list[dict]:
    """서브레딧 최신 포스트 RSS."""
    url = REDDIT_RSS_TEMPLATE.format(subreddit=subreddit.strip())
    return fetch_rss(url, source_id=source_id)
