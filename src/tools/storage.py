import os
import datetime


def append_daily_log(content: str):
    """
    Appends the given content to the daily markdown log file.
    The file is named YYYY-MM-DD.md and located in the data/ directory.
    """
    today = datetime.date.today().isoformat()
    filename = f"data/{today}.md"

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    with open(filename, "a", encoding="utf-8") as f:
        f.write(content + "\n\n")

    return f"Content appended to {filename}"
