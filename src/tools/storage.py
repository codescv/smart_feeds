import os
import datetime



def _get_details_path() -> str:
    """Returns the path for today's details log."""
    today = datetime.date.today().isoformat()
    return f"data/details/{today}.md"


def _get_summary_path() -> str:
    """Returns the path for today's daily news summary."""
    today = datetime.date.today().isoformat()
    return f"data/daily_news/{today}.md"


import re
from typing import List, Dict, Set

def _extract_urls_from_markdown(content: str) -> Set[str]:
    """
    Extracts all URLs from markdown content.
    Matches standard markdown links [text](url) and bare URLs.
    """
    # Regex for markdown links: [text](url)
    md_link_pattern = r'\[.*?\]\((https?://[^\s\)]+)\)'
    # Regex for bare URLs (simple version)
    url_pattern = r'(?<!\()https?://[^\s\)]+'
    
    urls = set(re.findall(md_link_pattern, content))
    urls.update(re.findall(url_pattern, content))
    return urls


def append_to_details_log(items: List[Dict[str, str]]):
    """
    Appends the given list of items to the daily details markdown log file.
    The file is named YYYY-MM-DD.md and located in the data/details/ directory.
    Performs robust deduplication by checking if the URL is already present in the file.
    
    Args:
        items: List of dictionaries, each containing 'url', 'title', 'source', 'relevance', 'summary'.
    """
    filename = _get_details_path()

    # Ensure details directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    existing_content = ""
    existing_urls = set()
    
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            existing_content = f.read()
            existing_urls = _extract_urls_from_markdown(existing_content)

    new_content_blocks = []
    added_count = 0
    skipped_count = 0

    for item in items:
        url = item.get("url")
        if not url:
            continue
            
        # Normalize URL simple check (strip trailing slash)
        normalized_url = url.rstrip("/")
        
        # Check against existing URLs (also normalized)
        is_duplicate = False
        for existing_url in existing_urls:
            if existing_url.rstrip("/") == normalized_url:
                is_duplicate = True
                break
        
        if is_duplicate:
            skipped_count += 1
            continue

        # Format item as markdown
        title = item.get("title", "No Title")
        source = item.get("source", "Unknown Source")
        relevance = item.get("relevance", "N/A")
        summary = item.get("summary", "No summary provided.")
        
        block = f"## [{title}]({url})\n" \
                f"**Source:** {source}\n" \
                f"**Relevance:** {relevance}\n" \
                f"**Summary:** {summary}\n"
        
        new_content_blocks.append(block)
        existing_urls.add(url) # Add to set to prevent duplicates within the same batch
        added_count += 1

    if not new_content_blocks:
        return f"All {len(items)} items were duplicates and skipped."

    with open(filename, "a", encoding="utf-8") as f:
        f.write("\n".join(new_content_blocks) + "\n\n")

    return f"Appended {added_count} new items. Skipped {skipped_count} duplicates."


def read_daily_details() -> str:
    """
    Reads the content of today's details log.
    """
    filename = _get_details_path()
    if not os.path.exists(filename):
        return "No details found for today."
    
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


def save_daily_summary(content: str):
    """
    Saves the daily summary to the daily news file.
    Overwrites if exists to allow updates.
    """
    filename = _get_summary_path()
    
    # Ensure daily_news directory exists
    os.makedirs(os.path.dirname(filename), exist_ok=True)

    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
        
    return f"Summary saved to {filename}"
