import sys
import os
import glob
import re

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import config
from tools.dedup import _compute_hash, _append_hashes, _get_seen_urls_path

def backfill_pd():
    """
    Reads all markdown files in data/all/ and data/curated/ and extracts URLs to populate seen_urls.txt
    """
    output_dir = config.get_output_dir()
    
    # Paths to search
    paths_to_search = [
        os.path.join(output_dir, "all", "*.md"),
        os.path.join(output_dir, "curated", "*.md"),
        # Also check deprecated "details" folder just in case
        os.path.join(output_dir, "details", "*.md"),
    ]
    
    all_files = []
    for p in paths_to_search:
        all_files.extend(glob.glob(p))
    
    print(f"Found {len(all_files)} files to scan.")
    
    # Regex for markdown links: [text](url)
    md_link_pattern = r'\[.*?\]\((https?://[^\s\)]+)\)'
    # Regex for bare URLs
    url_pattern = r'(?<!\()https?://[^\s\)]+'
    
    seen_hashes = set()
    total_urls_found = 0
    
    for filepath in all_files:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            urls = re.findall(md_link_pattern, content)
            urls.extend(re.findall(url_pattern, content))
            
            for url in urls:
                # Normalize?
                url = url.rstrip('/')
                h = _compute_hash(url)
                seen_hashes.add(h)
                total_urls_found += 1
                
        except Exception as e:
            print(f"Error reading {filepath}: {e}")
            
    print(f"Total URLs found: {total_urls_found}")
    print(f"Unique hashes computed: {len(seen_hashes)}")
    
    # Load existing hashes to avoid duplicates if file already exists
    existing_hashes = set()
    seen_path = _get_seen_urls_path()
    if os.path.exists(seen_path):
         with open(seen_path, "r", encoding="utf-8") as f:
            existing_hashes = {line.strip() for line in f if line.strip()}
            
    new_hashes = list(seen_hashes - existing_hashes)
    print(f"New hashes to append: {len(new_hashes)}")
    
    if new_hashes:
        _append_hashes(new_hashes)
        print(f"Successfully appended {len(new_hashes)} hashes to {seen_path}")
    else:
        print("No new hashes to append.")

if __name__ == "__main__":
    backfill_pd()
