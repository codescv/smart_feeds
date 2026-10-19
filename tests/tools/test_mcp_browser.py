import os
from pathlib import Path
from unittest.mock import patch
import pytest
from smart_feeds.tools.mcp_browser import (
    _get_mcp_args,
    _resolve_npx_command,
    get_browser_toolset,
)


def test_get_mcp_args_headed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies MCP CLI arguments in headed mode without proxy."""
    monkeypatch.delenv("HTTP_PROXY", raising=False)
    args = _get_mcp_args(headless=False, user_data_dir="/tmp/test-browser")
    assert args == ["-y", "@playwright/mcp", "--user-data-dir=/tmp/test-browser"]


def test_get_mcp_args_headless_with_proxy(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies MCP CLI arguments in headless mode with proxy."""
    monkeypatch.setenv("HTTP_PROXY", "http://127.0.0.1:3128")
    args = _get_mcp_args(headless=True, user_data_dir="/tmp/test-browser")
    assert args == [
        "-y",
        "@playwright/mcp",
        "--proxy-server=http://127.0.0.1:3128",
        "--user-data-dir=/tmp/test-browser",
        "--headless",
    ]


def test_resolve_npx_command_on_path_realpath(tmp_path: Path) -> None:
    """Verifies _resolve_npx_command resolves symlinks when npx is found on PATH."""
    real_bin = tmp_path / "real_node" / "bin"
    real_bin.mkdir(parents=True)
    real_npx = real_bin / "npx"
    real_npx.write_text("#!/bin/sh\n")

    symlink_dir = tmp_path / "fnm_multishells" / "12345" / "bin"
    symlink_dir.mkdir(parents=True)
    symlink_npx = symlink_dir / "npx"
    symlink_npx.symlink_to(real_npx)

    with patch("smart_feeds.tools.mcp_browser.shutil.which", return_value=str(symlink_npx)):
        resolved = _resolve_npx_command()
        assert resolved == str(real_npx.resolve())


def test_resolve_npx_command_fnm_default_alias_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies _resolve_npx_command falls back to fnm default alias when npx is not on PATH."""
    monkeypatch.setenv("HOME", str(tmp_path))
    real_bin = tmp_path / ".local/share/fnm/node-versions/v22.22.1/installation/bin"
    real_bin.mkdir(parents=True)
    real_npx = real_bin / "npx"
    real_npx.write_text("#!/bin/sh\n")

    alias_bin = tmp_path / ".local/share/fnm/aliases/default/bin"
    alias_bin.mkdir(parents=True)
    alias_npx = alias_bin / "npx"
    alias_npx.symlink_to(real_npx)

    with patch("smart_feeds.tools.mcp_browser.shutil.which", return_value=None):
        resolved = _resolve_npx_command()
        assert resolved == str(real_npx.resolve())


def test_resolve_npx_command_fnm_versions_glob_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies _resolve_npx_command falls back to highest fnm node-versions glob when default alias is absent."""
    monkeypatch.setenv("HOME", str(tmp_path))
    v20_bin = tmp_path / ".local/share/fnm/node-versions/v20.10.0/installation/bin"
    v20_bin.mkdir(parents=True)
    (v20_bin / "npx").write_text("#!/bin/sh\n")

    v22_bin = tmp_path / ".local/share/fnm/node-versions/v22.22.1/installation/bin"
    v22_bin.mkdir(parents=True)
    v22_npx = v22_bin / "npx"
    v22_npx.write_text("#!/bin/sh\n")

    with patch("smart_feeds.tools.mcp_browser.shutil.which", return_value=None):
        resolved = _resolve_npx_command()
        assert resolved == str(v22_npx.resolve())


def test_resolve_npx_command_bare_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verifies _resolve_npx_command returns 'npx' when neither PATH nor fnm directories have npx."""
    monkeypatch.setenv("HOME", str(tmp_path))
    with patch("smart_feeds.tools.mcp_browser.shutil.which", return_value=None):
        assert _resolve_npx_command() == "npx"


def test_get_browser_toolset_passes_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that get_browser_toolset resolves npx, prepends its dir to PATH, and passes env vars."""
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.setenv("WAYLAND_DISPLAY", "wayland-0")
    monkeypatch.setenv("PATH", "/usr/bin:/bin")

    fake_npx = "/home/user/.local/share/fnm/node-versions/v22.22.1/installation/bin/npx"
    with (
        patch("smart_feeds.tools.mcp_browser._resolve_npx_command", return_value=fake_npx),
        patch("smart_feeds.tools.mcp_browser.McpToolset") as mock_toolset,
    ):
        get_browser_toolset(headless=False, user_data_dir="/tmp/test-browser")
        assert mock_toolset.called
        conn_params = mock_toolset.call_args.kwargs["connection_params"]
        server_params = conn_params.server_params
        assert server_params.command == fake_npx
        assert server_params.env is not None
        assert server_params.env.get("DISPLAY") == ":0"
        assert server_params.env.get("WAYLAND_DISPLAY") == "wayland-0"
        assert server_params.env.get("PATH", "").startswith(
            "/home/user/.local/share/fnm/node-versions/v22.22.1/installation/bin:"
        )
