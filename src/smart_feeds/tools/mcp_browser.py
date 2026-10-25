import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.base_toolset import BaseToolset
from google.adk.tools.function_tool import FunctionTool
from playwright.async_api import BrowserContext, Page, Playwright, async_playwright

from smart_feeds import config
from smart_feeds.tools.dedup import deduplicate_items
from smart_feeds.tools.storage import append_to_raw_log

logger = logging.getLogger(__name__)

# Standard desktop Chrome User-Agent to prevent HeadlessChrome blocks on Cloudflare / X.com
DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36"
)

# Playwright passes --password-store=basic by default on Linux, which forces v10 ("peanuts")
# cookie encryption and prevents Chrome from decrypting v11 cookies saved via the system
# GNOME Keyring when logging in with /usr/bin/google-chrome.
IGNORED_DEFAULT_ARGS = ["--enable-automation", "--password-store=basic"]
CHROMIUM_ARGS = ["--disable-blink-features=AutomationControlled"]


def _ensure_linux_keyring_env() -> Dict[str, str]:
    """
    Ensures XDG_RUNTIME_DIR and DBUS_SESSION_BUS_ADDRESS are populated in os.environ
    on Linux so headless Chrome (even when launched from cron) can access the user's
    GNOME Keyring / libsecret daemon to decrypt v11 cookies.
    """
    if sys.platform.startswith("linux") and hasattr(os, "getuid"):
        uid = os.getuid()
        runtime_dir = f"/run/user/{uid}"
        bus_path = f"{runtime_dir}/bus"
        if os.path.exists(runtime_dir):
            os.environ.setdefault("XDG_RUNTIME_DIR", runtime_dir)
        if os.path.exists(bus_path):
            os.environ.setdefault("DBUS_SESSION_BUS_ADDRESS", f"unix:path={bus_path}")
    return os.environ.copy()


def _validate_http_url(url: str) -> Optional[str]:
    """
    Validates that the target URL uses http or https, blocking file:// or internal schemes.
    Returns an error message string if invalid, or None if valid.
    """
    parsed = urlparse(url.strip())
    if parsed.scheme not in ("http", "https"):
        return (
            f"Blocked URL '{url}': only http:// and https:// URLs are permitted "
            f"(got scheme '{parsed.scheme or 'none'}')."
        )
    return None


def _is_login_redirect(url: str) -> bool:
    """
    Checks whether the current browser URL indicates an unauthenticated login redirect.
    """
    lowered = url.lower()
    login_indicators = (
        "/i/flow/login",
        "/i/jf/onboarding",
        "mode=login",
        "redirect_after_login",
        "/login?",
    )
    return any(token in lowered for token in login_indicators)


