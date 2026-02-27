import pytest
from unittest.mock import MagicMock, patch
from agents.fetcher_agent import create_fetcher_agent, get_tools_for_source

def test_get_tools_for_source_http():
    tools = get_tools_for_source("http")
    assert len(tools) == 1
    assert tools[0].__name__ == "fetch_website_content"

def test_get_tools_for_source_rss():
    tools = get_tools_for_source("rss_text")
    assert len(tools) == 1
    assert tools[0].__name__ == "fetch_rss_feed"

@patch("agents.fetcher_agent.Agent")
def test_create_fetcher_agent(mock_agent_cls, mock_env):
    agent = create_fetcher_agent(source_type="http")
    
    # Verify Agent was initialized
    mock_agent_cls.assert_called_once()
    call_args = mock_agent_cls.call_args[1]
    
    assert call_args["name"] == "fetcher_agent"
    assert call_args["model"] == "gemini-2.0-flash-test" # from mock_env
    
    # Verify tools include standard + implementation specific
    tool_names = [t.__name__ for t in call_args["tools"]]
    assert "append_to_raw_log" in tool_names
    assert "deduplicate_items" in tool_names
    assert "fetch_website_content" in tool_names
