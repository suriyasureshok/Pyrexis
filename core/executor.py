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

from datetime import datetime
from typing import Any, Callable

from models.job import Job, JobStatus
from models.result import Result
from concurrency.threads import ThreadWorkerPool
from concurrency.processes import ProcessWorkerPool
from concurrency.async_tasks import AsyncTaskRunner


def _execute_job(job: Job, state_store, build_pipeline: Callable, on_progress: Callable):
    """
    Execute a job and save the result.

    Args:
        job (Job): Job to execute.
        state_store: State store for persisting job and result.
        build_pipeline (Callable): Function to build the pipeline.
        on_progress (Callable): Function to call on progress.
    """
    started_at = datetime.utcnow()

    try:
        pipeline = build_pipeline(job)
        final_output = None

        for step_output in pipeline.run(job.payload):
            final_output = step_output
            on_progress(job, step_output)

        ended_at = datetime.utcnow()

        job.transition_to(JobStatus.COMPLETED)
        state_store.update_job(job)

        result = Result(
            job_id=job.job_id,
            status="COMPLETED",
            output=final_output,
            started_at=started_at,
            ended_at=ended_at,
        )
        state_store.save_result(result)

    except Exception as e:
        ended_at = datetime.utcnow()

        job.record_failure(str(e))
        state_store.update_job(job)

        result = Result(
            job_id=job.job_id,
            status="FAILED",
            error=str(e),
            started_at=started_at,
            ended_at=ended_at,
        )
        state_store.save_result(result)


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
        self._thread_pool = ThreadWorkerPool()
        self._process_pool = ProcessWorkerPool()
        self._async_runner = AsyncTaskRunner()

    def execute(self, job: Job, state_store, build_pipeline: Callable, on_progress: Callable) -> None:
        """
        Execute a job using the appropriate executor.
        Args:
            job (Job): Job instance to execute.
            state_store: State store for persisting.
            build_pipeline (Callable): Function to build pipeline.
            on_progress (Callable): Function for progress.
        """
        mode = job.execution_mode

        if mode == "thread":
            self._thread_pool.submit(_execute_job, job, state_store, build_pipeline, on_progress)
        elif mode == "process":
            self._process_pool.submit(_execute_job, job, state_store, build_pipeline, on_progress)
        elif mode == "async":
            raise RuntimeError("Async execution not implemented")
        else:
            raise ValueError(f"Unknown execution mode: {mode}")