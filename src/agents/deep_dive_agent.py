import os
import config
from typing import Optional, List, Any
from google.adk.agents import Agent
from tools.storage import read_daily_summary, save_deep_dive_report


def create_deep_dive_agent(model_id=None, debug: bool = False):
    """
    Creates the Deep Dive Agent.
    Goal: Read daily summary, visit links, and generate a detailed analysis.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
    
    output_language = os.getenv("OUTPUT_LANGUAGE", "English")

    # Tools
    tools = []
    
    # 1. Storage tools
    tools.append(read_daily_summary)
    tools.append(save_deep_dive_report)
    
    # 2. Browser tools
    # Lazy import to avoid circular dependencies
    from tools.mcp_browser import get_browser_toolset
    user_data_dir = config.get_browser_user_data_dir()
    # If debug is True, headless is False (browser is visible)
    browser_toolset = get_browser_toolset(user_data_dir=user_data_dir, headless=not debug)
    tools.append(browser_toolset)

    instruction = f"""
    You are a Deep Dive Analyst Agent.
    
    Your goal is to provide a comprehensive analysis of the stories from today's Daily Summary (TLDR).
    
    Your workflow:
    1. READ: Use `read_daily_summary` to get the TLDR content consisting of stories with links.
    2. EXTRACT: For each story:
       - Use `browser_navigate` to visit the source URL.
       - Use `browser_get_content` to read the full article/page.
       - If the page is a paywall or inaccessible, skip it.
    3. ANALYZE: For each story, generate a deep dive section including:
       - **Content**: A detailed content of the story. If the content is very long (more than 500 words), summarize it.
       - **Facts**: What actually happened? Key data points.
       - **Opinions**: What are the main arguments or reactions?
       - **Analysis**: Your professional analysis / comments / point of view. Implications, future outlook, or missing context. Use a fair and professional tone.
    4. REPORT: Compile the analysis into a single markdown report.
    5. SAVE: Use `save_deep_dive_report` to save the final report.
    
    # Output Format
    The output should be in markdown format.
    
    Example:
    ```markdown
    # Deep Dive Report - [Date]
    
    ## [Title of Story 1]
    **Source**: [Link]
    ### Content
    ...

    ### Facts
    - ...
    
    ### Opinions
    - ...
    
    ### Analysis
    - ...
    
    ---
    
    ## [Title of Story 2]
    ...
    ```
    
    IMPORTANT: The final report MUST be in {output_language}.
    """

    agent = Agent(
        name="deep_dive_agent",
        model=model_id,
        instruction=instruction,
        tools=tools,
    )

    return agent
