import os
import tomllib
from functools import lru_cache

_workspace_dir = os.path.abspath(os.getcwd())

def set_workspace_dir(path: str):
    """Sets the workspace directory, resolving it to an absolute path."""
    global _workspace_dir
    _workspace_dir = os.path.abspath(path)
    # Clear parsed config cache so it re-reads from the new workspace if needed
    __get_parsed_config.cache_clear()

def get_workspace_dir() -> str:
    """Returns the workspace directory path."""
    return _workspace_dir

@lru_cache(maxsize=1)
def __get_parsed_config() -> dict:
    """Reads and parses the config.toml file once."""
    config_path = os.path.join(get_workspace_dir(), "config.toml")
    if os.path.exists(config_path):
        try:
            with open(config_path, "rb") as f:
                config_data = tomllib.load(f)
                _inject_env_vars(config_data)
                return config_data
        except Exception as e:
            print(f"Warning: Failed to parse {config_path}: {e}")
    return {}

def _inject_env_vars(config_data: dict):
    """Injects specific configuration settings back into the active environment variables."""
    # Network proxies
    network = config_data.get("network", {})
    for key in ["http_proxy", "https_proxy", "no_proxy"]:
        if key in network:
            os.environ[key] = str(network[key])
            os.environ[key.upper()] = str(network[key])
            
    # Auth/Cloud settings
    auth = config_data.get("auth", {})
    for key in ["google_api_key", "google_cloud_project", "google_cloud_location",
                "google_vertexai_project", "google_genai_use_vertexai", "google_vertexai_location"]:
        if key in auth:
            os.environ[key.upper()] = str(auth[key])

def _get_setting(section: str, key: str, default: any = None) -> any:
    """Helper to get a setting from TOML first, then default."""
    config_data = __get_parsed_config()
    if section in config_data and key in config_data[section]:
        return config_data[section][key]
            
    return default

def get_output_dir() -> str:
    """Returns the output directory path (for final summaries and raw logs)"""
    workspace = get_workspace_dir()
    output_dir = _get_setting("paths", "output_dir", default="data")
    if os.path.isabs(output_dir):
        return output_dir
    return os.path.join(workspace, output_dir)

def get_browser_user_data_dir() -> str:
    """Returns the browser user data directory path."""
    workspace = get_workspace_dir()
    env_val = _get_setting("paths", "browser_user_data_dir", default="browser")
    if os.path.isabs(env_val):
        return env_val
    return os.path.join(workspace, env_val)

def get_sources_config_path() -> str:
    """Returns the path to the sources configuration file."""
    return os.path.join(get_workspace_dir(), "sources.toml")

def get_retry_max_attempts() -> int:
    """Returns the maximum number of retries for 429 errors."""
    return int(_get_setting("settings", "retry_max_attempts", default="8"))

def get_retry_delay_seconds() -> float:
    """Returns the initial delay in seconds for retries."""
    return float(_get_setting("settings", "retry_delay_seconds", default="5.0"))

def get_model_id() -> str:
    """Returns the text generation model ID."""
    return _get_setting("models", "model_id", default="gemini-2.0-flash")

def get_image_model_id() -> str:
    """Returns the image generation model ID."""
    return _get_setting("models", "image_model_id", default="imagen-3.0-generate-001")

