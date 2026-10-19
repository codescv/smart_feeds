import hashlib
from typing import Any
from unittest.mock import patch, mock_open
from smart_feeds.tools.dedup import (
    deduplicate_items,
    _compute_hash,
    _normalize_url,
)


def test_normalize_url() -> None:
    """Tests URL normalization strips whitespace, trailing slashes, and tracking params."""
    assert _normalize_url("  https://example.com/post/  ") == "https://example.com/post"
    assert (
        _normalize_url(
            "https://example.com/post/?utm_source=rss&utm_medium=web&utm_campaign=daily"
            "&utm_term=ai&utm_content=top&fbclid=123&gclid=456"
        )
        == "https://example.com/post"
    )
    assert (
        _normalize_url("https://news.ycombinator.com/item?id=999&utm_source=hn")
        == "https://news.ycombinator.com/item?id=999"
    )
    assert (
        _normalize_url("https://www.youtube.com/watch?v=abc123&feature=youtu.be&gclid=xyz")
        == "https://www.youtube.com/watch?v=abc123&feature=youtu.be"
    )
    assert (
        _normalize_url("https://hnrss.org/frontpage?points=100&fbclid=abc")
        == "https://hnrss.org/frontpage?points=100"
    )


def test_compute_hash_16_chars_and_normalized() -> None:
    """Tests that _compute_hash produces a 64-bit (16-char) hash on the normalized URL."""
    h1 = _compute_hash("https://example.com/article")
    h2 = _compute_hash("https://example.com/article/?utm_source=newsletter")
    assert len(h1) == 16
    assert h1 == h2


def test_deduplicate_items(mock_env: Any) -> None:
    """Tests batch deduplication including normalized URL variants."""
    items = [
        {"url": "http://example.com/1", "title": "1"},
        {"url": "http://example.com/2", "title": "2"},
        {"url": "http://example.com/1", "title": "1-dup"},
        {"url": "http://example.com/1/?utm_source=rss", "title": "1-utm-dup"},
    ]

    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()):
        unique = deduplicate_items(items)
        assert len(unique) == 2
        assert unique[0]["url"] == "http://example.com/1"
        assert unique[1]["url"] == "http://example.com/2"


def test_deduplicate_with_existing(mock_env: Any) -> None:
    """Tests deduplication against existing 16-char hashes in seen_urls.txt."""
    items = [
        {"url": "http://example.com/1", "title": "1"},
        {"url": "http://example.com/3", "title": "3"},
    ]

    hash1 = _compute_hash("http://example.com/1")

    with patch("smart_feeds.tools.dedup._load_seen_hashes", return_value={hash1}), \
         patch("smart_feeds.tools.dedup._append_hashes") as mock_append:
        unique = deduplicate_items(items)
        assert len(unique) == 1
        assert unique[0]["url"] == "http://example.com/3"
        mock_append.assert_called_once()


def test_deduplicate_legacy_8_char_hashes(mock_env: Any) -> None:
    """Tests backward compatibility with both normalized and unnormalized 8-char hashes."""
    url_norm_match = "http://example.com/norm-legacy/?utm_source=test"
    url_raw_match = "http://example.com/raw-legacy/?utm_medium=social"
    url_new = "http://example.com/brand-new"

    # 8-char prefix of normalized URL hash
    norm_8_hash = _compute_hash("http://example.com/norm-legacy")[:8]
    # 8-char legacy unnormalized hash (computed directly on raw URL with tracking params)
    raw_8_hash = hashlib.md5(url_raw_match.encode("utf-8")).hexdigest()[:8]

    items = [
        {"url": url_norm_match, "title": "Norm Legacy"},
        {"url": url_raw_match, "title": "Raw Legacy"},
        {"url": url_new, "title": "New Item"},
    ]

    with patch(
        "smart_feeds.tools.dedup._load_seen_hashes",
        return_value={norm_8_hash, raw_8_hash},
    ), patch("smart_feeds.tools.dedup._append_hashes") as mock_append:
        unique = deduplicate_items(items)
        assert len(unique) == 1
        assert unique[0]["url"] == url_new
        mock_append.assert_called_once_with([_compute_hash(url_new)])

