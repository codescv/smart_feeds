import pytest
import os
import sys

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../src")))

@pytest.fixture
def mock_env(monkeypatch):
    """Sets up default environment variables for testing."""
    monkeypatch.setenv("WORKSPACE_DIR", "/tmp/workspace")
    monkeypatch.setenv("INPUT_DIR", "inputs")
    monkeypatch.setenv("OUTPUT_DIR", "data")
    monkeypatch.setenv("MODEL_ID", "gemini-2.0-flash-test")
    monkeypatch.setenv("OUTPUT_LANGUAGE", "English")
