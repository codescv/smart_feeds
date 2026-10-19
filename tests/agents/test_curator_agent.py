from typing import Any
from unittest.mock import MagicMock, patch, mock_open
import pytest
from smart_feeds.agents.curator_agent import create_curator_agent


@patch("smart_feeds.agents.curator_agent.Agent")
@patch("builtins.open", new_callable=mock_open, read_data="- AI\n- Space")
@patch("os.path.exists", return_value=True)
def test_create_curator_agent_with_interests(
    mock_exists: MagicMock,
    mock_file: MagicMock,
    mock_agent_cls: MagicMock,
    mock_env: Any,
) -> None:
    """Verifies curator agent creation with interests file and expected tools."""
    create_curator_agent()

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


@patch("smart_feeds.agents.curator_agent.Agent")
@patch("os.path.exists", return_value=False)
def test_create_curator_agent_no_interests(
    mock_exists: MagicMock,
    mock_agent_cls: MagicMock,
    mock_env: Any,
) -> None:
    """Verifies fallback instruction when interests.md does not exist."""
    create_curator_agent()

    call_args = mock_agent_cls.call_args[1]
    assert "No specific interests provided" in call_args["instruction"]


@patch("smart_feeds.agents.curator_agent.Agent")
@patch("os.path.exists", return_value=False)
def test_curator_agent_prompt_filtered_log_and_consistency_rules(
    mock_exists: MagicMock,
    mock_agent_cls: MagicMock,
    mock_env: Any,
) -> None:
    """
    Verifies that curator prompt instructions specify:
    1. Omitting `content` from `append_to_filtered_log` with a concise 1-sentence reason.
    2. Prioritizing primary/authoritative sources over secondary rumor threads.
    3. Evaluating Hacker News items by title/domain and preserving the HN discussion URL.
    """
    create_curator_agent()

    instruction = mock_agent_cls.call_args[1]["instruction"]

    # Verify append_to_filtered_log section omits content and specifies required fields
    filtered_section = instruction.split("IMPORTANT: `append_to_filtered_log`")[1]
    assert "- `title`:" in filtered_section
    assert "- `url`:" in filtered_section
    assert "- `source`:" in filtered_section
    assert "- `published`:" in filtered_section
    assert "- `reason`:" in filtered_section
    assert "- `content`:" not in filtered_section
    assert "Do NOT include `content` in `append_to_filtered_log`" in filtered_section
    assert "1-sentence" in filtered_section

    # Verify cross-source consistency and Hacker News rules
    assert "primary/authoritative source" in instruction
    assert "NEVER filter out an authoritative primary report while keeping a secondary rumor thread" in instruction
    assert "https://news.ycombinator.com/" in instruction
    assert "include the HN discussion URL in `content`" in instruction

