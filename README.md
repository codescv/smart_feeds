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

Then edit `.env`, `sources.toml`, and `interests.md` generated in that directory.

Run the curator pipelines:

```bash
# Run batch processing (fetch)
smartfeeds fetch

# Run filtering
smartfeeds curate

# Run summary
smartfeeds summarize
```

## Configuration
- `inputs/sources.toml`: Configure websites and RSS feeds.
- `inputs/interests.md`: Define your interests for filtering.
- `.env`: Set environment variables (API keys, etc).

## Debug
Use built-in web ui of ADK to debug agents.
```bash
uv run adk web debug_agents
```

