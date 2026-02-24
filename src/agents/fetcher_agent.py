import os
from typing import Optional, List, Any
from google.adk.agents import Agent
from tools.storage import append_to_raw_log

def create_fetcher_agent(
    model_id=None,
    tools: Optional[List[Any]] = None,
    source_type: str = "general",
    extra_instruction: str = "",
):
    """
    Creates the Fetcher Agent.
    Goal: Fetch content from sources and save raw items to data/all.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
    
    # Ensure raw logger is available to the agent
    if tools is None:
        tools = []
    
    # Check if append_to_raw_log is already in tools (by name)
    tool_names = {t.__name__ for t in tools if hasattr(t, '__name__')}
    if append_to_raw_log.__name__ not in tool_names:
        tools.append(append_to_raw_log)

    instruction = f"""
    You are a Content Fetcher Agent defined for source type: {source_type}.
    
    You will be given a source (URL or RSS feed) and instructions for how to fetch the content.
    Your workflow is:
    1. FETCH: Fetch the content using the provided tools.
        - If the source type is `browser`, you should be able to scroll down to get more items if there are not enough.
        - For x posts, if it's a repost, you should get the content for the original post as well.
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
    - `summary`: A brief summary or snippet of the content (raw text).
    
    Specific Instructions for this source:
    {extra_instruction}
    """

    agent = Agent(
        name="fetcher_agent",
        model=model_id,
        instruction=instruction,
        tools=tools,
    )

    return agent
