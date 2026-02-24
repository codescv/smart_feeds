import os
from typing import Optional, List, Any
from google.adk.agents import Agent
from tools.storage import append_to_raw_log
from tools.rss import fetch_rss_feed
from tools.http import fetch_website_content

def get_tools_for_source(source_type: str, debug: bool = False) -> List[Any]:
    tools = []
    if source_type == "browser":
        # Lazy import to avoid circular dependencies or unnecessary imports
        from tools.mcp_browser import get_browser_toolset
        user_data_dir = os.getenv("BROWSER_USER_DATA_DIR")
        if user_data_dir == "":
            user_data_dir = None
        # If debug is True, headless is False (browser is visible)
        browser_toolset = get_browser_toolset(user_data_dir=user_data_dir, headless=not debug)
        tools.append(browser_toolset)
    elif source_type == "http":
        tools.append(fetch_website_content)
    elif source_type == "rss_text":
        tools.append(fetch_rss_feed)
    elif source_type == "rss_audio":
        # from tools.audio import transcribe_audio_url
        tools.append(fetch_rss_feed)
        # tools.append(transcribe_audio_url)

    return tools

def create_fetcher_agent(
    model_id=None,
    tools: Optional[List[Any]] = None,
    source_type: str = "general",
    debug: bool = False,
):
    """
    Creates the Fetcher Agent.
    Goal: Fetch content from sources and save raw items to data/all.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
    
    # Ensure raw logger is available to the agent
    if tools is None:
        tools = get_tools_for_source(source_type, debug=debug)
    
    # Check if append_to_raw_log is already in tools (by name)
    tool_names = {t.__name__ for t in tools if hasattr(t, '__name__')}
    if append_to_raw_log.__name__ not in tool_names:
        tools.append(append_to_raw_log)

    browser_instruction = ""
    if source_type == "browser":
        browser_instruction = (
            "*IMPORTANT*: YOU MUST scroll down using the `browser_mouse_wheel` tool with deltaY=10000"
            "before doing anything to make sure there are enough items loaded."
        )

    instruction = f"""
    You are a Content Fetcher Agent defined for source type: {source_type}.
    
    You will be given a source (URL or RSS feed) and instructions for how to fetch the content.
    Your workflow is:
    1. FETCH: Fetch the content using the provided tools.
    {browser_instruction}
    2. EXTRACT: Extract key details for EACH item found.
       - AVOID filtering based on topic/interest. Your job is to capture EVERYTHING potentially useful from this source.
       - Exception: Explicitly exclude ads, spam, or navigation links.
    3. SAVE: Use `append_to_raw_log` to save the extracted items to the raw log.
    
    IMPORTANT: `append_to_raw_log` accepts a LIST of dictionaries.
    Each item in the list must have:
    - `title`: The title of the item.
    - `url`: The link to the item (CRITICAL for deduplication).
    - `source`: The name of the source (e.g. "Hacker News", "Twitter").
    - `published`: The publication date/time (if available, else "Unknown").
    - `content`: The content of the item (raw text).
    - `original_content` (optional): The original post content if the item is a repost.
    """

    agent = Agent(
        name="fetcher_agent",
        model=model_id,
        instruction=instruction,
        tools=tools,
    )

    return agent
