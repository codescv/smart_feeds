from typing import Optional, List, Callable, Any
import os
from google.adk.agents import Agent
from tools.mcp_browser import get_browser_toolset
from tools.rss import fetch_rss_feed
from tools.storage import append_to_details_log, read_daily_details, save_daily_summary


def create_fetcher_agent(
    model_id=None,
    tools: Optional[List[Any]] = None,
    source_type: str = "general",
    extra_instruction: str = "",
):
    """
    Creates the Fetcher Agent.
    Goal: Fetch content, filter it, and append details to the daily log.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
    
    output_language = os.getenv("OUTPUT_LANGUAGE", "English")
    
    # Load interests
    # Assuming running from project root
    interests_path = "inputs/interests.md"
    interests_content = "No specific interests provided."
    if os.path.exists(interests_path):
        with open(interests_path, "r") as f:
            interests_content = f.read()

    instruction = f"""
    You are a Content Fetcher Agent defined for source type: {source_type}.
    
    You have access to the user's interests:
    {interests_content}
    
    You will be given a source (URL or RSS feed) and instructions for how to fetch the content.
    Your workflow is:
    1. FETCH: Fetch the content using the provided tools.
    2. ANALYZE: Analyze the content against the user's interests.
    3. FILTER: If the content matches the user's dislikes or is irrelevant, IGNORE it.
    4. EXTRACT: If the content is relevant, extract key details for EACH item.
    5. SAVE: Use `append_to_details_log` to save the extracted items to the daily details log.
    
    IMPORTANT: `append_to_details_log` accepts a LIST of dictionaries.
    Each item in the list must have:
    - `title`: The title of the item.
    - `url`: The link to the item (CRITICAL for deduplication).
    - `source`: The name of the source (e.g. "Hacker News", "Twitter").
    - `relevance`: Why it matches interests.
    - `summary`: A brief summary of the content in {output_language}.
    
    Example usage:
    ```python
    items = [
        {{"title": "Example Title", "url": "https://example.com/1", "source": "Example", "relevance": "AI news", "summary": "..."}},
        {{"title": "Another Title", "url": "https://example.com/2", "source": "Example", "relevance": "Tech", "summary": "..."}}
    ]
    append_to_details_log(items)
    ```
    
    Be efficient. Do not save "noise".
    ENSURE the summary is in {output_language}.
    
    Specific Instructions for this source:
    {extra_instruction}
    """

    agent = Agent(
        name="fetcher_agent",
        model=model_id,
        instruction=instruction,
        tools=tools if tools else [],
    )

    return agent


def create_summarizer_agent(model_id=None):
    """
    Creates the Summarizer Agent.
    Goal: Read daily details and generate a curated daily newspaper.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
        
    output_language = os.getenv("OUTPUT_LANGUAGE", "English")

    instruction = f"""
    You are a TLDR Editor Agent.
    
    Your goal is to read the raw details collected by the Fetcher Agent and compile a clean, organized TLDR Digest.
    
    Your workflow:
    1. READ: Use `read_daily_details` to get all the items collected today.
    2. ORGANIZE: Group items by topic.
    3. SUMMARIZE: Create a cohesive narrative or list for each topic.
    4. OUTPUT: Generate the final markdown content.
    5. SAVE: Use `save_daily_summary` to save the final digest.
    
    # Output format
    The output should be in markdown format.
    Unless otherwise specified, the output should be grouped into sections, 
    with each section containing a summary of relevant content.
    Multiple similar items can be placed under the same summarized item.
    Each summarized item should contain the original link for easy reference.
    
    Example:
    ```markdown
    # TLDR - [Date]
    
    ## Topic 1
    [Summary of topic 1...]
    - [Summary Content] [Title1](Link1) [Title2](Link2)
    - [Summary Content] [Title3](Link3)
    
    ## Topic 2
    [Summary of topic 2...]
    - [Summary Content...] [Title4](Link4)
    
    (Add a few words about what messages are filtered and why)
    ```
    
    IMPORTANT: The final summary MUST be in {output_language}.
    """

    agent = Agent(
        name="summarizer_agent",
        model=model_id,
        instruction=instruction,
        tools=[read_daily_details, save_daily_summary],
    )

    return agent
