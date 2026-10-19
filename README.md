# Smart Feeds

A personal content curator agent that fetches content from websites and RSS feeds, filters it based on your interests, and summarizes relevant items.

## Setup

It is recommended to install Smart Feeds directly via `uv tool`:

```bash
# Install globally
uv tool install git+https://github.com/codescv/smart_feeds.git
# Or if developing locally:
# uv tool install -e .
```

## Usage

First, initialize a new workspace directory to hold your config and data:

```bash
mkdir my-feeds && cd my-feeds
smartfeeds init
```

Then edit `config.toml`, `sources.toml`, and `interests.md` generated in that directory.

Run the curator pipelines:

```bash
# Run batch processing (deterministic Python fetch for RSS, LLM agent for browser/HTTP)
smartfeeds fetch

# Run filtering & ranking (batches of 40 against interests.md)
smartfeeds curate

# Run daily summary
smartfeeds summarize

# Or run the full pipeline sequentially
smartfeeds run-all
```
## Scheduling

You can automatically run the full pipeline (`fetch`, `curate`, `summarize`) on a recurring schedule by installing a cron job:

```bash
# Provide a natural language description of your schedule
smartfeeds install-cron "every day at 8 AM"
```

This will parse your request into a valid cron expression, resolve persistent paths for `npx` (including `fnm` installations) and `gcloud` via `os.path.realpath`, and install it to your user's crontab for the current workspace. Ensure you are in your workspace directory or use the `-w` flag.

Note: in macOS, may need to approve several popups for cronjob to work.

## Configuration
- `sources.toml`: Configure `browser` websites, `http` pages, `rss_text` feeds, and `rss_audio` podcast feeds. URLs are automatically normalized (tracking parameters stripped) and deduplicated using 64-bit (16-char) MD5 hashes in `feeds/seen_urls.txt`.
- `interests.md`: Define your interests for curation and filtering.
- `config.toml`: Set application settings (model IDs, retry limits, paths, and optional `custom_prompt_path` for summarizer).
- Environment Variables: You can also use system environment variables like `GOOGLE_API_KEY` (or `GOOGLE_GENAI_USE_VERTEXAI=true` for Vertex AI) and `HTTP_PROXY`.

## Debug
Use built-in web ui of ADK to debug agents.
```bash
uv run adk web debug_agents
```

