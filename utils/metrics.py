"""
utils/metrics.py

Metrics collection and reporting utilities.

This module provides a MetricRegistry for tracking various
metrics such as counters and execution timings.
"""

import threading
from time import perf_counter
from collections import defaultdict
from typing import Any, Dict

# ---------- Metric Registry -----------
class MetricsRegistry:
    """
    Registry for collecting and reporting metrics.

    This registry supports counting occurrences of events
    and measuring execution time of code blocks.
    """
    
    def __init__(self):
        """
        Initialize the metric registry.
        """
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._timings: Dict[str, float] = defaultdict(list)

    # ---------- Counters -----------
    def inc(self, name: str, value: int = 1) -> None:
        """
        Increment the counter for a given metric.
        Args:
            name (str): Name of the metric.
            value (int): Amount to increment by.
        """
        with self._lock:
            self._counters[name] += value

    def get_counters(self) -> Dict[str, int]:
        """
        Get the current counter values.
        """
        with self._lock:
            return dict(self._counters)
        
    # ---------- Timings -----------
    def record_timing(self, name: str, duration: float) -> None:
        """
        Record a timing for a given metric.
        Args:
            name (str): Name of the metric.
            duration (float): Duration to record (in seconds).
        """
        with self._lock:
            self._timings[name].append(duration)

    def get_timings(self) -> Dict[str, Dict[str, float]]:
        """
        Get aggregated timing statistics.
        Returns:
            Dict[str, Dict[str, float]]: A dictionary with average and max timings.
        """
        with self._lock:
            return {
                name: {
                    "count": len(values),
                    "avg": sum(values) / len(values),
                    "max": max(values),
                }
                for name, values in self._timings.items()
                if values
            }
        
# ---------- Context Manager for Timing -----------
class TimedBlock:
    """
    Context manager to record execution time.
    """

    def __init__(self, registry: MetricsRegistry, name: str):
        """
        Initialize the timed block.
        """
        self._registry = registry
        self._name = name

    def __enter__(self):
        """
        Start timing.
        """
        self._start = perf_counter()

    def __exit__(self, exc_type, exc, tb):
        """
        Stop timing and record the duration.
        """
        duration = perf_counter() - self._start
        self._registry.record_timing(self._name, duration)
        return False