import typer
import logging
import os
import tomllib
import asyncio
from dotenv import load_dotenv
from tools.mcp_browser import configure_browser_session
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

from typing import Optional

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
    source_type: str,
    url: str,
    instruction: Optional[str] = None,
    model_id: Optional[str] = None,
    debug: bool = False,
):
    """
    Runs the fetcher agent for a single source.
    """
    print(f"\n>>> Processing {source_type}: {url}")

    agent = create_fetcher_agent(model_id=model_id, debug=debug)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )

    if source_type == "website":
        prompt = f"Process this website source: `{url}`"
    else:
        prompt = f"Process this RSS feed: `{url}`"

    if instruction:
        prompt = f"{prompt}\nInstructions:\n{instruction}"

    try:
        # If debug is True, we might want verbose logging or visible browser (handled in agent)
        events = await runner.run_debug(prompt, quiet=False, verbose=True)
        # We don't necessarily need to print the output as it's saved to the log, 
        # but showing the agent's thought process is helpful for debug.
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

    websites = sources_config.get("websites", [])
    rss_feeds = sources_config.get("rss", [])

    for item in websites:
        if isinstance(item, str):
            await process_source("website", item, model_id=model_id, debug=debug)
        elif isinstance(item, dict) and "url" in item:
            if not item.get("enabled", True):
                print(f"Skipping disabled source: {item['url']}")
                continue
            await process_source(
                "website",
                item["url"],
                instruction=item.get("instruction"),
                model_id=model_id,
                debug=debug,
            )

    for item in rss_feeds:
        if isinstance(item, str):
            await process_source("rss", item, model_id=model_id, debug=debug)
        elif isinstance(item, dict) and "url" in item:
            if not item.get("enabled", True):
                print(f"Skipping disabled source: {item['url']}")
                continue
            await process_source(
                "rss",
                item["url"],
                instruction=item.get("instruction"),
                model_id=model_id,
                debug=debug,
            )


async def run_summarize(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting TLDR Generation")
    # Summarizer agent doesn't use browser, so debug specifically for browser might not affect it much,
    # but we can pass it if we add more debug features later.
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


async def run_chat_loop(model_id: Optional[str] = None):
    print("Starting interactive chat mode (Debug)...")
    print("Type 'exit' to quit.")

    agent = create_fetcher_agent(model_id=model_id)
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


@app.command()
def webui(
    port: int = 8501,
    model: Optional[str] = typer.Option(None, help="Model ID to use"),
):
    """
    Launches an interactive chat session for debugging the agent.
    """
    asyncio.run(run_chat_loop(model_id=model))


if __name__ == "__main__":
    app()
