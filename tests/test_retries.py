"""
test_retries.py

Brutal tests for retry logic and failure handling.
"""

import unittest
import time

from models.job import Job, JobStatus


class TestRetryExhaustion(unittest.TestCase):
    """Test retry behavior under various failure conditions."""

    def test_retry_count_exactly_at_limit(self):
        """Test that job fails exactly at max_entries."""
        max_entries = 3
        job = Job(
            job_id="fail-exactly",
            priority=1,
            payload={},
            execution_mode="thread",
            max_entries=max_entries
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)

        # Fail exactly max_entries times with proper state transitions
        for i in range(max_entries - 1):
            job.record_failure(f"error {i}")
            job.transition_to(JobStatus.RUNNING)  # Back to RUNNING for retry
        
        # Final failure
        job.record_failure(f"error {max_entries - 1}")

        self.assertEqual(job.attempts, max_entries)
        self.assertEqual(job.status, JobStatus.FAILED)

    def test_retry_one_less_than_limit(self):
        """Test that job retries when below limit."""
        max_entries = 3
        job = Job(
            job_id="fail-one-less",
            priority=1,
            payload={},
            execution_mode="thread",
            max_entries=max_entries
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)

        # Fail one less than max with proper state transitions
        for i in range(max_entries - 2):
            job.record_failure(f"error {i}")
            job.transition_to(JobStatus.RUNNING)  # Back to RUNNING
        
        # One more failure (still under limit)
        job.record_failure(f"error {max_entries - 2}")

        self.assertEqual(job.attempts, max_entries - 1)
        self.assertEqual(job.status, JobStatus.RETRYING)

    def test_last_error_recorded(self):
        """Test that last error message is preserved."""
        job = Job(
            job_id="error-msg",
            priority=1,
            payload={},
            execution_mode="thread",
            max_entries=2
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)

        job.record_failure("first error")
        job.transition_to(JobStatus.RUNNING)  # Retry
        job.record_failure("second error")

        self.assertEqual(job.last_error, "second error")
        self.assertEqual(job.status, JobStatus.FAILED)

    def test_zero_retries(self):
        """Test job with no retries allowed."""
        job = Job(
            job_id="no-retries",
            priority=1,
            payload={},
            execution_mode="thread",
            max_entries=1  # Only 1 attempt
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)

        job.record_failure("immediate failure")

        self.assertEqual(job.attempts, 1)
        self.assertEqual(job.status, JobStatus.FAILED)

    def test_many_retries(self):
        """Test job with many retries allowed."""
        max_entries = 10
        job = Job(
            job_id="many-retries",
            priority=1,
            payload={},
            execution_mode="thread",
            max_entries=max_entries
        )
        job.transition_to(JobStatus.PENDING)
        job.transition_to(JobStatus.RUNNING)

        # Fail all attempts with proper state transitions
        for i in range(max_entries - 1):
            job.record_failure(f"error {i}")
            job.transition_to(JobStatus.RUNNING)  # Back to RUNNING
        
        # Final failure
        job.record_failure(f"error {max_entries - 1}")

        self.assertEqual(job.attempts, max_entries)
        self.assertEqual(job.status, JobStatus.FAILED)


if __name__ == "__main__":
    unittest.main()
