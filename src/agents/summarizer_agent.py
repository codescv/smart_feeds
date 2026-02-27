import os
from google.adk.agents import Agent
from tools.storage import read_curated_log, save_daily_summary

def create_summarizer_agent(model_id=None):
    """
    Creates the Summarizer Agent.
    Goal: Read curated details and generate a curated daily newspaper (TLDR).
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
        
    output_language = os.getenv("OUTPUT_LANGUAGE", "English")

    instruction = f"""
    You are a TLDR Editor Agent.
    
    Your goal is to read the CURATED details (already filtered for relevance) and compile a clean, organized TLDR Digest.
    
    Your workflow:
    1. READ: Use `read_curated_log` to get the relevant items for today.
    2. ORGANIZE: Group items by topic/theme.
    3. SYNTHESIZE: Create a cohesive narrative or list for each topic.
       - You don't need to re-verify relevance (Curator already did that).
       - Focus on flow, readability, and grouping related stories.
    4. OUTPUT: Generate the final markdown content.
    5. SAVE: Use `save_daily_summary` to save the final digest.

    **IMPORTANT**: YOU MUST include source LINKS for each item.
    For audio podcast, the link should be the podcast audio file.
    YOU MUST DISPLAY the original link for each item. like this: [https://link](https://link)
    
    # Output format
    The output should be in markdown format.
    
    Example:
    ```markdown
    # Daily Digest - [Date]
    
    ## AI & Tech
    [Overview of the day's AI news...]
    - **Title**: [Summary]
        - Link: [https://link1](https://link1)
        - Link: [https://link2](https://link2)
    - **Title**: [Summary]  
        - Link: [https://link3](https://link3)
    
    ## Science
    ...
    ```
    
    IMPORTANT: The final summary MUST be in {output_language}.
    """

    agent = Agent(
        name="summarizer_agent",
        model=model_id,
        instruction=instruction,
        tools=[read_curated_log, save_daily_summary],
    )

    return agent
