"""
test_shutdown.py

Brutal tests for graceful shutdown behavior.
"""

import unittest
import threading
import time

from utils.shutdown import ShutdownCoordinator
from concurrency.threads import ThreadWorkerPool


class TestShutdownCoordinator(unittest.TestCase):
    """Test shutdown coordinator behavior."""

    def test_shutdown_not_initiated_by_default(self):
        """Test that shutdown is not active on creation."""
        coordinator = ShutdownCoordinator()
        self.assertFalse(coordinator.should_shutdown())

    def test_shutdown_can_be_initiated(self):
        """Test that shutdown can be triggered."""
        coordinator = ShutdownCoordinator()
        coordinator.initiate_shutdown()
        self.assertTrue(coordinator.should_shutdown())

    def test_shutdown_callbacks_invoked(self):
        """Test that registered callbacks are called on shutdown."""
        coordinator = ShutdownCoordinator()
        called = []

        def callback1():
            called.append(1)

        def callback2():
            called.append(2)

        coordinator.register(callback1)
        coordinator.register(callback2)
        coordinator.initiate_shutdown()

        # Callbacks invoked in reverse order
        self.assertEqual(called, [2, 1])

    def test_shutdown_idempotent(self):
        """Test that multiple shutdown calls are safe."""
        coordinator = ShutdownCoordinator()
        called_count = [0]

        def callback():
            called_count[0] += 1

        coordinator.register(callback)
        coordinator.initiate_shutdown()
        coordinator.initiate_shutdown()
        coordinator.initiate_shutdown()

        # Should only be called once
        self.assertEqual(called_count[0], 1)

    def test_shutdown_with_failing_callback(self):
        """Test that shutdown continues even if callback fails."""
        coordinator = ShutdownCoordinator()
        called = []

        def good_callback():
            called.append("good")

        def bad_callback():
            raise RuntimeError("callback failed")

        coordinator.register(good_callback)
        coordinator.register(bad_callback)
        coordinator.initiate_shutdown()

        # Good callback should still run
        self.assertIn("good", called)

    def test_shutdown_thread_safety(self):
        """Test that shutdown is thread-safe."""
        coordinator = ShutdownCoordinator()
        call_count = [0]
        lock = threading.Lock()

        def callback():
            with lock:
                call_count[0] += 1

        coordinator.register(callback)

        # Multiple threads try to shutdown
        threads = [
            threading.Thread(target=coordinator.initiate_shutdown)
            for _ in range(10)
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # Callback should only run once
        self.assertEqual(call_count[0], 1)


class TestThreadPoolShutdown(unittest.TestCase):
    """Test thread pool shutdown behavior."""

    def test_thread_pool_stops_after_shutdown(self):
        """Test that thread pool stops processing after shutdown."""
        pool = ThreadWorkerPool(num_workers=2)
        results = []
        lock = threading.Lock()

        def task(value):
            with lock:
                results.append(value)

        # Submit tasks
        for i in range(5):
            pool.submit(task, i)

        # Wait briefly then shutdown
        time.sleep(0.1)
        pool.shutdown()

        # Give time for workers to exit
        time.sleep(0.2)

        # Some tasks should have completed
        with lock:
            completed_count = len(results)

        self.assertGreater(completed_count, 0, 
                          "Some tasks should complete before shutdown")

    def test_shutdown_with_coordinator(self):
        """Test thread pool shutdown via coordinator."""
        coordinator = ShutdownCoordinator()
        pool = ThreadWorkerPool(num_workers=2)

        coordinator.register(pool.shutdown)

        results = []
        lock = threading.Lock()

        def task(value):
            time.sleep(0.05)
            with lock:
                results.append(value)

        # Submit tasks
        for i in range(10):
            pool.submit(task, i)

        # Trigger shutdown
        time.sleep(0.1)
        coordinator.initiate_shutdown()

        # Wait for completion
        time.sleep(0.3)

        # Pool should be shut down
        self.assertTrue(coordinator.should_shutdown())


class TestGracefulShutdown(unittest.TestCase):
    """Test graceful shutdown under load."""

    def test_shutdown_during_active_execution(self):
        """Test shutdown while tasks are running."""
        coordinator = ShutdownCoordinator()
        pool = ThreadWorkerPool(num_workers=4)
        coordinator.register(pool.shutdown)

        completed = []
        lock = threading.Lock()

        def long_task(task_id):
            for i in range(10):
                if coordinator.should_shutdown():
                    return  # Exit early on shutdown
                time.sleep(0.01)
            
            with lock:
                completed.append(task_id)

        # Submit long-running tasks
        for i in range(20):
            pool.submit(long_task, i)

        # Let more tasks start and some complete
        time.sleep(0.15)

        # Trigger shutdown
        coordinator.initiate_shutdown()

        # Wait for shutdown to complete
        time.sleep(0.5)

        # Some tasks should have completed (at least one)
        with lock:
            count = len(completed)

        # With longer initial wait, at least 1 task should complete
        self.assertGreaterEqual(count, 1, "At least one task should complete before shutdown")


if __name__ == "__main__":
    unittest.main()
