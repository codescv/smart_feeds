import pytest
import asyncio
import time
from unittest.mock import MagicMock
from retry_utils import is_retryable_error, run_with_retry, run_with_retry_sync, retry_async, retry_sync

class ResourceExhaustedError(Exception):
    def __str__(self):
        return "429 Resource exhausted"

class OtherError(Exception):
    def __str__(self):
        return "Something else went wrong"

def test_is_retryable_error():
    assert is_retryable_error(ResourceExhaustedError())
    assert is_retryable_error(Exception("Some error with 429 in it"))
    assert not is_retryable_error(OtherError())

@pytest.mark.asyncio
async def test_run_with_retry_success():
    mock_func = MagicMock(return_value="success")
    async def async_func():
        return mock_func()
    
    result = await run_with_retry(async_func)
    assert result == "success"
    assert mock_func.call_count == 1

@pytest.mark.asyncio
async def test_run_with_retry_failure_then_success():
    mock_func = MagicMock(side_effect=[ResourceExhaustedError(), "success"])
    mock_func.__name__ = "mock_func"
    async def async_func():
        return mock_func()
    
    # Use small delay for test speed
    result = await run_with_retry(async_func, max_retries=2, initial_delay=0.01)
    assert result == "success"
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_run_with_retry_max_retries_exceeded():
    mock_func = MagicMock(side_effect=ResourceExhaustedError())
    mock_func.__name__ = "mock_func"
    async def async_func():
        return mock_func()
    
    with pytest.raises(ResourceExhaustedError):
        await run_with_retry(async_func, max_retries=2, initial_delay=0.01)
    
    assert mock_func.call_count == 3  # Initial + 2 retries

def test_run_with_retry_sync_success():
    mock_func = MagicMock(return_value="success")
    result = run_with_retry_sync(mock_func)
    assert result == "success"
    assert mock_func.call_count == 1

def test_run_with_retry_sync_failure_then_success():
    mock_func = MagicMock(side_effect=[ResourceExhaustedError(), "success"])
    mock_func.__name__ = "mock_func"
    result = run_with_retry_sync(mock_func, max_retries=2, initial_delay=0.01)
    assert result == "success"
    assert mock_func.call_count == 2

@pytest.mark.asyncio
async def test_retry_async_decorator():
    mock_func = MagicMock(side_effect=[ResourceExhaustedError(), "success"])
    
    @retry_async(max_retries=2, initial_delay=0.01)
    async def async_func():
        return mock_func()
    
    result = await async_func()
    assert result == "success"
    assert mock_func.call_count == 2

def test_retry_sync_decorator():
    mock_func = MagicMock(side_effect=[ResourceExhaustedError(), "success"])
    
    @retry_sync(max_retries=2, initial_delay=0.01)
    def sync_func():
        return mock_func()
    
    result = sync_func()
    assert result == "success"
    assert mock_func.call_count == 2
