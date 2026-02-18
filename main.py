import typer
import logging
import os
import yaml
import asyncio
from dotenv import load_dotenv
from src.tools.mcp_browser import configure_browser_session
from src.agent import create_agent
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
def configure_browser(
    user_dir: Optional[str] = typer.Option(
        None, help="Path to the browser user data directory"
    ),
):
    """
    Launches a visible browser to configure authentication (log in to sites).
    """
    configure_browser_session(user_data_dir=user_dir)


async def process_source(
    source_type: str,
    url: str,
    model_id: Optional[str] = None,
    user_dir: Optional[str] = None,
):
    """
    Runs the agent for a single source.
    """
    print(f"\n>>> Processing {source_type}: {url}")

    agent = create_agent(model_id=model_id, user_data_dir=user_dir)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )

    if source_type == "website":
        prompt = (
            f"Please check this website source: `{url}`\n"
            "Use browser tool to fetch its content, filter for my interests, and summarize if relevant."
        )
    else:
        prompt = (
            f"Please check this RSS feed: `{url}`\n"
            "Use `fetch_rss_feed` to Fetch its items, filter for my interests, and summarize if relevant."
        )

    try:
        events = await runner.run_debug(prompt, quiet=False)
        if events is None:
            events = []

        # Find the last response from the agent
        final_response = None
        if events:
            print(events)
            for event in reversed(events):
                if event.author == agent.name and event.content:
                    if event.content.parts:
                        text_parts = [p.text for p in event.content.parts if p.text]
                        if text_parts:
                            final_response = "".join(text_parts)
                            break

        if final_response:
            print(f"Agent:\n{final_response}")
        else:
            print("Agent finished (no text response).")

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        print(f"Error: {e}")


async def run_batch(model_id: Optional[str] = None, user_dir: Optional[str] = None):
    sources_path = "inputs/sources.yaml"
    if not os.path.exists(sources_path):
        print(f"Sources file not found at {sources_path}")
        return

    with open(sources_path, "r") as f:
        sources_config = yaml.safe_load(f)

    websites = sources_config.get("websites", [])
    rss_feeds = sources_config.get("rss", [])

    for url in websites:
        await process_source("website", url, model_id=model_id, user_dir=user_dir)

    for url in rss_feeds:
        await process_source("rss", url, model_id=model_id, user_dir=user_dir)


@app.command()
def run(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
    user_dir: Optional[str] = typer.Option(
        None, help="Path to the browser user data directory"
    ),
):
    """
    Runs the Smart Feeds agent to curate content from configured sources.
    """
    print("Starting Smart Feeds curation run...")
    asyncio.run(run_batch(model_id=model, user_dir=user_dir))
    print("Run complete.")


async def run_chat_loop(model_id: Optional[str] = None, user_dir: Optional[str] = None):
    print("Starting interactive chat mode (Debug)...")
    print("Type 'exit' to quit.")

    agent = create_agent(model_id=model_id, user_data_dir=user_dir)
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
    user_dir: Optional[str] = typer.Option(
        None, help="Path to the browser user data directory"
    ),
):
    """
    Launches an interactive chat session for debugging the agent.
    """
    asyncio.run(run_chat_loop(model_id=model, user_dir=user_dir))


if __name__ == "__main__":
    app()
