import os
import pytest
import config

def test_defaults(monkeypatch):
    # Ensure no env vars are set that might interfere (clean slate handled by fixture potentially, but being explicit here)
    monkeypatch.delenv("WORKSPACE_DIR", raising=False)
    monkeypatch.delenv("INPUT_DIR", raising=False)
    monkeypatch.delenv("OUTPUT_DIR", raising=False)
    
    assert config.get_workspace_dir() == "."
    assert config.get_input_dir() == "./inputs"
    assert config.get_output_dir() == "./data"
    assert config.get_retry_max_attempts() == 8

def test_env_overrides(monkeypatch):
    monkeypatch.setenv("WORKSPACE_DIR", "/custom/workspace")
    monkeypatch.setenv("INPUT_DIR", "custom_inputs")
    monkeypatch.setenv("OUTPUT_DIR", "custom_output")
    monkeypatch.setenv("RETRY_MAX_ATTEMPTS", "10")
    
    assert config.get_workspace_dir() == "/custom/workspace"
    assert config.get_input_dir() == "/custom/workspace/custom_inputs"
    assert config.get_output_dir() == "/custom/workspace/custom_output"
    assert config.get_retry_max_attempts() == 10

def test_absolute_paths(monkeypatch):
    monkeypatch.setenv("INPUT_DIR", "/abs/path/inputs")
    assert config.get_input_dir() == "/abs/path/inputs"

def test_browser_user_data_dir(monkeypatch):
    monkeypatch.setenv("BROWSER_USER_DATA_DIR", "custom_browser")
    monkeypatch.setenv("WORKSPACE_DIR", "/tmp")
    assert config.get_browser_user_data_dir() == "/tmp/custom_browser"
