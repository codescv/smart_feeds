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
from tools.storage import append_to_raw_log

# Import new agents
from agents.fetcher_agent import create_fetcher_agent
from agents.curator_agent import create_curator_agent
from agents.summarizer_agent import create_summarizer_agent

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

    # Manual tool selection is now handled by create_fetcher_agent
    agent = create_fetcher_agent(
        model_id=model_id,
        source_type=source_type,
        debug=debug
    )
    
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )

    prompt = f"Process this source: `{url}`"
    if instruction:
        prompt += f"\n\nHigh-level Instruction: {instruction}"

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


async def run_curate(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting Curation (Filtering & Ranking)")
    agent = create_curator_agent(model_id=model_id)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )
    
    prompt = "Read the daily raw log and filter for relevant content based on user interests."
    
    try:
        await runner.run_debug(prompt, quiet=False, verbose=True)
        print("Curation complete.")
    except Exception as e:
        logger.error(f"Error generating curation: {e}")
        print(f"Error: {e}")


async def run_summarize(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting TLDR Generation")
    agent = create_summarizer_agent(model_id=model_id)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )
    
    prompt = "Please read the daily CURATED details and generate the TLDR summary."
    
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
    Stage 1: Fetches content from configured sources and saves RAW items to data/all.
    """
    print(f"Starting Smart Feeds content fetch... (Debug: {debug})")
    asyncio.run(run_fetch_batch(model_id=model, debug=debug))
    print("Fetch complete.")


@app.command()
def curate(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
    debug: bool = typer.Option(
        False, help="Enable debug mode (verbose logs)"
    ),
):
    """
    Stage 2: Filters RAW items against interests and saves to data/curated.
    """
    asyncio.run(run_curate(model_id=model, debug=debug))


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
    Stage 3: Generates a TLDR summary from CURATED details.
    """
    asyncio.run(run_summarize(model_id=model, debug=debug))

if __name__ == "__main__":
    app()
