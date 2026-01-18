"""
utils/retry.py

Retry decorator for function execution with exponential backoff.

This module provides a `Retry` decorator that can be applied to functions
to automatically retry them upon failure, with configurable maximum retries
and delay between attempts.
"""

import time
import traceback
from functools import wraps
from turtle import delay

class Retry:
    """
    Decorator to retry a function upon exception.
    """

    def __init__(self, max_retries: int = 3, base_delay: float = 1.0):
        """
        Initialize the retry decorator.
        Args:
            max_retries (int): Maximum number of retry attempts.
            base_delay (float): Base delay in seconds between retries.
        """
        self.max_retries = max_retries
        self.base_delay = base_delay

    def __call__(self, func):
        """
        Wrap the function with retry logic.
        Args:
            func: Function to be decorated.
        Returns:
            Wrapped function with retry capability.
        """
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, self.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exc = e
                    wait_time = self.base_delay * (2 ** (attempt - 1))
                    print(f"Attempt {attempt} failed: {e}. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)

            raise last_exc
        return wrapper