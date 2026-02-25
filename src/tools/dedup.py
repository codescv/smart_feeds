import hashlib
import os
import config
from typing import List, Dict, Any, Set

def _get_seen_urls_path() -> str:
    """Returns the path for the seen URLs hash file."""
    return os.path.join(config.get_output_dir(), "seen_urls.txt")

def _compute_hash(url: str) -> str:
    """Computes the first 8 characters of the MD5 hash of the URL."""
    return hashlib.md5(url.encode('utf-8')).hexdigest()[:8]

def _load_seen_hashes() -> Set[str]:
    """Loads existing hashes from the file."""
    path = _get_seen_urls_path()
    if not os.path.exists(path):
        return set()
    
    with open(path, "r", encoding="utf-8") as f:
        return {line.strip() for line in f if line.strip()}

def _append_hashes(hashes: List[str]):
    """Appends new hashes to the file and manages file size."""
    path = _get_seen_urls_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Append new hashes
    with open(path, "a", encoding="utf-8") as f:
        for h in hashes:
            f.write(h + "\n")
            
    # Check file size (line count) - simple check to avoid reading huge files every time
    # For a strictly capped file, we might need a more robust approach (e.g. readlines)
    # But reading 100k lines is fast.
    # We can do this check occasionally or every time if performance permits.
    # Let's do it every time for correctness as per requirements.
    
    MAX_LINES = 100000
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
            
        if len(lines) > MAX_LINES:
            # Keep the last MAX_LINES
            new_lines = lines[-MAX_LINES:]
            with open(path, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
    except Exception as e:
        print(f"Error rotating hash file: {e}")

def deduplicate_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Filters out items that have been seen before based on URL hash.
    Also deduplicates within the current batch.
    """
    seen_hashes = _load_seen_hashes()
    unique_items = []
    new_hashes = []
    
    # Local dedup set for the current batch to avoid adding duplicates within the same fetch
    current_batch_hashes = set()

    for item in items:
        url = item.get("url")
        if not url:
            continue
            
        url_hash = _compute_hash(url)
        
        if url_hash in seen_hashes:
            continue
            
        if url_hash in current_batch_hashes:
            continue
            
        unique_items.append(item)
        new_hashes.append(url_hash)
        current_batch_hashes.add(url_hash)
    
    if new_hashes:
        _append_hashes(new_hashes)
        
    return unique_items
