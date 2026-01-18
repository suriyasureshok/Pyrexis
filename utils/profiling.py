"""
utils/profiling.py

Performance profiling and optimization utilities.

This module provides:
- Function execution profiling with cProfile
- Memory usage tracking with tracemalloc
- Performance decorators
- Profiling reports and analysis

Usage:
    # Profile a function
    @profile_time
    def my_function():
        ...

    # Profile with memory tracking
    @profile_memory
    def memory_intensive():
        ...

    # Generate profiling report
    with Profiler() as prof:
        # Code to profile
        ...
    prof.print_report()
"""

import time
import cProfile
import pstats
import io
import tracemalloc
import functools
import logging
from typing import Callable, Any, Optional
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ProfileStats:
    """Performance profiling statistics."""
    function_name: str
    call_count: int = 0
    total_time: float = 0.0
    min_time: float = float('inf')
    max_time: float = 0.0
    avg_time: float = 0.0
    memory_start: int = 0
    memory_end: int = 0
    memory_peak: int = 0

    def update(self, execution_time: float):
        """Update statistics with new execution time."""
        self.call_count += 1
        self.total_time += execution_time
        self.min_time = min(self.min_time, execution_time)
        self.max_time = max(self.max_time, execution_time)
        self.avg_time = self.total_time / self.call_count


class PerformanceTracker:
    """
    Track performance statistics across multiple function calls.

    Thread-safe performance tracking for profiling.
    """

    def __init__(self):
        self._stats: dict[str, ProfileStats] = defaultdict(lambda: ProfileStats(function_name=""))
        self._lock = __import__('threading').Lock()

    def record(self, function_name: str, execution_time: float):
        """Record function execution time."""
        with self._lock:
            if function_name not in self._stats:
                self._stats[function_name] = ProfileStats(function_name=function_name)
            self._stats[function_name].update(execution_time)

    def get_stats(self, function_name: str) -> Optional[ProfileStats]:
        """Get statistics for a function."""
        return self._stats.get(function_name)

    def get_all_stats(self) -> dict[str, ProfileStats]:
        """Get all tracked statistics."""
        return dict(self._stats)

    def print_report(self):
        """Print performance report."""
        print("\n" + "=" * 80)
        print("PERFORMANCE REPORT")
        print("=" * 80)
        
        if not self._stats:
            print("No profiling data collected.")
            return

        # Print header
        print(f"\n{'Function':<40} {'Calls':<10} {'Total(s)':<12} {'Avg(s)':<12} {'Min(s)':<12} {'Max(s)':<12}")
        print("-" * 80)

        # Sort by total time descending
        sorted_stats = sorted(self._stats.values(), key=lambda s: s.total_time, reverse=True)

        for stat in sorted_stats:
            print(
                f"{stat.function_name:<40} "
                f"{stat.call_count:<10} "
                f"{stat.total_time:<12.4f} "
                f"{stat.avg_time:<12.4f} "
                f"{stat.min_time:<12.4f} "
                f"{stat.max_time:<12.4f}"
            )

        print("=" * 80 + "\n")


# Global performance tracker
_tracker = PerformanceTracker()


def profile_time(func: Callable) -> Callable:
    """
    Decorator to profile function execution time.

    Args:
        func: Function to profile.

    Returns:
        Wrapped function with timing.

    Example:
        @profile_time
        def expensive_operation():
            time.sleep(1)

        expensive_operation()  # Automatically tracked
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            elapsed = time.perf_counter() - start_time
            _tracker.record(func.__name__, elapsed)
            logger.debug(f"⏱️  {func.__name__} executed in {elapsed:.4f}s")

    return wrapper


def profile_memory(func: Callable) -> Callable:
    """
    Decorator to profile function memory usage.

    Args:
        func: Function to profile.

    Returns:
        Wrapped function with memory tracking.

    Example:
        @profile_memory
        def memory_intensive():
            data = [i for i in range(1_000_000)]
            return data

        memory_intensive()  # Memory usage logged
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Start tracing
        tracemalloc.start()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Get memory stats
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            logger.debug(
                f"💾 {func.__name__} - Current: {current / 1024 / 1024:.2f} MB, "
                f"Peak: {peak / 1024 / 1024:.2f} MB"
            )

    return wrapper


