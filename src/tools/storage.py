import os
import datetime
import config
import re
import html2text
from typing import List, Dict, Set, Optional


SEPARATOR = "\n---\n"


def _get_details_path() -> str:
    """Returns the path for today's details log."""
    today = datetime.date.today().isoformat()
    return os.path.join(config.get_output_dir(), "details", f"{today}.md")


def _get_summary_path() -> str:
    """Returns the path for today's daily news summary (TLDR)."""
    today = datetime.date.today().isoformat()
    return os.path.join(config.get_output_dir(), "tldr", f"{today}.md")


def _get_raw_path() -> str:
    """Returns the path for today's raw collected items."""
    today = datetime.date.today().isoformat()
    return os.path.join(config.get_output_dir(), "all", f"{today}.md")


def _get_curated_path() -> str:
    """Returns the path for today's curated items."""
    today = datetime.date.today().isoformat()
    return os.path.join(config.get_output_dir(), "curated", f"{today}.md")


def _get_filtered_path() -> str:
    """Returns the path for today's filtered items."""
    today = datetime.date.today().isoformat()
    return os.path.join(config.get_output_dir(), "curated", f"{today}.filtered.md")


def _clean_html_to_markdown(html_content: str) -> str:
    """
    Converts HTML content to Markdown using html2text.
    """
    if not html_content:
        return ""
    
    h = html2text.HTML2Text()
    h.ignore_links = False
    h.ignore_images = False
    h.body_width = 0  # Disable line wrapping
    
    try:
        markdown = h.handle(html_content)
        
        # Post-process to convert headers to bold
        # Split by lines
        lines = markdown.split('\n')
        new_lines = []
        for line in lines:
            # Check if line starts with headers (#, ##, etc)
            # We use a regex to capture the content
            match = re.match(r'^(#+)\s+(.*)', line)
            if match:
                content = match.group(2)
                # Convert to bold
                new_lines.append(f"**{content}**")
            else:
                new_lines.append(line)
        
        return "\n".join(new_lines).strip()
    except Exception as e:
        # Fallback if something goes wrong
        print(f"Error converting HTML to Markdown: {e}")
        return html_content

def _clean_title(title: str) -> str:
    """
    Cleans the title:
    1. Removes HTML tags.
    2. Removes newlines.
    3. Truncates to 80 characters.
    """
    if not title:
        return "No Title"
    
    # Remove HTML tags
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    
    try:
        clean_title = h.handle(title).strip()
    except Exception as e:
        # Fallback if something goes wrong
        clean_title = title

    # Remove newlines
    clean_title = clean_title.replace("\n", " ").replace("\r", "")
    
    # Collapse multiple spaces
    clean_title = re.sub(r'\s+', ' ', clean_title).strip()
    
    # Truncate
    if len(clean_title) > 80:
        clean_title = clean_title[:77] + "..."
        
    return clean_title


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


def _append_to_log(items: List[Dict[str, str]], filename: str) -> str:
    """
    Generic function to append items to a markdown log file with deduplication.
    """
    # Ensure directory exists
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
        raw_title = item.get("title", "No Title")
        title = _clean_title(raw_title)
        # url is already extracted above
        
        # There is an extra SEPARATOR at the beginning of the file, but no easy fix
        # because this function is called multiple times to the same file.
        block = f"{SEPARATOR}## [{title}]({url})\n"
        
        exclude_keys = {"title", "url"}
        
        # Sort keys for consistent output, or just use iteration order?
        # Standard dict iteration order is insertion order (since Python 3.7).
        # But sorting by key is safer for diffs/consistency if insertion order varies.
        sorted_keys = sorted(item.keys())
        
        for key in sorted_keys:
            if key in exclude_keys:
                continue
            val = item[key]
            if val is not None and val != "":
                label = key.replace("_", " ").title()
                
                # Clean content if key is 'content'
                if key == "content":
                    val = _clean_html_to_markdown(val)
                
                # Handle lists or dicts? For now assume strings as per docstring hints.
                # If value is complex, maybe stringify it nicely?
                # But existing code assumed str.
                block += f"**{label}:** {val}\n"
        
        new_content_blocks.append(block)
        existing_urls.add(url) # Add to set to prevent duplicates within the same batch
        added_count += 1

    if not new_content_blocks:
        return f"All {len(items)} items were duplicates and skipped."

    with open(filename, "a", encoding="utf-8") as f:
        f.write("\n".join(new_content_blocks) + "\n\n")

    return f"Appended {added_count} new items to {filename}. Skipped {skipped_count} duplicates."


def append_to_raw_log(items: List[Dict[str, str]]):
    """
    Appends items to the raw log (e.g. data/all/YYYY-MM-DD.md).
    """
    return _append_to_log(items, _get_raw_path())


def append_to_curated_log(items: List[Dict[str, str]]):
    """
    Appends filtered/curated items to the curated log (e.g. data/curated/YYYY-MM-DD.md).
    """
    return _append_to_log(items, _get_curated_path())


def append_to_filtered_log(items: List[Dict[str, str]]):
    """
    Appends rejected/filtered items to the filtered log (e.g. data/curated/YYYY-MM-DD.filtered.md).
    """
    return _append_to_log(items, _get_filtered_path())


def append_to_details_log(items: List[Dict[str, str]]):
    """
    DEPRECATED: Use append_to_curated_log instead.
    Kept for backward compatibility during refactor.
    """
    return append_to_curated_log(items)


def read_raw_log() -> str:
    """Reads content of today's raw log."""
    filename = _get_raw_path()
    if not os.path.exists(filename):
        return "No raw items found for today."
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


def get_raw_item_count() -> int:
    """Returns the total number of raw items available today."""
    content = read_raw_log()
    if not content or content == "No raw items found for today.":
        return 0
    return content.count(SEPARATOR) + 1


def read_raw_items_batch(offset: int, limit: int) -> str:
    """
    Reads a batch of raw items.
    Returns string content containing the items.
    """
    content = read_raw_log()
    if not content or content == "No raw items found for today.":
        return "No raw items found."
    
    # So if we split by SEPARATOR, we get the blocks.
    items = content.split(SEPARATOR)
    
    # Handle edge case where file might start with separator or newlines
    items = [i for i in items if i.strip()]
    
    total = len(items)
    if offset >= total:
        return ""
        
    batch = items[offset : offset + limit]
    
    # Reconstruct for the agent
    return SEPARATOR.join(batch)


def read_curated_log() -> str:
    """Reads content of today's curated log."""
    filename = _get_curated_path()
    if not os.path.exists(filename):
        return "No curated items found for today."
    with open(filename, "r", encoding="utf-8") as f:
        return f.read()


def read_daily_details() -> str:
    """
    DEPRECATED: Use read_curated_log instead.
    """
    return read_curated_log()


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
