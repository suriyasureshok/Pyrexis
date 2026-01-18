"""
core/engine.py

Engine for managing job lifecycle and execution.

This module provides the `Engine` class, which orchestrates
the overall job lifecycle management. It integrates the:
- StateStore for persistent job and result storage
- Scheduler for priority-based job scheduling
"""

from typing import Optional

from models.job import Job, JobStatus
from core.scheduler import Scheduler
from storage.state import StateStore

class Engine:
    """
    Core engine managing job lifecycle and execution.

    This Engine:
    - Submits jobs to the scheduler
    - Advances job states on each tick
    - Persists job state changes to storage
    """

    def __init__(self, state_path: str):
        """
        Initialize the engine with storage and scheduler.

        Args:
            state_path (str): Filesystem path for persistent state storage.
        """
        self._state_store = StateStore(state_path)
        self._scheduler = Scheduler()

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

    # ---------- Engine Heartbeat -----------
    def tick(self) -> Optional[Job]:
        """
        Advance the engine state by one tick.

        Returns:
            Optional[Job]: Next job to execute, or None if no jobs are pending.
        """
        job = self._scheduler.next_job()

        if job is None:
            return None
        
        # Move job to RUNNING
        job.transition_to(JobStatus.RUNNING)

        # Persist job state
        self._state_store.update_job(job)

        return job
    
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