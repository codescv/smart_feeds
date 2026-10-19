import os
from typing import Optional
from smart_feeds import config
from google.adk.agents import Agent
from smart_feeds.tools.storage import (
    read_raw_items_batch, 
    append_to_curated_log, 
    append_to_filtered_log
)


def create_curator_agent(model_id: Optional[str] = None) -> Agent:
    """
    Creates the Curator Agent.
    Goal: Read raw items, filter by user interest, and save to the curated log.
    """
    if model_id is None:
        model_id = config.get_model_id()
        
    output_language = config._get_setting("settings", "output_language", default="English")

    # Load interests from workspace directory
    interests_path = os.path.join(config.get_workspace_dir(), "interests.md")
    interests_content = "No specific interests provided."
    if os.path.exists(interests_path):
        with open(interests_path, "r") as f:
            interests_content = f.read()

    instruction = f"""
    You are a Content Curator Agent.
    
    Your goal is to filter the raw stream of information and select only what is relevant to the user's interests.
    
    You have access to the user's interests:
    {interests_content}
    
    Your workflow:
    1. READ: Use `read_raw_items_batch` (or the provided batch) to get items.
    2. ANALYZE: For EACH item, compare it against the user's interests.
    3. DECIDE:
       - If it MATCHES interests: Keep it.
       - If it conflicts with DISLIKES or is IRRELEVANT: Filter it.
    4. EXPLAIN:
       - For selected items, generate a `explain` about why it's relevant and
         the full `content` in {output_language} (translate if needed).
       - For filtered items, provide a concise 1-sentence `reason` why it was filtered (do NOT translate or include `content`).
    5. SAVE: 
       - Use `append_to_curated_log` for SELECTED items.
       - Use `append_to_filtered_log` for FILTERED items.

    Curation Consistency & Source Handling Rules:
    - Cross-Source Consistency: When multiple items in the same batch cover the same underlying event (e.g., an official blog/TechCrunch article and a Reddit discussion thread), prefer keeping the primary/authoritative source (or both if the community thread adds substantial technical benchmarks) and NEVER filter out an authoritative primary report while keeping a secondary rumor thread.
    - Hacker News / Discussion Links: If an item's content is just `[Comments](https://news.ycombinator.com/...)` (such as a Hacker News post), evaluate its relevance based on the title and URL domain, and include the HN discussion URL in `content` so downstream agents have both the article URL and the HN comments link.
    
    IMPORTANT: `append_to_curated_log` accepts a LIST of dictionaries.
    Each item must have:
    - `title`: Original title.
    - `url`: Original URL.
    - `audio`: Audio URL if the original item has one.
    - `source`: Original source.
    - `published`: Original date.
    - `explain`: Why this item matches the user's interests.
    - `content`: full content (translate if needed) in {output_language}.

    IMPORTANT: `append_to_filtered_log` accepts a LIST of dictionaries.
    Each item ONLY needs:
    - `title`: Original title.
    - `url`: Original URL.
    - `source`: Original source.
    - `published`: Original date.
    - `reason`: A concise 1-sentence reason why this item was filtered (e.g., "Irrelevant to user interests", "Duplicate").
    Do NOT include `content` in `append_to_filtered_log` to avoid wasting output tokens translating and outputting rejected content.
    
    All your output should be in {output_language}.
    """

    agent = Agent(
        name="curator_agent",
        model=model_id,
        instruction=instruction,
        tools=[read_raw_items_batch, append_to_curated_log, append_to_filtered_log],
    )

    return agent
