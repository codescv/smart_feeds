import os
import config
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
        user_data_dir = config.get_browser_user_data_dir()
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
    Goal: Fetch content from sources and save raw items to the raw log.
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

    # deduplicate_items tool
    from tools.dedup import deduplicate_items
    if deduplicate_items not in tools:
        tools.append(deduplicate_items)

    browser_close_instruction = ""
    if source_type == "browser":
        browser_close_instruction = (
            "*IMPORTANT*: YOU MUST close the browser using the `browser_close` tool after you are done."
        )

    audio_link = ""
    if source_type == "rss_audio":
        audio_link = "- `audio`: The audio file url of the item."

    instruction = f"""
    You are a Content Fetcher Agent defined for source type: {source_type}.
    
    You will be given a source (URL or RSS feed) and instructions for how to fetch the content.
    Your workflow is:
    1. FETCH: Fetch the content using the provided tools.
    2. EXTRACT: Extract key details for EACH item found.
       - AVOID filtering based on topic/interest. Your job is to capture EVERYTHING potentially useful from this source.
       - Exception: Explicitly exclude ads, spam, or navigation links.
    3. DEDUP: Use `deduplicate_items` filter out items that have already been fetched.
       - Pass the extracted list of items to `deduplicate_items`.
       - It will return a filtered list of NEW items.
    4. SAVE: Use `append_to_raw_log` to save the FILTERED items to the raw log.
    {browser_close_instruction}
    
    IMPORTANT: `append_to_raw_log` accepts a LIST of dictionaries.
    Each item in the list must have:
    - `title`: The title of the item.
    - `url`: The link to the item (CRITICAL for deduplication).
    - `source`: The name of the source (e.g. "Hacker News", "Twitter").
    - `published`: The publication date/time (if available, else "Unknown").
    - `content`: The content of the item (raw text).
    - `original_content` (optional): The original post content if the item is a repost.
    {audio_link}
    """

    agent = Agent(
        name="fetcher_agent",
        model=model_id,
        instruction=instruction,
        tools=tools,
    )

    return agent
