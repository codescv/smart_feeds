# Smart Feeds Design Document

## 1. Overview
Smart Feeds is a personal content curator agent designed to alleviate information overload. It fetches content from various sources (websites, RSS feeds), filters it based on user-defined interests, and generates a daily summarized "TLDR" digest.

## 2. Architecture
The system follows a modular three-stage pipeline powered by Google ADK (Agent Development Kit):
1.  **Fetch Phase (`smartfeeds fetch`)**:
    *   **Deterministic RSS Pipeline**: Standard text (`rss_text`) and podcast (`rss_audio`) RSS feeds are fetched deterministically in pure Python (`process_rss_source`), deduplicated against `seen_urls.txt`, and appended directly to `feeds/raw/YYYY-MM-DD.md` without LLM overhead.
    *   **Fetcher Agent**: Invoked for dynamic websites (`browser`) and static HTML pages (`http`) to extract structured items and append them to the raw log.
2.  **Curate Phase (`smartfeeds curate`)**:
    *   **Curator Agent**: Reads raw items in batches (`BATCH_SIZE = 40`), filters and ranks them against `interests.md`, translates selected items into `feeds/curated/YYYY-MM-DD.md`, and logs rejected items with a concise 1-sentence reason (omitting full `content` to save output tokens) to `feeds/filtered/YYYY-MM-DD.md`.
3.  **Summarize Phase (`smartfeeds summarize`)**:
    *   **Summarizer Agent**: Reads curated items (`feeds/curated/YYYY-MM-DD.md`), transcribes audio enclosures if present, groups items by topic, and saves the daily digest to `feeds/tldr/YYYY-MM-DD.md`.

## 3. Components

### 3.1 CLI Entry Point (`src/smart_feeds/main.py`)
Built with `typer`, it provides the following commands exposed via the `smartfeeds` executable:
*   `init`: Scaffolds a new workspace with template configuration files.
*   `fetch`: Triggers the batch fetching process for all configured sources (deterministic Python fetch for RSS feeds, LLM Fetcher Agent for `browser`/`http` sources).
*   `curate`: Filters and ranks raw items in batches of 40 against user interests.
*   `summarize`: Triggers the daily summarization process (and optional cover image generation).
*   `run-all`: Runs `fetch`, `curate`, and `summarize` sequentially.
*   `install-cron`: Translates a natural language schedule into a cron expression and installs a persistent crontab entry (resolving `npx` and `gcloud` via `os.path.realpath` with `~/.local/share/fnm` fallbacks so ephemeral `fnm_multishells` paths are never written to crontab).
*   `configure-browser`: Launches a visible browser instance for the user to handle authentication (e.g., logging into Twitter/X).

### 3.2 Agents (`src/smart_feeds/agents/`)

#### Fetcher Agent (`fetcher_agent.py`)
*   **Role**: Content acquisition for `browser` and `http` sources.
*   **Tools**:
    *   `browser_toolset`: MCP-based Playwright browser for dynamic websites.
    *   `fetch_website_content`: HTTP/BeautifulSoup scraper for static pages.
    *   `deduplicate_items` & `append_to_raw_log`: Deduplicates and logs collected items.

#### Curator Agent (`curator_agent.py`)
*   **Role**: Filtering, ranking, and translating raw items based on `interests.md`.
*   **Tools**: `read_raw_log`, `append_to_curated_log`, `append_to_filtered_log`.
*   **Logic**:
    *   Evaluates batches of raw items against `interests.md`.
    *   **Token Optimization**: `append_to_filtered_log` records only `title`, `url`, `source`, `published`, and a concise 1-sentence `reason` (omitting `content` so the LLM does not translate or output rejected article bodies).
    *   **Cross-Source Consistency**: Prioritizes primary/authoritative sources (e.g., official lab blogs, TechCrunch) over secondary rumor threads when multiple items in a batch cover the same event.
    *   **Discussion Links**: Evaluates Hacker News items (`[Comments](https://news.ycombinator.com/...)`) by title and domain, preserving the HN discussion URL alongside the article URL.

#### Summarizer Agent (`summarizer_agent.py`)
*   **Role**: Editorial synthesis of curated items.
*   **Tools**:
    *   `read_curated_log`: Reads the curated log file.
    *   `transcribe_audio_url`: Downloads and transcribes podcast audio via Gemini (supports both `GOOGLE_API_KEY` and Vertex AI via `GOOGLE_GENAI_USE_VERTEXAI=true`, using the configured model ID).
    *   `save_daily_summary`: Writes the final markdown digest.

