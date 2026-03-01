import os
from google.adk.agents import Agent
from tools.storage import read_curated_log, save_daily_summary, get_current_date_str

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
    Your goal is to read the CURATED details (already filtered for relevance) and compile
    a clean,organized TLDR Digest.
    
    # Workflow
    1. READ: Use `read_curated_log` to get the items for today.
    2. ORGANIZE: Group items by topic/theme. 
        - Aim for ~6 diverse topics and ~30 sub-items in total for the final output.
        - Don't add numbers for the topics.
    3. SYNTHESIZE: Create a cohesive narrative (summary) or list for each topic.
        - Focus on flow, readability, and grouping related stories.
        - Include facts, opinions, and key insights from the original source.
        - Include a professional analysis / comments / point of view. Implications, future outlook,
          or missing context. Use a fair and professional tone.
    3. GET DATE: Use `get_current_date_str` tool to get the current date.
    4. SAVE SUMMARY: Generate the markdown summary as instructed below. 
        *IMPORTANT*: YOU MUST use `save_daily_summary` tool to save the summary. Don't output it.
    
    # Summary format
    **IMPORTANT**: YOU MUST include source LINKS for EVERY SINGLE item.
    **IMPORTANT**: YOU MUST DISPLAY the original link for each item. like this: [https://link](https://link)

    The summary should be in markdown format like the following example:
    ```markdown
    # Daily Digest - [Date from get_current_date_str]
    
    ## AI & Tech
    [Overview of the day's AI news...]
    - **Title**: Summary
        - the Facts: [facts]    
        - the Opinions: [opinions]
        - the Analysis: [analysis]
        - Link: [https://link1](https://link1)
        - Link: [https://link2](https://link2)
    - **Title**: Summary
        - the Facts: [facts]
        - the Opinions: [opinions]
        - the Analysis: [analysis]
        - Link: [https://link3](https://link3)
    
    ## Science
    ...
    ``` // (end of example)
    
    Translate ALL text in the markdown file into {output_language}.
    If there are special terms, you can list the term in the original language with in a bracket.
    """

    agent = Agent(
        name="summarizer_agent",
        model=model_id,
        instruction=instruction,
        tools=[read_curated_log, save_daily_summary, get_current_date_str],
    )

    return agent
