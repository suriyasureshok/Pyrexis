"""
models/job.py

Job model definition with status management and validation.

This module defines a `Job` data model using Pydantic. It includes:
- Strongly typed job status management using enums
- Explicitly defined allowed state transitions
- Field-level validation
- Helper methods for controlled state mutation (status transitions, failure handling)
"""

from enum import Enum
from datetime import datetime, UTC
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


class JobStatus(str, Enum):
    """
    Enumeration of all possible job lifecycle states.

    Attributes:
        CREATED: Job has been created but not queued.
        PENDING: Job is queued and waiting for execution.
        RUNNING: Job is currently executing.
        RETRYING: Job failed but will be retried.
        COMPLETED: Job finished successfully.
        FAILED: Job permanently failed after max retries.
        CANCELLED: Job was cancelled before completion.
    """
    CREATED = "created"
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


ALLOWED_TRANSITIONS = {
    JobStatus.CREATED: {JobStatus.PENDING, JobStatus.CANCELLED},
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.RETRYING},
    JobStatus.RETRYING: {JobStatus.RUNNING, JobStatus.FAILED},
}


class Job(BaseModel):
    """
    Represents a unit of work with controlled state transitions.

    This model encapsulates:
    - Job metadata
    - Execution configuration
    - Retry tracking
    - State transition enforcement

    Attributes:
        job_id (str): Unique identifier for the job.
        priority (int): Job priority (0–10). Higher means higher priority.
        payload (Dict[str, Any]): Arbitrary job-specific data.
        execution_mode (str): Execution strategy ("thread", "process", "async").
        max_entries (int): Maximum retry attempts allowed.
        attempts (int): Number of execution attempts made.
        status (JobStatus): Current lifecycle status of the job.
        last_error (Optional[str]): Most recent failure message.
        created_at (datetime): Job creation timestamp (UTC).
        updated_at (datetime): Last update timestamp (UTC).
    """

    job_id: str = Field(..., min_length=1)
    priority: int = Field(..., ge=0, le=10)
    payload: Dict[str, Any]
    execution_mode: str
    max_entries: int = Field(default=3, ge=0)
    attempts: int = 0
    status: JobStatus = JobStatus.CREATED
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("execution_mode")
    @classmethod
    def validate_execution_mode(cls, value: str) -> str:
        """
        Validate execution mode.

        Args:
            value (str): Execution mode to validate.

        Returns:
            str: Validated execution mode.

        Raises:
            ValueError: If execution mode is not supported.
        """
        allowed_modes = {"thread", "process", "async"}
        if value not in allowed_modes:
            raise ValueError(f"execution_mode must be one of {allowed_modes}")
        return value

    def transition_to(self, new_status: JobStatus) -> None:
        """
        Transition the job to a new status if allowed.

        This method enforces the state transition rules defined
        in `ALLOWED_TRANSITIONS`.

        Args:
            new_status (JobStatus): Target status.

        Raises:
            RuntimeError: If the state transition is illegal.
        """
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise RuntimeError(
                f"Illegal state transition: {self.status} -> {new_status}"
            )

        self.status = new_status
        self.updated_at = datetime.now(UTC)

    def record_failure(self, error_message: str) -> None:
        """
        Record a job execution failure.

        Updates retry count, stores the error message,
        and transitions the job to either RETRYING or FAILED
        depending on retry limits.

        Args:
            error_message (str): Error message describing the failure.
        """
        self.last_error = error_message
        self.attempts += 1

        if self.attempts >= self.max_entries:
            self.transition_to(JobStatus.FAILED)
        else:
            self.transition_to(JobStatus.RETRYING)

    def __eq__(self, other):
        """
        Equality comparison based on job_id.
        """
        return isinstance(other, Job) and self.job_id == other.job_id

    def __hash__(self):
        """
        Hash based on job_id.
        """
        return hash(self.job_id)