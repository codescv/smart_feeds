import pytest
import os
from unittest.mock import MagicMock, patch, mock_open
from tools.dedup import deduplicate_items, _get_seen_urls_path
from tools.dedup import _compute_hash

def test_deduplicate_items(mock_env):
    items = [
        {"url": "http://example.com/1", "title": "1"},
        {"url": "http://example.com/2", "title": "2"},
        {"url": "http://example.com/1", "title": "1-dup"}, # Duplicate in batch
    ]
    
    # Mock file operations to start empty
    with patch("os.path.exists", return_value=False), \
         patch("builtins.open", mock_open()) as mock_file:
        
        unique = deduplicate_items(items)
        assert len(unique) == 2
        assert unique[0]["url"] == "http://example.com/1"
        assert unique[1]["url"] == "http://example.com/2"

def test_deduplicate_with_existing(mock_env):
    items = [
        {"url": "http://example.com/1", "title": "1"}, # Already seen
        {"url": "http://example.com/3", "title": "3"},
    ]
    
    # Check what hash dedup uses (md5 first 8 chars)
    # http://example.com/1 -> md5 -> ...
    from tools.dedup import _compute_hash
    hash1 = _compute_hash("http://example.com/1")
    
    with patch("tools.dedup._load_seen_hashes", return_value={hash1}), \
         patch("tools.dedup._append_hashes") as mock_append:
        
        unique = deduplicate_items(items)
        assert len(unique) == 1
        assert unique[0]["url"] == "http://example.com/3"
        mock_append.assert_called_once()
