import httpx
from bs4 import BeautifulSoup
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)

def fetch_website_content(url: str, selector: Optional[str] = None) -> str:
    """
    Fetches the content of a website and returns the text.
    Uses httpx for fetching and BeautifulSoup for parsing.
    
    Args:
        url: The URL to fetch.
        selector: Optional CSS selector to extract specific content. 
                  If None, returns the whole body text.
    """
    logger.info(f"Fetching website content: {url}")
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"
    }

    try:
        # httpx automatically respects HTTP_PROXY and HTTPS_PROXY environment variables
        
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(url, headers=headers)
            response.raise_for_status()
            html = response.text

        soup = BeautifulSoup(html, "html.parser")
        
        # Remove script and style elements
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.decompose()

        if selector:
            selected_elements = soup.select(selector)
            text = "\n\n".join([elem.get_text(separator="\n", strip=True) for elem in selected_elements])
        else:
            text = soup.get_text(separator="\n", strip=True)
        
        print('text:', text)

        # Basic markdown cleaning (optional, but helpful for LLM)
        # For now, just returning the raw text is usually fine for Gemini.
        return text[:50000] # Limit to 50k chars to avoid context overflow if page is huge

    except Exception as e:
        logger.error(f"Error fetching {url}: {e}")
        return f"Error fetching content: {str(e)}"
