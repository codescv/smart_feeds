from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from smart_feeds.tools.mcp_browser import (
    DEFAULT_USER_AGENT,
    IGNORED_DEFAULT_ARGS,
    PlaywrightBrowserToolset,
    _ensure_linux_keyring_env,
    _is_login_redirect,
    _validate_http_url,
    get_browser_toolset,
)


def test_validate_http_url_allows_http_and_https() -> None:
    """Verifies that http:// and https:// URLs pass validation."""
    assert _validate_http_url("https://x.com/home") is None
    assert _validate_http_url("http://example.com") is None


def test_validate_http_url_blocks_file_and_other_schemes() -> None:
    """Verifies that file:// and non-http schemes are blocked."""
    err = _validate_http_url("file:///etc/passwd")
    assert err is not None
    assert "Blocked URL" in err


def test_is_login_redirect_detects_x_login_flows() -> None:
    """Verifies detection of X.com login and onboarding redirect URLs."""
    assert _is_login_redirect(
        "https://x.com/i/jf/onboarding/web?redirect_after_login=%2Fhome&mode=login"
    )
    assert _is_login_redirect("https://x.com/i/flow/login")
    assert not _is_login_redirect("https://x.com/home")


def test_ensure_linux_keyring_env_populates_dbus(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies _ensure_linux_keyring_env populates XDG_RUNTIME_DIR and DBUS_SESSION_BUS_ADDRESS."""
    monkeypatch.delenv("XDG_RUNTIME_DIR", raising=False)
    monkeypatch.delenv("DBUS_SESSION_BUS_ADDRESS", raising=False)
    with (
        patch("smart_feeds.tools.mcp_browser.sys.platform", "linux"),
        patch("smart_feeds.tools.mcp_browser.os.getuid", return_value=12345),
        patch("smart_feeds.tools.mcp_browser.os.path.exists", return_value=True),
    ):
        env = _ensure_linux_keyring_env()
        assert env.get("XDG_RUNTIME_DIR") == "/run/user/12345"
        assert env.get("DBUS_SESSION_BUS_ADDRESS") == "unix:path=/run/user/12345/bus"


@pytest.mark.asyncio
async def test_playwright_browser_toolset_launches_with_keyring_and_ua(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies PlaywrightBrowserToolset passes channel='chrome', UA, and ignore_default_args."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:3128")
    mock_page = MagicMock()
    mock_page.is_closed.return_value = False
    mock_page.url = "https://x.com/home"
    mock_page.goto = AsyncMock()
    mock_page.wait_for_selector = AsyncMock()
    mock_page.title = AsyncMock(return_value="Home / X")
    mock_locator = MagicMock()
    mock_locator.all_inner_texts = AsyncMock(return_value=["For you", "Following"])
    mock_page.locator.return_value = mock_locator

    mock_context = MagicMock()
    mock_context.pages = [mock_page]
    mock_context.close = AsyncMock()

    mock_pw_instance = MagicMock()
    mock_pw_instance.chromium.launch_persistent_context = AsyncMock(
        return_value=mock_context
    )
    mock_pw_instance.stop = AsyncMock()

    mock_apw = MagicMock()
    mock_apw.return_value.start = AsyncMock(return_value=mock_pw_instance)

    with patch("smart_feeds.tools.mcp_browser.async_playwright", mock_apw):
        toolset = get_browser_toolset(headless=True, user_data_dir=str(tmp_path))
        assert isinstance(toolset, PlaywrightBrowserToolset)

        tools = await toolset.get_tools()
        tool_names = [t.name for t in tools]
        assert "browser_navigate" in tool_names
        assert "browser_extract_items" in tool_names

        nav_res = await toolset.browser_navigate("https://x.com/home")
        assert nav_res["status"] == "ok"
        assert nav_res["tabs"] == ["For you", "Following"]

        launch_call = mock_pw_instance.chromium.launch_persistent_context
        assert launch_call.called
        kwargs = launch_call.call_args.kwargs
        assert kwargs["channel"] == "chrome"
        assert kwargs["headless"] is True
        assert kwargs["user_agent"] == DEFAULT_USER_AGENT
        assert kwargs["ignore_default_args"] == IGNORED_DEFAULT_ARGS
        assert kwargs["proxy"] == {"server": "http://127.0.0.1:3128"}

        await toolset.close()
        assert mock_context.close.called
        assert mock_pw_instance.stop.called
