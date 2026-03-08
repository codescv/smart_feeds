# Smart Feeds

A personal content curator agent that fetches content from websites and RSS feeds, filters it based on your interests, and summarizes relevant items.

## Setup

It is recommended to install Smart Feeds directly via `uv tool`:

```bash
# Install globally
uv tool install git+https://github.com/yourusername/smart_feeds.git
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
# Run batch processing (fetch)
smartfeeds fetch

# Run filtering
smartfeeds curate

# Run summary
smartfeeds summarize
```
## Scheduling

You can automatically run the full pipeline (fetch, curate, summarize) on a recurring schedule by installing a cron job:

```bash
# Provide a natural language description of your schedule
smartfeeds install-cron "every day at 8 AM"
```

This will parse your request into a valid cron expression and install it to your user's crontab for the current workspace. Ensure you are in your workspace directory or use the `-w` flag.

## Configuration
- `sources.toml`: Configure websites and RSS feeds.
- `interests.md`: Define your interests for filtering.
- `config.toml`: Set application settings (model IDs, retry limits, paths).
- Environment Variables: You can also use system environment variables like `GOOGLE_API_KEY` and `HTTP_PROXY`.

## Debug
Use built-in web ui of ADK to debug agents.
```bash
uv run adk web debug_agents
```

