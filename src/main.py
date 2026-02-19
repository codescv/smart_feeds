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
):
    """
    Runs the fetcher agent for a single source.
    """
    print(f"\n>>> Processing {source_type}: {url}")

    agent = create_fetcher_agent(model_id=model_id)
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
        events = await runner.run_debug(prompt, quiet=False, verbose=True)
        # We don't necessarily need to print the output as it's saved to the log, 
        # but showing the agent's thought process is helpful for debug.
        if events is None:
            print("No events returned.")

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        print(f"Error: {e}")


async def run_fetch_batch(model_id: Optional[str] = None):
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
            await process_source("website", item, model_id=model_id)
        elif isinstance(item, dict) and "url" in item:
            await process_source(
                "website",
                item["url"],
                instruction=item.get("instruction"),
                model_id=model_id,
            )

    for item in rss_feeds:
        if isinstance(item, str):
            await process_source("rss", item, model_id=model_id)
        elif isinstance(item, dict) and "url" in item:
            await process_source(
                "rss",
                item["url"],
                instruction=item.get("instruction"),
                model_id=model_id,
            )


async def run_summarize(model_id: Optional[str] = None):
    print("\n>>> Starting Daily Summary Generation")
    agent = create_summarizer_agent(model_id=model_id)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )
    
    prompt = "Please read the daily details and generate the daily news summary."
    
    try:
        await runner.run_debug(prompt, quiet=False, verbose=True)
        print("Summary generation complete.")
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        print(f"Error: {e}")


@app.command()
def fetch(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
):
    """
    Fetches content from configured sources and saves details.
    """
    print("Starting Smart Feeds content fetch...")
    asyncio.run(run_fetch_batch(model_id=model))
    print("Fetch complete.")


@app.command()
def summarize(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
):
    """
    Generates a daily news summary from fetched details.
    """
    asyncio.run(run_summarize(model_id=model))


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
