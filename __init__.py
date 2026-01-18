"""
Pyrexis - A concurrent job execution engine.

Public API for job scheduling, execution, and lifecycle management.
"""

from core.engine import Engine
from core.scheduler import Scheduler
from core.pipeline import Pipeline
from core.executor import ExecutorRouter

from models.job import Job, JobStatus
from models.result import Result

from storage.state import StateStore

from utils.metrics import MetricsRegistry, TimedBlock
from utils.shutdown import ShutdownCoordinator
from utils.logging import setup_logging, log_context, get_logger
from utils.cache import LRUCache
from utils.retry import Retry
from utils.registry import PluginRegistry
from utils.timing import Timer
from utils.profiling import (
    profile_time,
    profile_memory,
    profile_all,
    Profiler,
    memory_profiler,
    get_performance_report,
    print_performance_report,
)

from main import create_engine, run_daemon

__version__ = "0.1.0"

__all__ = [
    # Core
    "Engine",
    "Scheduler",
    "Pipeline",
    "ExecutorRouter",
    
    # Models
    "Job",
    "JobStatus",
    "Result",
    
    # Storage
    "StateStore",
    
    # Utils - Metrics
    "MetricsRegistry",
    "TimedBlock",
    
    # Utils - Shutdown
    "ShutdownCoordinator",
    
    # Utils - Logging
    "setup_logging",
    "log_context",
    "get_logger",
    
    # Utils - Other
    "LRUCache",
    "Retry",
    "PluginRegistry",
    "Timer",
    
    # Utils - Profiling
    "profile_time",
    "profile_memory",
    "profile_all",
    "Profiler",
    "memory_profiler",
    "get_performance_report",
    "print_performance_report",
    
    # Entry points
    "create_engine",
    "run_daemon",
]
