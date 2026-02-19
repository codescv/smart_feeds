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
# Run batch processing
uv run main.py run

# Run with specific model
uv run main.py run --model gemini-2.0-flash
```

## Configuration

- `inputs/sources.toml`: Configure websites and RSS feeds.
- `inputs/interests.md`: Define your interests for filtering.
- `.env`: Set environment variables (API keys, etc).
