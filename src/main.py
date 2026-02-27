import typer
import logging
import os
import tomllib
import asyncio
from dotenv import load_dotenv
import config
from tools.mcp_browser import configure_browser_session, get_browser_toolset
from tools.rss import fetch_rss_feed
from tools.http import fetch_website_content
from tools.storage import append_to_raw_log
from retry_utils import retry_async, retry_sync

# Import new agents
from agents.fetcher_agent import create_fetcher_agent
from agents.curator_agent import create_curator_agent
from agents.summarizer_agent import create_summarizer_agent
from agents.deep_dive_agent import create_deep_dive_agent

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
    user_data_dir = config.get_browser_user_data_dir()
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
    else:
        # If there are no instructions, use reasonable default 
        # fetch counts based on source type.
        # Avoid fetching too much to save LLM tokens.
        if source_type in ("rss_text", "http", "browser"):
            if 'reddit' in url:
                prompt += "\nFetch the top 30 updates."
            else:
                prompt += "\nFetch the top 10 updates."
        elif source_type == "rss_audio":
            # Podcasts are not updated that often.
            prompt += "\nFetch the top 3 updates."

    try:
        # Define local function with retry decorator
        @retry_async(
            max_retries=config.get_retry_max_attempts(),
            initial_delay=config.get_retry_delay_seconds()
        )
        async def run_agent():
            return await runner.run_debug(prompt, quiet=False, verbose=True)

        # Execute
        events = await run_agent()

        if events is None:
            print("No events returned.")

    except Exception as e:
        logger.error(f"Error processing {url}: {e}")
        print(f"Error: {e}")
    finally:
        # Cleanup any tools that need closing (e.g. browser)
        if agent and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, "close") and callable(tool.close):
                    print(f"Closing tool: {tool}")
                    await tool.close()


