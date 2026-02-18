# Smart Feeds - AI Agent to personalize my information intake

There are a lot of information from the internet (social network, news, feeds, podcasts, youtube), some
information are useful, and others are noisy.
You are my personal AI agent to help me deal with information overload, and ensure my mental health.

# Requirements
1. Fetch from multiple data sources
    - Websites (x.com, xiaohongshu.com, youtube etc) via Browser automation (playwright)
    - RSS sources import (text blogs / audio podcasts / maybe videos)
2. Interest based filtering and ranking
    - Store user interest in a markdown file that can be edited.
    - Offer to update the interest file based on user interaction and feedback.
3. Summarization capabilities
    - Cronjobs / on demand summarization of new feeds
4. Output
    - Display organized information in markdown in a Web UI.
    - Store my everyday reading (summarizations and my feedback / comments) in markdown files for my records.

# Non-Requirements
1. This is for "incremental, byte sized" readings only. I don't intend to read full books using this agent.

# Technical Requirements
1. Use Python to develop
2. Use `uv` to manage dependencies.
3. Use Google ADK (Agent Development Kit) with Gemini API Key as the LLM API.

