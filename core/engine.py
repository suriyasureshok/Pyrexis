"""
core/engine.py

Engine for managing job lifecycle and execution.

This module provides the `Engine` class, which orchestrates
the overall job lifecycle management. It integrates the:
- StateStore for persistent job and result storage
- Scheduler for priority-based job scheduling
- ExecutorRouter for executing jobs with different concurrency strategies

It offers methods for job submission, state advancement,
and querying job status.
"""

import time
from typing import Any, Optional
from datetime import datetime

from models.job import Job, JobStatus
from models.result import Result
from core.scheduler import Scheduler
from core.executor import ExecutorRouter
from core.pipeline import Pipeline
from storage.state import StateStore
from utils.metrics import MetricsRegistry, TimedBlock
from utils.shutdown import ShutdownCoordinator
from utils.registry import PluginRegistry


class Engine:
    """
    Core engine managing job lifecycle and execution.

    This Engine:
    - Submits jobs to the scheduler
    - Advances job states on each tick
    - Persists job state changes to storage
    - Executes jobs using the appropriate executor
    - Records execution results
    """

    def __init__(
        self,
        scheduler: Scheduler,
        executor: ExecutorRouter,
        state_store: StateStore,
        shutdown_coordinator: ShutdownCoordinator,
    ):
        """
        Initialize the engine with storage and scheduler.

        Args:
            scheduler: Job scheduler.
            executor: Job executor.
            state_store: State store.
            shutdown_coordinator: Shutdown coordinator.
        """
        self._scheduler = scheduler
        self._executor = executor
        self._state_store = state_store
        self._shutdown = shutdown_coordinator
        self._metrics = MetricsRegistry()

        # Register shutdown callbacks for concurrency pools
        self._shutdown.register(self._executor._thread_pool.shutdown)
        self._shutdown.register(self._executor._process_pool.shutdown)

    # ---------- Job Submission -----------

    def submit_job(self, job: Job) -> None:
        """
        Submit a new job to the engine.

        The job is persisted to storage and scheduled for execution.

        Args:
            job (Job): Job instance to submit.
        """
        if job.status != JobStatus.CREATED:
            raise ValueError("Only jobs with status 'created' can be submitted.")
        
        # Move to PENDING
        job.transition_to(JobStatus.PENDING)

        # Persist immediately
        self._state_store.save_job(job)

        # Hand off to scheduler
        self._scheduler.submit(job)

    # # ---------- Engine Heartbeat -----------
    # def tick(self) -> Optional[Job]:
    #     """
    #     Advance the engine state by one tick.

    #     Returns:
    #         Optional[Job]: Next job to execute, or None if no jobs are pending.
    #     """
    #     job = self._scheduler.next_job()

    #     if job is None:
    #         return None
        
    #     # Move job to RUNNING
    #     job.transition_to(JobStatus.RUNNING)

    #     # Persist job state
    #     self._state_store.update_job(job)

    #     return job
    
    # ------------- Query --------------
    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Retrieve a job by its identifier.

        Args:
            job_id (str): Identifier of the job to retrieve.

        Returns:
            Optional[Job]: Job instance if found, otherwise None.
        """
        return self._state_store.load_job(job_id)
    
    # ----------- Execution steps -----------
    def run_next(self) -> Optional[Result]:
        """
        Execute the next scheduled job.
        Returns:
            Optional[Result]: Result of the executed job, or None if no jobs to run.
        """
        if self._shutdown.should_shutdown():
            return None

        job = self._scheduler.next_job()
        if job is None:
            return None
        
        # Move job to RUNNING
        job.transition_to(JobStatus.RUNNING)
        self._state_store.update_job(job)

        # Execute using executor
        with TimedBlock(self._metrics, "job.execution"):
            self._executor.execute(job, self._state_store, self._build_pipeline, self._on_progress, self._metrics)

        return None
        
    def _build_pipeline(self, job: Job) -> Pipeline:
        """
        Construct the execution pipeline for a job.

        Args:
            job (Job): Job instance for which to build the pipeline.
        Returns:
            Pipeline: Constructed execution pipeline.
        """
        pipeline_type = job.payload["type"]

        pipeline_cls = PluginRegistry.get_plugin(pipeline_type)
        pipeline_instance = pipeline_cls()
    
        return Pipeline(pipeline_instance.stages())


    def _on_progress(self, job: Job, step_output: Any) -> None:
        """
        Hook for streaming progress.
        """
        pass

    def get_metrics(self):
        """
        Get the metrics registry.
        """
        return self._metrics

    def run_loop(self):
        """
        Run the engine loop until shutdown is initiated.
        """
        while not self._shutdown.should_shutdown():
            self.run_next()