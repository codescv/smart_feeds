# Smart Feeds

A personal content curator agent that fetches content from websites and RSS feeds, filters it based on your interests, and summarizes relevant items.

## Setup

This project uses `uv` for dependency management.

```bash
# Install dependencies
uv sync
```

## Usage

Run the curator:

```bash
# Run batch processing (fetch)
uv run src/main.py fetch

# Run filtering
uv run src/main.py curate

# Run summary
uv run src/main.py summarize
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

