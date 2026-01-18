"""
utils/timing.py

Utility functions for handling timing and duration calculations.

This module provides helper functions to compute durations
between timestamps and format time-related data.
"""

from time import perf_counter
from typing import Optional

class Timer:
    """
    Context manager for measuring elapsed time.
    """

    def __enter__(self):
        """
        Start the timer.
        """
        self.start_time = perf_counter()
        return self
    
    def __exit__(self, exec_type, exc, tb):
        """
        Stop the timer and calculate elapsed time.
        Args:
            exec_type: Exception type if raised.
            exc: Exception value if raised.
            tb: Traceback if exception raised.
        """
        self.end_time = perf_counter()
        self.elapsed = self.end_time - self.start_time
        return False # Do not suppress exceptions