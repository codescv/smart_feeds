import feedparser
import os
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


def fetch_rss_feed(url: str, limit: int = 5) -> List[Dict[str, str]]:
    """
    Fetches an RSS feed and returns the latest items.
    Respects HTTP_PROXY environment variable.
    """
    # feedparser uses urllib, which respects HTTP_PROXY env var automatically
    # but we can also explicitly pass it if needed, though typically env var is enough for urllib.

    logger.info(f"Fetching RSS feed: {url}")

    # Check if proxy is set in env, just for logging
    if os.environ.get("HTTP_PROXY"):
        logger.info(f"Using proxy: {os.environ.get('HTTP_PROXY')}")

    feed = feedparser.parse(url)

    if feed.bozo:
        logger.warning(f"Error parsing feed {url}: {feed.bozo_exception}")

    items = []
    for entry in feed.entries[:limit]:
        summary = entry.get("summary", "")
        if not isinstance(summary, str):
            summary = str(summary)

        items.append(
            {
                "title": entry.get("title", "No Title"),
                "link": entry.get("link", ""),
                "summary": summary[:500] + "..." if len(summary) > 500 else summary,
                "published": entry.get(
                    "published", entry.get("updated", "Unknown Date")
                ),
            }
        )

    return items