async def run_fetch_batch(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>>Fetching content...")
    # Assuming running from project root
    sources_path = config.get_sources_config_path()
    if not os.path.exists(sources_path):
        print(f"Sources file not found at {sources_path}")
        return

    with open(sources_path, "rb") as f:
        sources_config = tomllib.load(f)

    # Handle new list-based format [[source]]
    sources = sources_config.get("source", [])

    for item in sources:
        if not item.get("enabled", True):
            print(f"Skipping disabled source: {item.get('url')}")
            continue
        
        await process_source(
            item,
            model_id=model_id,
            debug=debug,
        )
    print("Fetch complete.")


async def run_curate(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting Curation (Filtering & Ranking)")
    
    # 1. Get total count of raw items
    from tools.storage import get_raw_item_count
    total_items = get_raw_item_count()
    print(f"Total raw items to process: {total_items}")
    
    if total_items == 0:
        print("No raw items found. Exiting curation.")
        return

    # 2. Batch processing configuration
    BATCH_SIZE = 20  # Adjust as needed to fit context window
    
    # 3. Process in batches
    for offset in range(0, total_items, BATCH_SIZE):
        limit = BATCH_SIZE
        print(f"\n--- Processing Batch: {offset} to {offset + limit} (of {total_items}) ---")
        
        # Instantiate a fresh agent for each batch to keep context clean (stateless)
        # Or reuse if we want some memory, but for curation stateless is usually safer/cheaper.
        agent = create_curator_agent(model_id=model_id)
        
        runner = Runner(
            agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
        )
        
        # We can either pass the data directly in prompt or tell agent to read it.
        # Passing directly saves one tool call (read_raw_items_batch) per batch.
        # But `read_raw_items_batch` is already implemented and agent has it.
        # Let's try telling the agent to read the specific batch.
        
        prompt = (
            f"Please process the raw log batch starting at offset {offset} with limit {limit}. "
            f"Read these {limit} items using `read_raw_items_batch({offset}, {limit})`, "
            f"then filter and save them."
        )
        
        try:
            @retry_async(
                max_retries=config.get_retry_max_attempts(),
                initial_delay=config.get_retry_delay_seconds()
            )
            async def run_batch():
                return await runner.run_debug(prompt, quiet=False, verbose=True)
            
            await run_batch()
        except Exception as e:
            logger.error(f"Error processing batch {offset}: {e}")
            print(f"Error in batch {offset}: {e}")
            
    print("Curation complete.")


async def run_summarize(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting TLDR Generation")
    agent = create_summarizer_agent(model_id=model_id)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )
    
    prompt = "Please read the daily CURATED details and generate the TLDR summary."
    
    try:
        @retry_async(
            max_retries=config.get_retry_max_attempts(),
            initial_delay=config.get_retry_delay_seconds()
        )
        async def run_summary():
            return await runner.run_debug(prompt, quiet=False, verbose=True)

        await run_summary()
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
    Stage 1: Fetches content from configured sources and saves RAW items to the configured output directory.
    """
    print(f"Starting Smart Feeds content fetch... (Debug: {debug})")
    asyncio.run(run_fetch_batch(model_id=model, debug=debug))


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
    Stage 2: Filters RAW items against interests and saves to the configured output directory.
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


async def run_deep_dive(model_id: Optional[str] = None, debug: bool = False):
    print("\n>>> Starting Deep Dive Analysis")
    agent = create_deep_dive_agent(model_id=model_id, debug=debug)
    runner = Runner(
        agent=agent, app_name="smart-feeds", session_service=InMemorySessionService()
    )
    
    prompt = "Please read the daily TLDR summary and generate a Deep Dive Report."
    
    try:
        @retry_async(
            max_retries=config.get_retry_max_attempts(),
            initial_delay=config.get_retry_delay_seconds()
        )
        async def run_deep_dive_job():
            return await runner.run_debug(prompt, quiet=False, verbose=True)

        await run_deep_dive_job()
        print("Deep Dive analysis complete.")
    except Exception as e:
        logger.error(f"Error generating deep dive report: {e}")
        print(f"Error: {e}")
    finally:
         # Cleanup (close browser if it was opened)
        if agent and agent.tools:
            for tool in agent.tools:
                if hasattr(tool, "close") and callable(tool.close):
                    print(f"Closing tool: {tool}")
                    await tool.close()


@app.command()
def deep_dive(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
    debug: bool = typer.Option(
        False, help="Enable debug mode (visible browser, verbose logs)"
    ),
):
    """
    Stage 4: Generates a Deep Dive Report from the TLDR summary using Browser.
    """
    asyncio.run(run_deep_dive(model_id=model, debug=debug))



@app.command()
def install_cron(
    spec: str = typer.Argument(..., help="The cron schedule (e.g. '0 8 * * *' or 'every day at 8am')"),
    model: Optional[str] = typer.Option(
        None, help="Model ID for NL parsing (if not a valid cron expression)"
    ),
):
    """
    Installs a cron job to run `run_all` command.
    """
    import shutil
    from crontab import CronTab
    from google import genai

    # 1. Parse Schedule
    cron_spec = spec.strip()
    is_cron = False
    
    # Check if likely a cron expression
    if cron_spec.startswith("@"):
        is_cron = True
    else:
        parts = cron_spec.split()
        # Basic check for 5 parts
        if len(parts) == 5:
             # Basic char check
             if all(c in "0123456789*/,-" for part in parts for c in part):
                 is_cron = True

    if not is_cron:
        try:
            print(f"Interpreting schedule: '{spec}'...")
            client = genai.Client()
            if not model:
                model = os.getenv("MODEL_ID", "gemini-2.0-flash")
            
            prompt = (
                f"Convert the following schedule description into a standard cron expression (5 fields).\n"
                f"Description: {spec}\n"
                f"Output ONLY the cron expression. Do not output any markdown or explanation."
            )
            
            @retry_sync(
                max_retries=config.get_retry_max_attempts(),
                initial_delay=config.get_retry_delay_seconds()
            )
            def generate_cron():
                return client.models.generate_content(model=model, contents=prompt)

            response = generate_cron()
            if response.text:
                 cron_spec = response.text.strip().replace("`", "")
                 print(f"Converted to: {cron_spec}")
            else:
                 print("Error: Empty response from LLM")
                 return
        except Exception as e:
            print(f"Error parsing schedule: {e}")
            return

    # 2. Locate uv and project root
    uv_path = shutil.which("uv")
    if not uv_path:
        # Fallback to absolute path if which fails but we are running via uv
        uv_path = "/usr/local/bin/uv" # weak guess, better to fail
        print("Error: `uv` not found in PATH.")
        return

    # Assuming this script is at src/main.py
    script_path = os.path.abspath(__file__)
    src_dir = os.path.dirname(script_path)
    project_root = os.path.dirname(src_dir)
    
    # 3. Construct command
    # cd "/path/to/project" && "/path/to/uv" run src/main.py run_all >> "/path/to/output/cron.log" 2>&1
    output_dir = config.get_output_dir()
    # Ensure absolute path for log file
    if not os.path.isabs(output_dir):
        output_dir = os.path.join(project_root, output_dir)
    
    log_file = os.path.join(output_dir, "cron.log")
    job_command = f'cd "{project_root}" && "{uv_path}" run src/main.py run_all >> "{log_file}" 2>&1'
    
    # 4. Update Crontab
    try:
        # User crontab
        cron = CronTab(user=True)
        # Remove existing job if any
        iter_jobs = cron.find_comment('smart-feeds-run-all')
        for job in iter_jobs:
            cron.remove(job)
        
        job = cron.new(command=job_command, comment='smart-feeds-run-all')
        job.setall(cron_spec)
        
        if not job.is_valid():
            print(f"Error: Invalid cron expression '{cron_spec}'")
            return

        cron.write()
        print(f"Successfully installed cron job: {cron_spec}")
        print(f"Command: {job_command}")
    except Exception as e:
        print(f"Error installing cron job: {e}")


@app.command()
def run_all(
    model: Optional[str] = typer.Option(
        None, help="Model ID to use (e.g., gemini-2.0-flash)"
    ),
    debug: bool = typer.Option(
        False, help="Enable debug mode (verbose logs)"
    ),
):
    """
    Runs the entire pipeline: Fetch -> Curate -> Summarize.
    """
    print(f"Starting Smart Feeds Pipeline... (Debug: {debug})")

    # 1. Fetch
    asyncio.run(run_fetch_batch(model_id=model, debug=debug))

    # 2. Curate
    asyncio.run(run_curate(model_id=model, debug=debug))

    # 3. Summarize
    asyncio.run(run_summarize(model_id=model, debug=debug))

    print("Pipeline complete.")

if __name__ == "__main__":
    app()
