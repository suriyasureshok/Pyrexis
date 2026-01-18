"""
Result module for handling model results.

This module defines a Result model using Pydantic, which encapsulates the outcome of a job,
including success status, output data, and error messages.
"""

from enum import Enum
from datetime import datetime
from typing import Any, Dict, Optional, Literal

from pydantic import BaseModel, Field, field_validator, model_validator

# Define Result model
class Result(BaseModel):
    job_id: str = Field(..., min_length=1)
    status: Literal["COMPLETED", "FAILED"]
    output: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    started_at: datetime
    ended_at: datetime
    duration: float = Field(init=False)

    @model_validator(mode="after")
    def validate_result_invariants(self) -> None:
        """
        Validate that ended_at is after started_at and calculate duration. 
        Raises:
        - ValueError: If ended_at is before started_at.

        """
        # Ensure ended_at is after started_at
        if self.ended_at < self.started_at:
            raise ValueError(
                "ended_at must be after started_at"
                )
        
        # Calculate duration in seconds
        self.duration = (self.ended_at - self.started_at).total_seconds()

        if self.status == "COMPLETED" and self.output is None:
            raise ValueError(
                "Output must be provided for COMPLETED results without errors."
                )
        
        if self.status == "FAILED" and self.error is None:
            raise ValueError(
                "Error message must be provided for FAILED results without outputs."
                )
        
        return self
    
    class Config:
        frozen = True