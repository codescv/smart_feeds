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


def test_env_injection():
    mock_config = {
        "network": {
            "http_proxy": "http://proxy:8080",
            "no_proxy": "localhost"
        },
        "auth": {
            "google_api_key": "test_key",
            "google_cloud_project": "test_project",
            "google_vertexai_project": "test_vertex_project",
            "google_genai_use_vertexai": "1"
        }
    }
    
    # We test the private method directly here as the caching 
    # of __get_parsed_config makes testing its side effects tricky
    config._inject_env_vars(mock_config)
    
    assert os.environ.get("http_proxy") == "http://proxy:8080"
    assert os.environ.get("HTTP_PROXY") == "http://proxy:8080"
    assert os.environ.get("no_proxy") == "localhost"
    assert os.environ.get("NO_PROXY") == "localhost"
    assert os.environ.get("GOOGLE_API_KEY") == "test_key"
    assert os.environ.get("GOOGLE_CLOUD_PROJECT") == "test_project"
    assert os.environ.get("GOOGLE_VERTEXAI_PROJECT") == "test_vertex_project"
    assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "1"
    
    # Cleanup
    for k in ["http_proxy", "HTTP_PROXY", "no_proxy", "NO_PROXY", "GOOGLE_API_KEY", "GOOGLE_CLOUD_PROJECT",
              "GOOGLE_VERTEXAI_PROJECT", "GOOGLE_GENAI_USE_VERTEXAI"]:
        if k in os.environ:
            del os.environ[k]
