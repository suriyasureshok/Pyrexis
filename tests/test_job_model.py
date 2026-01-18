"""
test_job_model.py

Unit tests for Job model state transitions and validation.
"""

import unittest
from datetime import datetime

from models.job import Job, JobStatus, ALLOWED_TRANSITIONS


class TestJobModel(unittest.TestCase):
    """Test Job model behavior."""

    def test_job_creation_defaults(self):
        """Test job is created with correct default status."""
        job = Job(
            job_id="test-1",
            priority=5,
            payload={"data": "test"},
            execution_mode="thread"
        )
        self.assertEqual(job.status, JobStatus.CREATED)
        self.assertEqual(job.attempts, 0)
        self.assertIsNone(job.last_error)

    def test_illegal_state_transition(self):
        """Test that illegal state transitions raise RuntimeError."""
        job = Job(
            job_id="test-2",
            priority=5,
            payload={},
            execution_mode="thread"
        )
        
        with self.assertRaises(RuntimeError):
            # Cannot go from CREATED to COMPLETED
            job.transition_to(JobStatus.COMPLETED)

    def test_legal_state_transitions(self):
        """Test valid state transition sequences."""
        job = Job(
            job_id="test-3",
            priority=5,
            payload={},
            execution_mode="thread"
        )
        
        # CREATED -> PENDING
        job.transition_to(JobStatus.PENDING)
        self.assertEqual(job.status, JobStatus.PENDING)
        
        # PENDING -> RUNNING
        job.transition_to(JobStatus.RUNNING)
        self.assertEqual(job.status, JobStatus.RUNNING)
        
        # RUNNING -> COMPLETED
        job.transition_to(JobStatus.COMPLETED)
        self.assertEqual(job.status, JobStatus.COMPLETED)

    def test_retry_exhaustion(self):
        """Test that job transitions to FAILED after max retries."""
        job = Job(
            job_id="test-4",
            priority=5,
            payload={},
            execution_mode="thread",
            max_entries=3
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)
        
        # Fail 3 times with proper state transitions
        job.record_failure("error 0")  # attempts=1, status=RETRYING
        job.transition_to(JobStatus.RUNNING)  # Back to RUNNING
        
        job.record_failure("error 1")  # attempts=2, status=RETRYING
        job.transition_to(JobStatus.RUNNING)  # Back to RUNNING
        
        job.record_failure("error 2")  # attempts=3, status=FAILED
        
        self.assertEqual(job.attempts, 3)
        self.assertEqual(job.status, JobStatus.FAILED)
        self.assertIsNotNone(job.last_error)

    def test_retry_not_exhausted(self):
        """Test that job transitions to RETRYING when retries remain."""
        job = Job(
            job_id="test-5",
            priority=5,
            payload={},
            execution_mode="thread",
            max_entries=3
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)
        
        # Fail once
        job.record_failure("error 1")
        
        self.assertEqual(job.attempts, 1)
        self.assertEqual(job.status, JobStatus.RETRYING)

    def test_invalid_execution_mode(self):
        """Test that invalid execution mode raises ValueError."""
        with self.assertRaises(ValueError):
            Job(
                job_id="test-6",
                priority=5,
                payload={},
                execution_mode="invalid"
            )

    def test_job_equality(self):
        """Test job equality based on job_id."""
        job1 = Job(
            job_id="test-7",
            priority=5,
            payload={},
            execution_mode="thread"
        )
        job2 = Job(
            job_id="test-7",
            priority=8,
            payload={"different": "data"},
            execution_mode="process"
        )
        
        self.assertEqual(job1, job2)
        self.assertEqual(hash(job1), hash(job2))


if __name__ == "__main__":
    unittest.main()
