import pytest
from unittest.mock import MagicMock, patch
from agents.summarizer_agent import create_summarizer_agent

@patch("agents.summarizer_agent.Agent")
def test_create_summarizer_agent(mock_agent_cls, mock_env):
    agent = create_summarizer_agent()
    
    mock_agent_cls.assert_called_once()
    call_args = mock_agent_cls.call_args[1]
    
    assert call_args["name"] == "summarizer_agent"
    
    # Verify tools
    tool_names = [t.__name__ for t in call_args["tools"]]
    assert "read_curated_log" in tool_names
    assert "save_daily_summary" in tool_names
    
    # Verify language injection
    assert "English" in call_args["instruction"]
