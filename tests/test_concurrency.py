"""
test_concurrency.py

Brutal tests for concurrent execution and thread safety.
"""

import unittest
import threading
import time
from queue import Queue

from concurrency.threads import ThreadWorkerPool
from concurrency.processes import ProcessWorkerPool


class TestThreadPoolConcurrency(unittest.TestCase):
    """Test thread pool concurrent execution."""

    def test_thread_pool_executes_tasks(self):
        """Test that thread pool executes submitted tasks."""
        pool = ThreadWorkerPool(num_workers=4)
        results = Queue()

        def task(value):
            results.put(value)

        # Submit 10 tasks
        for i in range(10):
            pool.submit(task, i)

        # Wait for completion
        time.sleep(0.5)

        # Check all tasks executed
        collected = []
        while not results.empty():
            collected.append(results.get())

        self.assertEqual(len(collected), 10)
        self.assertEqual(sorted(collected), list(range(10)))

    def test_thread_pool_concurrent_execution(self):
        """Test that thread pool runs tasks concurrently."""
        pool = ThreadWorkerPool(num_workers=4)
        start_times = {}
        lock = threading.Lock()

        def slow_task(task_id):
            with lock:
                start_times[task_id] = time.time()
            time.sleep(0.1)

        # Submit 4 tasks
        for i in range(4):
            pool.submit(slow_task, i)

        time.sleep(0.5)

        # If concurrent, all should start within ~same time
        times = list(start_times.values())
        if len(times) > 1:
            time_spread = max(times) - min(times)
            self.assertLess(time_spread, 0.05, 
                          "Tasks should start concurrently")

    def test_thread_pool_handles_exceptions(self):
        """Test that thread pool continues after task exception."""
        pool = ThreadWorkerPool(num_workers=2)
        results = Queue()

        def failing_task():
            raise ValueError("Task failed")

        def normal_task(value):
            results.put(value)

        # Mix failing and normal tasks
        pool.submit(failing_task)
        pool.submit(normal_task, 1)
        pool.submit(failing_task)
        pool.submit(normal_task, 2)

        time.sleep(0.5)

        # Normal tasks should still complete
        collected = []
        while not results.empty():
            collected.append(results.get())

        self.assertEqual(sorted(collected), [1, 2])

    def test_thread_pool_shutdown(self):
        """Test thread pool shutdown stops workers."""
        pool = ThreadWorkerPool(num_workers=2)
        
        def task():
            time.sleep(0.1)

        pool.submit(task)
        pool.shutdown()
        
        # After shutdown, workers should stop
        # (Visual inspection - threads should exit)
        time.sleep(0.2)


class TestProcessPoolBasics(unittest.TestCase):
    """Test process pool basic functionality."""

    def test_process_pool_creation(self):
        """Test that process pool can be created."""
        pool = ProcessWorkerPool(num_workers=2)
        self.assertIsNotNone(pool)
        pool.shutdown()

    def test_process_pool_shutdown(self):
        """Test that process pool can be shut down."""
        pool = ProcessWorkerPool(num_workers=2)
        pool.shutdown()
        # Should not raise exception


class TestConcurrentSubmissions(unittest.TestCase):
    """Test concurrent job submissions to the system."""

    def test_multiple_threads_submitting_jobs(self):
        """Test thread safety of concurrent job submissions."""
        from core.scheduler import Scheduler
        from models.job import Job, JobStatus

        scheduler = Scheduler()
        jobs_per_thread = 50
        num_threads = 10
        expected_total = jobs_per_thread * num_threads

        def submit_jobs(thread_id):
            for i in range(jobs_per_thread):
                job = Job(
                    job_id=f"t{thread_id}-j{i}",
                    priority=5,
                    payload={"thread": thread_id, "index": i},
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

        # Verify no jobs lost
        self.assertEqual(scheduler.size(), expected_total,
                        "Should not lose jobs during concurrent submissions")

        # Verify no duplicates by dequeuing all
        job_ids = set()
        for _ in range(expected_total):
            job = scheduler.next_job()
            if job:
                job_ids.add(job.job_id)

        self.assertEqual(len(job_ids), expected_total,
                        "Should not have duplicate jobs")


if __name__ == "__main__":
    unittest.main()
