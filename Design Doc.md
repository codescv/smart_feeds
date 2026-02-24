# Smart Feeds Design Document

## 1. Overview
Smart Feeds is a personal content curator agent designed to alleviate information overload. It fetches content from various sources (websites, RSS feeds), filters it based on user-defined interests, and generates a daily summarized "TLDR" digest.

## 2. Architecture
The system follows a modular agentic architecture powered by Google ADK (Agent Development Kit). It consists of two main agents:
1.  **Fetcher Agent**: Responsible for gathering raw content, filtering noise, and logging relevant items.
2.  **Summarizer Agent**: Responsible for synthesizing the logged items into a cohesive daily summary.

### High-Level Data Flow
1.  **Input**: User defines sources in `sources.toml` and interests in `interests.md`.
2.  **Fetch Phase**: `main.py` iterates through sources.
    *   For each source, the **Fetcher Agent** is instantiated.
    *   The agent uses **Tools** (Browser or RSS) to get content.
    *   The agent evaluates relevance against `interests.md`.
    *   Relevant items are appended to `data/details/YYYY-MM-DD.md`.
3.  **Summarize Phase**: `main.py` triggers the **Summarizer Agent**.
    *   The agent reads `data/details/YYYY-MM-DD.md`.
    *   The agent groups and summarizes items.
    *   The final output is saved to `data/tldr/YYYY-MM-DD.md`.

## 3. Components

### 3.1 CLI Entry Point (`src/main.py`)
Built with `typer`, it provides the following commands:
*   `fetch`: Triggers the batch fetching process for all configured sources.
*   `summarize`: Triggers the daily summarization process.
*   `configure-browser`: Launches a visible browser instance for the user to handle authentication (e.g., logging into Twitter/X).
*   `webui`: Launches an interactive chat loop for debugging.

### 3.2 Agents (`src/agents/agent.py`)

#### Fetcher Agent
*   **Role**: Content acquisition and filtering.
*   **Model**: Gemini 2.0 Flash (default).
*   **Tools**:
    *   `browser_toolset`: MCP-based Playwright browser for dynamic websites.
    *   `fetch_rss_feed`: Python-based RSS parser.
    *   `append_to_details_log`: Appends structured data to the daily log.
*   **Logic**:
    *   Receives a source URL and specific instructions.
    *   Fetches content.
    *   Filters based on `interests.md`.
    *   Extracts `title`, `url`, `source`, `relevance`, and a brief `summary`.

#### Summarizer Agent
*   **Role**: Editorial and synthesis.
*   **Model**: Gemini 2.0 Flash (default).
*   **Tools**:
    *   `read_daily_details`: Reads the raw log file.
    *   `save_daily_summary`: Writes the final markdown digest.
*   **Logic**:
    *   Reads all items collected in the day.
    *   Groups them by topic/theme.
    *   Generates a high-level summary (TLDR) in the configured `OUTPUT_LANGUAGE`.

### 3.3 Tools

#### MCP Browser (`src/tools/mcp_browser.py`)
*   Wraps the `@playwright/mcp` server.
*   Manages the browser lifecycle (headed vs headless).
*   Handles user data directory persistence to maintain login sessions.

#### RSS Fetcher (`src/tools/rss.py`)
*   Uses `feedparser` to fetch standard RSS/Atom feeds.
*   Returns normalized list of items (title, link, summary, published date).
*   Respects `HTTP_PROXY` if configured.

#### Storage (`src/tools/storage.py`)
*   **Details Log**: `data/details/YYYY-MM-DD.md`
    *   Format: Markdown with finding details.
    *   Deduplication: Checks existing URLs in the file to prevent duplicate entries within the same day.
*   **TLDR Summary**: `data/tldr/YYYY-MM-DD.md`
    *   Format: Clean Markdown for end-user reading.

## 4. Configuration

### 4.1 Inputs
*   `inputs/sources.toml`: Configuration file for sources.
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
*   `inputs/interests.md`: Natural language description of what the user cares about (and what to ignore).
*   `inputs/browser/`: Directory storing browser profile (cookies, local storage) for persistent sessions.

### 4.2 Environment Variables (`.env`)
*   `GOOGLE_API_KEY`: For Gemini access.
*   `MODEL_ID`: specific model version (default: `gemini-2.0-flash`).
*   `BROWSER_USER_DATA_DIR`: Custom path for browser profile.
*   `OUTPUT_LANGUAGE`: Language for the final summary (e.g., "English", "Chinese").

## 5. Directory Structure
```
.
├── .env                  # Secrets
├── inputs/
│   ├── sources.toml      # Source definitions
│   ├── interests.md      # User preferences
│   └── browser/          # Chrome profile data
├── data/
│   ├── details/          # Raw collected items (YYYY-MM-DD.md)
│   └── tldr/             # Final summaries (YYYY-MM-DD.md)
├── src/
│   ├── main.py           # CLI entry point
│   ├── agents/           # Agent definitions
│   └── tools/            # Tool definitions (browser, rss, storage)
└── ...
```

## 6. Future Considerations
*   **Database Integration**: Migrate from Markdown files to SQLite/PostgreSQL for better querying and history management.
*   **Parallel Fetching**: Run fetcher agents concurrently to speed up batch processing.
*   **Web UI**: Develop a proper frontend to view summaries and manage sources.