def profile_all(func: Callable) -> Callable:
    """
    Decorator to profile both time and memory.

    Args:
        func: Function to profile.

    Returns:
        Wrapped function with full profiling.

    Example:
        @profile_all
        def complex_operation():
            # Heavy computation
            ...
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        # Start memory tracing
        tracemalloc.start()
        start_time = time.perf_counter()
        
        try:
            result = func(*args, **kwargs)
            return result
        finally:
            # Time stats
            elapsed = time.perf_counter() - start_time
            _tracker.record(func.__name__, elapsed)
            
            # Memory stats
            current, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            
            logger.info(
                f"📊 {func.__name__} - "
                f"Time: {elapsed:.4f}s, "
                f"Memory: {current / 1024 / 1024:.2f} MB (peak: {peak / 1024 / 1024:.2f} MB)"
            )

    return wrapper


class Profiler:
    """
    Context manager for detailed profiling using cProfile.

    Captures detailed call statistics and generates reports.

    Example:
        with Profiler() as prof:
            # Code to profile
            expensive_function()
            another_function()

        prof.print_report(top=20)
    """

    def __init__(self, enabled: bool = True):
        """
        Initialize profiler.

        Args:
            enabled: Whether profiling is enabled.
        """
        self.enabled = enabled
        self._profiler: Optional[cProfile.Profile] = None
        self._stats: Optional[pstats.Stats] = None

    def __enter__(self):
        """Start profiling."""
        if self.enabled:
            self._profiler = cProfile.Profile()
            self._profiler.enable()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop profiling and collect stats."""
        if self.enabled and self._profiler:
            self._profiler.disable()
            # Create stats object
            stream = io.StringIO()
            self._stats = pstats.Stats(self._profiler, stream=stream)

    def print_report(self, top: int = 20, sort_by: str = 'cumulative'):
        """
        Print profiling report.

        Args:
            top: Number of top functions to show.
            sort_by: Sort key ('cumulative', 'time', 'calls').
        """
        if not self._stats:
            print("No profiling data available.")
            return

        print("\n" + "=" * 80)
        print("DETAILED PROFILING REPORT (cProfile)")
        print("=" * 80 + "\n")

        self._stats.sort_stats(sort_by)
        self._stats.print_stats(top)

    def save_report(self, filename: str):
        """
        Save profiling report to file.

        Args:
            filename: Output file path.
        """
        if not self._stats:
            logger.warning("No profiling data to save.")
            return

        with open(filename, 'w') as f:
            stats_stream = io.StringIO()
            sorted_stats = pstats.Stats(self._stats.stats, stream=stats_stream)
            sorted_stats.sort_stats('cumulative')
            sorted_stats.print_stats()
            f.write(stats_stream.getvalue())

        logger.info(f"Profiling report saved to {filename}")


@contextmanager
def memory_profiler():
    """
    Context manager for memory profiling.

    Tracks memory allocation during code execution.

    Example:
        with memory_profiler():
            # Code to profile
            large_data = [i for i in range(10_000_000)]
    """
    tracemalloc.start()
    snapshot_start = tracemalloc.take_snapshot()
    
    try:
        yield
    finally:
        snapshot_end = tracemalloc.take_snapshot()
        tracemalloc.stop()
        
        # Compare snapshots
        top_stats = snapshot_end.compare_to(snapshot_start, 'lineno')
        
        print("\n" + "=" * 80)
        print("MEMORY PROFILING REPORT")
        print("=" * 80)
        print("\nTop 10 memory allocations:")
        
        for stat in top_stats[:10]:
            print(f"{stat}")
        
        print("=" * 80 + "\n")


def get_performance_report() -> dict[str, ProfileStats]:
    """
    Get global performance statistics.

    Returns:
        Dictionary of function names to ProfileStats.

    Example:
        stats = get_performance_report()
        for func_name, stat in stats.items():
            print(f"{func_name}: {stat.avg_time:.4f}s avg")
    """
    return _tracker.get_all_stats()


def print_performance_report():
    """Print global performance report."""
    _tracker.print_report()


def reset_performance_stats():
    """Reset all performance statistics."""
    global _tracker
    _tracker = PerformanceTracker()
    logger.info("Performance statistics reset")


# Example usage
if __name__ == "__main__":
    # Setup logging to see profiling output
    logging.basicConfig(level=logging.DEBUG)

    # Test time profiling
    @profile_time
    def slow_function():
        time.sleep(0.1)
        return "done"

    # Test memory profiling
    @profile_memory
    def memory_function():
        data = [i ** 2 for i in range(100000)]
        return len(data)

    # Test combined profiling
    @profile_all
    def combined_function():
        data = []
        for i in range(50000):
            data.append(i ** 2)
        time.sleep(0.05)
        return data

    # Run functions multiple times
    for _ in range(5):
        slow_function()
        memory_function()
        combined_function()

    # Print performance report
    print_performance_report()

    # Test detailed profiling
    print("\n\nDetailed profiling with cProfile:")
    with Profiler() as prof:
        for _ in range(3):
            slow_function()
            combined_function()

    prof.print_report(top=15)
