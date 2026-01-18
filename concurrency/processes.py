"""
concurrency/processes.py

Process management utilities for concurrent job execution.

This module provides helper functions and classes to manage
process-based concurrency, including:
- Process pool management
- Safe process creation and termination
- Synchronization primitives for shared resource access
"""

from concurrent.futures import ProcessPoolExecutor
from typing import Any

from models.job import Job

class ProcessExecutor:
    """
    Process pool executor for managing concurrent job execution.
    This ProcessExecutor:
    - Manages a pool of worker processes
    - Provides an interface to submit jobs for execution
    - Handles process lifecycle and resource cleanup
    """

    def __init__(self, max_workers: int = 2):
        """
        Initialize the process pool executor.

        Args:
            max_workers (int): Maximum number of processes in the pool.
        """
        self._pool = ProcessPoolExecutor(max_workers=max_workers)

    def execute(self, job: Job) -> Any:
        """
        Execute a job in a separate process.

        Args:
            job (Job): Job instance to execute.
        Returns:
            Any: Result of the job execution.
        """
        future = self._pool.submit(self._run_job, job.payload)
        return future.result()

    @staticmethod
    def _run_job(payload: dict) -> Any:
        """
        Internal method to run the job logic.
        Args:
            payload (dict): Payload of the job to run.
        Returns:
            Any: Result of the job execution.
        """
        # Must be pickle-safe
        return {"process_result": payload}