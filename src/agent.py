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

    # Load interests
    interests_path = "inputs/interests.md"
    interests_content = "No specific interests provided."
    if os.path.exists(interests_path):
        with open(interests_path, "r") as f:
            interests_content = f.read()

    # Initialize browser toolset
    browser_toolset = get_browser_toolset(user_data_dir=user_data_dir)

    instruction = f"""
    You are a personal content curator agent. Your goal is to help the user manage information overload.
    
    You have access to the user's interests:
    {interests_content}
    
    Your workflow is:
    1. You will be given a source (URL or RSS feed).
    2. Fetch the content. 
       - For websites: Use the available browser tools (e.g., `navigate` to the URL). You may need to use `screenshot` or `evaluate` to inspect content if needed, but primarily get the text content.
       - For RSS: Use `fetch_rss_feed`.
    3. Analyze the content against the user's interests.
    4. FILTER: If the content is NOT relevant or is "noise" (e.g. celebrity gossip, sports, politics if not interested), IGNORE it.
    5. SUMMARIZE: If the content is relevant, create a concise summary.
    6. SAVE: Use `append_daily_log` to save the summary to the daily log.
    
    Format the summary as:
    ## [Title](Link)
    **Source:** [Source Name]
    **Summary:** [Your summary]
    **Relevance:** [Why this matches user interests]
    
    Be efficient. Do not save content that is not interesting.
    """

    agent = Agent(
        name="content_curator",
        model=model_id,
        instruction=instruction,
        tools=[browser_toolset, fetch_rss_feed, append_daily_log],
    )

    return agent
