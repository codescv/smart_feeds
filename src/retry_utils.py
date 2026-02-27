import asyncio
import logging
import time
import functools
from typing import Callable, Any, TypeVar, Awaitable, Union, Coroutine

logger = logging.getLogger(__name__)

T = TypeVar("T")

def is_retryable_error(e: Exception) -> bool:
    """
    Determines if an exception is a retryable 429 Resource Exhausted error.
    """
    error_str = str(e)
    # Check for "429" or "RESOURCE_EXHAUSTED" or "Resource exhausted"
    if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str or "Resource exhausted" in error_str:
        return True
    return False

async def run_with_retry(
    func: Callable[..., Awaitable[T]],
    *args,
    max_retries: int = 5,
    initial_delay: float = 2.0,
    **kwargs
) -> T:
    """
    Retries an async function call with exponential backoff if a 429 error occurs.
    """
    attempt = 0
    while True:
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            if not is_retryable_error(e):
                raise
            
            attempt += 1
            if attempt > max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}. Last error: {e}")
                raise
            
            delay = initial_delay * (2 ** (attempt - 1))
            logger.warning(
                f"Retryable error in {func.__name__} (attempt {attempt}/{max_retries}): {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            await asyncio.sleep(delay)

def run_with_retry_sync(
    func: Callable[..., T],
    *args,
    max_retries: int = 5,
    initial_delay: float = 2.0,
    **kwargs
) -> T:
    """
    Retries a synchronous function call with exponential backoff if a 429 error occurs.
    """
    attempt = 0
    while True:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if not is_retryable_error(e):
                raise
            
            attempt += 1
            if attempt > max_retries:
                logger.error(f"Max retries ({max_retries}) exceeded for {func.__name__}. Last error: {e}")
                raise
            
            delay = initial_delay * (2 ** (attempt - 1))
            logger.warning(
                f"Retryable error in {func.__name__} (attempt {attempt}/{max_retries}): {e}. "
                f"Retrying in {delay:.2f}s..."
            )
            time.sleep(delay)

def retry_async(max_retries: int = 5, initial_delay: float = 2.0):
    """
    Decorator for async functions to retry on 429 errors.
    """
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            return await run_with_retry(
                func, # Pass the original func
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                **kwargs
            )
        return wrapper
    return decorator

def retry_sync(max_retries: int = 5, initial_delay: float = 2.0):
    """
    Decorator for sync functions to retry on 429 errors.
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            return run_with_retry_sync(
                func,
                *args,
                max_retries=max_retries,
                initial_delay=initial_delay,
                **kwargs
            )
        return wrapper
    return decorator
