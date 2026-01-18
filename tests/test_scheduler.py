"""
test_scheduler.py

Brutal tests for Scheduler fairness and thread safety.
"""

import unittest
import threading
import time

from core.scheduler import Scheduler
from models.job import Job, JobStatus


class TestSchedulerFairness(unittest.TestCase):
    """Test scheduler fairness and starvation prevention."""

    def test_low_priority_eventually_runs(self):
        """Test that low-priority jobs eventually execute (starvation prevention)."""
        scheduler = Scheduler(aging_factor=0.1)

        # Submit 50 high-priority jobs
        high_jobs = [
            Job(
                job_id=f"high-{i}",
                priority=10,
                payload={},
                execution_mode="thread"
            )
            for i in range(50)
        ]
        
        for job in high_jobs:
            job.transition_to(JobStatus.PENDING)
            scheduler.submit(job)

        # Submit 1 low-priority job
        low_job = Job(
            job_id="low-priority",
            priority=1,
            payload={},
            execution_mode="thread"
        )
        low_job.transition_to(JobStatus.PENDING)
        scheduler.submit(low_job)

        # Execute jobs and track which ran
        executed = set()
        for _ in range(60):  # More than total jobs
            job = scheduler.next_job()
            if job:
                executed.add(job.job_id)

        # Assert low-priority job was executed
        self.assertIn("low-priority", executed, 
                     "Low-priority job should eventually run (starvation prevention failed)")

    def test_priority_ordering(self):
        """Test that higher priority jobs run first."""
        scheduler = Scheduler(aging_factor=0.0)  # No aging

        jobs = [
            Job(job_id="p1", priority=1, payload={}, execution_mode="thread"),
            Job(job_id="p5", priority=5, payload={}, execution_mode="thread"),
            Job(job_id="p10", priority=10, payload={}, execution_mode="thread"),
        ]

        for job in jobs:
            job.transition_to(JobStatus.PENDING)
            scheduler.submit(job)

        # Should get highest priority first
        first = scheduler.next_job()
        self.assertEqual(first.job_id, "p10")

    def test_empty_scheduler(self):
        """Test that empty scheduler returns None."""
        scheduler = Scheduler()
        self.assertIsNone(scheduler.next_job())
        self.assertEqual(scheduler.size(), 0)

    def test_scheduler_size(self):
        """Test scheduler size tracking."""
        scheduler = Scheduler()
        
        jobs = [
            Job(job_id=f"job-{i}", priority=5, payload={}, execution_mode="thread")
            for i in range(10)
        ]
        
        for job in jobs:
            job.transition_to(JobStatus.PENDING)
            scheduler.submit(job)

        self.assertEqual(scheduler.size(), 10)
        
        scheduler.next_job()
        self.assertEqual(scheduler.size(), 9)

    def test_non_pending_job_rejected(self):
        """Test that non-PENDING jobs cannot be submitted."""
        scheduler = Scheduler()
        
        job = Job(
            job_id="test",
            priority=5,
            payload={},
            execution_mode="thread"
        )
        # Don't transition to PENDING
        
        with self.assertRaises(ValueError):
            scheduler.submit(job)


class TestSchedulerConcurrency(unittest.TestCase):
    """Test scheduler thread safety."""

    def test_concurrent_submissions(self):
        """Test thread-safe job submissions."""
        scheduler = Scheduler()
        jobs_per_thread = 50
        num_threads = 10
        expected_total = jobs_per_thread * num_threads

        def submit_jobs(thread_id):
            for i in range(jobs_per_thread):
                job = Job(
                    job_id=f"thread-{thread_id}-job-{i}",
                    priority=5,
                    payload={},
                    execution_mode="thread"
                )
                job.transition_to(JobStatus.PENDING)
                scheduler.submit(job)

        threads = [
            threading.Thread(target=submit_jobs, args=(i,))
            for i in range(num_threads)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(scheduler.size(), expected_total,
                        "Concurrent submissions should not lose jobs")

    def test_concurrent_dequeue(self):
        """Test thread-safe job dequeue."""
        scheduler = Scheduler()
        
        # Submit 100 jobs
        for i in range(100):
            job = Job(
                job_id=f"job-{i}",
                priority=5,
                payload={},
                execution_mode="thread"
            )
            job.transition_to(JobStatus.PENDING)
            scheduler.submit(job)

        results = []
        lock = threading.Lock()

        def dequeue_jobs():
            local_jobs = []
            for _ in range(20):
                job = scheduler.next_job()
                if job:
                    local_jobs.append(job.job_id)
            
            with lock:
                results.extend(local_jobs)

        threads = [
            threading.Thread(target=dequeue_jobs)
            for _ in range(5)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Should have 100 unique jobs
        self.assertEqual(len(results), 100)
        self.assertEqual(len(set(results)), 100, "Should not have duplicate jobs")


if __name__ == "__main__":
    unittest.main()
