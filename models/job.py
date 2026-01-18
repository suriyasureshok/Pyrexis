"""
Job model definition with status management and validation.

This module defines a Job model using Pydantic, including status management with allowed transitions,
field validations, and methods to handle job state changes.
"""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator

# Define JobStatus enum
class JobStatus(str, Enum):
    CREATED = "created"
    PENDING = "pending"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

# Define allowed status transitions
ALLOWED_TRANSITIONS = {
    JobStatus.CREATED: {JobStatus.PENDING, JobStatus.CANCELLED},
    JobStatus.PENDING: {JobStatus.RUNNING, JobStatus.CANCELLED},
    JobStatus.RUNNING: {JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.RETRYING},
    JobStatus.RETRYING: {JobStatus.RUNNING, JobStatus.FAILED},
}

# Define Job model
class Job(BaseModel):
    """
    Model representing a job with various attributes and status management.

    Attributes:
    - job_id (str): Unique identifier for the job.
    - priority (int): Priority of the job, higher values indicate higher priority.
    - payload (Dict[str, Any]): Payload data for the job.
    - execution_mode (str): Execution mode of the job.
    - max_entries (int): Maximum number of entries for the job.
    - attempts (int): Number of attempts made for the job.
    - status (JobStatus): Current status of the job.
    - last_error (Optional[str]): Last error message if the job failed.
    - created_at (datetime): Timestamp when the job was created.
    - updated_at (datetime): Timestamp when the job was last updated.
    """
    job_id: str = Field(..., min_length=1)
    priority: int = Field(..., ge=0, le=10)
    payload: Dict[str, Any]
    execution_mode: str
    max_entries: int = Field(default=3, ge=0)
    attempts: int = 0
    status: JobStatus = JobStatus.CREATED
    last_error: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("execution_mode")
    def validate_execution_mode(cls, value: str) -> str:
        """
        Validate the execution_mode field to ensure it is one of the allowed modes.
        Args:
            value (str): The execution mode to validate.
        Returns:
            str: The validated execution mode.
        Raises:
            ValueError: If the execution mode is not allowed.
        """
        allowed_modes = {"thread", "process", "async"}
        if value not in allowed_modes:
            raise ValueError(f"execution_mode must be one of {allowed_modes}")
        return value
    
    def transition_to(self, new_status: JobStatus) -> None:
        """
        Transition the job to a new status if the transition is allowed.
        
        Args:
            new_status (JobStatus): The new status to transition to.
        Raises:
            RuntimeError: If the transition is not allowed.
        """
        allowed = ALLOWED_TRANSITIONS.get(self.status, set())
        if new_status not in allowed:
            raise RuntimeError(f"Illegal state transition: {self.status} -> {new_status}")
        
        self.status = new_status
        self.updated_at = datetime.utcnow()

    def record_failure(self, error_message: str) -> None:
        """
        Record a failure for the job, updating the last error and attempts.
        
        Args:
            error_message (str): The error message to record.
        """
        self.last_error = error_message
        self.attempts += 1
        
        if self.attempts >= self.max_entries:
            self.transition_to(JobStatus.FAILED)
        else:
            self.transition_to(JobStatus.RETRYING)