import os
import json
import logging
from typing import Optional, Dict, Any
from playwright.sync_api import sync_playwright, BrowserContext
from bs4 import BeautifulSoup
import html2text

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_proxy_config() -> Optional[Dict[str, str]]:
    """Get proxy configuration from environment variables."""
    http_proxy = os.getenv("HTTP_PROXY")
    if http_proxy:
        return {"server": http_proxy}
    return None


def fetch_page_content(url: str, headless: bool = True) -> str:
    """
    Fetches the content of a URL using Playwright.
    Uses the proxy and auth state if available.
    Returns the content as Markdown.
    """
    auth_state_path = "inputs/auth_state.json"
    proxy_config = get_proxy_config()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless, proxy=proxy_config)

        # Load auth state if it exists and is not empty
        context_options = {}
        if os.path.exists(auth_state_path):
            try:
                with open(auth_state_path, "r") as f:
                    state = json.load(f)
                    if state:
                        # context_options['storage_state'] = auth_state_path
                        # We pass the path directly to new_context
                        pass
            except json.JSONDecodeError:
                logger.warning(
                    f"Auth state file {auth_state_path} is invalid. Ignoring."
                )

        # Create context with storage_state if valid
        if os.path.exists(auth_state_path) and os.path.getsize(auth_state_path) > 2:
            context = browser.new_context(storage_state=auth_state_path)
        else:
            context = browser.new_context()

        page = context.new_page()

        try:
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=60000, wait_until="domcontentloaded")

            # Extract content
            content = page.content()

            # Convert to Markdown
            h = html2text.HTML2Text()
            h.ignore_links = False
            h.ignore_images = True
            h.body_width = 0  # No wrapping

            # Use BeautifulSoup to clean up a bit before markdown conversion if needed
            soup = BeautifulSoup(content, "html.parser")

            # Remove scripts and styles
            for script in soup(["script", "style", "noscript", "iframe", "svg"]):
                script.decompose()

            markdown_content = h.handle(str(soup))

            return markdown_content

        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return f"Error fetching {url}: {e}"
        finally:
            browser.close()


def configure_browser_session():
    """
    Launches a headed browser for the user to log in.
    Saves the storage state to inputs/auth_state.json.
    """
    auth_state_path = "inputs/auth_state.json"
    proxy_config = get_proxy_config()

    print(f"Launching browser with proxy: {proxy_config}")
    print("Please log in to your websites.")
    print(
        "Press Enter in this terminal when you are done to save the session and exit."
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False, proxy=proxy_config)

        # Load existing state if available
        if os.path.exists(auth_state_path) and os.path.getsize(auth_state_path) > 2:
            context = browser.new_context(storage_state=auth_state_path)
        else:
            context = browser.new_context()

        page = context.new_page()
        page.goto("https://www.google.com")  # Start somewhere

        input()  # Wait for user

        # Save state
        context.storage_state(path=auth_state_path)
        print(f"Session saved to {auth_state_path}")
        browser.close()
