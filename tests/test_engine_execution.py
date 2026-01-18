"""
test_engine_execution.py

Integration tests for engine execution behavior.
"""

import unittest
import tempfile
import os
import time

from models.job import Job, JobStatus
from core.scheduler import Scheduler
from core.executor import ExecutorRouter
from core.engine import Engine
from storage.state import StateStore
from utils.shutdown import ShutdownCoordinator


class TestEngineExecution(unittest.TestCase):
    """Test engine execution behavior."""

    def setUp(self):
        """Set up test engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.temp_dir, "test_state")
        
        scheduler = Scheduler()
        executor = ExecutorRouter()
        state_store = StateStore(self.state_path)
        shutdown_coordinator = ShutdownCoordinator()
        
        self.engine = Engine(
            scheduler=scheduler,
            executor=executor,
            state_store=state_store,
            shutdown_coordinator=shutdown_coordinator
        )

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_submit_job_transitions_to_pending(self):
        """Test that submitting a job transitions it to PENDING."""
        job = Job(
            job_id="test-1",
            priority=5,
            payload={"data": "test"},
            execution_mode="thread"
        )
        
        self.engine.submit_job(job)
        
        # Job should be PENDING
        self.assertEqual(job.status, JobStatus.PENDING)
        
        # Job should be in scheduler
        self.assertEqual(self.engine._scheduler.size(), 1)

    def test_cannot_submit_non_created_job(self):
        """Test that only CREATED jobs can be submitted."""
        job = Job(
            job_id="test-2",
            priority=5,
            payload={},
            execution_mode="thread"
        )
        job.transition_to(JobStatus.PENDING)
        
        with self.assertRaises(ValueError):
            self.engine.submit_job(job)

    def test_run_next_returns_none_when_empty(self):
        """Test that run_next returns None when no jobs queued."""
        result = self.engine.run_next()
        self.assertIsNone(result)

    def test_engine_respects_shutdown_signal(self):
        """Test that engine stops pulling jobs on shutdown."""
        # Submit jobs
        for i in range(10):
            job = Job(
                job_id=f"job-{i}",
                priority=5,
                payload={},
                execution_mode="thread"
            )
            self.engine.submit_job(job)

        # Trigger shutdown
        self.engine._shutdown.initiate_shutdown()

        # run_next should return None (shutdown respected)
        result = self.engine.run_next()
        self.assertIsNone(result)

        # Jobs should still be in queue
        self.assertGreater(self.engine._scheduler.size(), 0)

    def test_get_job_retrieves_from_storage(self):
        """Test that jobs can be retrieved from storage."""
        job = Job(
            job_id="stored-job",
            priority=5,
            payload={"data": "test"},
            execution_mode="thread"
        )
        
        self.engine.submit_job(job)
        
        # Retrieve from storage
        retrieved = self.engine.get_job("stored-job")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved.job_id, "stored-job")

    def test_metrics_available(self):
        """Test that metrics can be accessed."""
        metrics = self.engine.get_metrics()
        self.assertIsNotNone(metrics)
        
        # Should have counters and timings methods
        self.assertTrue(hasattr(metrics, 'get_counters'))
        self.assertTrue(hasattr(metrics, 'get_timings'))


class TestEngineStateConsistency(unittest.TestCase):
    """Test engine state consistency under various conditions."""

    def setUp(self):
        """Set up test engine."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = os.path.join(self.temp_dir, "test_state")
        
        scheduler = Scheduler()
        executor = ExecutorRouter()
        state_store = StateStore(self.state_path)
        shutdown_coordinator = ShutdownCoordinator()
        
        self.engine = Engine(
            scheduler=scheduler,
            executor=executor,
            state_store=state_store,
            shutdown_coordinator=shutdown_coordinator
        )

    def tearDown(self):
        """Clean up test files."""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_duplicate_job_ids_handled(self):
        """Test behavior with duplicate job IDs."""
        job1 = Job(
            job_id="duplicate",
            priority=5,
            payload={"version": 1},
            execution_mode="thread"
        )
        
        job2 = Job(
            job_id="duplicate",
            priority=8,
            payload={"version": 2},
            execution_mode="thread"
        )
        
        self.engine.submit_job(job1)
        
        # Second submission with same ID
        # (Behavior depends on implementation - document it)
        # For now, both will be queued as scheduler uses job objects
        self.engine.submit_job(job2)
        
        self.assertEqual(self.engine._scheduler.size(), 2)


if __name__ == "__main__":
    unittest.main()
