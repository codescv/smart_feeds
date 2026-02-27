import pytest
from unittest.mock import MagicMock, patch, mock_open
from agents.curator_agent import create_curator_agent

@patch("agents.curator_agent.Agent")
@patch("builtins.open", new_callable=mock_open, read_data="- AI\n- Space")
@patch("os.path.exists", return_value=True)
def test_create_curator_agent_with_interests(mock_exists, mock_file, mock_agent_cls, mock_env):
    agent = create_curator_agent()
    
    mock_agent_cls.assert_called_once()
    call_args = mock_agent_cls.call_args[1]
    
    assert call_args["name"] == "curator_agent"
    # Verify interests are injected into instruction
    assert "- AI" in call_args["instruction"]
    assert "- Space" in call_args["instruction"]
    
    # Verify tools
    tool_names = [t.__name__ for t in call_args["tools"]]
    assert "read_raw_items_batch" in tool_names
    assert "append_to_curated_log" in tool_names
    assert "append_to_filtered_log" in tool_names

@patch("agents.curator_agent.Agent")
@patch("os.path.exists", return_value=False)
def test_create_curator_agent_no_interests(mock_exists, mock_agent_cls, mock_env):
    agent = create_curator_agent()
    
    call_args = mock_agent_cls.call_args[1]
    assert "No specific interests provided" in call_args["instruction"]
