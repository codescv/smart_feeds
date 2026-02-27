import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def get_workspace_dir() -> str:
    """Returns the workspace directory path."""
    return os.getenv("WORKSPACE_DIR", ".")

def get_input_dir() -> str:
    """Returns the input directory path."""
    workspace = get_workspace_dir()
    input_dir = os.getenv("INPUT_DIR", "inputs")
    if os.path.isabs(input_dir):
        return input_dir
    return os.path.join(workspace, input_dir)

def get_output_dir() -> str:
    """Returns the output directory path."""
    workspace = get_workspace_dir()
    output_dir = os.getenv("OUTPUT_DIR", "data")
    if os.path.isabs(output_dir):
        return output_dir
    return os.path.join(workspace, output_dir)

def get_browser_user_data_dir() -> str:
    """Returns the browser user data directory path."""
    # Check for direct env var first
    env_val = os.getenv("BROWSER_USER_DATA_DIR")
    if env_val:
        if os.path.isabs(env_val):
            return env_val
        return os.path.join(get_workspace_dir(), env_val)
    
    # Fallback to input_dir/browser
    return os.path.join(get_input_dir(), "browser")

def get_sources_config_path() -> str:
    """Returns the path to the sources configuration file."""
    return os.path.join(get_input_dir(), "sources.toml")

def get_retry_max_attempts() -> int:
    """Returns the maximum number of retries for 429 errors."""
    return int(os.getenv("RETRY_MAX_ATTEMPTS", "8"))

def get_retry_delay_seconds() -> float:
    """Returns the initial delay in seconds for retries."""
    return float(os.getenv("RETRY_DELAY_SECONDS", "5.0"))


def get_model_id() -> str:
    """Returns the text generation model ID."""
    return os.getenv("MODEL_ID", "gemini-2.0-flash")


def get_image_model_id() -> str:
    """Returns the image generation model ID."""
    return os.getenv("IMAGE_MODEL_ID", "imagen-3.0-generate-001")
