import os
import config
from google.adk.agents import Agent
from tools.storage import (
    read_raw_items_batch, 
    append_to_curated_log, 
    append_to_filtered_log
)

def create_curator_agent(model_id=None):
    """
    Creates the Curator Agent.
    Goal: Read raw items, filter by user interest, and save to the curated log.
    """
    if model_id is None:
        model_id = os.getenv("MODEL_ID", "gemini-2.0-flash")
        
    output_language = os.getenv("OUTPUT_LANGUAGE", "English")

    # Load interests
    # Assuming running from project root
    interests_path = os.path.join(config.get_input_dir(), "interests.md")
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
    4. ENRICH: For selected items, generate a `relevance` explanation and a clean `summary` in {output_language}.
       For filtered items, provide a `reason` why it was filtered.
    5. SAVE: 
       - Use `append_to_curated_log` for SELECTED items.
       - Use `append_to_filtered_log` for FILTERED items.
    
    IMPORTANT: `append_to_curated_log` accepts a LIST of dictionaries.
    Each item must have:
    - `title`: Original title.
    - `url`: Original URL.
    - `source`: Original source.
    - `published`: Original date.
    - `relevance`: Why this item matches the user's interests.
    - `summary`: High-quality summary in {output_language}.
    - `reason`: (Optional) Additional context if needed.

    IMPORTANT: `append_to_filtered_log` accepts a LIST of dictionaries.
    Each item must have:
    - `title`: Original title.
    - `url`: Original URL.
    - `source`: Original source.
    - `published`: Original date.
    - `summary`: High-quality summary in {output_language}.
    - `reason`: Why this item was filtered (e.g., "Irrelevant to user interests", "Duplicate").
    
    Be strict. Quality over quantity.
    """

    agent = Agent(
        name="curator_agent",
        model=model_id,
        instruction=instruction,
        tools=[read_raw_items_batch, append_to_curated_log, append_to_filtered_log],
    )

    return agent
