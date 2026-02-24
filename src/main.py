import typer
import logging
import os
import tomllib
import asyncio
from dotenv import load_dotenv
from tools.mcp_browser import configure_browser_session, get_browser_toolset
from tools.rss import fetch_rss_feed
from tools.http import fetch_website_content
from tools.audio import transcribe_audio_url
from tools.storage import append_to_details_log

from agents.agent import create_fetcher_agent, create_summarizer_agent
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.ERROR, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

from typing import Optional, List, Any

app = typer.Typer()


@app.command()
def configure_browser():
    """
    Launches a visible browser to configure authentication (log in to sites).
    """
    user_data_dir = os.getenv("BROWSER_USER_DATA_DIR")
    if user_data_dir == "":
        user_data_dir = None
    configure_browser_session(user_data_dir=user_data_dir)


async def process_source(
    source_config: dict,
    model_id: Optional[str] = None,
    debug: bool = False,
):
    """
    Runs the fetcher agent for a single source.
    """
    url = source_config.get("url")
    source_type = source_config.get("type", "unknown")
    instruction = source_config.get("instruction", "")
    
    print(f"\n>>> Processing [{source_type}]: {url}")

    tools: List[Any] = [append_to_details_log]
    
    # Select tools based on type
    if source_type == "browser":
        user_data_dir = os.getenv("BROWSER_USER_DATA_DIR")
        if user_data_dir == "":
            user_data_dir = None
        # If debug is True, headless is False (browser is visible)
        browser_toolset = get_browser_toolset(user_data_dir=user_data_dir, headless=not debug)
        tools.append(browser_toolset)
        
    elif source_type == "http":
        tools.append(fetch_website_content)
        
    elif source_type == "rss_text":
        tools.append(fetch_rss_feed)
        
    elif source_type == "rss_audio":
        tools.append(fetch_rss_feed)
        tools.append(transcribe_audio_url)
        
    else:
        print(f"Unknown source type: {source_type}. Skipping.")
        return

    agent = create_fetcher_agent(
        model_id=model_id,
        tools=tools,
        source_type=source_type,
        extra_instruction=instruction
    )
    
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )

    prompt = f"Process this source: `{url}`"
    if source_type == "rss_audio":
        prompt += "\nThis is an audio RSS feed. Fetch the feed, find the latest audio links, transcribe them, and summarize."

    try:
        # If debug is True, we might want verbose logging
        events = await runner.run_debug(prompt, quiet=False, verbose=True)
        if events is None:
            print("No events returned.")

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        print(f"Error: {e}")


async def run_fetch_batch(model_id: Optional[str] = None, debug: bool = False):
    # Assuming running from project root
    sources_path = "inputs/sources.toml"
    if not os.path.exists(sources_path):
        print(f"Sources file not found at {sources_path}")
        return

    with open(sources_path, "rb") as f:
        sources_config = tomllib.load(f)

    # Handle new list-based format [[source]]
    sources = sources_config.get("source", [])
    
    # Backward compatibility checking
    if not sources:
        websites = sources_config.get("websites", [])
        rss = sources_config.get("rss", [])
        if websites or rss:
            print("Detected old configuration format. Please migrate to [[source]].")
            # We could migrate on the fly, but better to just warn or skip for now to encourage migration.
            # But let's try to adapt them simply if we want to be nice.
            for w in websites:
                if isinstance(w, str):
                    sources.append({"url": w, "type": "browser", "enabled": True})
                elif isinstance(w, dict):
                    w["type"] = "browser"
                    sources.append(w)
            for r in rss:
                if isinstance(r, str):
                    sources.append({"url": r, "type": "rss_text", "enabled": True})
                elif isinstance(r, dict):
                    r["type"] = "rss_text"
                    sources.append(r)

    for item in sources:
        if not item.get("enabled", True):
            print(f"Skipping disabled source: {item.get('url')}")
            continue
        
        await process_source(
            item,
            model_id=model_id,
            debug=debug,
        )


async def run_summarize(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting TLDR Generation")
    agent = create_summarizer_agent(model_id=model_id)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )
    
    prompt = "Please read the daily details and generate the TLDR summary."
    
    try:
        await runner.run_debug(prompt, quiet=False, verbose=True)
        print("TLDR generation complete.")
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        print(f"Error: {e}")


@app.command()
def fetch(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
    debug: bool = typer.Option(
        False, help="Enable debug mode (visible browser, verbose logs)"
    ),
):
    """
    Fetches content from configured sources and saves details.
    """
    print(f"Starting Smart Feeds content fetch... (Debug: {debug})")
    asyncio.run(run_fetch_batch(model_id=model, debug=debug))
    print("Fetch complete.")


@app.command()
def summarize(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
    debug: bool = typer.Option(
        False, help="Enable debug mode (verbose logs)"
    ),
):
    """
    Generates a TLDR summary from fetched details.
    """
    asyncio.run(run_summarize(model_id=model, debug=debug))


@app.command()
def run(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
):
    """
    DEPRECATED: Use 'fetch' instead. kept for backward compatibility.
    """
    print("Warning: 'run' is deprecated. Please use 'fetch' or 'summarize'. Running 'fetch'...")
    asyncio.run(run_fetch_batch(model_id=model))


@app.command()
def webui(
    port: int = 8501,
    model: Optional[str] = typer.Option(None, help="Model ID to use"),
):
    """
    Launches an interactive chat session for debugging the agent.
    """
    asyncio.run(run_chat_loop(model_id=model))


async def run_chat_loop(model_id: Optional[str] = None):
    print("Starting interactive chat mode (Debug)...")
    print("Type 'exit' to quit.")
    
    # Default to a browser fetcher for debug
    user_data_dir = os.getenv("BROWSER_USER_DATA_DIR")
    if user_data_dir == "":
        user_data_dir = None
    browser_toolset = get_browser_toolset(user_data_dir=user_data_dir, headless=False)
    
    tools = [browser_toolset, fetch_rss_feed, fetch_website_content, transcribe_audio_url, append_to_details_log]
    
    agent = create_fetcher_agent(
        model_id=model_id, 
        tools=tools, 
        source_type="debug", 
        extra_instruction="You are in debug mode with all tools available."
    )
    
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )

    while True:
        try:
            user_input = input("\nUser: ")
            if user_input.lower() in ["exit", "quit"]:
                break

            events = await runner.run_debug(user_input, quiet=True)
            if events is None:
                events = []

            for event in reversed(events):
                if event.author == agent.name and event.content:
                    if event.content.parts:
                        text_parts = [p.text for p in event.content.parts if p.text]
                        if text_parts:
                            print(f"Agent: {''.join(text_parts)}")
                            break
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"Error: {e}")
            print(f"Error: {e}")


if __name__ == "__main__":
    app()
