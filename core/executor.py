"""
core/executor.py

Executor for managing job execution across different concurrency strategies.

This module provides the `Executor` class, which serves as a
central interface for executing jobs using different concurrency
strategies, including:
- Thread-based execution
- Process-based execution
- Asynchronous task execution
"""

from typing import Any

from models.job import Job
from concurrency.threads import ThreadExecutor
from concurrency.processes import ProcessExecutor
from concurrency.async_tasks import AsyncTaskExecutor

class ExecutorRouter:
    """
    Routes jobs to the correct executor based on execution_mode.

    This ExecutorRouter:
    - Initializes thread, process, and async executors
    - Routes job execution requests to the appropriate executor
    - Provides a unified interface for job execution
    """

    def __init__(self):
        """
        Initialize the executor router with all executors.
        """
        self._thread_exec = ThreadExecutor()
        self._process_exec = ProcessExecutor()
        self._async_exec = AsyncTaskExecutor()

    def execute(self, job: Job) -> Any:
        """
        Execute a job using the appropriate executor.
        Args:
            job (Job): Job instance to execute.
        Returns:
            Any: Result of the job execution.
        """
        mode = job.execution_mode

        if mode == "thread":
            return self._thread_exec.execute(job)

        if mode == "process":
            return self._process_exec.execute(job)

        if mode == "async":
            raise RuntimeError(
                "Async execution must be handled in an event loop"
            )

        raise ValueError(f"Unknown execution mode: {mode}")