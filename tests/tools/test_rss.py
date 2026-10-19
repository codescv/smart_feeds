import asyncio
from unittest.mock import MagicMock, patch
from smart_feeds.tools.rss import fetch_rss_feed
from smart_feeds.main import process_rss_source, process_source


def test_fetch_rss_feed_success() -> None:
    """Tests that fetch_rss_feed extracts entry fields and feed title as source."""
    mock_feed = MagicMock()
    mock_feed.bozo = 0
    mock_feed.feed = {"title": "Example Tech Feed"}
    mock_entry = {
        "title": "Test Entry",
        "link": "http://example.com/1",
        "summary": "Summary",
        "published": "2023-01-01",
        "links": [{"rel": "enclosure", "href": "http://example.com/audio.mp3"}],
    }
    mock_feed.entries = [mock_entry]

    with patch("feedparser.parse", return_value=mock_feed):
        items = fetch_rss_feed("http://example.com/feed.xml")
        assert len(items) == 1
        assert items[0]["title"] == "Test Entry"
        assert items[0]["media"] == "http://example.com/audio.mp3"
        assert items[0]["source"] == "Example Tech Feed"


def test_fetch_rss_feed_no_title() -> None:
    """Tests that fetch_rss_feed omits 'source' when feed title is empty."""
    mock_feed = MagicMock()
    mock_feed.bozo = 0
    mock_feed.feed = {"title": ""}
    mock_entry = {
        "title": "Test Entry",
        "link": "http://example.com/1",
        "summary": "Summary",
        "published": "2023-01-01",
        "links": [],
    }
    mock_feed.entries = [mock_entry]

    with patch("feedparser.parse", return_value=mock_feed):
        items = fetch_rss_feed("http://example.com/feed.xml")
        assert len(items) == 1
        assert "source" not in items[0]


def test_fetch_rss_feed_bozo_warning() -> None:
    """Tests that fetch_rss_feed handles bozo parse warnings gracefully."""
    mock_feed = MagicMock()
    mock_feed.bozo = 1
    mock_feed.bozo_exception = Exception("Parsing Error")
    mock_feed.entries = []

    with patch("feedparser.parse", return_value=mock_feed):
        items = fetch_rss_feed("http://example.com/bad.xml")
        assert items == []


def test_process_rss_source_text_and_reddit_limit() -> None:
    """Tests deterministic RSS text processing, netloc fallback, and Reddit limit=30."""
    fake_entries = [
        {
            "title": "Post 1",
            "link": "https://www.reddit.com/r/LocalLLaMA/1",
            "summary": "Hello world",
            "published": "2026-10-19",
            "media": "",
        }
    ]
    with (
        patch("smart_feeds.main.fetch_rss_feed", return_value=fake_entries) as mock_fetch,
        patch("smart_feeds.main.deduplicate_items", side_effect=lambda x: x) as mock_dedup,
        patch("smart_feeds.main.append_to_raw_log", return_value="Appended 1") as mock_append,
    ):
        process_rss_source({
            "url": "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day",
            "type": "rss_text",
        })
        mock_fetch.assert_called_once_with(
            "https://www.reddit.com/r/LocalLLaMA/top/.rss?t=day", limit=30
        )
        mock_dedup.assert_called_once()
        expected_mapped = [
            {
                "title": "Post 1",
                "url": "https://www.reddit.com/r/LocalLLaMA/1",
                "source": "www.reddit.com",
                "published": "2026-10-19",
                "content": "Hello world",
            }
        ]
        mock_append.assert_called_once_with(expected_mapped)


def test_process_rss_source_audio() -> None:
    """Tests deterministic RSS audio processing with limit=3 and audio enclosure mapping."""
    fake_entries = [
        {
            "title": "Episode 1",
            "link": "https://podcast.example.com/ep1",
            "summary": "Show notes",
            "published": "2026-10-19",
            "media": "https://podcast.example.com/ep1.mp3",
            "source": "My Podcast",
        }
    ]
    with (
        patch("smart_feeds.main.fetch_rss_feed", return_value=fake_entries) as mock_fetch,
        patch("smart_feeds.main.deduplicate_items", side_effect=lambda x: x),
        patch("smart_feeds.main.append_to_raw_log", return_value="Appended 1") as mock_append,
    ):
        process_rss_source({
            "url": "https://podcast.example.com/feed.xml",
            "type": "rss_audio",
        })
        mock_fetch.assert_called_once_with("https://podcast.example.com/feed.xml", limit=3)
        mock_append.assert_called_once_with([
            {
                "title": "Episode 1",
                "url": "https://podcast.example.com/ep1",
                "source": "My Podcast",
                "published": "2026-10-19",
                "content": "Show notes",
                "audio": "https://podcast.example.com/ep1.mp3",
            }
        ])


def test_process_rss_source_all_seen(capsys) -> None:
    """Tests deterministic RSS processing when all items have already been seen."""
    fake_entries = [
        {
            "title": "Item 1",
            "link": "https://example.com/1",
            "summary": "Text",
            "published": "2026-10-19",
            "media": "",
            "source": "Example",
        }
    ]
    with (
        patch("smart_feeds.main.fetch_rss_feed", return_value=fake_entries) as mock_fetch,
        patch("smart_feeds.main.deduplicate_items", return_value=[]),
        patch("smart_feeds.main.append_to_raw_log") as mock_append,
    ):
        process_rss_source({"url": "https://example.com/rss", "type": "rss_text"})
        mock_fetch.assert_called_once_with("https://example.com/rss", limit=10)
        mock_append.assert_not_called()
        captured = capsys.readouterr()
        assert "All 1 items from https://example.com/rss already seen; 0 new items." in captured.out


def test_process_source_bypasses_llm_for_rss() -> None:
    """Tests that process_source routes rss_text and rss_audio to process_rss_source without LLM."""
    with (
        patch("smart_feeds.main.process_rss_source") as mock_rss,
        patch("smart_feeds.main.create_fetcher_agent") as mock_agent,
    ):
        asyncio.run(process_source({"url": "https://example.com/rss", "type": "rss_text"}))
        mock_rss.assert_called_once_with({"url": "https://example.com/rss", "type": "rss_text"})
        mock_agent.assert_not_called()

