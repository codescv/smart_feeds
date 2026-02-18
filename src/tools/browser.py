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

# Realistic Chrome User Agent
USER_DATA_DIR = os.path.abspath("inputs/browser_data")

# Possible paths for Google Chrome on macOS
CHROME_PATHS = [
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    "/Applications/Google Chrome Canary.app/Contents/MacOS/Google Chrome Canary",
]


def get_chrome_executable_path() -> Optional[str]:
    """Finds the Google Chrome executable path."""
    for path in CHROME_PATHS:
        if os.path.exists(path):
            return path
    return None


def get_proxy_config() -> Optional[Dict[str, str]]:
    """Get proxy configuration from environment variables."""
    http_proxy = os.getenv("HTTP_PROXY")
    if http_proxy:
        return {"server": http_proxy}
    return None


def fetch_page_content(url: str, headless: bool = True) -> str:
    """
    Fetches the content of a URL using Playwright.
    Uses the proxy and persistent user data directory.
    Returns the content as Markdown.
    """
    proxy_config = get_proxy_config()

    with sync_playwright() as p:
        # Try to use Chrome if available, otherwise use bundled Chromium
        executable_path = get_chrome_executable_path()

        # Args for launch_persistent_context
        launch_args = {
            "user_data_dir": USER_DATA_DIR,
            "headless": headless,
            "proxy": proxy_config,
            "viewport": {"width": 1280, "height": 720},
            "locale": "en-US",
            # We need to accept downloads to avoid popups, though we ignore them
            "accept_downloads": True,
        }

        if executable_path:
            logger.info(f"Using Chrome executable: {executable_path}")
            launch_args["executable_path"] = executable_path

        context = p.chromium.launch_persistent_context(**launch_args)

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
            context.close()


def configure_browser_session():
    """
    Launches a headed browser with persistent context for the user to log in.
    """
    proxy_config = get_proxy_config()

    print(f"Launching browser with proxy: {proxy_config}")
    print(f"User Data Directory: {USER_DATA_DIR}")

    executable_path = get_chrome_executable_path()
    if executable_path:
        print(f"Using Chrome executable: {executable_path}")
    else:
        print("Using bundled Chromium (Chrome not found)")

    print("Please log in to your websites.")
    print(
        "Press Enter in this terminal when you are done to exit (state is saved automatically to user-data-dir)."
    )

    with sync_playwright() as p:
        launch_args = {
            "user_data_dir": USER_DATA_DIR,
            "headless": False,
            "proxy": proxy_config,
            "viewport": {"width": 1280, "height": 720},
            "locale": "en-US",
        }

        if executable_path:
            launch_args["executable_path"] = executable_path

        context = p.chromium.launch_persistent_context(**launch_args)

        page = context.new_page()
        try:
            page.goto("https://www.google.com")  # Start somewhere
        except Exception as e:
            print(f"Warning: Failed to load initial page: {e}")

        input()  # Wait for user

        context.close()