### 3.3 Tools (`src/smart_feeds/tools/`)

#### MCP Browser (`src/smart_feeds/tools/mcp_browser.py`)
*   Wraps the `@playwright/mcp` server.
*   Manages the browser lifecycle (headed vs headless) and user data directory persistence.
*   Passes the full process environment (`os.environ.copy()`) into `StdioServerParameters` so desktop display variables (`DISPLAY`, `WAYLAND_DISPLAY`, `XAUTHORITY`, `XDG_RUNTIME_DIR`) are preserved on Linux when launching a headed browser.
*   Resolves `npx` via `_resolve_npx_command()` using `os.path.realpath` and falls back to `~/.local/share/fnm/aliases/default/bin/npx` or `~/.local/share/fnm/node-versions/*/installation/bin/npx` when running in restricted `PATH` environments like `cron`, prepending the resolved binary directory to `env["PATH"]` so `node` is always discoverable.

#### RSS Fetcher (`src/smart_feeds/tools/rss.py`)
*   Uses `feedparser` to fetch standard RSS/Atom feeds (`limit=30` for Reddit, `limit=3` for audio podcasts, `limit=10` for standard feeds).
*   Extracts feed title (`source`), entry `title`, `link`, `summary`, `published` date, and audio `media` enclosures.
*   Respects `HTTP_PROXY` if configured.

#### Deduplication (`src/smart_feeds/tools/dedup.py`)
*   Normalizes URLs (`_normalize_url`) by stripping whitespace, trailing `/`, and common tracking query parameters (`utm_source`, `utm_medium`, `utm_campaign`, `utm_term`, `utm_content`, `fbclid`, `gclid`) while preserving meaningful query parameters.
*   Computes a 16-character (64-bit) MD5 hex digest (`_compute_hash`) stored in `feeds/seen_urls.txt` (up to 100,000 entries) to prevent birthday-paradox hash collisions, while maintaining backward compatibility with legacy 8-character hashes.

#### Storage (`src/smart_feeds/tools/storage.py`)
*   **Raw Log**: `feeds/raw/YYYY-MM-DD.md` (cleaned titles up to 200 chars, HTML-to-Markdown content conversion, and exact item counting via non-empty separator splits).
*   **Curated Log**: `feeds/curated/YYYY-MM-DD.md` (selected items with relevance scores and explanations).
*   **Filtered Log**: `feeds/filtered/YYYY-MM-DD.md` (rejected items with concise 1-sentence filtering reasons).
*   **TLDR Summary**: `feeds/tldr/YYYY-MM-DD.md` (clean Markdown digest for end-user reading).

## 4. Configuration

### 4.1 Inputs
Workspace configuration files:
*   `sources.toml`: Configuration file for sources.
    ```toml
    # Example
    websites = [
        "https://news.ycombinator.com",
        { url = "https://x.com/home", instruction = "Scan visible tweets..." }
    ]
    rss = [
        "https://feeds.feedburner.com/PythonInsider"
    ]
    ```
*   `interests.md`: Natural language description of what the user cares about (and what to ignore).
*   `config.toml`: Settings governing the core agent logic:
    *   `model_id`: specific model version (default: `gemini-2.0-flash`).
    *   `output_language`: Language for the final summary (e.g., "English", "Chinese").
    *   `browser_user_data_dir`: Override path for browser profile.
    *   `custom_prompt_path`: Optional path to a markdown file (absolute or relative to workspace) to use as the summarizer prompt instead of the hardcoded one.
*   Environment Variables:
    *   `GOOGLE_API_KEY`: For Gemini access.
    *   `HTTP_PROXY` / `HTTPS_PROXY`: For proxy routing.

## 5. Directory Structure
```
.
├── config.toml           # App settings
├── sources.toml          # Source definitions
├── interests.md          # User preferences
├── browser/              # Chrome profile data
├── data/
│   ├── details/          # Raw collected items (YYYY-MM-DD.md)
│   └── tldr/             # Final summaries (YYYY-MM-DD.md)
├── src/
│   └── smart_feeds/      # Package source
│       ├── main.py       # CLI entry point
│       ├── agents/       # Agent definitions
│       └── tools/        # Tool definitions (browser, rss, storage)
└── ...
```

## 6. Future Considerations
*   **Database Integration**: Migrate from Markdown files to SQLite/PostgreSQL for better querying and history management.
*   **Parallel Fetching**: Run fetcher agents concurrently to speed up batch processing.
*   **Web UI**: Develop a proper frontend to view summaries and manage sources.
