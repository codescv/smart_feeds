from typing import Any, List, Optional

from google.adk.agents import Agent

from smart_feeds import config
from smart_feeds.tools.dedup import deduplicate_items
from smart_feeds.tools.http import fetch_website_content
from smart_feeds.tools.mcp_browser import get_browser_toolset
from smart_feeds.tools.rss import fetch_rss_feed
from smart_feeds.tools.storage import append_to_raw_log


def get_tools_for_source(source_type: str, debug: bool = False) -> List[Any]:
    """
    Returns the list of ADK tools configured for the given source_type.
    """
    tools: List[Any] = []
    if source_type == "browser":
        user_data_dir = config.get_browser_user_data_dir()
        # If debug is True, headless is False (browser is visible)
        browser_toolset = get_browser_toolset(
            user_data_dir=user_data_dir, headless=not debug
        )
        tools.append(browser_toolset)
    elif source_type == "http":
        tools.append(fetch_website_content)
    elif source_type == "rss_text":
        tools.append(fetch_rss_feed)
    elif source_type == "rss_audio":
        tools.append(fetch_rss_feed)

    return tools


def create_fetcher_agent(
    model_id: Optional[str] = None,
    tools: Optional[List[Any]] = None,
    source_type: str = "general",
    debug: bool = False,
) -> Agent:
    """
    Creates the Fetcher Agent.
    Goal: Fetch content from sources and save raw items to the raw log.
    """
    if model_id is None:
        model_id = config.get_model_id()

    if tools is None:
        tools = get_tools_for_source(source_type, debug=debug)

    tool_names = {t.__name__ for t in tools if hasattr(t, "__name__")}
    if append_to_raw_log.__name__ not in tool_names:
        tools.append(append_to_raw_log)

    if deduplicate_items not in tools:
        tools.append(deduplicate_items)

    audio_link = ""
    if source_type == "rss_audio":
        audio_link = "- `audio`: The audio file url of the item."

    browser_hint = ""
    if source_type == "browser":
        browser_hint = """
    BROWSER WORKFLOW:
    - First call `browser_navigate(url=...)` to open the target URL.
    - If `browser_navigate` returns `status == "login_required"`, immediately stop and report that authentication is required. Do NOT attempt workarounds.
    - Next, call `browser_extract_items(max_items=..., tab=..., auto_save=True)` (for example, `browser_extract_items(max_items=50, tab="Following")` on X.com, or `browser_extract_items(max_items=5)` on news pages).
    - Because `browser_extract_items` with `auto_save=True` automatically deduplicates and saves new items to the raw log in Python, you do NOT need to call `deduplicate_items` or `append_to_raw_log` again after `browser_extract_items` succeeds!
        """

    instruction = f"""
    You are a Content Fetcher Agent defined for source type: {source_type}.
    
    You will be given a source (URL or RSS feed) and instructions for how to fetch the content.
    Your workflow is:
    1. FETCH: Fetch the content using the provided tools.
    2. EXTRACT: Extract key details for EACH item found.
       - AVOID filtering based on topic/interest. Your job is to capture EVERYTHING potentially useful from this source.
       - Exception: Explicitly exclude ads, spam, or navigation links.
    3. DEDUP: Use `deduplicate_items` to filter out items that have already been fetched.
       - Pass the extracted list of items to `deduplicate_items`.
       - It will return a filtered list of NEW items.
    4. SAVE: Use `append_to_raw_log` to save the FILTERED items to the raw log (only if the deduplicated list is non-empty).
    {browser_hint}
    IMPORTANT: `append_to_raw_log` accepts a LIST of dictionaries.
    Each item in the list must have:
    - `title`: The title of the item.
    - `url`: The link to the item (CRITICAL for deduplication).
    - `source`: The name of the source (e.g. "Hacker News", "X (@handle)").
    - `published`: The publication date/time (if available, else "Unknown").
    - `content`: The content of the item (raw text). Also add the quoted post if the item is a repost.
    {audio_link}
    """

    agent = Agent(
        name="fetcher_agent",
        model=model_id,
        instruction=instruction,
        tools=tools,
    )

    return agent
