import sys
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add the project root to sys.path so we can import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', 'src'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from agents.summarizer_agent import create_summarizer_agent

# Initialize the agent instance required by adk web
# We can pass specific model_id or other params if needed
root_agent = create_summarizer_agent()
