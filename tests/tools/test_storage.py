from typing import Any
from unittest.mock import patch
from smart_feeds.tools.storage import (
    _clean_title,
    _clean_html_to_markdown,
    _extract_urls_from_markdown,
    append_to_raw_log,
    get_raw_item_count,
)


def test_clean_title() -> None:
    """Tests title cleaning, newline removal, and 200-character truncation limit."""
    assert _clean_title("<b>Hello</b> World") == "**Hello** World"
    assert _clean_title("  Space   ") == "Space"
    assert _clean_title("Line\nBreak") == "Line Break"
    # Titles between 80 and 200 chars should be preserved without truncation
    assert len(_clean_title("a" * 120)) == 120
    assert len(_clean_title("a" * 200)) == 200
    # Titles exceeding 200 chars should be truncated to 200 chars with ellipsis
    truncated = _clean_title("a" * 250)
    assert len(truncated) == 200
    assert truncated == ("a" * 197) + "..."


def test_clean_html_to_markdown() -> None:
    html = "<h1>Title</h1><p>Body</p>"
    md = _clean_html_to_markdown(html)
    assert "**Title**" in md
    assert "Body" in md


def test_extract_urls_from_markdown() -> None:
    """Tests extracting both markdown link URLs and bare URLs."""
    md = "Check [Google](https://google.com) or https://example.com"
    urls = _extract_urls_from_markdown(md)
    assert "https://google.com" in urls
    assert "https://example.com" in urls
    assert len(urls) == 2


def test_get_raw_item_count(tmp_path: Any) -> None:
    """Tests that get_raw_item_count returns exact item count without off-by-one."""
    with patch("smart_feeds.config.get_output_dir", return_value=str(tmp_path)):
        assert get_raw_item_count() == 0

        append_to_raw_log(
            [
                {"title": "Item 1", "url": "https://example.com/1"},
                {"title": "Item 2", "url": "https://example.com/2"},
            ]
        )
        assert get_raw_item_count() == 2

        append_to_raw_log(
            [
                {"title": "Item 3", "url": "https://example.com/3"},
            ]
        )
        assert get_raw_item_count() == 3

