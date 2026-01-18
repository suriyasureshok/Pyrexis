"""
models/result.py

Result model definition for job execution outcomes.

This module defines a `Result` data model using Pydantic. It provides:
- Strongly typed execution status using literals
- Cross-field validation to enforce result invariants
- Computed execution duration
- Immutable result objects for data integrity
"""

from datetime import datetime
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel, Field, model_validator, computed_field


class Result(BaseModel):
    """
    Represents the final outcome of a job execution.

    This model captures execution metadata, timing information,
    output or error details, and enforces consistency rules
    between fields.

    Attributes:
        job_id (str): Unique identifier of the associated job.
        status (Literal["COMPLETED", "FAILED"]): Final execution status.
        output (Optional[Dict[str, Any]]): Execution output data.
            Required when status is COMPLETED.
        error (Optional[str]): Error message describing failure.
            Required when status is FAILED.
        started_at (datetime): Execution start timestamp (UTC).
        ended_at (datetime): Execution end timestamp (UTC).
        duration (float): Execution duration in seconds, computed post-validation.
    """

    job_id: str = Field(..., min_length=1)
    status: Literal["COMPLETED", "FAILED"]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    ended_at: datetime
    
    @computed_field
    @property
    def duration(self) -> float:
        """Compute execution duration in seconds."""
        return (self.ended_at - self.started_at).total_seconds()

    @model_validator(mode="after")
    def validate_result_invariants(self) -> "Result":
        """
        Validate cross-field invariants.

        Validation rules enforced:
        - ended_at must be later than started_at
        - output must be present when status is COMPLETED
        - error must be present when status is FAILED

        Returns:
            Result: The validated Result instance.

        Raises:
            ValueError: If timestamps are invalid or required fields
                are missing for the given status.
        """
        if self.ended_at < self.started_at:
            raise ValueError("ended_at must be after started_at")

        if self.status == "COMPLETED" and self.output is None:
            raise ValueError("output must be provided for COMPLETED results")

        if self.status == "FAILED" and self.error is None:
            raise ValueError("error must be provided for FAILED results")

        return self

    class Config:
        """
        Pydantic configuration for the Result model.

        Attributes:
            frozen (bool): Prevents mutation after model creation.
        """
        frozen = True
