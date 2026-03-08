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

