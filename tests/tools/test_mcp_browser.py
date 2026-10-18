import os
from unittest.mock import patch
from smart_feeds.tools.mcp_browser import _get_mcp_args, get_browser_toolset


def test_get_mcp_args_headed(monkeypatch) -> None:
    """Verifies MCP CLI arguments in headed mode without proxy."""
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    args = _get_mcp_args(headless=False, user_data_dir="/tmp/test-browser")
    assert args == ["-y", "@playwright/mcp@latest", "--user-data-dir=/tmp/test-browser"]


def test_get_mcp_args_headless_with_proxy(monkeypatch) -> None:
    """Verifies MCP CLI arguments in headless mode with proxy."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:3128")
    args = _get_mcp_args(headless=True, user_data_dir="/tmp/test-browser")
    assert args == [
        "-y",
        "@playwright/mcp@latest",
        "--proxy-server=http://127.0.0.1:3128",
        "--user-data-dir=/tmp/test-browser",
        "--headless",
    ]


def test_get_browser_toolset_passes_environment(monkeypatch) -> None:
    """Verifies that get_browser_toolset passes DISPLAY and environment variables to StdioServerParameters."""
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")

    with patch("smart_feeds.tools.mcp_browser.McpToolset") as mock_toolset:
        get_browser_toolset(headless=False, user_data_dir="/tmp/test-browser")
        assert mock_toolset.called
        conn_params = mock_toolset.call_args.kwargs["connection_params"]
        server_params = conn_params.server_params
        assert server_params.command == "npx"
        assert server_params.env is not None
        assert server_params.env.get("DISPLAY") == ":0"
        assert server_params.env.get("WAYLAND_DISPLAY") == "wayland-0"
