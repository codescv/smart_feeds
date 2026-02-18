import os
import logging
import asyncio
import subprocess
import sys
from typing import List, Optional
from google.adk.tools import McpToolset
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from mcp import StdioServerParameters

logger = logging.getLogger(__name__)

# Constants
DEFAULT_USER_DATA_DIR = os.path.abspath("inputs/browser_data")


def _get_mcp_args(headless: bool, user_data_dir: Optional[str] = None) -> List[str]:
    """
    Constructs the arguments for the Playwright MCP server.
    """
    proxy_server = os.environ.get("HTTP_PROXY")

    # Construct arguments for npx @playwright/mcp
    args = ["-y", "@playwright/mcp@latest"]

    if proxy_server:
        args.append(f"--proxy-server={proxy_server}")

    if user_data_dir is None:
        user_data_dir = DEFAULT_USER_DATA_DIR

    args.append(f"--user-data-dir={user_data_dir}")

    if headless:
        args.append("--headless")

    print("args:", args)

    return args


def get_browser_toolset(
    headless: bool = True, user_data_dir: Optional[str] = None
) -> McpToolset:
    """
    Creates an McpToolset for the Playwright MCP server.
    """
    # The actual args passed to McpToolset must be the ones AFTER "npx"
    # because McpToolset takes command="npx" and args=[...].
    # _get_mcp_args returns the args for npx.
    args = _get_mcp_args(headless=headless, user_data_dir=user_data_dir)
    logger.info(f"Initializing Playwright MCP with args: {args}")

    return McpToolset(
        connection_params=StdioServerParameters(
            command="npx",
            args=args,
        )
    )


async def _run_configuration_direct(user_data_dir: Optional[str] = None):
    print("Initializing Browser via MCP...")
    # Initialize toolset in headed mode
    toolset = get_browser_toolset(headless=False, user_data_dir=user_data_dir)

    try:
        print("Connecting to MCP server...")
        # Access the session manager directly to bypass ADK Tool wrapper complexity
        session_manager = toolset._mcp_session_manager

        # Create a session
        session = await session_manager.create_session()

        # List tools to find the right name
        tools_result = await session.list_tools()
        navigate_tool_name = None

        # Search for the navigate tool
        for tool in tools_result.tools:
            if tool.name == "browser_navigate" or tool.name == "navigate":
                navigate_tool_name = tool.name
                break

        if not navigate_tool_name:
            # Fallback search
            for tool in tools_result.tools:
                if "navigate" in tool.name and "back" not in tool.name:
                    navigate_tool_name = tool.name
                    break

        if navigate_tool_name:
            print(f"Navigating to x.com...")

            # Call the tool directly on the session
            await session.call_tool(
                navigate_tool_name, arguments={"url": "https://x.com"}
            )
            print("Navigation command sent.")

        else:
            print("Could not find a 'navigate' tool. Available tools:")
            for tool in tools_result.tools:
                print(f"- {tool.name}")

        print("\nBrowser should be open.")
        print("Please log in to your websites in the opened window.")

        # Keep session open
        await asyncio.get_event_loop().run_in_executor(
            None, input, "Press Enter here when you are done to close the session..."
        )

    except Exception as e:
        print(f"Error during MCP interaction: {e}")
    finally:
        print("Closing session...")
        await toolset.close()


def configure_browser_session(user_data_dir: Optional[str] = None):
    """
    Launches a browser using the MCP toolset directly.
    """
    asyncio.run(_run_configuration_direct(user_data_dir=user_data_dir))
