from typing import Optional
import os
from google.adk.agents import Agent
from src.tools.mcp_browser import get_browser_toolset
from src.tools.rss import fetch_rss_feed
from src.tools.storage import append_daily_log


def create_agent(model_id=None, user_data_dir: Optional[str] = None):
    """
    Creates and configures the Smart Feeds agent.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
    
    output_language = os.getenv("OUTPUT_LANGUAGE", "English")

    if user_data_dir is None:
        user_data_dir = os.getenv("BROWSER_USER_DATA_DIR")
        if user_data_dir == "":
            user_data_dir = None

    # Load interests
    interests_path = "inputs/interests.md"
    interests_content = "No specific interests provided."
    if os.path.exists(interests_path):
        with open(interests_path, "r") as f:
            interests_content = f.read()

    # Initialize browser toolset
    browser_toolset = get_browser_toolset(user_data_dir=user_data_dir, headless=False)

    instruction = f"""
    You are a personal content curator agent. Your goal is to help the user manage information overload.
    
    You have access to the user's interests:
    {interests_content}
    
    You will be given a source (URL or RSS feed) and instructions for how to fetch the content.
    Your workflow is:
    1. FETCH: Fetch the content according to the instructions.
       - For websites: Use the available browser tools (e.g., `navigate` to the URL). You may need to use `screenshot` or `evaluate` to inspect content if needed, but primarily get the text content.
       - For RSS: Use `fetch_rss_feed`.
    2. ANALYZE: Analyze the content against the user's interests.
    3. FILTER: If the content matches the user's dislikes, IGNORE it.
    4. SUMMARIZE: If the content is relevant, create a concise summary.
    5. SAVE: Use `append_daily_log` to save the summary to the daily log.
    
    # Output format
    The output should be in markdown format.
    Unless otherwise specified, the output should be grouped into sections, 
    with each section containing a summary of relevant content.
    Multiple similar items can be placed under the same summarized item.
    Each summarized item should contain the orginal link for easy reference.

    Example:
    ```
    ## Topic 1
    [Summary of topic 1...]
    - [Summary Content] [Title1](Link1) [Title2](Link2)
    - [Summary Content] [Title3](Link3)
    
    ## Topic 2
    [Summary of topic 2...]
    - [Summary Content...] [Title4](Link4)

    (Add a few words about what messages are filtered and why)
    ```
    
    IMPORTANT: Both the summary saved to the daily log AND your final response MUST be in {output_language}.
    
    Be efficient. Do not save content that is not interesting.
    """

    agent = Agent(
        name="content_curator",
        model=model_id,
        instruction=instruction,
        tools=[browser_toolset, fetch_rss_feed, append_daily_log],
    )

    return agent
