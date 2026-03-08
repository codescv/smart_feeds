import os
import pytest
from unittest.mock import patch
from smart_feeds import config

@pytest.fixture(autouse=True)
def _clear_cache():
    config.__get_parsed_config.cache_clear()
    yield

def test_defaults():
    config.set_workspace_dir(".")
    with patch("smart_feeds.config.__get_parsed_config", return_value={}):
        assert config.get_workspace_dir() == os.path.abspath(".")
        assert config.get_output_dir() == os.path.join(os.path.abspath("."), "data")
        assert config.get_retry_max_attempts() == 8

def test_config_overrides():
    config.set_workspace_dir("/custom/workspace")
    mock_config = {
        "paths": {"output_dir": "custom_output"},
        "settings": {"retry_max_attempts": 10}
    }
    with patch("smart_feeds.config.__get_parsed_config", return_value=mock_config):
        assert config.get_workspace_dir() == os.path.abspath("/custom/workspace")
        assert config.get_output_dir() == os.path.join(os.path.abspath("/custom/workspace"), "custom_output")
        assert config.get_retry_max_attempts() == 10

def test_absolute_paths():
    config.set_workspace_dir("/custom/workspace")
    mock_config = {
        "paths": {"output_dir": "/abs/path/output"}
    }
    with patch("smart_feeds.config.__get_parsed_config", return_value=mock_config):
        assert config.get_output_dir() == "/abs/path/output"

def test_browser_user_data_dir():
    config.set_workspace_dir("/tmp")
    mock_config = {
        "paths": {"browser_user_data_dir": "custom_browser"}
    }
    with patch("smart_feeds.config.__get_parsed_config", return_value=mock_config):
        assert config.get_browser_user_data_dir() == os.path.join(os.path.abspath("/tmp"), "custom_browser")
