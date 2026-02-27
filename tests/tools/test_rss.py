import pytest
from unittest.mock import MagicMock, patch
from tools.rss import fetch_rss_feed

def test_fetch_rss_feed_success():
    mock_feed = MagicMock()
    mock_feed.bozo = 0
    mock_entry = {
        "title": "Test Entry",
        "link": "http://example.com/1",
        "summary": "Summary",
        "published": "2023-01-01",
        "links": [{"rel": "enclosure", "href": "http://example.com/audio.mp3"}]
    }
    mock_feed.entries = [mock_entry]
    
    with patch("feedparser.parse", return_value=mock_feed):
        items = fetch_rss_feed("http://example.com/feed.xml")
        assert len(items) == 1
        assert items[0]["title"] == "Test Entry"
        assert items[0]["media"] == "http://example.com/audio.mp3"

def test_fetch_rss_feed_bozo_warning():
    mock_feed = MagicMock()
    mock_feed.bozo = 1
    mock_feed.bozo_exception = Exception("Parsing Error")
    mock_feed.entries = []
    
    with patch("feedparser.parse", return_value=mock_feed):
        items = fetch_rss_feed("http://example.com/bad.xml")
        assert items == []