class PlaywrightBrowserToolset(BaseToolset):
    """
    Native Python Playwright browser toolset for Google ADK agents.

    Replaces the external Node.js `@playwright/mcp` server with direct
    `playwright.async_api` persistent browser contexts using system Chrome.
    """

    def __init__(
        self,
        headless: bool = True,
        user_data_dir: Optional[str] = None,
    ) -> None:
        """
        Initializes the PlaywrightBrowserToolset with headless mode and user profile directory.
        """
        super().__init__()
        self.headless = headless
        self.user_data_dir = (
            os.path.abspath(user_data_dir)
            if user_data_dir
            else os.path.abspath(config.get_browser_user_data_dir())
        )
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None

    async def _ensure_page(self) -> Page:
        """
        Lazily starts Playwright and launches a persistent Chrome context configured
        to share system GNOME Keyring cookies and bypass headless automation checks.
        """
        if self._page is not None and not self._page.is_closed():
            return self._page

        _ensure_linux_keyring_env()
        os.makedirs(self.user_data_dir, exist_ok=True)

        if self._playwright is None:
            self._playwright = await async_playwright().start()

        proxy_server = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
        launch_kwargs: Dict[str, Any] = {
            "headless": self.headless,
            "user_agent": DEFAULT_USER_AGENT,
            "viewport": {"width": 1280, "height": 900},
            "args": list(CHROMIUM_ARGS),
            "ignore_default_args": list(IGNORED_DEFAULT_ARGS),
        }
        if proxy_server:
            launch_kwargs["proxy"] = {"server": proxy_server}

        if self._context is None:
            try:
                # Prefer system Google Chrome so v11 cookies encrypted under
                # "Chrome Safe Storage" are decrypted identically to user-chrome.sh.
                self._context = await self._playwright.chromium.launch_persistent_context(
                    self.user_data_dir,
                    channel="chrome",
                    **launch_kwargs,
                )
            except Exception as exc:
                logger.warning(
                    "Launching channel='chrome' failed (%s); falling back to default chromium.",
                    exc,
                )
                self._context = await self._playwright.chromium.launch_persistent_context(
                    self.user_data_dir,
                    **launch_kwargs,
                )

        self._page = (
            self._context.pages[0]
            if self._context.pages
            else await self._context.new_page()
        )
        return self._page

    async def browser_navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigates the browser to an http(s) URL and returns page status, title, and tabs.

        Args:
            url: The destination http:// or https:// URL to open.
        """
        err = _validate_http_url(url)
        if err:
            return {"status": "error", "error": err}

        page = await self._ensure_page()
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)

        # For X.com / Twitter, wait briefly for feed articles or login redirect to settle
        if "x.com" in url or "twitter.com" in url:
            try:
                await page.wait_for_selector("article", timeout=10000)
            except Exception:
                await page.wait_for_timeout(2500)
        else:
            await page.wait_for_timeout(2000)

        final_url = page.url
        title = await page.title()
        if _is_login_redirect(final_url):
            return {
                "status": "login_required",
                "url": final_url,
                "title": title,
                "error": (
                    "Redirected to login page. The browser profile is not authenticated "
                    "for this site."
                ),
            }

        try:
            tabs = [
                t.strip()
                for t in await page.locator('[role="tab"]').all_inner_texts()
                if t.strip()
            ]
        except Exception:
            tabs = []

        return {
            "status": "ok",
            "url": final_url,
            "title": title,
            "tabs": tabs,
        }

    async def browser_click(self, target: str) -> Dict[str, Any]:
        """
        Clicks a tab, button, or element matching the visible text or CSS selector.

        Args:
            target: The visible text (e.g. 'Following') or CSS selector to click.
        """
        page = await self._ensure_page()

        # 1. Check role="tab" matching target text first (common on X.com)
        tab_loc = page.locator(f'[role="tab"]:has-text("{target}")')
        if await tab_loc.count() > 0:
            await tab_loc.first.click(timeout=10000)
            await page.wait_for_timeout(2500)
            return {"status": "ok", "clicked": f"tab:{target}", "url": page.url}

        # 2. Try matching by exact or partial visible text
        text_loc = page.get_by_text(target, exact=False)
        if await text_loc.count() > 0:
            await text_loc.first.click(timeout=10000)
            await page.wait_for_timeout(2000)
            return {"status": "ok", "clicked": f"text:{target}", "url": page.url}

        # 3. Fallback to CSS selector
        css_loc = page.locator(target)
        if await css_loc.count() > 0:
            await css_loc.first.click(timeout=10000)
            await page.wait_for_timeout(2000)
            return {"status": "ok", "clicked": f"selector:{target}", "url": page.url}

        return {"status": "error", "error": f"Element '{target}' not found on {page.url}"}

    async def browser_extract_items(
        self,
        max_items: int = 50,
        tab: Optional[str] = None,
        auto_save: bool = True,
    ) -> Dict[str, Any]:
        """
        Extracts structured feed/news items from the current page, automatically handling
        tab switching and infinite-scroll virtualization (such as X.com timelines).
        When auto_save is True (default), automatically deduplicates and appends new items
        to the daily raw log in Python to avoid LLM copy-paste token overhead.

        Args:
            max_items: Maximum number of unique items to collect (default 50).
            tab: Optional tab name to click before extracting (e.g. 'Following' on X.com).
            auto_save: Whether to automatically deduplicate and append extracted items to the raw log.
        """
        page = await self._ensure_page()
        current_url = page.url

        if _is_login_redirect(current_url):
            return {
                "status": "login_required",
                "url": current_url,
                "items": [],
                "error": "Cannot extract items because the session is redirected to login.",
            }

        # Switch tab if requested (e.g. "Following" / "正在关注")
        if tab:
            candidates = [tab]
            if tab.lower() == "following":
                candidates.append("正在关注")
            for candidate in candidates:
                tab_loc = page.locator(f'[role="tab"]:has-text("{candidate}")')
                if await tab_loc.count() > 0:
                    await tab_loc.first.click(timeout=10000)
                    await page.wait_for_timeout(2500)
                    break

        items_list: List[Dict[str, str]] = []

        # Specialized virtualized scroll extractor for X.com / Twitter
        if "x.com" in current_url or "twitter.com" in current_url:
            collected: Dict[str, Dict[str, str]] = {}
            stale_rounds = 0
            max_scrolls = max(10, (max_items // 2) + 5)

            for _ in range(max_scrolls):
                batch: List[Dict[str, str]] = await page.evaluate(
                    """() => {
                    const articles = Array.from(
                        document.querySelectorAll('article[data-testid="tweet"], article')
                    );
                    const results = [];
                    for (const a of articles) {
                        const timeEl = a.querySelector("time");
                        if (!timeEl) continue; // Skip promoted posts lacking a timestamp
                        const linkEl = timeEl.closest("a") || a.querySelector('a[href*="/status/"]');
                        if (!linkEl || !linkEl.href || linkEl.href.includes("/analytics")) continue;
                        const url = linkEl.href.split("?")[0];
                        const published = timeEl.getAttribute("datetime") || "Unknown";
                        const userEl = a.querySelector('[data-testid="User-Name"]');
                        const userRaw = userEl ? userEl.innerText.replace(/\\n+/g, " ").trim() : "X";
                        const handleMatch = userRaw.match(/@[A-Za-z0-9_]+/);
                        const handle = handleMatch ? handleMatch[0] : userRaw;
                        const textEls = Array.from(a.querySelectorAll('[data-testid="tweetText"]'));
                        const mainText = textEls.length > 0
                            ? textEls[0].innerText.trim()
                            : a.innerText.trim();
                        const quoteText = textEls.length > 1
                            ? textEls.slice(1).map(el => el.innerText.trim()).join("\\n\\n[Quoted]: ")
                            : "";
                        const content = quoteText ? `${mainText}\\n\\n[Quoted]: ${quoteText}` : mainText;
                        if (!content) continue;
                        const firstLine = mainText.replace(/\\s+/g, " ").slice(0, 100);
                        const title = `${handle}: ${firstLine}`;
                        results.push({
                            title,
                            url,
                            source: `X (${handle})`,
                            published,
                            content
                        });
                    }
                    return results;
                }"""
                )
                before_count = len(collected)
                for item in batch:
                    item_url = item.get("url", "")
                    if item_url and item_url not in collected:
                        collected[item_url] = item
                        if len(collected) >= max_items:
                            break
                if len(collected) >= max_items:
                    break
                if len(collected) == before_count:
                    stale_rounds += 1
                    if stale_rounds >= 3:
                        break
                else:
                    stale_rounds = 0
                await page.evaluate("window.scrollBy(0, 1800)")
                await page.wait_for_timeout(1200)

            items_list = list(collected.values())[:max_items]
        else:
            # General article/news extractor for websites like anthropic.com/news
            items_list = await page.evaluate(
                """(maxItems) => {
                const skipPatterns = [
                    /\\/news\\/(announcements|product|policy|research|company|safety)\\/?$/i,
                    /#$/,
                    /\\/login/i,
                    /\\/signup/i
                ];
                const dateRegex = /\\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\\s+\\d{1,2},\\s+\\d{4}\\b/i;
                const categoryLabels = new Set([
                    "Announcements", "Product", "Policy", "Research",
                    "News", "Latest news", "Read more", "Featured"
                ]);
                const anchors = Array.from(document.querySelectorAll("main a[href], article a[href], body a[href]"));
                const seen = new Set();
                const results = [];
                const hostTitle = document.title.split("|")[0].split("—")[0].trim() || window.location.hostname;

                for (const a of anchors) {
                    const href = a.href ? a.href.split("#")[0] : "";
                    if (!href || seen.has(href) || href === window.location.href) continue;
                    if (skipPatterns.some(rx => rx.test(href))) continue;

                    const container = a.closest("article, li, tr, [class*='row'], [class*='card'], [class*='item'], [class*='Post']") || a;
                    const rawText = (container.innerText || a.innerText || "").trim();
                    if (!rawText || rawText.length < 15) continue;

                    const lines = rawText.split(/\\n+/).map(s => s.trim()).filter(Boolean);
                    const dateLine = lines.find(l => dateRegex.test(l));
                    const published = dateLine ? (dateLine.match(dateRegex)[0]) : "Unknown";

                    const contentLines = lines.filter(
                        l => !dateRegex.test(l) && !categoryLabels.has(l)
                    );
                    if (contentLines.length === 0) continue;

                    const title = contentLines[0].slice(0, 180);
                    if (title.length < 5 || categoryLabels.has(title)) continue;

                    seen.add(href);
                    const summary = contentLines.slice(1).join(" ") || title;
                    results.push({
                        title,
                        url: href,
                        source: hostTitle,
                        published,
                        content: summary
                    });
                    if (results.length >= maxItems) break;
                }
                return results;
            }""",
                max_items,
            )

        if auto_save:
            new_items = deduplicate_items(items_list)
            if new_items:
                save_msg = append_to_raw_log(new_items)
            else:
                save_msg = f"All {len(items_list)} extracted items already seen; 0 new items appended."
            return {
                "status": "ok",
                "url": page.url,
                "extracted_count": len(items_list),
                "new_saved_count": len(new_items),
                "save_result": save_msg,
                "sample_titles": [it.get("title", "") for it in items_list[:5]],
            }

        return {
            "status": "ok",
            "url": page.url,
            "count": len(items_list),
            "items": items_list,
        }

    async def browser_get_content(
        self, selector: str = "body", max_chars: int = 30000
    ) -> Dict[str, Any]:
        """
        Extracts readable text content from the current page or a specific CSS selector.

        Args:
            selector: CSS selector to read from (default 'body').
            max_chars: Maximum number of characters to return (default 30000).
        """
        page = await self._ensure_page()
        try:
            loc = page.locator(selector).first
            text = await loc.inner_text(timeout=10000)
        except Exception:
            text = await page.inner_text("body")
        return {
            "status": "ok",
            "url": page.url,
            "title": await page.title(),
            "content": text[:max_chars],
        }

    async def browser_scroll(self, pixels: int = 1500) -> Dict[str, Any]:
        """
        Scrolls the current page vertically by the specified number of pixels.

        Args:
            pixels: Vertical scroll distance in pixels (default 1500).
        """
        page = await self._ensure_page()
        await page.evaluate(f"window.scrollBy(0, {int(pixels)})")
        await page.wait_for_timeout(1500)
        return {"status": "ok", "url": page.url, "scrolled_pixels": pixels}

    async def browser_evaluate(self, script: str) -> Dict[str, Any]:
        """
        Evaluates a JavaScript expression or function in the current page context.

        Args:
            script: JavaScript function or expression to evaluate on the page.
        """
        page = await self._ensure_page()
        err = _validate_http_url(page.url)
        if err and page.url != "about:blank":
            return {"status": "error", "error": err}
        result = await page.evaluate(script)
        return {"status": "ok", "result": result}

    async def get_tools(
        self, readonly_context: Optional[ReadonlyContext] = None
    ) -> List[BaseTool]:
        """
        Returns the list of ADK FunctionTools backed by this Playwright browser session.
        """
        return [
            FunctionTool(self.browser_navigate),
            FunctionTool(self.browser_click),
            FunctionTool(self.browser_extract_items),
            FunctionTool(self.browser_get_content),
            FunctionTool(self.browser_scroll),
            FunctionTool(self.browser_evaluate),
        ]

    async def close(self) -> None:
        """
        Closes the browser context and stops the Playwright driver cleanly.
        """
        if self._context is not None:
            try:
                await self._context.close()
            except Exception as exc:
                logger.debug("Error closing browser context: %s", exc)
            finally:
                self._context = None
                self._page = None

        if self._playwright is not None:
            try:
                await self._playwright.stop()
            except Exception as exc:
                logger.debug("Error stopping playwright: %s", exc)
            finally:
                self._playwright = None


def get_browser_toolset(
    headless: bool = True, user_data_dir: Optional[str] = None
) -> PlaywrightBrowserToolset:
    """
    Creates a native Python PlaywrightBrowserToolset (no MCP server required).
    """
    return PlaywrightBrowserToolset(headless=headless, user_data_dir=user_data_dir)


async def _run_configuration_direct(user_data_dir: Optional[str] = None) -> None:
    """
    Launches a headed Chrome browser session via Playwright and waits for the user
    to complete authentication before closing the session.
    """
    print("Initializing Browser via native Playwright (no MCP)...")
    toolset = get_browser_toolset(headless=False, user_data_dir=user_data_dir)
    try:
        print("Navigating to https://x.com ...")
        res = await toolset.browser_navigate("https://x.com")
        print(f"Navigation status: {res.get('status')} ({res.get('url')})")
        print("\nBrowser is open. Please log in to your websites in the opened window.")
        await asyncio.get_event_loop().run_in_executor(
            None, input, "Press Enter here when you are done to close the session..."
        )
    except Exception as exc:
        print(f"Error during browser configuration: {exc}")
    finally:
        print("Closing session...")
        await toolset.close()


def configure_browser_session(user_data_dir: Optional[str] = None) -> None:
    """
    Launches a visible browser session for interactive login configuration.
    """
    asyncio.run(_run_configuration_direct(user_data_dir=user_data_dir))
