import pytest
from unittest.mock import MagicMock, patch
from smart_feeds.agents.summarizer_agent import create_summarizer_agent
import datetime

@patch("smart_feeds.agents.summarizer_agent.Agent")
def test_create_summarizer_agent(mock_agent_cls, mock_env):
    agent = create_summarizer_agent()
    
    mock_agent_cls.assert_called()
    call_args = mock_agent_cls.call_args[1]
    
    assert call_args["name"] == "summarizer_agent"
    
    # Verify tools
    tool_names = [t.__name__ for t in call_args["tools"]]
    assert "read_curated_log" in tool_names
    assert "save_daily_summary" in tool_names
    assert "get_current_date_str" in tool_names
    
    # Verify language injection
    assert "English" in call_args["instruction"]
    
    # Verify instruction references the tool
    assert "get_current_date_str" in call_args["instruction"]

@patch("smart_feeds.agents.summarizer_agent.Agent")
@patch("smart_feeds.config._get_setting")
def test_create_summarizer_agent_custom_prompt(mock_get_setting, mock_agent_cls, mock_env, tmp_path):
    # Setup custom prompt file
    prompt_file = tmp_path / "custom_prompt.md"
    prompt_file.write_text("Custom instructions from file")
    
    def get_setting_mock(section, key, default=None):
        if key == "custom_prompt_path":
            return str(prompt_file)
        if key == "output_language":
            return "English"
        return default
        
    mock_get_setting.side_effect = get_setting_mock
    
    agent = create_summarizer_agent()
    
    mock_agent_cls.assert_called()
    call_args = mock_agent_cls.call_args[1]
    
    assert call_args["instruction"] == "Custom instructions from file"
